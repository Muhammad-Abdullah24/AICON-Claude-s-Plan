"""SQLite store for runtime records (task C2, blueprint section 9): farmers, their crops, recommendations,
alerts, WhatsApp/SMS messages and chat messages. Standard library only.

The offline tables (prices, costs, transport, support prices, seasonal tables) are read-only CSVs under
data/processed/ and are served by backend/app/services.py, not copied in here.

FS_DB_PATH sets the file (default var/farmsight.sqlite, ignored by git). ":memory:" works for tests.
Phone numbers are stored as digits only, so "+92 300 1234567" and "923001234567" are the same farmer.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "var" / "farmsight.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS farmers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE,
    language TEXT NOT NULL DEFAULT 'ur',
    district TEXT NOT NULL,
    land_area_acres REAL,
    arhti_commission_pct REAL,
    alerts_enabled INTEGER NOT NULL DEFAULT 0,   -- opt-in: off until the farmer turns alerts on
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS farmer_crops (
    farmer_id TEXT NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
    crop TEXT NOT NULL,
    preferred_mandi TEXT NOT NULL,
    harvest_quantity_maund REAL NOT NULL,
    PRIMARY KEY (farmer_id, crop)
);
CREATE TABLE IF NOT EXISTS recommendations (
    id TEXT PRIMARY KEY,
    farmer_id TEXT REFERENCES farmers(id) ON DELETE SET NULL,
    crop TEXT NOT NULL,
    mandi TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    farmer_id TEXT NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
    crop TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    message_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    mandi TEXT,
    signal TEXT,
    price REAL,
    for_date TEXT
);
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    farmer_id TEXT REFERENCES farmers(id) ON DELETE SET NULL,
    alert_id TEXT REFERENCES alerts(id) ON DELETE SET NULL,
    channel TEXT NOT NULL,
    direction TEXT NOT NULL,
    content TEXT,
    status TEXT,
    sent_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    farmer_id TEXT REFERENCES farmers(id) ON DELETE SET NULL,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    used_fallback INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
-- The numbered-menu step a WhatsApp or SMS farmer is on (backend/app/channels/conversation.py). Codes and
-- numbers only, never message text; a row lives SESSION_MINUTES and expired rows are deleted.
CREATE TABLE IF NOT EXISTS conversations (
    channel TEXT NOT NULL CHECK (channel IN ('whatsapp', 'sms')),
    phone TEXT NOT NULL,
    step TEXT NOT NULL,
    pending TEXT,
    draft_crop TEXT,
    draft_mandi TEXT,
    draft_quantity REAL,
    last_crop TEXT,
    last_mandi TEXT,
    last_quantity REAL,
    expires_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (channel, phone)
);
-- Incoming message ids already handled, so a provider's retry is not answered twice, even after a restart.
CREATE TABLE IF NOT EXISTS seen_messages (
    channel TEXT NOT NULL,
    message_id TEXT NOT NULL,
    seen_at TEXT NOT NULL,
    PRIMARY KEY (channel, message_id)
);
"""

