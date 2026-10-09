import datetime as dt

import pytest

from backend.app.config import HISTORY_WEEKS

VERDICTS = {"sell_now", "sell_elsewhere", "store", "split"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_root_redirects_to_docs(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/docs"


def test_meta_is_labelled_and_complete(meta):
    assert meta["is_synthetic"] is True
    assert meta["unit"] == "40kg"
    crops = {c["id"] for c in meta["crops"]}
    mandis = {m["id"] for m in meta["mandis"]}
    assert meta["series"] and all(s["crop"] in crops and s["mandi"] in mandis for s in meta["series"])


def test_every_series_has_a_latest_forecast(client, meta):
    for s in meta["series"]:
        r = client.get("/api/forecast", params=s)
        assert r.status_code == 200, s
        body = r.json()
        assert body["as_of"] == meta["latest_as_of"]
        assert body["is_synthetic"] is True and body["unit"] == "40kg"
        assert 0 < len(body["history"]) <= HISTORY_WEEKS
        assert body["history"][-1]["price"] == body["price_now"]


# ---------------------------------------------------------- time machine


def test_as_of_between_forecasts_uses_the_earlier_one(client, meta):
    s = meta["series"][0]
    latest = dt.date.fromisoformat(meta["latest_as_of"])
    midweek = latest - dt.timedelta(days=10)  # a Thursday between two weekly forecasts
    body = client.get("/api/forecast", params={**s, "as_of": midweek.isoformat()}).json()
    used = dt.date.fromisoformat(body["as_of"])
    assert used <= midweek
    assert midweek - used < dt.timedelta(days=7)
    assert all(dt.date.fromisoformat(p["date"]) <= used for p in body["history"])


def test_as_of_never_returns_future_data(client, meta):
    s = meta["series"][0]
    for days_back in (0, 3, 50, 400, 1000):
        as_of = dt.date.fromisoformat(meta["latest_as_of"]) - dt.timedelta(days=days_back)
        r = client.get("/api/forecast", params={**s, "as_of": as_of.isoformat()})
        if r.status_code == 404:
            continue
        body = r.json()
        assert dt.date.fromisoformat(body["as_of"]) <= as_of
        assert all(dt.date.fromisoformat(p["date"]) <= as_of for p in body["history"])


def test_as_of_before_any_data_is_404(client, meta):
    s = meta["series"][0]
    r = client.get("/api/forecast", params={**s, "as_of": "2000-01-01"})
    assert r.status_code == 404


def test_advice_respects_as_of(client, meta):
    s = meta["series"][0]
    body = client.post("/api/advice", json={
        **s, "quantity_maund": 10, "storage": "home", "as_of": "2024-03-13",
    }).json()
    assert dt.date.fromisoformat(body["as_of"]) <= dt.date(2024, 3, 13)


# ---------------------------------------------------------- errors


def test_undeclared_series_is_404(client, meta):
    declared = {(s["crop"], s["mandi"]) for s in meta["series"]}
    for c in meta["crops"]:
        for m in meta["mandis"]:
            if (c["id"], m["id"]) not in declared:
                r = client.get("/api/forecast", params={"crop": c["id"], "mandi": m["id"]})
                assert r.status_code == 404


def test_unknown_crop_is_404(client):
    assert client.get("/api/forecast", params={"crop": "banana", "mandi": "vehari"}).status_code == 404
    assert client.get("/api/alerts", params={"crop": "banana"}).status_code == 404


def test_bad_date_is_422(client, meta):
    s = meta["series"][0]
    assert client.get("/api/forecast", params={**s, "as_of": "yesterday"}).status_code == 422


@pytest.mark.parametrize("bad", [
    {"quantity_maund": 0},
    {"quantity_maund": -5},
    {"storage": "fridge"},
    {"lang": "fr"},
    {"spoilage_pct_week": 150},
    {"typo_field": 1},
])
def test_advice_rejects_bad_input(client, meta, bad):
    req = {**meta["series"][0], "quantity_maund": 100, "storage": "home", **bad}
    assert client.post("/api/advice", json=req).status_code == 422


# ---------------------------------------------------------- advice


@pytest.mark.parametrize("storage", ["none", "home", "cold_store", "warehouse"])
@pytest.mark.parametrize("lang", ["ur", "en"])
def test_advice_for_every_series(client, meta, storage, lang):
    for s in meta["series"]:
        r = client.post("/api/advice", json={**s, "quantity_maund": 100, "storage": storage, "lang": lang})
        assert r.status_code == 200, (s, r.text)
        body = r.json()
        assert body["verdict"] in VERDICTS
        assert body["reasons"] and body["risk_line"] and body["verdict_text"]
        assert body["is_synthetic"] is True
        if storage == "none":
            assert body["verdict"] in {"sell_now", "sell_elsewhere"}
            assert not any(a["name"].startswith(("storage", "spoilage", "finance")) for a in body["assumptions"])


def test_advice_text_follows_language(client, meta):
    req = {**meta["series"][0], "quantity_maund": 100, "storage": "none"}
    ur = client.post("/api/advice", json={**req, "lang": "ur"}).json()
    en = client.post("/api/advice", json={**req, "lang": "en"}).json()
    assert any("؀" <= ch <= "ۿ" for ch in ur["verdict_text"])  # Arabic-script block
    assert en["verdict_text"].isascii()


def test_farmer_costs_override_defaults(client, meta):
    req = {
        **meta["series"][0], "quantity_maund": 100, "storage": "home",
        "storage_cost_per_maund_week": 0, "spoilage_pct_week": 0.3,
    }
    body = client.post("/api/advice", json=req).json()
    used = {a["name"]: a for a in body["assumptions"]}
    assert used["storage_cost_per_maund_week"]["value"] == 0
    assert used["storage_cost_per_maund_week"]["source"] == "farmer"
    assert used["spoilage_pct_week"]["source"] == "farmer"
    assert used["finance_cost_pct_month"]["source"] == "default"


def test_rupee_difference_scales_with_quantity(client, meta):
    req = {**meta["series"][0], "storage": "home"}
    small = client.post("/api/advice", json={**req, "quantity_maund": 10}).json()
    big = client.post("/api/advice", json={**req, "quantity_maund": 100}).json()
    assert small["verdict"] == big["verdict"]
    assert abs(big["rupee_difference"] - 10 * small["rupee_difference"]) <= 10


# ---------------------------------------------------------- alerts, replay, backtest


def test_alerts_only_return_active_events(client, meta):
    for c in meta["crops"]:
        body = client.get("/api/alerts", params={"crop": c["id"]}).json()
        on = dt.date.fromisoformat(body["as_of"])
        for e in body["events"]:
            assert dt.date.fromisoformat(e["date"]) <= on <= dt.date.fromisoformat(e["active_until"])
            assert c["id"] in e["crops"]
        assert all(dt.date.fromisoformat(a["date"]) <= on for a in body["alarms"])


def test_every_replay_case_loads_in_both_languages(client, meta):
    assert meta["replay_cases"]
    for ref in meta["replay_cases"]:
        ur = client.get(f"/api/replay/{ref['case_id']}").json()
        en = client.get(f"/api/replay/{ref['case_id']}", params={"lang": "en"}).json()
        assert ur["title"] == ref["title_ur"] and en["title"] == ref["title_en"]
        assert ur["steps"] and ur["is_synthetic"] is True


def test_unknown_replay_case_is_404(client):
    assert client.get("/api/replay/nope").status_code == 404


def test_backtest_reports_unmeasured_metrics_as_null(client):
    body = client.get("/api/backtest").json()
    assert body["is_synthetic"] is True
    assert all(row["mase"] is None for row in body["metrics"])


# ---------------------------------------------------------- whatsapp


def test_whatsapp_webhook_is_mounted_and_refuses_unsigned(client):
    # The Meta webhook lives in backend/app/channels (tested there). Unsigned posts never get through.
    assert client.post("/webhooks/whatsapp", content=b"{}").status_code in (403, 503)
    assert client.post("/whatsapp", data={"Body": "x"}).status_code == 404   # the Twilio placeholder is gone
