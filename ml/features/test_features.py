import csv
from datetime import date, timedelta

import pytest

from ml.features import config as cfg
from ml.features.build import OUT_PATH, WEATHER_PATH, build_rows, format_value, load_weekly, to_lines
from ml.features.core import (
    FEATURE_COLUMNS,
    in_season,
    monday_of,
    price_features,
    runtime_features,
    weather_features,
)


@pytest.fixture(scope="module")
def built():
    return build_rows()


@pytest.fixture(scope="module")
def committed():
    with OUT_PATH.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_build_reproduces_committed_features_csv(built):
    rows, _ = built
    assert to_lines(rows) == OUT_PATH.read_text(encoding="utf-8").splitlines()


def test_no_row_targets_a_later_split(built):
    rows, _ = built
    for r in rows:
        if r["split"] == "train":
            assert r["target_week"] < cfg.TRAIN_TARGET_BEFORE
        elif r["split"] == "val":
            assert cfg.VAL_START <= r["week_start"] and r["target_week"] < cfg.VAL_TARGET_BEFORE
        else:
            assert r["week_start"] >= cfg.TEST_START


def test_runtime_features_match_the_training_row(committed):
    """The runtime path (I1) must produce exactly the features the model was trained on."""
    weekly = load_weekly()
    with WEATHER_PATH.open(encoding="utf-8", newline="") as f:
        daily = [r for r in csv.DictReader(f) if r["district"] == "Bahawalpur"]
    targets = [r for r in committed if r["series"] == "BahawalPur|Wheat|none" and r["split"] == "test"]
    assert targets
    for row in targets[:5]:
        ws = date.fromisoformat(row["week_start"])
        history = [(w["week_start"], w["price"], w["filled"]) for w in weekly[("BahawalPur", "Wheat", "none")]]
        start, end = ws - timedelta(days=92), ws + timedelta(days=6)
        recent_weather = [d for d in daily if start <= date.fromisoformat(d["date"]) <= end]
        feats = runtime_features("BahawalPur", "Wheat", "none", history, recent_weather, ws)
        for col in FEATURE_COLUMNS:
            assert format_value(feats[col]) == row[col], (row["week_start"], col)


def test_price_features_never_use_later_weeks():
    weeks = [date(2026, 1, 5) + timedelta(days=7 * k) for k in range(20)]
    history = [(w, 1000.0 + 10 * k, 0) for k, w in enumerate(weeks)]
    cut = weeks[12]
    full = price_features(history, cut)
    truncated = price_features(history[:13], cut)
    assert full == truncated
    assert full["price_rs_per_40kg"] == 1120.0
    assert full["price_lag_4w"] == 1080.0


def test_price_features_default_to_the_latest_priced_week():
    weeks = [date(2025, 11, 3) + timedelta(days=7 * k) for k in range(3)]
    feats = price_features([(w, 4000.0, 0) for w in weeks])
    assert feats["week_start"] == weeks[-1]
    assert price_features([(weeks[0], 4000.0, 0)], weeks[2]) is None  # no price in the asked week


def test_weather_week_needs_five_days_and_counts_hot_days():
    monday = date(2026, 6, 1)

    def day(k, tmax):
        return {"date": monday + timedelta(days=k), "tmax": tmax, "tmin": 25, "precip_mm": 1.5,
                "rh_mean": 40, "et0": 6}

    full_week = weather_features([day(k, 41 if k < 3 else 38) for k in range(7)], monday)
    assert full_week["hot_days_wk"] == 3
    assert full_week["precip_mm_wk"] == pytest.approx(10.5)
    assert full_week["precip_mm_4w"] is None  # only one week of history

    four_days = weather_features([day(k, 41) for k in range(4)], monday)
    assert four_days["tmax_c"] is None


def test_seasons_that_wrap_the_new_year():
    assert in_season(11, (11, 3)) and in_season(2, (11, 3))
    assert not in_season(6, (11, 3))
    assert in_season(5, (4, 6)) and not in_season(7, (4, 6))


def test_monday_of():
    assert monday_of(date(2026, 10, 11)) == date(2026, 10, 5)  # a Sunday
    assert monday_of(date(2026, 10, 5)) == date(2026, 10, 5)


def test_format_value_matches_the_original_pipeline():
    assert format_value(7600.0) == "7600"
    assert format_value(None) == ""
    assert format_value(0.00005) == "0.0001"   # half up, not half to even
    assert format_value(-0.00001) == "0"
    assert format_value(1.23456) == "1.2346"
