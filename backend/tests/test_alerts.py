"""Price alerts (C9 on Owner B's alert_check): when they fire, the weekly limit, delivery failures, the route."""

import datetime as dt
import sqlite3

import pytest

from backend.app import alerts, db, services

DAY = dt.date(2025, 3, 24)


@pytest.fixture
def fresh_db():
    db.reset()
    yield
    db.reset()


@pytest.fixture
def market(monkeypatch):
    """Advice and 4-week moves the test controls: {crop_option: [signal, price, change_4w_pct, frozen]}."""
    table = {"Wheat": ["SELL", 3800.0, 0.0, False], "Cotton": ["SELL", 9000.0, 0.0, False]}

    def get_advice(crop_option, mandi, quantity_maund=100, phone=None, as_of=None):
        signal, price, _, _ = table[crop_option]
        return {"crop_option": crop_option, "mandi": mandi, "current_price": price, "predicted_price": price,
                "range": {"low": price * 0.9, "high": price * 1.1}, "signal": signal, "confidence": "MEDIUM",
                "quantity_maund": quantity_maund, "rupee_impact": -100, "interest_cost": 100, "is_stale": False,
                "prices_as_of": (as_of or DAY).isoformat(), "is_synthetic": False}

    def alert_candidate(crop_option, mandi, signal, previous_signal, as_of=None):
        _, _, change, frozen = table[crop_option]
        return {"crop_option": crop_option, "mandi": mandi, "signal": signal, "previous_signal": previous_signal,
                "prices_as_of": "week start, replaced by the advice's date", "change_4w_pct": change,
                "band_q10_pct": -10.0, "band_q90_pct": 10.0, "is_frozen": frozen, "is_stale": False}

    monkeypatch.setattr(services, "get_advice", get_advice)
    monkeypatch.setattr(alerts.engine_inputs, "alert_candidate", alert_candidate)
    return table


class Outbox:
    def __init__(self, ok=True):
        self.ok, self.sent = ok, []

    def __call__(self, phone, text, summary):
        self.sent.append((phone, text, summary))
        return self.ok


def later(days):
    return DAY + dt.timedelta(days=days)


def test_first_check_is_silent_then_a_signal_change_alerts(fresh_db, market):
    out = Outbox()
    [r] = alerts.run(send=out, as_of=DAY)
    assert r["skipped"] == "no_event" and out.sent == []
    market["Wheat"][0] = "WAIT"
    [r] = alerts.run(send=out, as_of=later(1))
    assert r["status"] == "SENT" and [(i["crop"], i["kind"]) for i in r["items"]] == [("wheat", "SELL_SIGNAL")]
    phone, text, summary = out.sent[0]
    assert phone == "920000000001" and alerts.HEADER in text and alerts.SIGNAL_CHANGED in text
    assert "\n" not in summary and "Rs 3,800" in summary


def test_a_move_outside_the_band_alerts_but_not_when_frozen(fresh_db, market):
    out = Outbox()
    market["Cotton"][2:] = [-15.0, True]    # outside the ±10% band, but a frozen AMIS stretch
    [r] = alerts.run(send=out, as_of=DAY)
    assert r["skipped"] == "no_event"
    market["Cotton"][3] = False
    [r] = alerts.run(send=out, as_of=later(1))
    assert [(i["crop"], i["kind"], i["change_4w_pct"]) for i in r["items"]] == [("cotton", "PRICE_SPIKE", -15.0)]
    assert "15% گرا" in out.sent[0][1]


def test_one_alert_a_week_and_the_rest_are_suppressed(fresh_db, market):
    out = Outbox()
    alerts.run(send=out, as_of=DAY)
    market["Wheat"][0], market["Cotton"][2] = "WAIT", 20.0
    [r] = alerts.run(send=out, as_of=later(1))
    assert r["items"][0]["kind"] == "SELL_SIGNAL" and r["suppressed"] == 1   # signal changes outrank price moves
    [r] = alerts.run(send=out, as_of=later(6))
    assert r["skipped"] == "weekly_limit" and len(out.sent) == 1
    [r] = alerts.run(send=out, as_of=later(8))
    assert [(i["crop"], i["kind"]) for i in r["items"]] == [("cotton", "PRICE_SPIKE")]


