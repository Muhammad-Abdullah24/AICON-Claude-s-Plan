"""Price alerts (C9): when they fire, the one-a-week limit, delivery failures, and the on-demand route."""

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
def fake_advice(monkeypatch):
    """Advice the test controls: {crop_option: (signal, price)}."""
    table = {"Wheat": ("SELL", 3800.0), "Cotton": ("WAIT", 9000.0)}

    def get_advice(crop_option, mandi, quantity_maund=100, phone=None, as_of=None):
        signal, price = table[crop_option]
        return {"crop_option": crop_option, "mandi": mandi, "current_price": price, "predicted_price": price,
                "range": {"low": price * 0.95, "high": price * 1.05}, "signal": signal, "confidence": "MEDIUM",
                "quantity_maund": quantity_maund, "rupee_impact": -100, "interest_cost": 100,
                "prices_as_of": (as_of or DAY).isoformat(), "is_synthetic": False}

    monkeypatch.setattr(services, "get_advice", get_advice)
    return table


class Outbox:
    def __init__(self, ok=True):
        self.ok, self.sent = ok, []

    def __call__(self, phone, text, summary):
        self.sent.append((phone, text, summary))
        return self.ok


def test_first_check_sends_one_message_with_every_crop(fresh_db, fake_advice):
    out = Outbox()
    [r] = alerts.run(send=out, as_of=DAY)
    assert r["status"] == "SENT" and r["channel"] == "whatsapp"
    assert [i["kind"] for i in r["items"]] == ["FIRST", "FIRST"]
    assert len(out.sent) == 1
    phone, text, summary = out.sent[0]
    assert phone == "920000000001" and alerts.HEADER in text and "گندم" in text and "کپاس" in text
    assert "\n" not in summary and "Rs 3,800" in summary


def test_at_most_one_message_a_week(fresh_db, fake_advice):
    out = Outbox()
    alerts.run(send=out, as_of=DAY)
    fake_advice["Wheat"] = ("WAIT", 4200.0)
    [r] = alerts.run(send=out, as_of=DAY + dt.timedelta(days=6))
    assert r["skipped"] == "weekly_limit" and len(out.sent) == 1
    [r] = alerts.run(send=out, as_of=DAY + dt.timedelta(days=7))
    assert [(i["crop"], i["kind"]) for i in r["items"]] == [("wheat", "SIGNAL_CHANGE")]


def test_no_alert_without_a_change_and_big_moves_alert(fresh_db, fake_advice):
    out = Outbox()
    alerts.run(send=out, as_of=DAY)
    fake_advice["Cotton"] = ("WAIT", 9000.0 * 1.05)   # under the 10% move
    [r] = alerts.run(send=out, as_of=DAY + dt.timedelta(days=7))
    assert r["skipped"] == "no_change" and len(out.sent) == 1
    fake_advice["Cotton"] = ("WAIT", 9000.0 * 1.12)
    [r] = alerts.run(send=out, as_of=DAY + dt.timedelta(days=14))
    assert [i["kind"] for i in r["items"]] == ["PRICE_MOVE"]


def test_failed_delivery_is_recorded_and_sms_is_the_fallback(fresh_db, fake_advice):
    [r] = alerts.run(send=Outbox(ok=False), as_of=DAY)
    assert r["status"] == "FAILED"
    # A failed alert still counts as raised (no repeat of the same news), but not against the weekly limit.
    [r] = alerts.run(send=Outbox(ok=False), sms=Outbox(), as_of=DAY + dt.timedelta(days=1))
    assert r["skipped"] == "no_change"
    fake_advice["Wheat"] = ("WAIT", 4000.0)
    sms = Outbox()
    [r] = alerts.run(send=Outbox(ok=False), sms=sms, as_of=DAY + dt.timedelta(days=2))
    assert r["status"] == "SENT" and r["channel"] == "sms" and len(sms.sent) == 1


def test_dry_run_writes_nothing_and_alerts_off_means_no_check(fresh_db, fake_advice):
    out = Outbox()
    [r] = alerts.run(send=out, as_of=DAY, dry_run=True)
    assert r["message"] and "status" not in r and out.sent == []
    assert db.last_sent_date(db.get_farmer_by_phone("+920000000001")["id"]) is None
    db.set_alerts_by_phone("+920000000001", False)
    assert alerts.run(send=out, as_of=DAY) == []


def test_real_data_alert_for_the_demo_farmer(fresh_db):
    [r] = alerts.run(send=Outbox(), as_of=DAY, dry_run=True)
    assert {i["crop"] for i in r["items"]} == {"wheat", "cotton"}
    assert all(i["advice"]["prices_as_of"] <= DAY.isoformat() for i in r["items"])


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
    url = "/api/alerts/run?as_of=2025-03-24&dry_run=true"
    monkeypatch.delenv("FS_ADMIN_TOKEN", raising=False)
    assert client.post(url).status_code == 503
    monkeypatch.setenv("FS_ADMIN_TOKEN", "letmein")
    assert client.post(url).status_code == 401
    assert client.post(url, headers={"X-Admin-Token": "nope"}).status_code == 401
    r = client.post(url, headers={"X-Admin-Token": "letmein"})
    assert r.status_code == 200
    body = r.json()
    assert body["dry_run"] is True and body["sent"] == 0 and body["farmers_checked"] == 1
    assert "phone" not in str(body) and body["results"][0]["message"]
