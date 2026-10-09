"""Channel conversation state in SQLite (task A11, phase 2)."""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from backend.app import db
from backend.app.channels import conversation as conv
from backend.app.channels.conversation import State

NOW = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)
A, B = "+92 300 1234567", "923009999999"
WHEAT_DRAFT = {"step": "quantity", "pending": "advice", "draft_crop": "Wheat", "draft_mandi": "Vehari"}


@pytest.fixture(autouse=True)
def fresh_db():
    db.reset()
    yield
    db.reset()


def test_save_and_get_back_with_expiry():
    db.save_conversation("whatsapp", A, WHEAT_DRAFT, minutes=30, at=NOW)
    row = db.get_conversation("whatsapp", A)
    assert {k: row[k] for k in WHEAT_DRAFT} == WHEAT_DRAFT
    assert row["draft_quantity"] is None and row["last_crop"] is None
    assert row["expires_at"] == NOW + timedelta(minutes=30)


def test_phone_formats_are_the_same_farmer():
    db.save_conversation("whatsapp", A, WHEAT_DRAFT, 30, NOW)
    assert db.get_conversation("whatsapp", "923001234567") is not None
    stored = db.connect().execute("SELECT phone FROM conversations").fetchone()["phone"]
    assert stored == "923001234567"   # digits only, as farmers.phone


def test_save_overwrites_the_previous_step():
    db.save_conversation("whatsapp", A, WHEAT_DRAFT, 30, NOW)
    db.save_conversation("whatsapp", A, {"step": "post_advice", "last_crop": "Wheat", "last_mandi": "Vehari",
                                         "last_quantity": 100}, 30, NOW + timedelta(minutes=10))
    row = db.get_conversation("whatsapp", A)
    assert row["step"] == "post_advice" and row["draft_crop"] is None and row["last_quantity"] == 100
    assert row["expires_at"] == NOW + timedelta(minutes=40)   # every save renews the expiry
    assert db.connect().execute("SELECT COUNT(*) FROM conversations").fetchone()[0] == 1


def test_clear_removes_the_session():
    db.save_conversation("sms", A, WHEAT_DRAFT, 30, NOW)
    db.clear_conversation("sms", A)
    assert db.get_conversation("sms", A) is None
    db.clear_conversation("sms", A)   # clearing nothing is fine


def test_expiry_deletes_only_expired_rows():
    db.save_conversation("whatsapp", A, WHEAT_DRAFT, 30, NOW)
    db.save_conversation("whatsapp", B, WHEAT_DRAFT, 30, NOW + timedelta(minutes=20))
    assert db.expire_old_conversations(NOW + timedelta(minutes=29)) == 0
    assert db.expire_old_conversations(NOW + timedelta(minutes=30)) == 1
    assert db.get_conversation("whatsapp", A) is None and db.get_conversation("whatsapp", B) is not None


def test_whatsapp_and_sms_sessions_are_separate():
    db.save_conversation("whatsapp", A, WHEAT_DRAFT, 30, NOW)
    db.save_conversation("sms", A, {"step": "menu"}, 30, NOW)
    assert db.get_conversation("whatsapp", A)["step"] == "quantity"
    assert db.get_conversation("sms", A)["step"] == "menu"
    db.clear_conversation("sms", A)
    assert db.get_conversation("whatsapp", A) is not None


def test_no_cross_farmer_contamination():
    db.save_conversation("whatsapp", A, WHEAT_DRAFT, 30, NOW)
    assert db.get_conversation("whatsapp", B) is None
    db.save_conversation("whatsapp", B, {"step": "crop", "pending": "compare"}, 30, NOW)
    assert db.get_conversation("whatsapp", A)["draft_crop"] == "Wheat"
    assert db.get_conversation("whatsapp", B)["draft_crop"] is None


@pytest.mark.parametrize("channel, phone", [("web", A), ("telegram", A), ("sms", "no digits")])
def test_bad_channel_or_phone_is_refused(channel, phone):
    with pytest.raises(ValueError):
        db.save_conversation(channel, phone, WHEAT_DRAFT, 30, NOW)


