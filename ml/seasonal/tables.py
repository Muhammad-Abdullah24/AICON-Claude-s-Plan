"""Seasonal tables for What to Grow, the selling window and the price-history chart (task A6).

Writes to data/processed/runtime/:
  seasonal_index.csv       each month's price as % of the 12-month moving average around it
  harvest_ratios.csv       next-harvest price / price in a reference month
  post_harvest_ratios.csv  price k months after harvest starts / price in the harvest-start month

All from the clean daily AMIS prices (Rs per 40 kg), as the median, min and max across years.
Usage (repo root):  .venv/Scripts/python -m ml.seasonal.tables

How Owner B uses them (B7):
  harvest estimate = latest price x harvest_ratios[series, month of that latest price].ratio_median
    (key on the month of the latest price, not today's month: cotton has no mandi price from March to June)
  selling window   = the offset k in post_harvest_ratios with the best ratio_median after interest for k months
  risk badge       = from spread_pct (max - min) / median across years; n_years says how much history backs it
"""

import csv
from collections.abc import Iterable
from pathlib import Path

from ml.features import config as fcfg
from ml.ingest.runtime_tables import DAILY_PATH, OUT_DIR, render

MIN_OBS_PER_MONTH = 3      # daily prices needed before a month's mean is trusted
MA_WINDOW = (-5, 6)        # 12 months around the month: 5 before, the month, 6 after
MIN_MONTHS_IN_WINDOW = 6   # of those 12
MIN_HARVEST_MONTHS = 2     # monthly means needed inside a harvest window
MONTHS_AFTER_HARVEST = 3   # blueprint UC-06: selling window runs from harvest to 3 months after
ENOUGH_YEARS = 3           # fewer years than this: published, but flagged

Month = tuple[int, int]    # (year, month)


def add_months(ym: Month, k: int) -> Month:
    y, m = ym
    total = y * 12 + (m - 1) + k
    return total // 12, total % 12 + 1


def _mean(values: list[float]) -> float:
    total = 0.0
    for v in values:
        total += v
    return total / len(values)


def _median(values: list[float]) -> float:
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def monthly_means(daily: Iterable[dict]) -> dict[str, dict[Month, float]]:
    prices: dict[str, dict[Month, list[float]]] = {}
    for r in daily:
        series = f"{r['city']}|{r['crop']}|{r['variety']}"
        ym = (int(r["date"][:4]), int(r["date"][5:7]))
        prices.setdefault(series, {}).setdefault(ym, []).append(float(r["price_rs_per_40kg"]))
    trusted = {s: {ym: _mean(v) for ym, v in months.items() if len(v) >= MIN_OBS_PER_MONTH}
               for s, months in sorted(prices.items())}
    return {s: months for s, months in trusted.items() if months}


def harvest_months(crop: str) -> list[int]:
    start, end = fcfg.CROP_CALENDAR[crop]["harvest"]
    return [(start - 1 + k) % 12 + 1 for k in range((end - start) % 12 + 1)]


def _summary(values: list[float], digits: int) -> dict:
    if not values:
        return {"median": "", "min": "", "max": "", "spread_pct": "", "n_years": 0, "enough_years": 0}
    med = _median(values)
    return {
        "median": round(med, digits),
        "min": round(min(values), digits),
        "max": round(max(values), digits),
        "spread_pct": round((max(values) - min(values)) / med * 100, 1) if med else "",
        "n_years": len(values),
        "enough_years": int(len(values) >= ENOUGH_YEARS),
    }


def _series_meta(series: str) -> dict:
    city, crop, variety = series.split("|")
    return {"series": series, "mandi": city, "crop_option": fcfg.CROP_OPTION[(crop, variety)]}


def seasonal_index(monthly: dict[str, dict[Month, float]]) -> list[dict]:
    rows = []
    for series, means in monthly.items():
        per_month: dict[int, list[float]] = {m: [] for m in range(1, 13)}
        for ym, value in means.items():
            window = [means[w] for w in (add_months(ym, k) for k in range(MA_WINDOW[0], MA_WINDOW[1] + 1))
                      if w in means]
            if len(window) >= MIN_MONTHS_IN_WINDOW:
                per_month[ym[1]].append(100 * value / _mean(window))
        for m in range(1, 13):
            s = _summary(per_month[m], 1)
            rows.append({**_series_meta(series), "month": m,
                         "index_median": s["median"], "index_min": s["min"], "index_max": s["max"],
                         "n_years": s["n_years"], "enough_years": s["enough_years"]})
    return rows


def _next_harvest_start(ym: Month, crop: str) -> Month:
    start = harvest_months(crop)[0]
    y, m = ym
    return (y, start) if m < start else (y + 1, start)


def harvest_ratios(monthly: dict[str, dict[Month, float]]) -> list[dict]:
    rows = []
    for series, means in monthly.items():
        crop = series.split("|")[1]
        n_harvest = len(harvest_months(crop))
        window_label = f"{harvest_months(crop)[0]}-{harvest_months(crop)[-1]}"
        for ref_month in range(1, 13):
            ratios, ahead = [], None
            for ym, ref_price in means.items():
                if ym[1] != ref_month:
                    continue
                h0 = _next_harvest_start(ym, crop)
                ahead = (h0[0] - ym[0]) * 12 + h0[1] - ym[1]
                window = [means[w] for w in (add_months(h0, k) for k in range(n_harvest)) if w in means]
                if len(window) >= min(MIN_HARVEST_MONTHS, n_harvest):
                    ratios.append(_mean(window) / ref_price)
            if ahead is None:
                start = harvest_months(crop)[0]
                ahead = (start - ref_month) % 12 or 12
            s = _summary(ratios, 4)
            rows.append({**_series_meta(series), "ref_month": ref_month,
                         "harvest_months": window_label,
                         "months_ahead": ahead,
                         "ratio_median": s["median"], "ratio_min": s["min"], "ratio_max": s["max"],
                         "spread_pct": s["spread_pct"], "n_years": s["n_years"], "enough_years": s["enough_years"]})
    return rows


def post_harvest_ratios(monthly: dict[str, dict[Month, float]]) -> list[dict]:
    rows = []
    for series, means in monthly.items():
        crop = series.split("|")[1]
        months = harvest_months(crop)
        span = len(months) - 1 + MONTHS_AFTER_HARVEST
        bases = {ym: v for ym, v in means.items() if ym[1] == months[0]}
        for k in range(span + 1):
            ratios = [means[add_months(ym, k)] / base for ym, base in bases.items() if add_months(ym, k) in means]
            s = _summary(ratios, 4)
            rows.append({**_series_meta(series), "harvest_start_month": months[0], "offset_months": k,
                         "month": add_months((2000, months[0]), k)[1],
                         "in_harvest_window": int(k < len(months)),
                         "ratio_median": s["median"], "ratio_min": s["min"], "ratio_max": s["max"],
                         "spread_pct": s["spread_pct"], "n_years": s["n_years"], "enough_years": s["enough_years"]})
    return rows


def build_all(daily_path: Path = DAILY_PATH) -> dict[str, list[dict]]:
    with daily_path.open(encoding="utf-8", newline="") as f:
        monthly = monthly_means(csv.DictReader(f))
    return {
        "seasonal_index.csv": seasonal_index(monthly),
        "harvest_ratios.csv": harvest_ratios(monthly),
        "post_harvest_ratios.csv": post_harvest_ratios(monthly),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, rows in build_all().items():
        (OUT_DIR / name).write_text(render(rows), encoding="utf-8", newline="")
        print(f"data/processed/runtime/{name}: {len(rows)} rows")


if __name__ == "__main__":
    main()
