"""Interface I2 (Owner B): `forecast(crop_option, mandi, as_of, weather) -> dict`.

B1 STUB. No trained model yet. It returns the I2 shape so the API (C) and the channels (A) can build
against it today:

- current price: the latest observed AMIS weekly price on or before `as_of` (real data, never typed in);
- predicted price: persistence (the price stays the same), so trend is always STABLE;
- q10 / q90: today's price moved by the 10th and 90th percentile of this series' past 4-week changes;
- shap: empty, because there is no model to explain yet.

`is_synthetic` is True and `model_version` starts with "stub" until B6 replaces this file with the
trained model. The return shape stays the same, so callers will not change.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from ml.features.config import CROP_OPTION, HORIZON_WEEKS
from ml.features.core import monday_of

ROOT = Path(__file__).resolve().parents[2]
WEEKLY_PRICES = ROOT / "data" / "processed" / "farmsight_prices_clean_weekly.csv"
RUNTIME = ROOT / "data" / "processed" / "runtime"

MODEL_VERSION = "stub-persistence-v0"
DATA_SOURCE = "amis"
UNIT = "40kg"

# A range needs enough past 4-week changes to mean anything; below this we pool the crop option's series.
MIN_CHANGES_FOR_RANGE = 20
# Volatility bands on the half-width of the q10-q90 range, in % of today's price (blueprint glossary).
VOLATILITY_BANDS_PCT = ((5.0, "STABLE"), (15.0, "MODERATE"))

_OPTION_TO_AMIS = {option: amis for amis, option in CROP_OPTION.items()}


@lru_cache(maxsize=1)
def _mandi_names() -> dict[str, str]:
    """Display name or AMIS name -> AMIS name, from the runtime table (never hardcoded)."""
    with open(RUNTIME / "mandis.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    names = {}
    for row in rows:
        names[row["amis_name"]] = row["amis_name"]
        names[row["name"]] = row["amis_name"]
    return names


@lru_cache(maxsize=1)
def _crop_options() -> frozenset[str]:
    with open(RUNTIME / "crops.csv", encoding="utf-8", newline="") as f:
        return frozenset(row["crop_option"] for row in csv.DictReader(f))


@lru_cache(maxsize=1)
def _observed_prices() -> dict[tuple[str, str, str], list[tuple[date, float]]]:
    """(city, crop, variety) -> observed (not forward-filled) weekly prices, Rs per 40 kg, sorted by week."""
    series: dict[tuple[str, str, str], list[tuple[date, float]]] = {}
    with open(WEEKLY_PRICES, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["filled"] != "0":
                continue
            key = (row["city"], row["crop"], row["variety"])
            series.setdefault(key, []).append((date.fromisoformat(row["week_start"]), float(row["price_rs_per_40kg"])))
    for prices in series.values():
        prices.sort()
    return series


def _four_week_changes(prices: list[tuple[date, float]]) -> list[float]:
    """% changes between observed weeks exactly HORIZON_WEEKS apart."""
    by_week = dict(prices)
    gap = timedelta(weeks=HORIZON_WEEKS)
    return [(by_week[w + gap] - p) / p * 100 for w, p in prices if w + gap in by_week]


def _percentile(values: list[float], q: float) -> float:
    """Linear-interpolated percentile, q in [0, 1]."""
    s = sorted(values)
    pos = (len(s) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def _volatility(half_width_pct: float) -> str:
    for limit, label in VOLATILITY_BANDS_PCT:
        if half_width_pct < limit:
            return label
    return "VOLATILE"


def forecast(
    crop_option: str,
    mandi: str,
    as_of: date | None = None,
    weather: Mapping[str, Any] | None = None,
) -> dict | None:
    """4-week forecast for one crop option at one mandi, using only prices from weeks on or before `as_of`.

    `crop_option` is Wheat, Cotton, IRRI or SuperBasmati. `mandi` is the display name ("Rahim Yar Khan")
    or the AMIS name ("RahimYarKhan"). `as_of` defaults to the latest data. `weather` is the dict from
    ml.features.weather_features; the stub ignores it.

    Returns None when the series has no observed price on or before `as_of` (e.g. IRRI at Rahim Yar Khan).
    Raises ValueError for an unknown crop option or mandi.
    """
    if crop_option not in _crop_options() or crop_option not in _OPTION_TO_AMIS:
        raise ValueError(f"unknown crop option: {crop_option!r}")
    city = _mandi_names().get(mandi)
    if city is None:
        raise ValueError(f"unknown mandi: {mandi!r}")
    crop, variety = _OPTION_TO_AMIS[crop_option]

    cutoff = monday_of(as_of) if as_of is not None else None
    history = [(w, p) for w, p in _observed_prices().get((city, crop, variety), []) if cutoff is None or w <= cutoff]
    if not history:
        return None
    prices_as_of, current = history[-1]

    changes = _four_week_changes(history)
    if len(changes) < MIN_CHANGES_FOR_RANGE:
        changes = [
            c
            for (other_city, other_crop, other_variety), prices in _observed_prices().items()
            if (other_crop, other_variety) == (crop, variety)
            for c in _four_week_changes([(w, p) for w, p in prices if cutoff is None or w <= cutoff])
        ]
    if changes:
        q10 = current * (1 + _percentile(changes, 0.10) / 100)
        q90 = current * (1 + _percentile(changes, 0.90) / 100)
        volatility = _volatility((q90 - q10) / 2 / current * 100)
    else:
        q10 = q90 = volatility = None

    return {
        "crop_option": crop_option,
        "mandi": city,
        "unit": UNIT,
        "current_price": round(current, 2),
        "predicted_price": round(current, 2),
        "q10": round(q10, 2) if q10 is not None else None,
        "q90": round(q90, 2) if q90 is not None else None,
        "trend": "STABLE",
        "volatility": volatility,
        "prices_as_of": prices_as_of.isoformat(),
        "target_date": (prices_as_of + timedelta(weeks=HORIZON_WEEKS)).isoformat(),
        "model_version": MODEL_VERSION,
        "shap": [],
        "data_source": DATA_SOURCE,
        "is_synthetic": True,
    }
