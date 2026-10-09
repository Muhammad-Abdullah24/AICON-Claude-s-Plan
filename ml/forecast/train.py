"""B3 training scaffold (Owner B): XGBoost on the real rows of features.csv.

Usage (repo root):
    .venv/Scripts/python -m ml.forecast.train                      # point model, scores on validation
    .venv/Scripts/python -m ml.forecast.train --quantiles          # also the q10 and q90 models
    .venv/Scripts/python -m ml.forecast.train --quantiles --predictions preds.csv
                                                                   # file for: python -m ml.eval.gate
    .venv/Scripts/python -m ml.forecast.train --save               # write models to artifacts/models/

Design choices:
- Target is the 4-week % change (price_change_4w_pct), not the price: prices rose about 3x over
  2015-2026, so a model on price levels would be extrapolating. The price forecast is
  today's price x (1 + predicted change / 100).
- Inputs are FEATURE_COLUMNS minus absolute price levels (same reason). The frozen-price flags are
  not in FEATURE_COLUMNS, so they can never be inputs (hand-off H-B8).
- Training uses real rows only (is_synthetic = 0) from the `train` split. The `val` split is scored
  and never used for fitting or early stopping. The `test` split is not touched here (A5's gate,
  once, at the end).
- Fixed seed, so the same data gives the same model.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import xgboost as xgb

from ml.features import FEATURE_COLUMNS

ROOT = Path(__file__).resolve().parents[2]
FEATURES_PATH = ROOT / "data" / "processed" / "features.csv"
MODELS_DIR = ROOT / "artifacts" / "models"
DEPLOYED_PATH = MODELS_DIR / "deployed.json"
GATE_REPORT = ROOT / "ml" / "eval" / "report.json"
BASELINES = {"persistence", "persistence_band", "seasonal_naive"}

TARGET = "price_change_4w_pct"
SEED = 42

# Absolute price levels: excluded because the target is a % change and the price level tripled.
LEVEL_COLUMNS = {
    "price_rs_per_40kg", "price_lag_1w", "price_lag_2w", "price_lag_4w", "price_lag_8w", "price_lag_12w",
    "price_ma_4w", "price_ma_8w", "price_ma_12w",
}
MODEL_FEATURES = [c for c in FEATURE_COLUMNS if c not in LEVEL_COLUMNS]

# Model settings. Chosen by ml/forecast/tune.py on the training years only; see docs/MODEL_CARD.md.
CONFIG = {
    "objective": "reg:absoluteerror",
    "max_depth": 3,
    "num_rounds": 100,
    "drop_frozen": False,  # leave out rows whose price or target week is a frozen AMIS price (H-B8)
}
# Fixed booster settings, small for about 2,700 training rows.
BOOSTER = {
    "eta": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "seed": SEED,
    "nthread": 1,  # one thread keeps results reproducible across machines
}
QUANTILES = {"q10": 0.10, "q90": 0.90}


def _number(value: str) -> float:
    return float(value) if value not in ("", None) else math.nan


def load_split(split: str, path: Path = FEATURES_PATH) -> list[dict]:
    """Real rows of one split (train / val). Rows without a target cannot be learned from or scored."""
    if split == "test":
        raise ValueError("the test split is scored once, by ml.eval.gate --split test --final")
    with path.open(encoding="utf-8", newline="") as f:
        return [
            r for r in csv.DictReader(f)
            if r["split"] == split and r["is_synthetic"] == "0" and r[TARGET] != ""
        ]


def matrix(rows: list[dict]) -> np.ndarray:
    return np.array([[_number(r[c]) for c in MODEL_FEATURES] for r in rows], dtype=float)


def target(rows: list[dict]) -> np.ndarray:
    return np.array([float(r[TARGET]) for r in rows], dtype=float)


def is_frozen(r: dict) -> bool:
    return r.get("price_is_frozen") == "1" or r.get("target_is_frozen") == "1"


def training_rows(rows: list[dict], config: dict = CONFIG) -> list[dict]:
    return [r for r in rows if not is_frozen(r)] if config["drop_frozen"] else rows


def fit(rows: list[dict], quantile: float | None = None, config: dict = CONFIG) -> xgb.Booster:
    """Point model with config["objective"] or, with `quantile`, a quantile model of the 4-week % change."""
    params = {**BOOSTER, "max_depth": config["max_depth"]}
    if quantile is None:
        params["objective"] = config["objective"]
    else:
        params.update(objective="reg:quantileerror", quantile_alpha=quantile)
    data = xgb.DMatrix(matrix(rows), label=target(rows), feature_names=MODEL_FEATURES)
    return xgb.train(params, data, num_boost_round=config["num_rounds"])


def predict_change(model: xgb.Booster, rows: list[dict]) -> np.ndarray:
    return model.predict(xgb.DMatrix(matrix(rows), feature_names=MODEL_FEATURES))


def to_prices(rows: list[dict], change_pct: np.ndarray) -> np.ndarray:
    today = np.array([float(r["price_rs_per_40kg"]) for r in rows])
    return today * (1 + change_pct / 100)


def mape(rows: list[dict], predicted_price: np.ndarray) -> float:
    actual = np.array([float(r["price_next_4w"]) for r in rows])
    return float(np.mean(np.abs(predicted_price - actual) / actual) * 100)


def persistence_mape(rows: list[dict]) -> float:
    return mape(rows, np.array([float(r["price_rs_per_40kg"]) for r in rows]))


def write_predictions(path: Path, rows: list[dict], point: np.ndarray, bands: dict[str, np.ndarray]) -> None:
    """The gate's predictions contract: series, week_start, pred_price_next_4w, q10, q90 (Rs per 40 kg)."""
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["series", "week_start", "pred_price_next_4w", "q10", "q90"])
        for i, r in enumerate(rows):
            q10 = f"{bands['q10'][i]:.2f}" if "q10" in bands else ""
            q90 = f"{bands['q90'][i]:.2f}" if "q90" in bands else ""
            w.writerow([r["series"], r["week_start"], f"{point[i]:.2f}", q10, q90])


