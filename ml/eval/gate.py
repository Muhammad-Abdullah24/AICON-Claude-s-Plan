"""Evaluation gate (NFR-01): does a forecast beat the naive baseline on real held-out rows?

Usage (repo root):
    .venv/Scripts/python -m ml.eval.gate                                    # baselines only, validation
    .venv/Scripts/python -m ml.eval.gate --predictions preds.csv --model xgb  # score a model on validation
    .venv/Scripts/python -m ml.eval.gate --predictions preds.csv --model xgb --split test --final
                                                                            # once, at the very end

Predictions contract (Owner B writes, this gate reads): a CSV with one row per features.csv row to score,
    series, week_start, pred_price_next_4w, q10, q90      (Rs per 40 kg; q10/q90 may be empty)
Every row of the chosen split must have a prediction, so a model cannot pick its easy rows.
"""

import argparse
import csv
import hashlib
import json
import math
from collections.abc import Callable, Iterable
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEATURES_PATH = ROOT / "data" / "processed" / "features.csv"
EVAL_DIR = Path(__file__).resolve().parent
REPORT_JSON = EVAL_DIR / "report.json"
REPORT_MD = EVAL_DIR / "report.md"
TEST_REPORT_JSON = EVAL_DIR / "report_test.json"

MOVE_THRESHOLD_PCT = 3       # directional accuracy counts only moves bigger than this
TARGET_COVERAGE = 0.80       # a q10-q90 band should hold the real price about 80% of the time
MIN_ROWS_FOR_A_VERDICT = 20  # fewer rows than this: shown, but flagged as too few to judge
SEASON_WEEKS = 52


# ---------------------------------------------------------------- data

def load_rows(path: Path = FEATURES_PATH) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["is_synthetic"] == "0"]
    for r in rows:
        r["price"] = float(r["price_rs_per_40kg"])
        r["actual"] = float(r["price_next_4w"])
    return rows


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _weekly_prices(rows: Iterable[dict]) -> dict[str, dict[date, float]]:
    """Every known weekly price per series, from the rows themselves and their 4-week targets."""
    prices: dict[str, dict[date, float]] = {}
    for r in rows:
        s = prices.setdefault(r["series"], {})
        s[date.fromisoformat(r["week_start"])] = r["price"]
        s[date.fromisoformat(r["target_week"])] = r["actual"]
    return prices


# ---------------------------------------------------------------- baselines

