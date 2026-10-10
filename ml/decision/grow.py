"""What to Grow, made cautious (task F4, docs/PIVOT.md section 5; BLUEPRINT section 0).

Pure Python, no I/O. `crop_plan()` (advisory.py) estimates each crop's profit at harvest; this module decides which
of those estimates may be put side by side, and says why the others may not:

- **Same season only.** A Rabi crop (wheat) is never ranked against a Kharif crop (cotton, rice): they are not the
  same planting decision. The season comes from crops.csv, never from this code.
- **Reliable current evidence only.** A crop whose reference price is stale (the app's one staleness rule, decided
  by the caller), sits in a frozen AMIS stretch, or rests on too few years of seasonal history keeps its card and its
  numbers but gets no rank, with the reasons listed.
- **No winner by default.** A season ranks only when at least `MIN_COMPARABLE_CROPS` of its crops have reliable
  evidence. Otherwise the season says why there is no comparison.

It never predicts more than before: the ranking metric is still crop_plan's labelled estimate.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date

from ml.decision import config

SEASON_ORDER = ("RABI", "KHARIF")


def evidence_issues(item: Mapping) -> list[str]:
    """Why this crop's estimate is not comparable today (empty = comparable)."""
    issues = []
    if item.get("is_stale"):
        issues.append("STALE_PRICE")
    if item.get("is_frozen"):
        issues.append("FROZEN_PRICE")
    if not item.get("enough_years"):
        issues.append("FEW_YEARS")
    return issues


def rank_within_seasons(items: Iterable[Mapping], min_comparable: int = config.MIN_COMPARABLE_CROPS) -> dict:
    """Rank crop_plan rows (those with data) within their season, reliable evidence only.

    Each row needs `crop_option`, `season`, `expected_profit` (or `profit_total`) and the evidence flags
    (`is_stale`, `is_frozen`, `enough_years`). Returns the rows (each with `evidence_issues` and `rank`, None when
    not ranked; ranked rows first within a season, then the rest by profit) and one summary per season:
    {season, status, n_crops, n_comparable}, where status is
      RANKED                       at least `min_comparable` crops with reliable evidence;
      TOO_FEW_CROPS                fewer crops than that in the season at all (e.g. wheat, the only Rabi crop);
      NOT_ENOUGH_CURRENT_EVIDENCE  enough crops, but too few with reliable evidence (all stale included).
    """
    if min_comparable < 2:
        raise ValueError("a comparison needs at least 2 crops")
    by_season: dict[str, list[dict]] = {}
    for item in items:
        if item.get("season") not in SEASON_ORDER:
            raise ValueError(f"unknown season for {item.get('crop_option')!r}: {item.get('season')!r}")
        row = {**item, "evidence_issues": evidence_issues(item), "rank": None}
        by_season.setdefault(row["season"], []).append(row)

    def profit(r: Mapping) -> float:
        return r.get("expected_profit", r.get("profit_total", 0))

    rows, seasons = [], []
    for season in SEASON_ORDER:
        group = by_season.get(season, [])
        if not group:
            continue
        comparable = sorted((r for r in group if not r["evidence_issues"]), key=profit, reverse=True)
        others = sorted((r for r in group if r["evidence_issues"]), key=profit, reverse=True)
        if len(group) < min_comparable:
            status = "TOO_FEW_CROPS"
        elif len(comparable) < min_comparable:
            status = "NOT_ENOUGH_CURRENT_EVIDENCE"
        else:
            status = "RANKED"
            for rank, r in enumerate(comparable, start=1):
                r["rank"] = rank
        rows += comparable + others
        seasons.append({"season": season, "status": status, "n_crops": len(group),
                        "n_comparable": len(comparable)})
    return {"items": rows, "seasons": seasons}


def support_price_context(events: Sequence[Mapping], as_of: date,
                          max_age_days: int = config.SUPPORT_PRICE_CONTEXT_MAX_AGE_DAYS) -> dict:
    """The latest SUPPORT_PRICE item from the policy timeline (H3's get_policy_events, already cut at as_of).

    state: CURRENT (within max_age_days), OUTDATED (older: shown as "the latest we have"), or UNAVAILABLE (none).
    Policy context only: never a mandi price and never a price the farmer is promised.
    """
    support = [e for e in events if e.get("tag") == "SUPPORT_PRICE" and e.get("date", "") <= as_of.isoformat()]
    if not support:
        return {"state": "UNAVAILABLE", "event": None, "age_days": None, "max_age_days": max_age_days}
    latest = max(support, key=lambda e: e["date"])
    age = (as_of - date.fromisoformat(latest["date"])).days
    return {"state": "CURRENT" if age <= max_age_days else "OUTDATED", "event": dict(latest), "age_days": age,
            "max_age_days": max_age_days}


def context_notes(crop_option: str, mandi: str, notes: Sequence[Mapping] = config.CONTEXT_NOTES) -> list[dict]:
    """The sourced context notes for this crop at this mandi (data names, e.g. "IRRI", "BahawalPur")."""
    return [{k: n[k] for k in ("id", "source", "source_date", "url")}
            for n in notes if crop_option in n["crop_options"] and mandi in n["mandis"]]