def direction_accuracy(rows: list[dict], change_pct: np.ndarray, min_move_pct: float = 3.0) -> dict:
    """% of real moves bigger than `min_move_pct` whose sign the model called right, per crop option."""
    hits: dict[str, list[bool]] = {}
    for r, c in zip(rows, change_pct, strict=True):
        actual = float(r[TARGET])
        if abs(actual) > min_move_pct:
            for key in ("all", r["crop_option"]):
                hits.setdefault(key, []).append((c > 0) == (actual > 0))
    return {k: {"pct": round(sum(v) / len(v) * 100, 1), "moves": len(v)} for k, v in sorted(hits.items())}


def save(models: dict[str, xgb.Booster], scores: dict) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for name, model in models.items():
        model.save_model(MODELS_DIR / f"price_{name}.json")
    trained_at = datetime.now(UTC)
    meta = {
        "version": f"xgb-{trained_at:%Y%m%d}",
        "trained_at": trained_at.isoformat(timespec="seconds"),
        "target": TARGET,
        "features": MODEL_FEATURES,
        "config": CONFIG,
        "booster": BOOSTER,
        "quantiles": {k: v for k, v in QUANTILES.items() if k in models},
        "training_rows": scores["train_rows"],
        "validation": scores,
        "direction_accuracy_pct": {k: v["pct"] for k, v in scores.get("direction", {}).items()},
        "xgboost_version": xgb.__version__,
    }
    (MODELS_DIR / "price_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def write_fallback(report_path: Path = GATE_REPORT) -> dict:
    """Record that the persistence-band fallback is deployed, from the gate's latest validation report.

    Forecast = today's price; range = today's price moved by the q10 and q90 of the 4-week % changes in
    the train split, per crop option. The band comes from train rows only, exactly as ml.eval.gate scores it.
    """
    from ml.eval.gate import change_quantiles

    report = json.loads(report_path.read_text(encoding="utf-8"))
    verdict = report["verdict"]
    if verdict["passes_nfr01"]:
        raise ValueError("the model passed NFR-01: deploy it instead of the fallback")
    model = next(name for name in report["models"] if name not in BASELINES)
    gate_result = {
        "split": report["split"], "rows": report["rows"], "features_csv_sha256": report["features_csv_sha256"],
        "model": model, "passes_nfr01": False, "passes_excluding_frozen": verdict["passes_excluding_frozen"],
        "model_mape_pct": round(verdict["model_mape_pct"], 2),
        "persistence_mape_pct": round(verdict["persistence_mape_pct"], 2),
    }
    band = change_quantiles(load_split("train"))
    record = {
        "deployed": "persistence_band",
        "label": "baseline",
        "reason": "The XGBoost model did not beat persistence on pooled validation MAPE (NFR-01).",
        "band_change_pct": {k: {"q10": round(lo, 3), "q90": round(hi, 3)} for k, (lo, hi) in sorted(band.items())},
        "gate": gate_result,
        "written_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DEPLOYED_PATH.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quantiles", action="store_true", help="also train the q10 and q90 models")
    parser.add_argument("--predictions", type=Path, help="write validation predictions for ml.eval.gate")
    parser.add_argument("--save", action="store_true", help="save models to artifacts/models/")
    parser.add_argument("--drop-frozen", action="store_true", help="train without frozen-price rows (H-B8)")
    parser.add_argument("--record-fallback", action="store_true",
                        help="after a failed gate run, write artifacts/models/deployed.json for the fallback")
    args = parser.parse_args(argv)
    if args.record_fallback:
        record = write_fallback()
        print(f"deployed: {record['deployed']} -> {DEPLOYED_PATH}")
        return record
    config = {**CONFIG, "drop_frozen": args.drop_frozen or CONFIG["drop_frozen"]}

    train_rows, val_rows = training_rows(load_split("train"), config), load_split("val")
    models = {"point": fit(train_rows, config=config)}
    if args.quantiles:
        models.update({name: fit(train_rows, q, config) for name, q in QUANTILES.items()})

    val_change = predict_change(models["point"], val_rows)
    point = to_prices(val_rows, val_change)
    bands = {name: to_prices(val_rows, predict_change(models[name], val_rows)) for name in QUANTILES if name in models}
    scores = {
        "train_rows": len(train_rows),
        "val_rows": len(val_rows),
        "val_mape_pct": round(mape(val_rows, point), 2),
        "val_persistence_mape_pct": round(persistence_mape(val_rows), 2),
        "direction": direction_accuracy(val_rows, val_change),
    }
    if bands:
        actual = np.array([float(r["price_next_4w"]) for r in val_rows])
        lo, hi = np.minimum(bands["q10"], bands["q90"]), np.maximum(bands["q10"], bands["q90"])
        scores["val_band_coverage_pct"] = round(float(np.mean((actual >= lo) & (actual <= hi)) * 100), 1)

    print(json.dumps(scores, indent=2))
    print("Indicative only. The NFR-01 verdict is ml.eval.gate's (B4).")
    if args.predictions:
        write_predictions(args.predictions, val_rows, point, bands)
        print(f"wrote {args.predictions}")
    if args.save:
        save(models, scores)
        print(f"saved models to {MODELS_DIR}")
    return scores


if __name__ == "__main__":
    main()
