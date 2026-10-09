"""The API contract (docs/BLUEPRINT.md section 12), end to end on the real data files."""

import datetime as dt

import pytest

CROPS = ["wheat", "cotton", "irri", "super_basmati"]
MANDIS = ["bahawalpur", "vehari", "rahim_yar_khan"]


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_root_redirects_to_docs(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/docs"


# ---------------------------------------------------------------- meta

def test_meta_is_labelled_and_complete(meta):
    assert meta["is_synthetic"] is False and meta["data_source"] == "amis" and meta["unit"] == "40kg"
    assert [c["id"] for c in meta["crops"]] and {c["id"] for c in meta["crops"]} == set(CROPS)
    assert {m["id"] for m in meta["mandis"]} == set(MANDIS)
    pairs = {(s["crop"], s["mandi"]) for s in meta["series"]}
    assert len(pairs) == 11 and ("irri", "rahim_yar_khan") not in pairs
    assert all(c["name_ur"] and c["name_en"] for c in meta["crops"] + meta["mandis"])


# ---------------------------------------------------------------- every series

def test_every_series_forecasts_and_advises(client, meta):
    for s in meta["series"]:
        f = client.get("/api/forecast", params={"crop": s["crop"], "mandi": s["mandi"]})
        assert f.status_code == 200, s
        body = f.json()
        assert body["prices_as_of"] == s["prices_as_of"] and body["current_price"] == s["latest_price"]
        assert body["range"]["low"] <= body["predicted_price"] <= body["range"]["high"]
        assert 0 < len(body["history"]) <= 52
        assert all(p["date"] <= body["prices_as_of"] for p in body["history"])
        a = client.get("/api/advice", params={"crop": s["crop"], "mandi": s["mandi"]}).json()
        assert a["signal"] in ("SELL", "WAIT") and a["rupee_impact"] == a["gross_gain"] - a["interest_cost"]
        if s["is_stale"]:
            assert a["confidence"] == "LOW"


def test_missing_series_is_404_with_a_reason(client):
    r = client.get("/api/advice", params={"crop": "irri", "mandi": "rahim_yar_khan"})
    assert r.status_code == 404 and "IRRI" in r.json()["detail"]


def test_unknown_ids_are_422(client):
    assert client.get("/api/forecast", params={"crop": "potato", "mandi": "vehari"}).status_code == 422
    assert client.get("/api/forecast", params={"crop": "wheat", "mandi": "lahore"}).status_code == 422


# ---------------------------------------------------------------- time machine

@pytest.mark.parametrize("as_of", ["2025-03-24", "2025-08-04", "2024-04-15"])
def test_as_of_never_uses_later_data(client, as_of):
    q = {"crop": "wheat", "mandi": "bahawalpur", "as_of": as_of}
    f = client.get("/api/forecast", params=q).json()
    assert f["prices_as_of"] <= as_of and all(p["date"] <= as_of for p in f["history"])
    h = client.get("/api/history", params=q).json()
    assert all(p["date"] <= as_of for p in h["weekly"])
    c = client.get("/api/compare-mandis", params=q).json()
    assert all(r["prices_as_of"] <= as_of for r in c["rows"] if r["has_data"])


def test_as_of_before_any_data_is_404(client):
    r = client.get("/api/forecast", params={"crop": "wheat", "mandi": "bahawalpur", "as_of": "2000-01-01"})
    assert r.status_code == 404


# ---------------------------------------------------------------- advice details

def test_advice_scales_with_quantity(client):
    q = {"crop": "wheat", "mandi": "bahawalpur"}
    one = client.get("/api/advice", params={**q, "quantity_maund": 1}).json()
    hundred = client.get("/api/advice", params={**q, "quantity_maund": 100}).json()
    assert abs(hundred["interest_cost"] - 100 * one["interest_cost"]) <= 100


def test_guest_gets_the_100_maund_example(client):
    assert client.get("/api/advice", params={"crop": "cotton", "mandi": "vehari"}).json()["quantity_maund"] == 100


def test_explain_gives_reasons_in_both_languages(client):
    e = client.get("/api/explain", params={"crop": "wheat", "mandi": "bahawalpur"}).json()
    assert e["source"] in ("facts", "shap") and e["reasons"]
    assert all(r["text_ur"] and r["text_en"] for r in e["reasons"])


def test_compare_best_first_and_flags_missing(client):
    c = client.get("/api/compare-mandis", params={"crop": "irri", "mandi": "vehari"}).json()
    priced = [r for r in c["rows"] if r["has_data"]]
    assert [r["net_price"] for r in priced] == sorted((r["net_price"] for r in priced), reverse=True)
    assert {"mandi": "rahim_yar_khan", "has_data": False}.items() <= next(
        r for r in c["rows"] if r["mandi"] == "rahim_yar_khan").items()
    assert c["transport_is_estimate"] is True


def test_offer_check(client):
    base = {"crop": "wheat", "mandi": "bahawalpur"}
    fair = client.post("/api/offer-check", json={**base, "offer_price": 1}).json()
    assert fair["verdict"] == "below" and fair["difference_total"] < 0
    high = client.post("/api/offer-check", json={**base, "offer_price": 999_999}).json()
    assert high["verdict"] == "above"
    assert client.post("/api/offer-check", json={**base, "offer_price": -5}).status_code == 422


def test_margin_with_support_price_for_wheat_only(client):
    w = client.get("/api/margin", params={"crop": "wheat", "price": 3820, "arhti_pct": 2}).json()
    assert w["support_price"] is not None and w["arhti_amount"] == pytest.approx(76.4)
    assert w["profit"] == pytest.approx(3820 - w["production_cost"] - 76.4)
    assert client.get("/api/margin", params={"crop": "cotton", "price": 9000}).json()["support_price"] is None


def test_wheat_carries_the_models_direction_call_and_shap_reasons(client):
    q = {"crop": "wheat", "mandi": "bahawalpur"}
    f = client.get("/api/forecast", params=q).json()
    assert f["direction"]["call"] in ("UP", "DOWN") and f["model"] == "baseline_persistence_band"
    e = client.get("/api/explain", params=q).json()
    assert e["source"] == "shap" and e["direction"] == f["direction"] and len(e["reasons"]) >= 2
    assert client.get("/api/forecast", params={"crop": "cotton", "mandi": "bahawalpur"}).json()["direction"] is None
    # The time machine reaches the model too: the 2025 crash and rally weeks get the calls that came true.
    calls = [client.get("/api/forecast", params={**q, "as_of": d}).json()["direction"]["call"]
             for d in ("2025-03-24", "2025-08-04")]
    assert calls == ["DOWN", "UP"]


def test_history_shows_gaps_and_frozen_weeks(client):
    h = client.get("/api/history", params={"crop": "wheat", "mandi": "bahawalpur", "as_of": "2026-10-09"}).json()
    assert len(h["weekly"]) == 52 and any(p["frozen"] for p in h["weekly"])   # the 2026 summer freeze
    assert all(p["price"] is None or p["price"] > 0 for p in h["weekly"])


def test_crop_plan_ranks_by_profit(client):
    p = client.get("/api/crop-plan", params={"mandi": "rahim_yar_khan", "land_area_acres": 5}).json()
    profits = [i["expected_profit"] for i in p["items"]]
    assert profits == sorted(profits, reverse=True)
    assert [i["rank"] for i in p["items"]] == list(range(1, len(profits) + 1))
    assert "irri" in p["not_available"] and p["is_estimate"] is True
    for i in p["items"]:
        assert i["harvest_price_low"] <= i["harvest_price_estimate"] <= i["harvest_price_high"]
        # The engine rounds profit per acre to whole rupees, so the total can differ by up to half a rupee an acre.
        assert i["expected_profit"] == pytest.approx(i["profit_per_acre"] * 5, abs=0.5 * 5)
        assert i["profit_per_acre_low"] <= i["profit_per_acre"] <= i["profit_per_acre_high"]


def test_history_has_twelve_seasonal_months(client):
    h = client.get("/api/history", params={"crop": "cotton", "mandi": "vehari"}).json()
    assert [s["month"] for s in h["seasonal"]] == list(range(1, 13)) and h["weekly"]


def test_weather_falls_back_to_offline_when_live_is_down(client, monkeypatch):
    from backend.app import weather

    def down(lat, lon, timeout=8.0):
        raise TimeoutError

    monkeypatch.setattr(weather, "fetch_open_meteo", down)
    monkeypatch.setattr(weather, "_cache", {})
    w = client.get("/api/weather", params={"mandi": "vehari"}).json()["weather"]
    assert w["cached"] is True and w["source"] == "offline file" and "Open-Meteo" in w["attribution"]


# ---------------------------------------------------------------- farmers and login

def test_login_and_profile(client):
    t = client.post("/api/auth/login", json={"phone": "+92 000 0000001"}).json()
    headers = {"Authorization": f"Bearer {t['token']}"}
    me = client.get("/api/farmers/me", headers=headers).json()
    assert me["name"] == "Ahmed" and me["district"] == "bahawalpur"
    # The profile's quantity is used when none is given.
    a = client.get("/api/advice", params={"crop": "cotton", "mandi": "bahawalpur"}, headers=headers).json()
    assert a["quantity_maund"] == 60
    updated = client.put("/api/farmers/me", json={"arhti_commission_pct": 3}, headers=headers).json()
    assert updated["arhti_commission_pct"] == 3


def test_register_then_duplicate_is_409(client):
    body = {"name": "Test", "phone": "+920000000777", "district": "vehari",
            "crops": [{"crop": "irri", "preferred_mandi": "vehari", "harvest_quantity_maund": 40}]}
    first = client.post("/api/farmers", json=body)
    assert first.status_code == 201 and first.json()["token"]
    assert client.post("/api/farmers", json=body).status_code == 409


def test_auth_failures(client):
    assert client.get("/api/farmers/me").status_code == 401
    assert client.get("/api/farmers/me", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"phone": "+920000009999"}).status_code == 404


# ---------------------------------------------------------------- channels are mounted

def test_whatsapp_webhook_is_mounted_and_refuses_unsigned(client):
    assert client.post("/webhooks/whatsapp", content=b"{}").status_code in (403, 503)
    assert client.post("/whatsapp", data={"Body": "x"}).status_code == 404   # the Twilio placeholder is gone


def test_chat_route_uses_api_ids(client):
    from backend.app.chat import llm

    client.app.dependency_overrides[llm.get_llm] = lambda: type("L", (), {"generate": lambda s, a, b: "Rs 1"})()
    try:
        r = client.post("/api/chat", json={"question": "rate?", "crop": "super_basmati", "mandi": "vehari"})
    finally:
        client.app.dependency_overrides.clear()
    assert r.status_code == 200 and r.json()["crop"] == "super_basmati" and r.json()["mandi"] == "vehari"
    assert client.post("/api/chat", json={"question": "x", "crop": "Wheat"}).status_code == 422


def test_dates_in_responses_are_iso(client):
    f = client.get("/api/forecast", params={"crop": "wheat", "mandi": "vehari"}).json()
    dt.date.fromisoformat(f["prices_as_of"])
