"""Feature definitions shared by training (ml.features.build) and runtime forecasting (interface I1).

Standard library only, so the backend can import it without pulling in pandas.
Prices are Rs per 40 kg. Weeks start on Monday.
"""

import math
from collections.abc import Iterable, Mapping
from datetime import date, timedelta

from ml.features import config as cfg

PRICE_COLUMNS = [
    "price_rs_per_40kg", "price_was_filled",
    "price_lag_1w", "price_lag_2w", "price_lag_4w", "price_lag_8w", "price_lag_12w",
    "momentum_1w_pct", "momentum_4w_pct", "momentum_8w_pct",
    "volatility_4w", "volatility_8w",
    "price_ma_4w", "price_ma_8w", "price_ma_12w", "price_vs_ma_8w_pct",
]
CALENDAR_COLUMNS = ["month", "week_of_year", "month_sin", "month_cos", "is_sowing", "is_harvest"]
WEATHER_COLUMNS = [
    "tmax_c", "tmin_c", "precip_mm_wk", "rh_pct", "et0_mm_wk", "hot_days_wk",
    "precip_mm_4w", "tmax_c_4w", "precip_mm_12w",
]
ID_COLUMNS = ["city_id", "crop_id", "variety_id", "crop_option_id"]

# Everything a model may use as input. Which of these to feed the model is Owner B's choice.
FEATURE_COLUMNS = ID_COLUMNS + PRICE_COLUMNS + CALENDAR_COLUMNS + WEATHER_COLUMNS


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _total(values: Iterable[float]) -> float:
    # An explicit loop, not sum(): Python 3.12+ sum() compensates float error, which would make results
    # depend on the Python version.
    total = 0.0
    for v in values:
        total += v
    return total


def _mean(values: list[float]) -> float:
    return _total(values) / len(values)


def _std(values: list[float]) -> float:
    m = _mean(values)
    return math.sqrt(_total((x - m) ** 2 for x in values) / len(values))