# The demo profile from the blueprint's demo script. Invented, not a real person. Alerts are opt-in for every
# farmer; Ahmed is seeded with them on, explicitly, so the alert demo (docs/DEMO.md section 3) works.
DEMO_FARMER = {
    "name": "Ahmed", "phone": "+920000000001", "language": "ur", "district": "bahawalpur",
    "land_area_acres": 12.5, "arhti_commission_pct": None, "alerts_enabled": True,
    "crops": [
        {"crop": "wheat", "preferred_mandi": "bahawalpur", "harvest_quantity_maund": 100},
        {"crop": "cotton", "preferred_mandi": "bahawalpur", "harvest_quantity_maund": 60},
    ],
}

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def digits(phone: str) -> str:
    return re.sub(r"\D", "", phone)


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def connect(path: str | None = None) -> sqlite3.Connection:
    """Open (once) and migrate the database, then seed the demo farmer."""
    global _conn
    with _lock:
        if _conn is None:
            target = path or os.environ.get("FS_DB_PATH") or str(DEFAULT_PATH)
            if target != ":memory:":
                Path(target).parent.mkdir(parents=True, exist_ok=True)
            _conn = sqlite3.connect(target, check_same_thread=False)
            _conn.row_factory = sqlite3.Row
            _conn.execute("PRAGMA foreign_keys = ON")
            _conn.executescript(SCHEMA)
            _migrate(_conn)
            if get_farmer_by_phone(DEMO_FARMER["phone"], _conn) is None:
                create_farmer(DEMO_FARMER, _conn)
        return _conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Columns added after the first release, for databases created before them."""
    have = {r["name"] for r in conn.execute("PRAGMA table_info(alerts)")}
    for column, kind in (("mandi", "TEXT"), ("signal", "TEXT"), ("price", "REAL"), ("for_date", "TEXT")):
        if column not in have:
            conn.execute(f"ALTER TABLE alerts ADD COLUMN {column} {kind}")  # noqa: S608 (fixed names above)


def reset(path: str = ":memory:") -> sqlite3.Connection:
    """A fresh database (tests)."""
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
        _conn = None
    return connect(path)


# ---------------------------------------------------------------- farmers

def _farmer(row: sqlite3.Row, conn: sqlite3.Connection) -> dict:
    crops = [dict(r) for r in conn.execute(
        "SELECT crop, preferred_mandi, harvest_quantity_maund FROM farmer_crops WHERE farmer_id = ? ORDER BY rowid",
        (row["id"],))]
    return {**dict(row), "alerts_enabled": bool(row["alerts_enabled"]), "crops": crops}


def get_farmer(farmer_id: str, conn: sqlite3.Connection | None = None) -> dict | None:
    conn = conn or connect()
    row = conn.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,)).fetchone()
    return _farmer(row, conn) if row else None


def get_farmer_by_phone(phone: str, conn: sqlite3.Connection | None = None) -> dict | None:
    conn = conn or connect()
    row = conn.execute("SELECT * FROM farmers WHERE phone = ?", (digits(phone),)).fetchone()
    return _farmer(row, conn) if row else None


def _write_crops(conn: sqlite3.Connection, farmer_id: str, crops: list[dict]) -> None:
    conn.execute("DELETE FROM farmer_crops WHERE farmer_id = ?", (farmer_id,))
    conn.executemany(
        "INSERT INTO farmer_crops (farmer_id, crop, preferred_mandi, harvest_quantity_maund) VALUES (?, ?, ?, ?)",
        [(farmer_id, c["crop"], c["preferred_mandi"], c["harvest_quantity_maund"]) for c in crops])


def create_farmer(f: dict, conn: sqlite3.Connection | None = None) -> dict:
    """Raises ValueError if the phone number is already registered."""
    conn = conn or connect()
    farmer_id = str(uuid.uuid4())
    try:
        with conn:
            conn.execute(
                "INSERT INTO farmers (id, name, phone, language, district, land_area_acres, arhti_commission_pct,"
                " alerts_enabled, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (farmer_id, f["name"], digits(f["phone"]), f.get("language", "ur"), f["district"],
                 f.get("land_area_acres"), f.get("arhti_commission_pct"), int(f.get("alerts_enabled", False)), now()))
            _write_crops(conn, farmer_id, f.get("crops", []))
    except sqlite3.IntegrityError as e:
        raise ValueError("phone already registered") from e
    return get_farmer(farmer_id, conn)


def update_farmer(farmer_id: str, changes: dict, conn: sqlite3.Connection | None = None) -> dict | None:
    conn = conn or connect()
    fields = {k: v for k, v in changes.items() if k in
              ("name", "language", "district", "land_area_acres", "arhti_commission_pct", "alerts_enabled")}
    with conn:
        if fields:
            if "alerts_enabled" in fields:
                fields["alerts_enabled"] = int(fields["alerts_enabled"])
            sets = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(f"UPDATE farmers SET {sets} WHERE id = ?", (*fields.values(), farmer_id))  # noqa: S608 (keys are whitelisted above)
        if changes.get("crops") is not None:
            _write_crops(conn, farmer_id, changes["crops"])
    return get_farmer(farmer_id, conn)


def set_alerts_by_phone(phone: str, enabled: bool) -> bool:
    """Returns False if no farmer has this phone number."""
    conn = connect()
    with conn:
        cur = conn.execute("UPDATE farmers SET alerts_enabled = ? WHERE phone = ?", (int(enabled), digits(phone)))
    return cur.rowcount > 0


def alerts_enabled_by_phone(phone: str) -> bool:
    """False for a number that is not registered: nobody gets alerts without turning them on."""
    f = get_farmer_by_phone(phone)
    return False if f is None else f["alerts_enabled"]


def list_alert_farmers() -> list[dict]:
    conn = connect()
    return [_farmer(r, conn) for r in conn.execute("SELECT * FROM farmers WHERE alerts_enabled = 1")]


# ---------------------------------------------------------------- logs

def log_recommendation(farmer_id: str | None, crop: str, mandi: str, payload: dict) -> None:
    conn = connect()
    with conn:
        conn.execute("INSERT INTO recommendations VALUES (?, ?, ?, ?, ?, ?)",
                     (str(uuid.uuid4()), farmer_id, crop, mandi, json.dumps(payload, ensure_ascii=False), now()))


def log_chat(farmer_id: str | None, role: str, text: str, used_fallback: bool = False) -> None:
    conn = connect()
    with conn:
        conn.execute("INSERT INTO chat_messages VALUES (?, ?, ?, ?, ?, ?)",
                     (str(uuid.uuid4()), farmer_id, role, text, int(used_fallback), now()))


def last_alert(farmer_id: str, crop: str) -> dict | None:
    """The newest signal the farmer was told for this crop (sent, tried and failed, or the silent first
    BASELINE): what the next check compares with. SUPPRESSED alerts were not told, so they do not count."""
    row = connect().execute(
        "SELECT * FROM alerts WHERE farmer_id = ? AND crop = ? AND status IN ('SENT', 'FAILED', 'BASELINE') "
        "ORDER BY for_date DESC, created_at DESC LIMIT 1", (farmer_id, crop)).fetchone()
    return dict(row) if row else None


def last_sent_date(farmer_id: str) -> str | None:
    """The date (the check's as-of date) of the farmer's newest delivered alert, for the one-a-week limit."""
    row = connect().execute("SELECT MAX(for_date) AS d FROM alerts WHERE farmer_id = ? AND status = 'SENT'",
                            (farmer_id,)).fetchone()
    return row["d"] if row else None


def add_alert(farmer_id: str, crop: str, mandi: str, kind: str, signal: str, price: float, for_date: str,
              status: str, text: str) -> str:
    alert_id = str(uuid.uuid4())
    conn = connect()
    with conn:
        conn.execute("INSERT INTO alerts (id, farmer_id, crop, type, status, message_text, created_at, mandi, signal,"
                     " price, for_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (alert_id, farmer_id, crop, kind, status, text, now(), mandi, signal, price, for_date))
    return alert_id


def log_message(farmer_id: str | None, channel: str, direction: str, content: str, status: str,
                alert_id: str | None = None) -> None:
    conn = connect()
    with conn:
        conn.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (str(uuid.uuid4()), farmer_id, alert_id, channel, direction, content, status, now()))


# ---------------------------------------------------------------- channel conversations (task A11)

CHANNELS = ("whatsapp", "sms")
CONVERSATION_FIELDS = ("step", "pending", "draft_crop", "draft_mandi", "draft_quantity", "last_crop", "last_mandi",
                       "last_quantity")
SEEN_KEEP_HOURS = 24


def _key(channel: str, phone: str) -> tuple[str, str]:
    if channel not in CHANNELS:
        raise ValueError(f"unknown channel {channel!r}")
    number = digits(phone)
    if not number:
        raise ValueError("phone has no digits")
    return channel, number


def _ts(t: datetime) -> str:
    return t.astimezone(UTC).isoformat(timespec="seconds")


def get_conversation(channel: str, phone: str) -> dict | None:
    """The stored session, expired or not (the engine tells the farmer when it expired), or None.
    `expires_at` comes back as a datetime."""
    row = connect().execute("SELECT * FROM conversations WHERE channel = ? AND phone = ?",
                            _key(channel, phone)).fetchone()
    if row is None:
        return None
    out = {k: row[k] for k in CONVERSATION_FIELDS}
    out["expires_at"] = datetime.fromisoformat(row["expires_at"])
    return out


def save_conversation(channel: str, phone: str, fields: dict, minutes: float, at: datetime | None = None) -> None:
    """Insert or replace the session; it expires `minutes` after `at` (default now). Unknown keys are ignored."""
    at = at or datetime.now(UTC)
    values = [fields.get(k) for k in CONVERSATION_FIELDS]
    conn = connect()
    with conn:
        conn.execute(
            f"INSERT OR REPLACE INTO conversations (channel, phone, {', '.join(CONVERSATION_FIELDS)}, expires_at,"  # noqa: S608 (fixed names)
            f" updated_at) VALUES (?, ?, {', '.join('?' * len(CONVERSATION_FIELDS))}, ?, ?)",
            (*_key(channel, phone), *values, _ts(at + timedelta(minutes=minutes)), _ts(at)))


def clear_conversation(channel: str, phone: str) -> None:
    conn = connect()
    with conn:
        conn.execute("DELETE FROM conversations WHERE channel = ? AND phone = ?", _key(channel, phone))


def expire_old_conversations(at: datetime | None = None) -> int:
    """Delete expired sessions and message ids older than SEEN_KEEP_HOURS. Returns how many sessions went."""
    at = at or datetime.now(UTC)
    conn = connect()
    with conn:
        n = conn.execute("DELETE FROM conversations WHERE expires_at <= ?", (_ts(at),)).rowcount
        conn.execute("DELETE FROM seen_messages WHERE seen_at <= ?", (_ts(at - timedelta(hours=SEEN_KEEP_HOURS)),))
    return n


def first_time_seen(channel: str, message_id: str, at: datetime | None = None) -> bool:
    """Record an incoming message id; False if it was already recorded (a provider retry)."""
    conn = connect()
    try:
        with conn:
            conn.execute("INSERT INTO seen_messages VALUES (?, ?, ?)",
                         (channel, message_id, _ts(at or datetime.now(UTC))))
    except sqlite3.IntegrityError:
        return False
    return True