def _quantile(sorted_values: list[float], q: float) -> float:
    pos = (len(sorted_values) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def change_quantiles(train_rows: Iterable[dict], q_low: float = 0.10, q_high: float = 0.90) -> dict[str, tuple]:
    """Empirical q10/q90 of the 4-week % change per crop option, from TRAIN rows only."""
    changes: dict[str, list[float]] = {}
    for r in train_rows:
        changes.setdefault(r["crop_option"], []).append(float(r["price_change_4w_pct"]))
    return {k: (_quantile(sorted(v), q_low), _quantile(sorted(v), q_high)) for k, v in changes.items()}


def persistence(rows: list[dict], band: dict[str, tuple] | None = None) -> dict[tuple, dict]:
    """Price in 4 weeks = today's price. With `band`, adds the empirical q10-q90 range (the B4 fallback)."""
    out = {}
    for r in rows:
        p = {"pred": r["price"], "q10": None, "q90": None}
        if band and r["crop_option"] in band:
            lo, hi = band[r["crop_option"]]
            p["q10"], p["q90"] = r["price"] * (1 + lo / 100), r["price"] * (1 + hi / 100)
        out[(r["series"], r["week_start"])] = p
    return out


def seasonal_naive(rows: list[dict], history: list[dict]) -> tuple[dict[tuple, dict], int]:
    """Apply last year's 4-week change to today's price; persistence where last year is missing.

    `history` must only be rows at or before each row's own date for this to be fair; we look up prices
    52 and 48 weeks back, which are always in the past. Returns predictions and how many rows had last year.
    """
    weekly = _weekly_prices(history)
    out, used = {}, 0
    for r in rows:
        w = date.fromisoformat(r["week_start"])
        s = weekly.get(r["series"], {})
        a, b = s.get(w - timedelta(weeks=SEASON_WEEKS)), s.get(w - timedelta(weeks=SEASON_WEEKS - 4))
        if a and b:
            pred, used = r["price"] * b / a, used + 1
        else:
            pred = r["price"]
        out[(r["series"], r["week_start"])] = {"pred": pred, "q10": None, "q90": None}
    return out, used


def load_predictions(path: Path) -> dict[tuple, dict]:
    out = {}
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out[(r["series"], r["week_start"])] = {
                "pred": float(r["pred_price_next_4w"]),
                "q10": float(r["q10"]) if r.get("q10") not in (None, "") else None,
                "q90": float(r["q90"]) if r.get("q90") not in (None, "") else None,
            }
    return out


# ---------------------------------------------------------------- metrics

def metrics(rows: list[dict], preds: dict[tuple, dict], naive: dict[tuple, dict]) -> dict:
    n = len(rows)
    if n == 0:
        return {"n": 0}
    abs_err, naive_err, ape, dir_hits, dir_n = 0.0, 0.0, 0.0, 0, 0
    covered, band_n, width, pinball = 0, 0, 0.0, 0.0
    for r in rows:
        key = (r["series"], r["week_start"])
        p, base = preds[key], naive[key]
        actual, today = r["actual"], r["price"]
        abs_err += abs(p["pred"] - actual)
        naive_err += abs(base["pred"] - actual)
        ape += abs(p["pred"] - actual) / actual
        actual_change = (actual / today - 1) * 100
        if abs(actual_change) > MOVE_THRESHOLD_PCT:
            dir_n += 1
            dir_hits += (p["pred"] - today) * (actual - today) > 0
        if p["q10"] is not None and p["q90"] is not None:
            band_n += 1
            covered += p["q10"] <= actual <= p["q90"]
            width += (p["q90"] - p["q10"]) / today
            pinball += (_pinball(actual, p["q10"], 0.10) + _pinball(actual, p["q90"], 0.90)) / today
    return {
        "n": n,
        "mape_pct": 100 * ape / n,
        "mae_rs": abs_err / n,
        "mase_vs_persistence": (abs_err / naive_err) if naive_err else None,
        "directional_accuracy": (dir_hits / dir_n) if dir_n else None,
        "moves_over_3pct": dir_n,
        "band_coverage": (covered / band_n) if band_n else None,
        "band_width_pct": (100 * width / band_n) if band_n else None,
        "pinball_loss_pct": (100 * pinball / (2 * band_n)) if band_n else None,
        "enough_rows": n >= MIN_ROWS_FOR_A_VERDICT,
    }


def _pinball(actual: float, q_pred: float, q: float) -> float:
    diff = actual - q_pred
    return max(q * diff, (q - 1) * diff)


def _groups(rows: list[dict], key: Callable[[dict], str]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(key(r), []).append(r)
    return dict(sorted(out.items()))


def score(rows: list[dict], preds: dict[tuple, dict], naive: dict[tuple, dict]) -> dict:
    return {
        "pooled": metrics(rows, preds, naive),
        "by_crop_option": {k: metrics(v, preds, naive) for k, v in _groups(rows, lambda r: r["crop_option"]).items()},
        "by_series": {k: metrics(v, preds, naive) for k, v in _groups(rows, lambda r: r["series"]).items()},
    }


def verdict(model: dict, baseline: dict) -> dict:
    """PASS only if the model's pooled MAPE beats persistence's on the same rows (NFR-01)."""
    m, b = model["pooled"], baseline["pooled"]
    crops_beaten = {k: v["mape_pct"] < baseline["by_crop_option"][k]["mape_pct"]
                    for k, v in model["by_crop_option"].items()}
    return {
        "passes_nfr01": m["mape_pct"] < b["mape_pct"],
        "model_mape_pct": m["mape_pct"],
        "persistence_mape_pct": b["mape_pct"],
        "mape_improvement_pct_points": b["mape_pct"] - m["mape_pct"],
        "crop_options_beating_persistence": crops_beaten,
        "rule": "Deploy only if pooled MAPE on real validation rows is below persistence (blueprint NFR-01). "
                "Otherwise ship the labelled persistence-band fallback (docs/PLAN.md B4).",
    }


# ---------------------------------------------------------------- report

def build_report(split: str = "val", predictions: dict | None = None, model_name: str | None = None,
                 rows: list[dict] | None = None, features_sha: str | None = None) -> dict:
    rows = load_rows() if rows is None else rows
    train = [r for r in rows if r["split"] == "train"]
    target = [r for r in rows if r["split"] == split]
    # Seasonal naive only looks 52 and 48 weeks back, so every price it uses was known at forecast time.
    history = rows
    band = change_quantiles(train)

    naive = persistence(target)
    models = {
        "persistence": (naive, "Price in 4 weeks = today's price"),
        "persistence_band": (persistence(target, band), "Persistence with the q10-q90 of train-set 4-week changes"),
    }
    seasonal, seasonal_used = seasonal_naive(target, history)
    models["seasonal_naive"] = (seasonal, f"Last year's 4-week change applied to today's price "
                                          f"({seasonal_used} of {len(target)} rows had last year; rest = persistence)")
    if predictions is not None:
        missing = [k for k in ((r["series"], r["week_start"]) for r in target) if k not in predictions]
        if missing:
            raise ValueError(f"{len(missing)} {split} rows have no prediction, e.g. {missing[:3]}")
        models[model_name or "model"] = (predictions, "Owner B model")

    scored = {name: {"description": desc, **score(target, p, naive)} for name, (p, desc) in models.items()}
    report = {
        "split": split,
        "rows": len(target),
        "features_csv_sha256": features_sha or file_sha256(FEATURES_PATH),
        "train_change_quantiles_pct": {k: {"q10": v[0], "q90": v[1]} for k, v in band.items()},
        "models": scored,
    }
    if predictions is not None:
        report["verdict"] = verdict(scored[model_name or "model"], scored["persistence"])
    return report


def _fmt(x, pct=False, digits=2) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return "yes" if x else "no"
    return f"{100 * x:.0f}%" if pct else f"{x:.{digits}f}"


def to_markdown(report: dict) -> str:
    lines = [f"# Evaluation report ({report['split']} split, {report['rows']} real rows)", "",
             "Generated by `python -m ml.eval.gate`. MASE below 1 means better than persistence.", "",
             "## Pooled", "",
             "| Model | MAPE % | MASE | Direction (moves > 3%) | Band coverage | Band width % |",
             "|---|---|---|---|---|---|"]
    for name, m in report["models"].items():
        p = m["pooled"]
        lines.append(f"| {name} | {_fmt(p['mape_pct'])} | {_fmt(p['mase_vs_persistence'])} | "
                     f"{_fmt(p['directional_accuracy'], pct=True)} | {_fmt(p['band_coverage'], pct=True)} | "
                     f"{_fmt(p['band_width_pct'], digits=1)} |")
    lines += ["", "## MAPE % by crop option", "",
              "| Crop | Rows | " + " | ".join(report["models"]) + " |",
              "|---|---|" + "---|" * len(report["models"])]
    crops = next(iter(report["models"].values()))["by_crop_option"]
    for crop, m in crops.items():
        cells = " | ".join(_fmt(v["by_crop_option"][crop]["mape_pct"]) for v in report["models"].values())
        flag = "" if m["enough_rows"] else " (too few rows)"
        lines.append(f"| {crop}{flag} | {m['n']} | {cells} |")
    if "verdict" in report:
        v = report["verdict"]
        lines += ["", "## Verdict (NFR-01)", "",
                  f"**{'PASS' if v['passes_nfr01'] else 'FAIL'}**: model MAPE {_fmt(v['model_mape_pct'])}% vs "
                  f"persistence {_fmt(v['persistence_mape_pct'])}%.", "", v["rule"]]
    lines += ["", "Persistence scores 0% on direction by definition: it never predicts a move."]
    lines += ["", "Limits: a backtest on historical AMIS prices, not a field trial. Series with fewer than "
              f"{MIN_ROWS_FOR_A_VERDICT} rows are shown but not judged."]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--predictions", type=Path)
    ap.add_argument("--model", default="model")
    ap.add_argument("--split", choices=["val", "test"], default="val")
    ap.add_argument("--final", action="store_true", help="required to touch the test split")
    args = ap.parse_args()

    if args.split == "test":
        if not args.final:
            raise SystemExit("The test split is used once, at the end. Re-run with --final if that is now.")
        if TEST_REPORT_JSON.exists():
            raise SystemExit(f"{TEST_REPORT_JSON.name} already exists: the test split has been used. "
                             "Delete it only with the team's agreement.")
    preds = load_predictions(args.predictions) if args.predictions else None
    report = build_report(args.split, preds, args.model)
    json_path = TEST_REPORT_JSON if args.split == "test" else REPORT_JSON
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    if args.split == "val":
        REPORT_MD.write_text(to_markdown(report), encoding="utf-8", newline="\n")
    print(to_markdown(report))
    print(f"written: {json_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
