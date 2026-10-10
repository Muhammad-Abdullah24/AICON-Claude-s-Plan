"""The news and policy feed the app shows (task H2/H3, docs/PIVOT.md section 3.2).

`get_news` never raises: a live fetch feeds the 6-hour cache; if that fails it serves the last cache, and if there
is none, the committed snapshot. Abd's services.py decides what the news does to the advice (the conflict banner and
lowering confidence) — this module only supplies it. `get_policy_events` serves the curated, dated policy timeline
and honours `as_of`, so it works in a replay.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from backend.app.news import cache, config, fetch, tag

log = logging.getLogger("farmsight.news")
HERE = Path(__file__).resolve().parent
SNAPSHOT_PATH = HERE / "snapshot.json"


def _crop_id(crop_option: str | None) -> str | None:
    if crop_option is None:
        return None
    if crop_option in config.CROP_IDS:
        return crop_option
    return config.DATA_TO_ID.get(crop_option)   # accept the data name too; unknown -> None (general feed)


def _build(crop_key: str, query: str) -> dict:
    items = fetch.fetch_rss(query)[: config.MAX_ITEMS]
    try:
        from backend.app.chat.llm import get_llm  # noqa: PLC0415 (optional; no hard dependency on chat)
        tagged, tagged_by = tag.tag_items(items, get_llm)
    except Exception as e:  # noqa: BLE001 (chat module missing or unusable -> keyword rules)
        log.info("news: LLM tagging unavailable (%s), using rules", type(e).__name__)
        tagged, tagged_by = tag.tag_with_rules(items), "rules"
    return {
        "items": tagged,
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "is_snapshot": False,
        "tagged_by": tagged_by,
    }


@lru_cache(maxsize=1)
def _snapshot() -> dict:
    try:
        return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _from_snapshot(crop_key: str) -> dict:
    snap = _snapshot()
    payload = snap.get(crop_key) or snap.get("all") or {"items": [], "fetched_at": None, "tagged_by": "rules"}
    return {**payload, "is_snapshot": True}


def get_news(crop_option: str | None = None, limit: int = config.MAX_ITEMS) -> dict:
    """Today's Pakistan farm news for one crop (or all). Never raises; see the module docstring for the fallbacks."""
    crop_key = _crop_id(crop_option) or "all"
    query = config.QUERIES.get(crop_key, config.QUERIES[None])
    cached = None
    try:
        cached = cache.load(crop_key)
        if cached is not None:
            payload, fetched_at = cached
            if datetime.now(UTC) - fetched_at < timedelta(hours=config.CACHE_TTL_HOURS):
                return {**payload, "items": payload["items"][:limit], "is_snapshot": False}
    except Exception:  # noqa: BLE001 (a cache read must never break the feed)
        log.warning("news: cache read failed", exc_info=True)

    try:
        payload = _build(crop_key, query)
        try:
            cache.save(crop_key, payload)
        except Exception:  # noqa: BLE001 (saving is best-effort)
            log.warning("news: cache save failed", exc_info=True)
        return {**payload, "items": payload["items"][:limit]}
    except Exception:  # noqa: BLE001 (any fetch/parse failure -> last cache, else snapshot)
        log.warning("news: live fetch failed, serving cache or snapshot", exc_info=True)
        if cached is not None:
            payload, _ = cached
            return {**payload, "items": payload["items"][:limit], "is_snapshot": False}
        return _from_snapshot(crop_key)