def test_failed_delivery_is_recorded_and_sms_is_the_fallback(fresh_db, market):
    alerts.run(send=Outbox(), as_of=DAY)
    market["Wheat"][0] = "WAIT"
    [r] = alerts.run(send=Outbox(ok=False), as_of=later(1))
    assert r["status"] == "FAILED"
    market["Wheat"][0] = "SELL"
    sms = Outbox()
    [r] = alerts.run(send=Outbox(ok=False), sms=sms, as_of=later(2))   # a failure does not use up the week
    assert r["status"] == "SENT" and r["channel"] == "sms" and len(sms.sent) == 1


def test_dry_run_writes_nothing_and_alerts_off_means_no_check(fresh_db, market):
    alerts.run(send=Outbox(), as_of=DAY)
    market["Wheat"][0] = "WAIT"
    out = Outbox()
    [r] = alerts.run(send=out, as_of=later(1), dry_run=True)
    assert r["message"] and "status" not in r and out.sent == []
    assert db.last_sent_date(db.get_farmer_by_phone("+920000000001")["id"]) is None
    db.set_alerts_by_phone("+920000000001", False)
    assert alerts.run(send=out, as_of=later(1)) == []


def test_real_data_replays_the_april_2025_wheat_drop(fresh_db):
    [r] = alerts.run(send=Outbox(), as_of=dt.date(2025, 4, 21), dry_run=True)
    [item] = r["items"]
    assert (item["crop"], item["kind"]) == ("wheat", "PRICE_SPIKE") and item["change_4w_pct"] < -15
    assert item["prices_as_of"] <= "2025-04-21"


def test_candidate_uses_only_weeks_up_to_as_of_and_the_advice_date():
    day = dt.date(2025, 4, 21)
    advice = services.get_advice("Wheat", "BahawalPur", 100, as_of=day)
    c = alerts._candidate(advice, "SELL", day)
    assert c["change_4w_pct"] == pytest.approx(-19.72, abs=0.01)
    # The alert carries the same price date and staleness the farmer sees in the app (H-C21, H-B16).
    assert (c["prices_as_of"], c["is_stale"]) == (advice["prices_as_of"], advice["is_stale"])


def test_a_57_day_old_price_is_stale_in_alerts_as_on_home():
    """The engine's inputs round to whole weeks; the app's one rule is more than 56 days (H-B16)."""
    day = dt.date(2026, 3, 16)   # Rahim Yar Khan cotton: no mandi price from March, last one 57-62 days back
    advice = services.get_advice("Cotton", "RahimYarKhan", 100, as_of=day)
    age = (day - dt.date.fromisoformat(advice["prices_as_of"])).days
    assert 56 < age <= 62 and advice["is_stale"]
    assert alerts._candidate(advice, None, day)["is_stale"] is True


def test_crop_plan_staleness_matches_home():
    day = dt.date(2026, 3, 16)
    items = {i["crop_option"]: i for i in services.crop_plan("RahimYarKhan", 10, day)["items"]}
    assert items["Cotton"]["is_stale"] == services.get_advice("Cotton", "RahimYarKhan", 100, as_of=day)["is_stale"]


def test_old_databases_gain_the_new_alert_columns(tmp_path):
    path = tmp_path / "old.sqlite"
    with sqlite3.connect(path) as old:
        old.execute("CREATE TABLE alerts (id TEXT PRIMARY KEY, farmer_id TEXT NOT NULL, crop TEXT NOT NULL,"
                    " type TEXT NOT NULL, status TEXT NOT NULL, message_text TEXT NOT NULL, created_at TEXT NOT NULL)")
    try:
        conn = db.reset(str(path))
        columns = {r["name"] for r in conn.execute("PRAGMA table_info(alerts)")}
        assert {"mandi", "signal", "price", "for_date"} <= columns
    finally:
        db.reset()


def test_route_needs_the_admin_token(client, monkeypatch, fresh_db):
    url = "/api/alerts/run?as_of=2025-04-21&dry_run=true"
    monkeypatch.delenv("FS_ADMIN_TOKEN", raising=False)
    assert client.post(url).status_code == 503
    monkeypatch.setenv("FS_ADMIN_TOKEN", "letmein")
    assert client.post(url).status_code == 401
    assert client.post(url, headers={"X-Admin-Token": "nope"}).status_code == 401
    r = client.post(url, headers={"X-Admin-Token": "letmein"})
    assert r.status_code == 200
    body = r.json()
    assert body["dry_run"] is True and body["sent"] == 0 and body["farmers_checked"] == 1
    assert "phone" not in str(body) and body["results"][0]["items"][0]["kind"] == "PRICE_SPIKE"
