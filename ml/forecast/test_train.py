import csv

import pytest

# CI installs only the backend requirements; training needs ml/forecast/requirements.txt.
pytest.importorskip("xgboost")

from ml.forecast import train  # noqa: E402


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


def test_training_is_reproducible(monkeypatch):
    monkeypatch.setattr(train, "NUM_ROUNDS", 20)
    rows = train.load_split("train")[:300]
    first = train.predict_change(train.fit(rows), rows[:10])
    second = train.predict_change(train.fit(rows), rows[:10])
    assert first.tolist() == second.tolist()


def test_predictions_file_matches_the_gate_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(train, "NUM_ROUNDS", 5)
    rows = train.load_split("val")[:5]
    point = train.to_prices(rows, train.predict_change(train.fit(train.load_split("train")[:200]), rows))
    path = tmp_path / "preds.csv"
    train.write_predictions(path, rows, point, {})
    with path.open(encoding="utf-8", newline="") as f:
        out = list(csv.DictReader(f))
    assert list(out[0]) == ["series", "week_start", "pred_price_next_4w", "q10", "q90"]
    assert [r["series"] for r in out] == [r["series"] for r in rows]
    assert out[0]["q10"] == ""