def test_no_message_text_column():
    columns = {r["name"] for r in db.connect().execute("PRAGMA table_info(conversations)")}
    assert not columns & {"text", "content", "body", "message", "message_text"}


def test_sessions_survive_a_restart(tmp_path):
    path = str(tmp_path / "farmsight.sqlite")
    db.reset(path)
    db.save_conversation("sms", A, WHEAT_DRAFT, 30, NOW)
    assert db.first_time_seen("whatsapp", "wamid.1", NOW)
    db.reset(path)   # a new connection to the same file, as after a server restart
    assert db.get_conversation("sms", A)["draft_mandi"] == "Vehari"
    assert not db.first_time_seen("whatsapp", "wamid.1", NOW)


def test_an_old_database_gains_the_new_tables(tmp_path):
    path = tmp_path / "old.sqlite"
    with sqlite3.connect(path) as old:   # a database from before this change: farmers only
        old.execute("CREATE TABLE farmers (id TEXT PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL UNIQUE,"
                    " language TEXT NOT NULL DEFAULT 'ur', district TEXT NOT NULL, land_area_acres REAL,"
                    " arhti_commission_pct REAL, alerts_enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL)")
    old.close()
    db.reset(str(path))
    db.save_conversation("whatsapp", A, WHEAT_DRAFT, 30, NOW)
    assert db.get_conversation("whatsapp", A) is not None
    db.reset(str(path))   # initialising twice is harmless
    assert db.get_conversation("whatsapp", A) is not None


def test_seen_message_ids_dedupe_per_channel_and_are_pruned():
    assert db.first_time_seen("whatsapp", "m1", NOW)
    assert not db.first_time_seen("whatsapp", "m1", NOW)
    assert db.first_time_seen("sms", "m1", NOW)
    db.expire_old_conversations(NOW + timedelta(hours=db.SEEN_KEEP_HOURS, seconds=1))
    assert db.first_time_seen("whatsapp", "m1", NOW)


# ---------------------------------------------------------------- the engine's load and store

class Provider:
    def advice(self, crop_option, mandi, quantity_maund, phone):
        return {"crop_option": crop_option, "mandi": mandi, "quantity_maund": quantity_maund}

    def explain(self, crop_option, mandi, phone):
        return []

    def compare(self, crop_option, mandi, quantity_maund, phone):
        return []


def turn(text, channel="whatsapp", phone=A, at=NOW):
    out = conv.handle(text, conv.load(channel, phone), Provider(), phone=phone, now=at)
    conv.store(channel, phone, out, at)
    return out


def test_a_guided_flow_continues_across_messages_through_the_database():
    turn("0")
    turn("1")
    turn(str(conv.default_options().crops.index("Wheat") + 1))
    assert conv.load("whatsapp", A).step == conv.MANDI
    turn("1")
    out = turn("100")
    assert out.reply.kind == "advice" and conv.load("whatsapp", A).step == conv.POST_ADVICE


def test_store_clears_after_a_completed_alert_change():
    turn("0")
    out = turn("5")
    assert out.persist == "clear" and db.get_conversation("whatsapp", A) is None


def test_expired_session_in_the_database_sends_the_farmer_to_the_menu():
    turn("0")
    turn("1")
    out = turn("1", at=NOW + timedelta(minutes=conv.SESSION_MINUTES + 1))
    assert out.expired and out.reply.kind == "menu" and out.reply.data["note"] == "expired"


def test_a_corrupt_row_counts_as_no_session():
    db.save_conversation("whatsapp", A, {"step": "quantity", "draft_crop": "Bananas"}, 30, NOW)
    assert conv.load("whatsapp", A) is None
    db.connect().execute("UPDATE conversations SET step = 'gone'")
    assert conv.load("whatsapp", A) is None


def test_round_trip_keeps_every_field():
    s = State(step=conv.POST_ADVICE, pending=None, last_crop="IRRI", last_mandi="Vehari", last_quantity=12.5)
    db.save_conversation("sms", B, conv.to_fields(s), 30, NOW)
    back = conv.load("sms", B)
    assert conv.to_fields(back) == conv.to_fields(s) and back.expires_at == NOW + timedelta(minutes=30)