def _pct(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return (a / b - 1) * 100


def in_season(month: int, span: tuple[int, int]) -> bool:
    start, end = span
    return start <= month <= end if start <= end else month >= start or month <= end


# ---------------------------------------------------------------- ids and calendar

def id_features(city: str, crop: str, variety: str) -> dict:
    option = cfg.CROP_OPTION[(crop, variety)]
    return {
        "city_id": cfg.CITY_ID[city],
        "crop_id": cfg.CROP_ID[crop],
        "variety_id": cfg.VARIETY_ID[variety],
        "crop_option_id": cfg.CROP_OPTION_ID[option],
    }


def calendar_features(crop: str, week_start: date) -> dict:
    m = week_start.month
    day_of_year = (week_start - date(week_start.year, 1, 1)).days
    cal = cfg.CROP_CALENDAR[crop]
    return {
        "month": m,
        "week_of_year": day_of_year // 7 + 1,
        "month_sin": math.sin(2 * math.pi * m / 12),
        "month_cos": math.cos(2 * math.pi * m / 12),
        "is_sowing": 1 if in_season(m, cal["sow"]) else 0,
        "is_harvest": 1 if in_season(m, cal["harvest"]) else 0,
    }


# ---------------------------------------------------------------- weather

def group_weather_by_week(daily: Iterable[Mapping]) -> dict[date, list[Mapping]]:
    """Daily records ({date, tmax, tmin, precip_mm, rh_mean, et0}) for ONE city, grouped by Monday."""
    weeks: dict[date, list[Mapping]] = {}
    for rec in daily:
        d = rec["date"] if isinstance(rec["date"], date) else date.fromisoformat(rec["date"])
        weeks.setdefault(monday_of(d), []).append(rec)
    return weeks


def _weekly_aggregate(days: list[Mapping] | None) -> dict | None:
    if not days or len(days) < cfg.MIN_DAYS_PER_WEEK:
        return None
    return {
        "tmax": _mean([float(r["tmax"]) for r in days]),
        "tmin": _mean([float(r["tmin"]) for r in days]),
        "precip": _total(float(r["precip_mm"]) for r in days),
        "rh": _mean([float(r["rh_mean"]) for r in days]),
        "et0": _total(float(r["et0"]) for r in days),
        "hot": len([r for r in days if float(r["tmax"]) >= cfg.HOT_DAY_TMAX_C]),
    }


def weather_features_from_weeks(weeks: Mapping[date, list[Mapping]], week_start: date) -> dict:
    def agg(k: int) -> dict | None:
        return _weekly_aggregate(weeks.get(week_start - timedelta(days=7 * k)))

    w0 = agg(0)
    w4 = [w for w in (agg(k) for k in range(4)) if w]
    w12 = [w for w in (agg(k) for k in range(12)) if w]
    return {
        "tmax_c": w0["tmax"] if w0 else None,
        "tmin_c": w0["tmin"] if w0 else None,
        "precip_mm_wk": w0["precip"] if w0 else None,
        "rh_pct": w0["rh"] if w0 else None,
        "et0_mm_wk": w0["et0"] if w0 else None,
        "hot_days_wk": w0["hot"] if w0 else None,
        "precip_mm_4w": _total(w["precip"] for w in w4) if len(w4) >= cfg.MIN_WEEKS_4W else None,
        "tmax_c_4w": _mean([w["tmax"] for w in w4]) if len(w4) >= cfg.MIN_WEEKS_4W else None,
        "precip_mm_12w": _total(w["precip"] for w in w12) if len(w12) >= cfg.MIN_WEEKS_12W else None,
    }


def weather_features(daily: Iterable[Mapping], week_start: date) -> dict:
    """I1: weather features for the week starting `week_start`, from at least 12 weeks of daily records.

    The runtime weather service passes Open-Meteo's last 92 days (past_days=92) for one mandi.
    """
    return weather_features_from_weeks(group_weather_by_week(daily), week_start)


# ---------------------------------------------------------------- prices

def build_grid(history: Iterable[tuple[date, float, int]], until: date | None = None) -> list[dict]:
    """Weekly grid from the first week to the last (or `until`), with missing weeks as price None.

    `history` is (week_start, price_rs_per_40kg, filled) for ONE series, filled = 1 for a forward-filled week.
    """
    by_week = {w: (p, f) for w, p, f in history if until is None or w <= until}
    if not by_week:
        return []
    first, last = min(by_week), max(by_week)
    if until is not None:
        last = monday_of(until)
    grid, w = [], first
    while w <= last:
        if w in by_week:
            p, f = by_week[w]
            grid.append({"week_start": w, "price": p, "filled": int(f), "missing": False})
        else:
            grid.append({"week_start": w, "price": None, "filled": 0, "missing": True})
        w += timedelta(days=7)
    return grid


def price_features_at(prices: list[float | None], i: int, filled: int = 0) -> dict:
    """Price features for index `i` of a weekly price list (None = no price that week). Uses only i and earlier."""
    def at(j: int) -> float | None:
        return prices[j] if 0 <= j < len(prices) else None

    def window(n: int) -> list[float]:
        return [x for x in (at(j) for j in range(i - n + 1, i + 1)) if x is not None]

    price = prices[i]
    v4, v8, v12 = window(4), window(8), window(12)
    return {
        "price_rs_per_40kg": price,
        "price_was_filled": filled,
        "price_lag_1w": at(i - 1), "price_lag_2w": at(i - 2), "price_lag_4w": at(i - 4),
        "price_lag_8w": at(i - 8), "price_lag_12w": at(i - 12),
        "momentum_1w_pct": _pct(price, at(i - 1)),
        "momentum_4w_pct": _pct(price, at(i - 4)),
        "momentum_8w_pct": _pct(price, at(i - 8)),
        "volatility_4w": _std(v4) / _mean(v4) if len(v4) >= 3 else None,
        "volatility_8w": _std(v8) / _mean(v8) if len(v8) >= 4 else None,
        "price_ma_4w": _mean(v4) if len(v4) >= 2 else None,
        "price_ma_8w": _mean(v8) if len(v8) >= 4 else None,
        "price_ma_12w": _mean(v12) if len(v12) >= 6 else None,
        "price_vs_ma_8w_pct": _pct(price, _mean(v8)) if len(v8) >= 4 else None,
    }


def price_features(history: Iterable[tuple[date, float, int]], week_start: date | None = None) -> dict | None:
    """I1: price features for one series at `week_start` (default: the latest week that has a price).

    Returns None if there is no price that week. The result includes `week_start`, which is the
    "prices as of" week.
    """
    grid = build_grid(history, until=week_start)
    if not grid:
        return None
    if week_start is None:
        i = max(k for k, g in enumerate(grid) if g["price"] is not None)
    else:
        i = len(grid) - 1
        if grid[i]["week_start"] != monday_of(week_start):
            return None
    if grid[i]["price"] is None:
        return None
    out = price_features_at([g["price"] for g in grid], i, grid[i]["filled"])
    out["week_start"] = grid[i]["week_start"]
    return out


def runtime_features(city: str, crop: str, variety: str, history: Iterable[tuple[date, float, int]],
                     daily_weather: Iterable[Mapping], week_start: date | None = None) -> dict | None:
    """All FEATURE_COLUMNS for one forecast, built exactly as in training. None if there is no price."""
    prices = price_features(history, week_start)
    if prices is None:
        return None
    ws = prices["week_start"]
    return {
        "week_start": ws,
        **id_features(city, crop, variety),
        **prices,
        **calendar_features(crop, ws),
        **weather_features(daily_weather, ws),
    }
