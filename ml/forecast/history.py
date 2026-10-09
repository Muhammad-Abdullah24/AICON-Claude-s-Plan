"""Price history for the history chart (UC-12, task B9). Standard library only.

`history(crop_option, mandi, as_of)` returns:
- `weeks`: the last 52 weeks up to the latest price on or before `as_of`, one point per week. A week with no
  AMIS price is `price: None`, so the chart draws a gap instead of a made-up line. `filled` marks a short gap
  forward-filled by the cleaning step; `frozen` marks a week starting inside a stretch where AMIS repeated
  the same price (H-C7).
- `seasonal`: each month's typical price as % of the 12-month average around it (A6's seasonal_index.csv),
  with the min-max across years. Months without enough data are `index_median: None`.
- `calendar`: sowing and harvest months, for shading the chart.
All prices are Rs per 40 kg from AMIS; nothing is interpolated or invented.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

from ml.decision import inputs
from ml.features.build import load_weekly
from ml.features.config import CROP_OPTION
from ml.features.core import monday_of

WEEKS = 52
UNIT = "40kg"
DATA_SOURCE = "amis"

_OPTION_TO_AMIS = {option: amis for amis, option in CROP_OPTION.items()}


@lru_cache(maxsize=1)
def _weekly() -> dict:
    return load_weekly()


def _frozen_stretches(crop_option: str, mandi: str) -> list[tuple[str, str]]:
    return [(r["from_date"], r["to_date"]) for r in inputs._rows("frozen_stretches.csv")
            if r["crop_option"] == crop_option and r["mandi"] == mandi]


def _seasonal(crop_option: str, mandi: str) -> list[dict]:
    def number(v: str) -> float | None:
        return float(v) if v else None

    rows = [r for r in inputs._rows("seasonal_index.csv") if r["crop_option"] == crop_option and r["mandi"] == mandi]
    return [{
        "month": int(r["month"]),
        "index_median": number(r["index_median"]),
        "index_min": number(r["index_min"]),
        "index_max": number(r["index_max"]),
        "n_years": int(r["n_years"]),
        "enough_years": r["enough_years"] == "1",
    } for r in sorted(rows, key=lambda r: int(r["month"]))]


def history(crop_option: str, mandi: str, as_of: date | None = None, weeks: int = WEEKS) -> dict | None:
    """52 weeks of prices, the seasonal pattern and the crop calendar for one crop at one mandi.

    Returns None when the series has no price on or before `as_of` (e.g. IRRI at Rahim Yar Khan).
    Raises ValueError for an unknown crop option or mandi.
    """
    if crop_option not in _OPTION_TO_AMIS:
        raise ValueError(f"unknown crop option: {crop_option!r}")
    city = inputs.amis_name(mandi)
    crop, variety = _OPTION_TO_AMIS[crop_option]

    cutoff = monday_of(as_of) if as_of is not None else None
    rows = [r for r in _weekly().get((city, crop, variety), []) if cutoff is None or r["week_start"] <= cutoff]
    observed = [r for r in rows if r["filled"] == 0]
    if not observed:
        return None
    last = observed[-1]["week_start"]
    by_week = {r["week_start"]: r for r in rows}
    stretches = _frozen_stretches(crop_option, city)

    points = []
    for k in range(weeks - 1, -1, -1):
        week = last - timedelta(weeks=k)
        row = by_week.get(week)
        iso = week.isoformat()
        points.append({
            "week_start": iso,
            "price": round(row["price"], 2) if row else None,
            "filled": bool(row and row["filled"]),
            "frozen": bool(row) and any(start <= iso <= end for start, end in stretches),
        })

    priced = [p["price"] for p in points if p["price"] is not None]
    return {
        "crop_option": crop_option,
        "mandi": city,
        "unit": UNIT,
        "data_source": DATA_SOURCE,
        "prices_as_of": last.isoformat(),
        "is_stale": inputs.is_stale(crop_option, mandi),
        "weeks": points,
        "weeks_with_price": len(priced),
        "low": min(priced),
        "high": max(priced),
        "seasonal": _seasonal(crop_option, city),
        "calendar": inputs.crop_calendar(crop_option),
        "is_synthetic": False,
    }
