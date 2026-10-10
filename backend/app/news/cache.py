"""SQLite cache for the news feed (task H2). Its own table, created on first use through backend.app.db.connect();
this module never edits db.py (docs/PIVOT.md). One row per query (crop id or "all") holding the built payload.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from backend.app import db

_READY = False


def _conn():
    global _READY
    conn = db.connect()
    if not _READY:
        conn.execute("CREATE TABLE IF NOT EXISTS news_items ("
                     "crop_key TEXT PRIMARY KEY, payload TEXT NOT NULL, fetched_at TEXT NOT NULL)")
        _READY = True
    return conn


def load(crop_key: str) -> tuple[dict, datetime] | None:
    """The saved payload and when it was fetched, or None if this key was never cached."""
    row = _conn().execute("SELECT payload, fetched_at FROM news_items WHERE crop_key = ?", (crop_key,)).fetchone()
    if row is None:
        return None
    return json.loads(row["payload"]), datetime.fromisoformat(row["fetched_at"])


def save(crop_key: str, payload: dict) -> None:
    conn = _conn()
    with conn:
        conn.execute(
            "INSERT INTO news_items (crop_key, payload, fetched_at) VALUES (?, ?, ?) "
            "ON CONFLICT(crop_key) DO UPDATE SET payload = excluded.payload, fetched_at = excluded.fetched_at",
            (crop_key, json.dumps(payload, ensure_ascii=False), datetime.now(UTC).isoformat(timespec="seconds")))
