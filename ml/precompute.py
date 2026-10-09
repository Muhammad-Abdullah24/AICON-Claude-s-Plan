"""Writes every file in artifacts/ (PLAN.md section 14.5). Owner B.

Run from the repo root:

    python -m ml.precompute --placeholder

`--placeholder` writes synthetic artifacts with the real crop and mandi names
and the exact shapes of the contract, so the backend and front end can be
built before the real models exist. Every placeholder file is marked
is_synthetic: true and data_source: "placeholder". The output is
deterministic: running it twice gives identical files.

The real pipeline (clean series -> Chronos-2 / boosting / naive -> backtest ->
artifacts) replaces `build_placeholder` later. It must keep writing the same
shapes. Check them with `python -m backend.app.check_artifacts`.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

from ml.decision.engine import BandPoint, Costs, DecisionInput, decide

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"

SCHEMA_VERSION = 1
SEED = 20261009
PLACEHOLDER = "placeholder"
MODEL_NAME = "placeholder-random-walk"
HORIZONS = (1, 2, 3, 4)

CROPS = [
    {"id": "wheat", "name_ur": "گندم", "name_en": "Wheat"},
    {"id": "rice", "name_ur": "چاول (اری)", "name_en": "Rice (IRRI)"},
    {"id": "cotton", "name_ur": "کپاس (پھٹی)", "name_en": "Cotton (phutti)"},
]
MANDIS = [
    {"id": "bahawalpur", "name_ur": "بہاولپور", "name_en": "Bahawalpur"},
    {"id": "vehari", "name_ur": "وہاڑی", "name_en": "Vehari"},
    {"id": "rahim_yar_khan", "name_ur": "رحیم یار خان", "name_en": "Rahim Yar Khan"},
]
# Rahim Yar Khan rice is dropped for low coverage (docs/DATA_NOTES.md).
SERIES = [
    (c["id"], m["id"]) for c in CROPS for m in MANDIS if (c["id"], m["id"]) != ("rice", "rahim_yar_khan")
]

FIRST_WEEK = date(2022, 1, 2)  # a Sunday: every date is a week-ending Sunday
LAST_WEEK = date(2026, 10, 4)
FIRST_FORECAST_INDEX = 12  # forecasts start once there are 12 weeks of history

# Synthetic levels, Rs per 40 kg. Chosen only so the charts look sensible.
SYNTHETIC_LEVEL = {"wheat": 3500.0, "rice": 3000.0, "cotton": 8000.0}

REPLAY_CASES = [
    {
        "case_id": "wheat_2024_crash", "crop": "wheat", "mandi": "vehari",
        "start": date(2024, 2, 4), "end": date(2024, 7, 28),
        "title_ur": "گندم 2024 (عارضی ڈیٹا)",
        "title_en": "Wheat 2024 crash (placeholder data)",
    },
    {
        "case_id": "cotton_2022_floods", "crop": "cotton", "mandi": "rahim_yar_khan",
        "start": date(2022, 7, 3), "end": date(2022, 12, 25),
        "title_ur": "کپاس، 2022 کا سیلاب (عارضی ڈیٹا)",
        "title_en": "Cotton, 2022 floods (placeholder data)",
    },
]
REPLAY_SUMMARY_UR = "عارضی: یہ مراحل مصنوعی قیمتوں سے بنے ہیں، اصل بحران سے نہیں۔"
REPLAY_SUMMARY_EN = "Placeholder: these steps come from synthetic prices, not the real crisis."

PLACEHOLDER_EVENTS = [
    {
        "date": "2024-04-07", "active_until": "2024-06-30", "event_type": "other",
        "crops": ["wheat"], "direction": "unclear", "region": PLACEHOLDER,
        "headline": "Placeholder event for testing the UI. Not real news.",
        "source_url": None, "confidence": "low", "is_synthetic": True,
    },
    {
        "date": "2026-09-20", "active_until": "2026-10-31", "event_type": "other",
        "crops": ["cotton"], "direction": "unclear", "region": PLACEHOLDER,
        "headline": "Placeholder event for testing the UI. Not real news.",
        "source_url": None, "confidence": "low", "is_synthetic": True,
    },
]

# Placeholder costs. Owner B replaces these with values from data/economics_inputs.json.
PLACEHOLDER_STORAGE = {  # storage -> (Rs per maund per week, spoilage % per week)
    "home": (3.5, 0.2),
    "cold_store": (6.0, 0.05),
    "warehouse": (5.0, 0.1),
}
PLACEHOLDER_FINANCE_PCT_MONTH = 1.4
PLACEHOLDER_TRANSPORT = {  # Rs per maund, symmetric
    ("bahawalpur", "vehari"): 145.0,
    ("bahawalpur", "rahim_yar_khan"): 250.0,
    ("vehari", "rahim_yar_khan"): 375.0,
}


def weeks() -> list[date]:
    out, d = [], FIRST_WEEK
    while d <= LAST_WEEK:
        out.append(d)
        d += timedelta(days=7)
    return out


def synthetic_prices(crop: str, mandi: str, dates: list[date]) -> list[float]:
    """Seasonal cycle plus a random walk. Seeded per series so output is reproducible."""
    rng = random.Random(f"{SEED}-{crop}-{mandi}")
    level = SYNTHETIC_LEVEL[crop] * rng.uniform(0.95, 1.05)
    walk, out = 0.0, []
    for d in dates:
        walk += rng.gauss(0, 0.015)
        walk *= 0.98  # pull back towards the level so prices stay plausible
        seasonal = 0.06 * math.sin(2 * math.pi * d.timetuple().tm_yday / 365.25)
        out.append(round(level * (1 + seasonal + walk)))
    return out


def band_for(prices: list[float], i: int) -> list[dict]:
    p = prices[i]
    momentum = (p / prices[i - 4] - 1) * 0.25
    band = []
    for h in HORIZONS:
        q50 = p * (1 + momentum * h / 4)
        spread = p * 0.03 * math.sqrt(h)
        band.append({
            "weeks_ahead": h,
            "q10": round(q50 - 1.2816 * spread),
            "q50": round(q50),
            "q90": round(q50 + 1.2816 * spread),
        })
    return band


def tier_for(indicator: float) -> str:
    a = abs(indicator)  # PLAN.md 7.5 thresholds, applied in both directions
    if a < 0.25:
        return "normal"
    if a < 1:
        return "stress"
    if a < 2:
        return "alert"
    return "crisis"


def events_active(events: list[dict], crop: str, on: date) -> list[dict]:
    return [
        e for e in events
        if crop in e["crops"] and date.fromisoformat(e["date"]) <= on <= date.fromisoformat(e["active_until"])
    ]


def build_placeholder() -> dict[str, dict]:
    dates = weeks()
    labels = {"data_source": PLACEHOLDER, "is_synthetic": True}

    series_out, alarms, prices_by_series = [], [], {}
    for crop, mandi in SERIES:
        prices = synthetic_prices(crop, mandi, dates)
        prices_by_series[(crop, mandi)] = prices
        forecasts = [
            {
                "as_of": dates[i].isoformat(),
                "price_now": prices[i],
                "forecast": band_for(prices, i),
                "naive": [{"weeks_ahead": h, "price": prices[i]} for h in HORIZONS],
                "model": MODEL_NAME,
                "mase_vs_naive": None,
            }
            for i in range(FIRST_FORECAST_INDEX, len(dates))
        ]
        series_out.append({
            "crop": crop,
            "mandi": mandi,
            "history": [{"date": d.isoformat(), "price": p} for d, p in zip(dates, prices, strict=True)],
            "forecasts": forecasts,
        })
        # Placeholder alarm: distance from the trailing-year mean in standard deviations.
        # Starts with the forecasts so every replay step has a real tier, never a default.
        for i in range(FIRST_FORECAST_INDEX, len(dates)):
            window = prices[max(0, i - 52):i]
            spread = statistics.pstdev(window) or 1.0
            indicator = (prices[i] - statistics.fmean(window)) / spread
            flags = ["yoy_drop_over_50pct"] if i >= 52 and prices[i] < 0.5 * prices[i - 52] else []
            alarms.append({
                "crop": crop, "mandi": mandi, "date": dates[i].isoformat(),
                "indicator": round(indicator, 3), "tier": tier_for(indicator), "flags": flags,
            })

    alarm_index = {(a["crop"], a["mandi"], a["date"]): a["tier"] for a in alarms}
    home_cost, home_spoil = PLACEHOLDER_STORAGE["home"]
    replay_costs = Costs(home_cost, home_spoil, PLACEHOLDER_FINANCE_PCT_MONTH)

    cases = []
    for case in REPLAY_CASES:
        crop, mandi = case["crop"], case["mandi"]
        prices = prices_by_series[(crop, mandi)]
        steps = []
        for i, d in enumerate(dates):
            if not (case["start"] <= d <= case["end"]):
                continue
            band = band_for(prices, i)
            active = events_active(PLACEHOLDER_EVENTS, crop, d)
            decision = decide(DecisionInput(
                price_now=prices[i],
                band=[BandPoint(**b) for b in band],
                can_store=True,
                costs=replay_costs,
                alert_active=bool(active),
            ))
            h4 = band[-1]
            steps.append({
                "as_of": d.isoformat(),
                "price_now": prices[i],
                "forecast_q10": h4["q10"], "forecast_q50": h4["q50"], "forecast_q90": h4["q90"],
                "verdict": decision.verdict,
                "alarm_tier": alarm_index[(crop, mandi, d.isoformat())],
                "events_active": [
                    {"event_type": e["event_type"], "headline": e["headline"], "source_url": e["source_url"]}
                    for e in active
                ],
                "actual_price_4w_later": prices[i + 4] if i + 4 < len(prices) else None,
            })
        cases.append({
            "case_id": case["case_id"], "crop": crop, "mandi": mandi,
            "title_ur": case["title_ur"], "title_en": case["title_en"],
            "summary_ur": REPLAY_SUMMARY_UR, "summary_en": REPLAY_SUMMARY_EN,
            "steps": steps,
        })

    transport = []
    for (a, b), cost in PLACEHOLDER_TRANSPORT.items():
        transport.append({"from_mandi": a, "to_mandi": b, "cost_per_maund": cost, "source": PLACEHOLDER})
        transport.append({"from_mandi": b, "to_mandi": a, "cost_per_maund": cost, "source": PLACEHOLDER})

    meta = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": LAST_WEEK.isoformat(),
        "crops": CROPS,
        "mandis": MANDIS,
        "series": [{"crop": c, "mandi": m} for c, m in SERIES],
        "replay_cases": [
            {k: c[k] for k in ("case_id", "crop", "mandi", "title_ur", "title_en")} for c in REPLAY_CASES
        ],
        "date_range": {"start": dates[0].isoformat(), "end": dates[-1].isoformat()},
        "latest_as_of": dates[-1].isoformat(),
        "unit": "40kg",
        "price_type": "wholesale",
        "models": [{"name": MODEL_NAME, "version": "0", "role": "placeholder"}],
        "assumptions": {
            "finance_cost_pct_month": {"value": PLACEHOLDER_FINANCE_PCT_MONTH, "source": PLACEHOLDER},
            "storage_defaults": [
                {
                    "crop": c["id"], "storage": s,
                    "storage_cost_per_maund_week": cost, "spoilage_pct_week": spoil, "source": PLACEHOLDER,
                }
                for c in CROPS for s, (cost, spoil) in PLACEHOLDER_STORAGE.items()
            ],
            "transport": transport,
        },
        **labels,
    }

    backtest = {
        "schema_version": SCHEMA_VERSION,
        "horizon_weeks": max(HORIZONS),
        "cutoffs": [],
        "metrics": [
            {
                "crop": c, "mandi": m, "model": MODEL_NAME,
                "mase": None, "quantile_loss": None, "coverage_80": None, "n_forecasts": 0,
            }
            for c, m in SERIES
        ],
        "rupee_backtest": None,
        "limitations": ["Placeholder artifact: no backtest has been run yet."],
        **labels,
    }

    return {
        "meta.json": meta,
        "forecasts.json": {"schema_version": SCHEMA_VERSION, "series": series_out, **labels},
        "alarms.json": {"schema_version": SCHEMA_VERSION, "alarms": alarms, "events": PLACEHOLDER_EVENTS, **labels},
        "replay.json": {"schema_version": SCHEMA_VERSION, "cases": cases, **labels},
        "backtest.json": backtest,
    }


def write_artifacts(files: dict[str, dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in files.items():
        # Big files are written compactly; small ones are indented for readable diffs.
        # encoding="utf-8" is required: Windows would otherwise mangle the Urdu.
        indent = None if name in ("forecasts.json", "alarms.json") else 2
        text = json.dumps(payload, ensure_ascii=False, indent=indent)
        (out_dir / name).write_text(text + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {out_dir / name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--placeholder", action="store_true", help="write synthetic placeholder artifacts")
    parser.add_argument("--out", type=Path, default=ARTIFACTS_DIR, help="output directory")
    args = parser.parse_args(argv)
    if not args.placeholder:
        print("The real pipeline is not built yet. Use --placeholder.", file=sys.stderr)
        return 1
    write_artifacts(build_placeholder(), args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
