"""Engine inputs read from the offline files, so no rate, cost or price is typed into the engine.

Standard library only (csv, json), so ml/decision/ keeps its no-third-party-imports rule.
Mandis are accepted by display name ("Rahim Yar Khan") or AMIS name ("RahimYarKhan").
"""

from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
RUNTIME = PROCESSED / "runtime"


def _rows(name: str) -> list[dict]:
    with open(RUNTIME / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def _mandis() -> list[dict]:
    return _rows("mandis.csv")


def amis_name(mandi: str) -> str:
    for row in _mandis():
        if mandi in (row["name"], row["amis_name"]):
            return row["amis_name"]
    raise ValueError(f"unknown mandi: {mandi!r}")


def display_name(mandi: str) -> str:
    for row in _mandis():
        if mandi in (row["name"], row["amis_name"]):
            return row["name"]
    raise ValueError(f"unknown mandi: {mandi!r}")


@lru_cache(maxsize=1)
def interest_pct_per_year() -> float:
    """Holding interest rate (policy rate + 5% spread), from economics_inputs.json."""
    with open(PROCESSED / "economics_inputs.json", encoding="utf-8") as f:
        return float(json.load(f)["macro"]["holding_interest_rate_pct_per_year"]["value"])


def production_cost_per_40kg(crop_option: str) -> float:
    """Rs per 40 kg (rice: milled-rice equivalent, matching the AMIS rice price level)."""
    for row in _rows("crops.csv"):
        if row["crop_option"] == crop_option:
            return float(row["production_cost_per_40kg"])
    raise ValueError(f"unknown crop option: {crop_option!r}")


def transport_cost(from_district: str, to_mandi: str) -> float | None:
    """Rs per 40 kg from the farmer's district to a mandi (an estimate), or None if the district is unknown."""
    try:
        district, target = display_name(from_district), amis_name(to_mandi)
    except ValueError:
        return None
    for row in _rows("transport_costs.csv"):
        if row["from_district"] == district and row["to_mandi"] == target:
            return float(row["cost_per_40kg"])
    return None


def support_price(crop_option: str, crop_year: int | None = None) -> dict | None:
    """Latest (or the given crop year's) support price row, or None: only wheat has one, and some years none."""
    rows = [r for r in _rows("support_prices.csv") if r["crop_option"] == crop_option]
    if crop_year is not None:
        rows = [r for r in rows if int(r["year"]) == crop_year]
    if not rows:
        return None
    row = max(rows, key=lambda r: int(r["year"]))
    return {"price_per_40kg": float(row["price_per_40kg"]), "status": row["status"], "crop_year": row["crop_year"]}


def is_stale(crop_option: str, mandi: str) -> bool:
    """True when the series' latest price is old (series_coverage.csv); unknown series count as stale."""
    target = amis_name(mandi)
    for row in _rows("series_coverage.csv"):
        if row["crop_option"] == crop_option and row["mandi"] == target:
            return row["is_stale"] == "1"
    return True
