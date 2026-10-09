"""B4 model search (Owner B): pick the model settings on the TRAINING years only, never on validation.

Usage (repo root):
    .venv/Scripts/python -m ml.forecast.tune

Rolling-origin cross-validation inside the train split: for each fold year Y in CV_YEARS, fit on rows whose
target week is before Y and score rows whose target week falls in Y. The validation split (2025) is then
scored once, by ml.eval.gate, with the winning settings. Results go in docs/MODEL_CARD.md.
"""

from __future__ import annotations

import itertools
import json

import numpy as np

from ml.forecast import train

CV_YEARS = (2021, 2022, 2023, 2024)

GRID = {
    "objective": ["reg:squarederror", "reg:absoluteerror", "reg:pseudohubererror"],
    "max_depth": [2, 3, 4],
    "num_rounds": [100, 300],
    "drop_frozen": [False, True],
}


def folds(rows: list[dict]):
    for year in CV_YEARS:
        start, end = f"{year}-01-01", f"{year + 1}-01-01"
        fit_rows = [r for r in rows if r["target_week"] < start]
        score_rows = [r for r in rows if start <= r["target_week"] < end]
        if fit_rows and score_rows:
            yield year, fit_rows, score_rows


def cross_validate(rows: list[dict], config: dict) -> dict:
    """Pooled out-of-fold MAPE vs persistence, plus the out-of-fold change residuals for the band."""
    errors, naive_errors, residuals = [], [], []
    for _, fit_rows, score_rows in folds(rows):
        model = train.fit(train.training_rows(fit_rows, config), config=config)
        change = train.predict_change(model, score_rows)
        actual = np.array([float(r["price_next_4w"]) for r in score_rows])
        today = np.array([float(r["price_rs_per_40kg"]) for r in score_rows])
        errors += list(np.abs(today * (1 + change / 100) - actual) / actual * 100)
        naive_errors += list(np.abs(today - actual) / actual * 100)
        residuals += list(train.target(score_rows) - change)
    return {
        "cv_mape_pct": round(float(np.mean(errors)), 3),
        "cv_persistence_mape_pct": round(float(np.mean(naive_errors)), 3),
        "cv_rows": len(errors),
        "residuals": residuals,
    }


def main() -> list[dict]:
    rows = train.load_split("train")
    results = []
    for values in itertools.product(*GRID.values()):
        config = {**train.CONFIG, **dict(zip(GRID, values, strict=True))}
        scores = cross_validate(rows, config)
        scores.pop("residuals")
        results.append({**{k: config[k] for k in GRID}, **scores})
        print(json.dumps(results[-1]))
    results.sort(key=lambda r: r["cv_mape_pct"])
    print("\nbest 5 by cross-validated MAPE (persistence on the same rows: "
          f"{results[0]['cv_persistence_mape_pct']}%):")
    for r in results[:5]:
        print(json.dumps(r))
    return results


if __name__ == "__main__":
    main()
