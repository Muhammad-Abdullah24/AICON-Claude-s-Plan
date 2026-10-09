"""Evaluate the selling action plan (ml/decision/policy.py) out of sample, and record the hold gate's evidence.

Usage (repo root):  .venv/Scripts/python -m ml.forecast.policy_eval

Two out-of-sample periods, both time-respecting; the 2026 test split is NOT used (it was scored once, for the
forecast, and is not reused to tune a policy):
- CV 2021-2024: rolling origin inside the train split (fit on earlier target weeks, score the next year);
- Validation 2025: the model trained on the train split, scored on the val split.

For each period it reports, per crop option and scenario (storage available or not):
- the plan's recommended action and mode counts;
- how often the upside watch appears;
- the hold gate's evidence: of wheat weeks with an UP call on a non-frozen price, the share where holding
  4 weeks beat the interest cost, and the realized result after interest per 40 kg retained;
- frozen-price exclusions.
Writes artifacts/models/policy_eval.json; the hold gate reads `hold_gate_evidence` from it.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

from ml.decision import action_plan, config, inputs
from ml.forecast import train, tune
from ml.forecast.predict import DIRECTION_CROP_OPTIONS

OUT = Path(__file__).resolve().parents[2] / "artifacts" / "models" / "policy_eval.json"
SCENARIOS = {"no_storage": {"storage_available": False}, "storage": {"storage_available": True}}

LIMITS = [
    "A backtest on historical AMIS weekly prices, not a field trial.",
    "Only the interest cost of holding is counted; storage loss, godown fees and transport are not, so real "
    "holding results are worse than shown.",
    "Historical weeks always have an observed price, so the stale-data rule (price older than 8 weeks) does not "
    "occur here; frozen AMIS stretches are excluded from the hold evidence and flagged in the action counts.",
    "The 2026 test split is not used.",
    "The direction model gives only a sign, no probability, so no confidence threshold is applied.",
]


def _rows_with_calls() -> dict[str, list[tuple[dict, float]]]:
    """Out-of-sample (row, predicted 4-week % change) pairs for each period."""
    cfg = train.CONFIG
    cv = []
    for _, fit_rows, score_rows in tune.folds(train.load_split("train")):
        model = train.fit(train.training_rows(fit_rows, cfg), config=cfg)
        cv += list(zip(score_rows, map(float, train.predict_change(model, score_rows)), strict=True))
    model = train.fit(train.training_rows(train.load_split("train"), cfg), config=cfg)
    val_rows = train.load_split("val")
    val = list(zip(val_rows, map(float, train.predict_change(model, val_rows)), strict=True))
    return {"cv_2021_2024": cv, "validation_2025": val}


def _hold_stats(pairs: list[tuple[dict, float]], carry_pct: float) -> dict:
    """Wheat weeks with an UP call on a non-frozen price: did holding 4 weeks beat the interest cost?"""
    moves = [float(r["price_change_4w_pct"]) for r, c in pairs
             if r["crop_option"] in DIRECTION_CROP_OPTIONS and c > 0 and not train.is_frozen(r)]
    if not moves:
        return {"weeks": 0}
    net = [m - carry_pct for m in moves]
    return {
        "weeks": len(moves),
        "beat_carry_weeks": sum(n > 0 for n in net),
        "beat_carry_pct": round(100 * sum(n > 0 for n in net) / len(net), 1),
        "mean_net_pct": round(statistics.fmean(net), 2),
        "median_net_pct": round(statistics.median(net), 2),
        "worst_net_pct": round(min(net), 2),
        "best_net_pct": round(max(net), 2),
    }


def evaluate() -> dict:
    rate = inputs.interest_pct_per_year()
    carry_pct = rate * config.HORIZON_WEEKS / 52
    periods = {}
    for name, pairs in _rows_with_calls().items():
        scen = {}
        for sname, kw in SCENARIOS.items():
            actions, modes, watch_by_crop = Counter(), Counter(), Counter()
            for r, change in pairs:
                direction = ({"call": "UP" if change > 0 else "DOWN"}
                             if r["crop_option"] in DIRECTION_CROP_OPTIONS else None)
                plan = action_plan(
                    r["crop_option"], 100, float(r["price_rs_per_40kg"]), None, direction,
                    is_stale=False, is_frozen=train.is_frozen(r), interest_pct_per_year=rate,
                    prices_as_of=date.fromisoformat(r["week_start"]), hold_evidence=None, **kw,
                )
                actions[plan["recommended_action"]] += 1
                modes[plan["mode"]] += 1
                if plan["upside_watch"]:
                    watch_by_crop[r["crop_option"]] += 1
            scen[sname] = {"actions": dict(actions), "modes": dict(modes),
                           "upside_watch_by_crop": dict(watch_by_crop)}
        periods[name] = {
            "weeks": len(pairs),
            "frozen_weeks": sum(train.is_frozen(r) for r, _ in pairs),
            "scenarios": scen,
            "hold_if_wheat_up": _hold_stats(pairs, carry_pct),
        }
    beat = [p["hold_if_wheat_up"]["beat_carry_pct"] for p in periods.values() if p["hold_if_wheat_up"]["weeks"]]
    return {
        "written_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "carry_pct_4w": round(carry_pct, 3),
        "interest_pct_per_year": rate,
        "periods": periods,
        "hold_gate_evidence": {
            "beat_carry_pct_min": min(beat) if beat else None,
            "beat_carry_pct_by_period": {k: v["hold_if_wheat_up"].get("beat_carry_pct") for k, v in periods.items()},
            "required_beat_carry_pct": config.HOLD_GATE_MIN_BEAT_CARRY_PCT,
            "source": "artifacts/models/policy_eval.json (ml.forecast.policy_eval; CV 2021-2024 and validation 2025)",
        },
        "limits": LIMITS,
    }


def main() -> dict:
    report = evaluate()
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("carry_pct_4w", "hold_gate_evidence")}, indent=2))
    for name, p in report["periods"].items():
        print(name, "weeks", p["weeks"], "frozen", p["frozen_weeks"], "hold-if-UP", p["hold_if_wheat_up"])
        for sname, s in p["scenarios"].items():
            print("  ", sname, s["actions"], s["modes"], "watch:", s["upside_watch_by_crop"])
    print(f"wrote {OUT}")
    return report


if __name__ == "__main__":
    main()
