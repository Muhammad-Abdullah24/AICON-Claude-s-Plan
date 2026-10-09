"""Rebuild data/processed/features.csv (real rows only) from the clean weekly prices and daily weather.

Usage (repo root):  .venv/Scripts/python -m ml.features.build
"""

import argparse
import csv
import math
from collections.abc import Iterable
from datetime import date, timedelta
from pathlib import Path

from ml.features import config as cfg
from ml.features.core import (
    calendar_features,
    group_weather_by_week,
    id_features,
    price_features_at,
    weather_features_from_weeks,
)
from ml.ingest.frozen import load_daily, week_flags

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
WEEKLY_PATH = PROCESSED / "farmsight_prices_clean_weekly.csv"
WEATHER_PATH = PROCESSED / "weather_daily_2015_2026.csv"
OUT_PATH = PROCESSED / "features.csv"

COLUMNS = [
    "week_start", "city", "crop", "variety", "crop_option", "series",
    "city_id", "crop_id", "variety_id", "crop_option_id",
    "price_rs_per_40kg", "price_was_filled",
    "price_lag_1w", "price_lag_2w", "price_lag_4w", "price_lag_8w", "price_lag_12w",
    "momentum_1w_pct", "momentum_4w_pct", "momentum_8w_pct",
    "volatility_4w", "volatility_8w", "price_ma_4w", "price_ma_8w", "price_ma_12w", "price_vs_ma_8w_pct",
    "month", "week_of_year", "month_sin", "month_cos", "is_sowing", "is_harvest",
    "tmax_c", "tmin_c", "precip_mm_wk", "rh_pct", "et0_mm_wk", "hot_days_wk",
    "precip_mm_4w", "tmax_c_4w", "precip_mm_12w",
    "target_week", "price_next_4w", "price_change_4w_pct", "direction",
    "hold_cost_pct_4w", "net_gain_pct_4w", "action", "baseline_pred_persistence",
    "is_synthetic", "data_source", "split",
    # Evaluation-only flags (task A12). They need days after the week to spot a 28-day freeze, so they are
    # NOT model inputs. Appended last so earlier column positions never change.
    "price_is_frozen", "target_is_frozen",
]


