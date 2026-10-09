import csv
import json

import pytest

# CI installs only the backend requirements; training needs ml/forecast/requirements.txt.
pytest.importorskip("xgboost")

from ml.forecast import train, tune  # noqa: E402

SMALL = {**train.CONFIG, "num_rounds": 10}


def test_inputs_exclude_price_levels_and_frozen_flags():
    assert not set(train.MODEL_FEATURES) & train.LEVEL_COLUMNS
    assert "price_is_frozen" not in train.MODEL_FEATURES
    assert "target_is_frozen" not in train.MODEL_FEATURES
    assert train.TARGET not in train.MODEL_FEATURES
    assert "momentum_4w_pct" in train.MODEL_FEATURES


def test_loads_real_rows_of_one_split_only():
    rows = train.load_split("train")
    assert rows
    assert {r["split"] for r in rows} == {"train"}
    assert {r["is_synthetic"] for r in rows} == {"0"}


def test_refuses_the_test_split():
    with pytest.raises(ValueError):
        train.load_split("test")


def test_drop_frozen_removes_frozen_rows():
    rows = train.load_split("train")
    kept = train.training_rows(rows, {**SMALL, "drop_frozen": True})
    assert 0 < len(kept) < len(rows)
    assert not any(train.is_frozen(r) for r in kept)
    assert train.training_rows(rows, {**SMALL, "drop_frozen": False}) == rows


def test_training_is_reproducible():
    rows = train.load_split("train")[:300]
    first = train.predict_change(train.fit(rows, config=SMALL), rows[:10])
    second = train.predict_change(train.fit(rows, config=SMALL), rows[:10])
    assert first.tolist() == second.tolist()


def test_cross_validation_never_fits_on_the_year_it_scores():
    for year, fit_rows, score_rows in tune.folds(train.load_split("train")):
        assert max(r["target_week"] for r in fit_rows) < f"{year}-01-01"
        assert {r["target_week"][:4] for r in score_rows} == {str(year)}


def test_predictions_file_matches_the_gate_contract(tmp_path):
    rows = train.load_split("val")[:5]
    model = train.fit(train.load_split("train")[:200], config=SMALL)
    point = train.to_prices(rows, train.predict_change(model, rows))
    path = tmp_path / "preds.csv"
    train.write_predictions(path, rows, point, {})
    with path.open(encoding="utf-8", newline="") as f:
        out = list(csv.DictReader(f))
    assert list(out[0]) == ["series", "week_start", "pred_price_next_4w", "q10", "q90"]
    assert [r["series"] for r in out] == [r["series"] for r in rows]
    assert out[0]["q10"] == ""


def _report(tmp_path, passes: bool):
    report = {
        "split": "val", "rows": 10, "features_csv_sha256": "x",
        "models": {"persistence": {}, "persistence_band": {}, "seasonal_naive": {}, "xgb": {}},
        "verdict": {"passes_nfr01": passes, "passes_excluding_frozen": True,
                    "model_mape_pct": 5.7, "persistence_mape_pct": 5.6},
    }
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_fallback_record_uses_the_train_band(tmp_path, monkeypatch):
    monkeypatch.setattr(train, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(train, "DEPLOYED_PATH", tmp_path / "deployed.json")
    record = train.write_fallback(_report(tmp_path, passes=False))
    assert record["deployed"] == "persistence_band"
    assert record["gate"]["model"] == "xgb"
    for band in record["band_change_pct"].values():
        assert band["q10"] < 0 < band["q90"]
    assert json.loads((tmp_path / "deployed.json").read_text(encoding="utf-8")) == record


def test_no_fallback_when_the_model_passed(tmp_path):
    with pytest.raises(ValueError):
        train.write_fallback(_report(tmp_path, passes=True))


def test_every_model_input_can_be_explained():
    from ml.explain import GROUPS

    assert set(train.MODEL_FEATURES) <= set(GROUPS)
