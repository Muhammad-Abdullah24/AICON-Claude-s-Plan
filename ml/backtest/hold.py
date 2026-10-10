"""Hold backtest (task H1, docs/PIVOT.md section 3.1): did waiting to sell actually pay in past years?

For one crop at one mandi, compare **selling in `start_month`** with **selling `wait_months` later**, for every
past year, net of two real costs of holding: the interest on the money the unsold crop ties up, and the grain lost
in storage. Real AMIS weekly prices only (filled/forward-filled weeks dropped), the **median price of each calendar
month**, Rs per 40 kg. Standard library only.

    net_gain = later_price * (1 - loss_pct/100) - start_price * (1 + annual_rate/100 * wait_months/12)

This never changes the advice (docs/PIVOT.md rule 8). It tells the farmer how often waiting *would have* paid and
how bad the worst year was, so they can judge the risk with their own eyes. Abd's wait engine calls `hold_history`.

No peeking: with `as_of` set, a year counts only if its later month has fully ended on or before that date, so a
replay of a past week sees exactly what was knowable then.
"""

from __future__ import annotations

import calendar
import csv
import statistics
from datetime import date
from functools import lru_cache
from pathlib import Path

from ml.features.build import load_weekly
from ml.features.config import CROP_OPTION

ROOT = Path(__file__).resolve().parents[2]
MANDIS = ROOT / "data" / "processed" / "runtime" / "mandis.csv"

# "Wheat" -> ("Wheat", "none"), so we can look the crop up in the weekly table.
_OPTION_TO_CROP = {option: cv for cv, option in CROP_OPTION.items()}


@lru_cache(maxsize=1)
def _amis_names() -> dict[str, str]:
    """Display name or AMIS name -> AMIS name (the key the weekly table uses)."""
    out: dict[str, str] = {}
    with open(MANDIS, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out[r["name"]] = r["amis_name"]
            out[r["amis_name"]] = r["amis_name"]
    return out


def _monthly_medians(crop_option: str, mandi: str) -> dict[tuple[int, int], float]:
    """(year, month) -> median of that month's real weekly prices, Rs per 40 kg."""
    if crop_option not in _OPTION_TO_CROP:
        raise ValueError(f"unknown crop option: {crop_option!r}")
    amis = _amis_names().get(mandi)
    if amis is None:
        raise ValueError(f"unknown mandi: {mandi!r}")
    crop, variety = _OPTION_TO_CROP[crop_option]
    buckets: dict[tuple[int, int], list[float]] = {}
    for w in load_weekly().get((amis, crop, variety), []):
        if w["filled"]:
            continue
        d = w["week_start"]
        buckets.setdefault((d.year, d.month), []).append(w["price"])
    return {k: statistics.median(v) for k, v in buckets.items()}


def _percentile(values: list[float], pct: float) -> float:
    """Linear-interpolation percentile (same convention as numpy's default), stable on small samples."""
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    rank = pct / 100 * (len(s) - 1)
    lo = int(rank)
    if lo + 1 >= len(s):
        return s[-1]
    return s[lo] + (s[lo + 1] - s[lo]) * (rank - lo)


def hold_history(crop_option: str, mandi: str, start_month: int, wait_months: int,
                 annual_rate: float, loss_pct: float, as_of: date | None = None) -> dict | None:
    """One season per past year: sell in `start_month` vs `wait_months` later, net of interest and storage loss.

    `crop_option` is Wheat / Cotton / IRRI / SuperBasmati; `mandi` is the display or AMIS name. `annual_rate` is the
    cost of the money tied up (% per year; 0 = own cash), `loss_pct` the grain lost over the wait. Returns None when
    fewer than 3 years have a price in both months (e.g. IRRI at Rahim Yar Khan). Prices and gains are whole rupees.
    """
    medians = _monthly_medians(crop_option, mandi)
    total = (start_month - 1) + wait_months
    later_month = total % 12 + 1
    year_offset = total // 12

    seasons = []
    for year in sorted({y for (y, _) in medians}):
        start = medians.get((year, start_month))
        later_year = year + year_offset
        later = medians.get((later_year, later_month))
        if start is None or later is None:
            continue
        month_end = date(later_year, later_month, calendar.monthrange(later_year, later_month)[1])
        if as_of is not None and month_end > as_of:
            continue   # the later month has not finished yet as of this date: unknown, so skip
        net = later * (1 - loss_pct / 100) - start * (1 + annual_rate / 100 * wait_months / 12)
        seasons.append({"year": year, "start_price": round(start), "later_price": round(later),
                        "net_gain_per_maund": round(net), "paid": net > 0})

    if len(seasons) < 3:
        return None
    nets = [s["net_gain_per_maund"] for s in seasons]
    return {
        "seasons": seasons,                                   # oldest first
        "n": len(seasons),
        "wins": sum(1 for s in seasons if s["paid"]),
        "median_net_per_maund": round(statistics.median(nets)),
        "worst_p10_net_per_maund": round(_percentile(nets, 10)),
        "start_month": start_month,
        "later_month": later_month,
        "annual_rate_pct": annual_rate,
        "loss_pct": loss_pct,
    }