def load_weekly(path: Path = WEEKLY_PATH) -> dict[tuple[str, str, str], list[dict]]:
    series: dict[tuple[str, str, str], list[dict]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            key = (r["city"], r["crop"], r["variety"])
            series.setdefault(key, []).append({
                "week_start": date.fromisoformat(r["week_start"]),
                "price": float(r["price_rs_per_40kg"]),
                "filled": int(r["filled"]),
            })
    return series


def load_weather(path: Path = WEATHER_PATH) -> dict[str, dict[date, list[dict]]]:
    daily: dict[str, list[dict]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            city = cfg.WEATHER_CITY.get(r["district"])
            if city:
                daily.setdefault(city, []).append(r)
    return {city: group_weather_by_week(recs) for city, recs in daily.items()}


def _split(row_week: str, target_week: str) -> str | None:
    if target_week < cfg.TRAIN_TARGET_BEFORE:
        return "train"
    if row_week >= cfg.VAL_START and target_week < cfg.VAL_TARGET_BEFORE:
        return "val"
    if row_week >= cfg.TEST_START:
        return "test"
    return None  # the 4-week window crosses a split boundary: dropped so nothing leaks


def series_rows(key: tuple[str, str, str], weeks: list[dict], weather_weeks: dict, stats: dict,
                frozen=lambda monday: 0) -> list[dict]:
    city, crop, variety = key
    weeks = sorted(weeks, key=lambda w: w["week_start"])
    by_week = {w["week_start"]: w for w in weeks}
    grid, w = [], weeks[0]["week_start"]
    while w <= weeks[-1]["week_start"]:
        grid.append(by_week.get(w, {"week_start": w, "price": None, "filled": 0, "missing": True}))
        w += timedelta(days=7)
    prices = [g["price"] for g in grid]
    observed = [not g.get("missing") and g["filled"] == 0 for g in grid]
    option = cfg.CROP_OPTION[(crop, variety)]
    ids = id_features(city, crop, variety)

    rows = []
    for i, g in enumerate(grid):
        price = prices[i]
        if price is None:
            stats["no_price"] += 1
            continue
        t = i + cfg.HORIZON_WEEKS
        if t >= len(grid) or prices[t] is None or not observed[t]:
            stats["no_target"] += 1
            continue
        row_week, target_week = g["week_start"].isoformat(), grid[t]["week_start"].isoformat()
        split = _split(row_week, target_week)
        if split is None:
            stats["boundary"] += 1
            continue
        target = prices[t]
        change = (target / price - 1) * 100
        hold_cost = cfg.STORAGE_RS_PER_40KG_MONTH / price * 100 + cfg.INTEREST_PCT_PER_MONTH
        net = change - hold_cost
        rows.append({
            "week_start": row_week, "city": city, "crop": crop, "variety": variety,
            "crop_option": option, "series": f"{city}|{crop}|{variety}",
            **ids,
            **price_features_at(prices, i, g["filled"]),
            **calendar_features(crop, g["week_start"]),
            **weather_features_from_weeks(weather_weeks, g["week_start"]),
            "target_week": target_week, "price_next_4w": target, "price_change_4w_pct": change,
            "direction": ("UP" if change > cfg.DIRECTION_THRESHOLD_PCT
                          else "DOWN" if change < -cfg.DIRECTION_THRESHOLD_PCT else "FLAT"),
            "hold_cost_pct_4w": hold_cost, "net_gain_pct_4w": net,
            "action": ("WAIT" if net > cfg.NET_GAIN_WAIT_PCT
                       else "SELL" if change < cfg.SELL_DROP_PCT else "HOLD"),
            "baseline_pred_persistence": price,
            "is_synthetic": 0, "data_source": "real", "split": split,
            "price_is_frozen": frozen(g["week_start"]), "target_is_frozen": frozen(grid[t]["week_start"]),
        })
    return rows


def build_rows(weekly: dict | None = None, weather: dict | None = None,
               daily: dict | None = None) -> tuple[list[dict], dict]:
    weekly = load_weekly() if weekly is None else weekly
    weather = load_weather() if weather is None else weather
    daily = load_daily() if daily is None else daily
    stats = {"no_price": 0, "no_target": 0, "boundary": 0}
    rows: list[dict] = []
    for key in sorted(weekly, key=lambda k: "|".join(k)):
        flags = week_flags(daily.get("|".join(key), []))
        rows.extend(series_rows(key, weekly[key], weather.get(key[0], {}), stats, flags))
    return rows, stats


def format_value(v) -> str:
    """Round to 4 decimals and print like the original pipeline: 7600 not 7600.0, None as empty."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    x = math.floor(v * 10000 + 0.5) / 10000   # round half up, not Python's round-half-even
    if x == 0:
        return "0"
    if x == int(x):
        return str(int(x))
    return repr(x)


def to_lines(rows: Iterable[dict]) -> list[str]:
    return [",".join(COLUMNS)] + [",".join(format_value(r[c]) for c in COLUMNS) for r in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()
    rows, stats = build_rows()
    args.out.write_text("\n".join(to_lines(rows)) + "\n", encoding="utf-8", newline="\n")
    counts = {s: sum(1 for r in rows if r["split"] == s) for s in ("train", "val", "test")}
    print(f"features.csv: {len(rows)} rows, {len(COLUMNS)} columns -> {args.out}")
    print(f"dropped: no current price {stats['no_price']}, no observed target {stats['no_target']}, "
          f"split boundary {stats['boundary']}")
    print("split: " + "  ".join(f"{s} {n}" for s, n in counts.items()))


if __name__ == "__main__":
    main()
