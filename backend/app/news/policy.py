"""Curated policy timeline (task H3, docs/PIVOT.md 3.2). Reads the hand-written policy_events.json.

Standard library only. Honours `as_of` so a replay of a past week shows only the events known by then.

Each event's `date` is the publication date of its source article (checked on the page, 10 Oct), not the day the
decision was taken: a replay should only show what a farmer could have read by then.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
POLICY_PATH = HERE / "policy_events.json"

# Accept the data name too, so a caller that passes "Wheat" still works.
_DATA_TO_ID = {"Wheat": "wheat", "Cotton": "cotton", "IRRI": "irri", "SuperBasmati": "super_basmati"}
_CROP_IDS = ("wheat", "cotton", "irri", "super_basmati")


def _crop_id(crop_option: str | None) -> str | None:
    if crop_option is None:
        return None
    if crop_option in _CROP_IDS:
        return crop_option
    return _DATA_TO_ID.get(crop_option)


def get_policy_events(crop_option: str, as_of: date | None = None) -> list[dict]:
    """Curated, dated, sourced policy events up to `as_of` (newest first). Works in replay."""
    try:
        events = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    crop_id = _crop_id(crop_option)
    cutoff = (as_of or date.today()).isoformat()
    fields = ("date", "tag", "text_ur", "text_en", "source", "url")   # "crop" is for filtering only, not returned
    out = [{k: e[k] for k in fields} for e in events
           if e.get("date", "") <= cutoff and (e.get("crop") in (None, crop_id))]
    return sorted(out, key=lambda e: e["date"], reverse=True)
