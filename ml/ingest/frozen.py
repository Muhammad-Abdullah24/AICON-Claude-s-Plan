"""Frozen AMIS prices: the same daily price reported for at least 28 days in a row (task A12).

AMIS sometimes repeats one price for months (Vehari IRRI: 66% of days). Those weeks are stale reporting,
not a flat market, and they make "price stays the same" look more accurate than it is.

These flags use days AFTER a week to know a stretch is long, so they are for evaluation and display only.
Never feed them to a model as inputs.
"""

import csv
from collections.abc import Iterable
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAILY_PATH = ROOT / "data" / "processed" / "farmsight_prices_clean_daily.csv"
FROZEN_MIN_DAYS = 28


def frozen_stretches(prices: Iterable[tuple[str, float]], min_days: int = FROZEN_MIN_DAYS) -> list[dict]:
    """Runs of an identical reported price, from (date, price) pairs in date order."""
    runs: list[dict] = []
    current: list[tuple[str, float]] = []

    def close() -> None:
        if len(current) >= min_days:
            runs.append({"from": current[0][0], "to": current[-1][0], "days": len(current), "price": current[0][1]})

    for d, p in prices:
        if current and p != current[-1][1]:
            close()
            current = []
        current.append((d, p))
    close()
    return runs


def load_daily(path: Path = DAILY_PATH) -> dict[str, list[tuple[str, float]]]:
    """Daily prices (Rs per 40 kg) per series 'city|crop|variety', in date order."""
    series: dict[str, list[tuple[str, float]]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            series.setdefault(f"{r['city']}|{r['crop']}|{r['variety']}", []).append(
                (r["date"], float(r["price_rs_per_40kg"])))
    return {k: sorted(v) for k, v in sorted(series.items())}


def week_flags(daily: list[tuple[str, float]], min_days: int = FROZEN_MIN_DAYS) -> "WeekFlags":
    return WeekFlags(daily, frozen_stretches(daily, min_days))


class WeekFlags:
    """Is the week starting on a Monday frozen? Yes if every price reported that week sits inside a frozen
    stretch, or, for a week with no reports, if the whole week lies inside one stretch."""

    def __init__(self, daily: list[tuple[str, float]], stretches: list[dict]):
        self.stretches = [(date.fromisoformat(s["from"]), date.fromisoformat(s["to"])) for s in stretches]
        frozen_days = {d for s_from, s_to in self.stretches for d in _days(s_from, s_to)}
        self._observed: dict[date, list[bool]] = {}
        for d_str, _ in daily:
            d = date.fromisoformat(d_str)
            self._observed.setdefault(d - timedelta(days=d.weekday()), []).append(d in frozen_days)

    def __call__(self, monday: date) -> int:
        seen = self._observed.get(monday)
        if seen:
            return int(all(seen))
        sunday = monday + timedelta(days=6)
        return int(any(s_from <= monday and sunday <= s_to for s_from, s_to in self.stretches))


def _days(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)
