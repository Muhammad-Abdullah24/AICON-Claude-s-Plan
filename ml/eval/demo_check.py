"""Data checks behind the demo (task A7): frozen AMIS prices and honest backup weeks.

Usage (repo root):  .venv/Scripts/python -m ml.eval.demo_check [--series BahawalPur|Wheat|none]
Findings are written up in docs/DATA_NOTES.md, section "A7".
"""

import argparse
import csv
from pathlib import Path

from ml.ingest.frozen import FROZEN_MIN_DAYS, frozen_stretches, load_daily

ROOT = Path(__file__).resolve().parents[2]
FEATURES_PATH = ROOT / "data" / "processed" / "features.csv"


def biggest_moves(series: str, n: int = 3) -> dict[str, list[dict]]:
    with FEATURES_PATH.open(encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["series"] == series]
    out = {}
    for split in ("train", "val", "test"):
        rs = sorted((r for r in rows if r["split"] == split), key=lambda r: float(r["price_change_4w_pct"]))
        out[split] = rs[:n] + rs[-n:] if len(rs) > 2 * n else rs
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--series", default="BahawalPur|Wheat|none")
    args = ap.parse_args()

    print(f"Frozen stretches (same price for >= {FROZEN_MIN_DAYS} reported days):")
    for key, prices in load_daily().items():
        runs = frozen_stretches(prices)
        days = sum(r["days"] for r in runs)
        longest = max((r["days"] for r in runs), default=0)
        print(f"  {key:32s} {days:5d} of {len(prices):5d} days ({100 * days / len(prices):3.0f}%)  longest {longest}")

    print(f"\nBiggest real 4-week moves, {args.series} (week, price -> price in 4 weeks, change):")
    for split, rows in biggest_moves(args.series).items():
        print(f"  {split}:")
        for r in rows:
            print(f"    {r['week_start']}  {float(r['price_rs_per_40kg']):7.0f} -> {float(r['price_next_4w']):7.0f}"
                  f"  {float(r['price_change_4w_pct']):+6.1f}%")


if __name__ == "__main__":
    main()
