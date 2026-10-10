"""Engine inputs read from the offline files, so no rate, cost or price is typed into the engine.

Standard library only (csv, json), so ml/decision/ keeps its no-third-party-imports rule.
Mandis are accepted by display name ("Rahim Yar Khan") or AMIS name ("RahimYarKhan").
Functions that take `as_of` read only data on or before that date, so the demo's replay mode can use them;
without it they use the latest snapshot (series_coverage.csv).
"""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from ml.ingest.runtime_tables import STALE_AFTER_WEEKS

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


@lru_cache(maxsize=1)
def _daily_observed() -> dict[tuple[str, str], list[tuple[str, float]]]:
    """(crop_option, AMIS mandi) -> sorted (date, Rs per 40 kg) of real AMIS daily prices."""
    options = {(r["amis_crop"], r["amis_variety"]): r["crop_option"] for r in _rows("crops.csv")}
    out: dict[tuple[str, str], list[tuple[str, float]]] = {}
    with open(PROCESSED / "farmsight_prices_clean_daily.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            option = options.get((r["crop"], r["variety"]))
            if option:
                out.setdefault((option, r["city"]), []).append((r["date"], float(r["price_rs_per_40kg"])))
    return {k: sorted(v) for k, v in out.items()}


def latest_price(crop_option: str, mandi: str, as_of: date | None = None) -> tuple[float, str] | None:
    """(latest AMIS price Rs per 40 kg, its date) on or before `as_of`, or None if there is none.

    Without `as_of`, the snapshot in series_coverage.csv; with it, the real daily prices up to that day.
    """
    target = amis_name(mandi)
    if as_of is None:
        for row in _rows("series_coverage.csv"):
            if row["crop_option"] == crop_option and row["mandi"] == target and row["latest_price_per_40kg"]:
                return float(row["latest_price_per_40kg"]), row["prices_as_of"]
        return None
    days = [d for d in _daily_observed().get((crop_option, target), []) if d[0] <= as_of.isoformat()]
    return (days[-1][1], days[-1][0]) if days else None


def is_stale(crop_option: str, mandi: str, as_of: date | None = None) -> bool:
    """True when the latest price is more than STALE_AFTER_WEEKS old (A2's rule); no price counts as stale.

    Without `as_of`, the flag in series_coverage.csv; with it, the age of the latest price on that day.
    """
    if as_of is None:
        target = amis_name(mandi)
        for row in _rows("series_coverage.csv"):
            if row["crop_option"] == crop_option and row["mandi"] == target:
                return row["is_stale"] == "1"
        return True
    latest = latest_price(crop_option, mandi, as_of)
    return latest is None or (as_of - date.fromisoformat(latest[1])).days // 7 > STALE_AFTER_WEEKS


def crop_economics(crop_option: str) -> dict:
    """Cost per acre and the yield in the unit the price is quoted in (rice: paddy x milling yield)."""
    for row in _rows("crops.csv"):
        if row["crop_option"] == crop_option:
            milling = float(row["milling_yield"]) if row["milling_yield"] else None
            return {
                "cost_per_acre": float(row["production_cost_per_acre"]),
                "yield_maund_per_acre": float(row["yield_maund_per_acre"]),
                "yield_unit": row["yield_unit"],
                "milling_yield": milling,
                "yield_is_estimate": milling is not None,  # the 0.65 milling yield is an assumption
            }
    raise ValueError(f"unknown crop option: {crop_option!r}")


def crop_calendar(crop_option: str) -> dict:
    for row in _rows("crop_calendar.csv"):
        if row["crop_option"] == crop_option:
            return {k: int(row[k]) for k in
                    ("sowing_start_month", "sowing_end_month", "harvest_start_month", "harvest_end_month")}
    raise ValueError(f"unknown crop option: {crop_option!r}")


def _ratio(row: dict) -> dict:
    return {
        "ratio_median": float(row["ratio_median"]),
        "ratio_min": float(row["ratio_min"]),
        "ratio_max": float(row["ratio_max"]),
        "spread_pct": float(row["spread_pct"]),
        "n_years": int(row["n_years"]),
        "enough_years": row["enough_years"] == "1",
    }


def harvest_ratio(crop_option: str, mandi: str, ref_month: int) -> dict | None:
    """Next-harvest price / price in `ref_month` (A6), keyed on the month of the latest price (H-B7)."""
    target = amis_name(mandi)
    for row in _rows("harvest_ratios.csv"):
        if (row["crop_option"] == crop_option and row["mandi"] == target and int(row["ref_month"]) == ref_month
                and row["ratio_median"]):
            return {**_ratio(row), "months_ahead": int(row["months_ahead"]), "harvest_months": row["harvest_months"]}
    return None


def post_harvest_ratios(crop_option: str, mandi: str) -> list[dict]:
    """Price k months after harvest starts / price in the harvest-start month (A6), by offset k."""
    target = amis_name(mandi)
    rows = [
        {**_ratio(r), "offset_months": int(r["offset_months"]), "month": int(r["month"])}
        for r in _rows("post_harvest_ratios.csv")
        if r["crop_option"] == crop_option and r["mandi"] == target and r["ratio_median"]
    ]
    return sorted(rows, key=lambda r: r["offset_months"])


def crop_plan_inputs(mandi: str, as_of: date | None = None) -> list[dict]:
    """Everything crop_plan() needs for every crop option at one mandi, using prices on or before `as_of`."""
    out = []
    seasons = {r["crop_option"]: r["season"] for r in _rows("crops.csv")}
    for crop_option in sorted(seasons):
        latest = latest_price(crop_option, mandi, as_of)
        ratio = harvest_ratio(crop_option, mandi, int(latest[1][5:7])) if latest else None
        out.append({
            "crop_option": crop_option,
            "season": seasons[crop_option],   # RABI / KHARIF: What to Grow compares crops within one season (F4)
            "latest_price": latest[0] if latest else None,
            "prices_as_of": latest[1] if latest else None,
            "is_stale": is_stale(crop_option, mandi, as_of),
            # The latest price sits in a stretch where AMIS repeated one price for 28+ days (A12), so it may not
            # be a real quote. Only stretches already in frozen_stretches.csv are known.
            "is_frozen": bool(latest) and _in_frozen_stretch(crop_option, amis_name(mandi), latest[1]),
            "harvest_ratio": ratio,
            **crop_economics(crop_option),
        })
    return out


MODELS = ROOT / "artifacts" / "models"


@lru_cache(maxsize=1)
def _weekly_observed() -> dict[tuple[str, str], dict[str, float]]:
    """(crop_option, AMIS mandi) -> {week_start: observed Rs per 40 kg}, forward-filled weeks left out."""
    options = {(r["amis_crop"], r["amis_variety"]): r["crop_option"] for r in _rows("crops.csv")}
    out: dict[tuple[str, str], dict[str, float]] = {}
    with open(PROCESSED / "farmsight_prices_clean_weekly.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            option = options.get((r["crop"], r["variety"]))
            if option and r["filled"] == "0":
                out.setdefault((option, r["city"]), {})[r["week_start"]] = float(r["price_rs_per_40kg"])
    return out


def _in_frozen_stretch(crop_option: str, mandi: str, week_start: str) -> bool:
    for r in _rows("frozen_stretches.csv"):
        if r["crop_option"] == crop_option and r["mandi"] == mandi and r["from_date"] <= week_start <= r["to_date"]:
            return True
    return False


def alert_candidate(crop_option: str, mandi: str, signal: str, previous_signal: str | None,
                    as_of: date | None = None) -> dict | None:
    """Inputs for alert_check() for one crop at one mandi, from weeks on or before `as_of`; None without prices.

    change_4w_pct compares the latest observed weekly price with the observed price exactly 4 weeks earlier
    (None if that week has no price). The week containing `as_of` counts, as in ml.features (I1).
    The band is the deployed forecast band (artifacts/models/deployed.json).
    """
    target = amis_name(mandi)
    prices = _weekly_observed().get((crop_option, target), {})
    if as_of is not None:
        prices = {w: p for w, p in prices.items() if w <= as_of.isoformat()}
    if not prices:
        return None
    latest = max(prices)
    earlier = (date.fromisoformat(latest) - timedelta(weeks=4)).isoformat()
    band = json.loads((MODELS / "deployed.json").read_text(encoding="utf-8"))["band_change_pct"][crop_option]
    return {
        "crop_option": crop_option,
        "mandi": target,
        "signal": signal,
        "previous_signal": previous_signal,
        "prices_as_of": latest,
        "change_4w_pct": round((prices[latest] / prices[earlier] - 1) * 100, 2) if earlier in prices else None,
        "band_q10_pct": band["q10"],
        "band_q90_pct": band["q90"],
        "is_frozen": any(_in_frozen_stretch(crop_option, target, week) for week in (latest, earlier)),
        "is_stale": is_stale(crop_option, mandi, as_of),
    }
