import importlib.util
from datetime import date

import pytest

from ml.forecast import forecast, predict

I2_KEYS = {
    "current_price", "predicted_price", "q10", "q90", "trend", "volatility", "prices_as_of",
    "model_version", "shap", "data_source", "is_synthetic",
}
needs_xgboost = pytest.mark.skipif(importlib.util.find_spec("xgboost") is None, reason="needs xgboost")


def test_today_is_the_latest_daily_price_not_the_week_average():
    out = forecast("Cotton", "Bahawalpur")
    assert (out["prices_as_of"], out["current_price"]) == ("2026-10-09", 9200.0)


def _latest_observed(city, crop, variety):
    return [h for h in predict._weekly()[(city, crop, variety)] if h["filled"] == 0][-1]


def test_returns_the_i2_shape_on_real_data():
    out = forecast("Cotton", "Bahawalpur")
    assert I2_KEYS <= out.keys()
    assert out["unit"] == "40kg"
    assert out["is_synthetic"] is False
    assert out["data_source"] == "amis"
    assert out["forecast_type"] == "baseline"
    assert out["model_version"] == "baseline_persistence_band"


def test_baseline_price_is_the_latest_observed_amis_price():
    out = forecast("Wheat", "BahawalPur")
    latest = _latest_observed("BahawalPur", "Wheat", "none")
    assert out["week_start"] == latest["week_start"].isoformat()
    # the exact last AMIS day in that week, as in series_coverage.csv (H-C3)
    assert out["prices_as_of"] == "2026-10-09"
    # today's price is the last real AMIS day's price, as in series_coverage.csv
    assert out["current_price"] == 3820.0
    assert out["predicted_price"] == out["current_price"]
    assert out["trend"] == "STABLE"


def test_range_comes_from_the_deployed_band():
    out = forecast("IRRI", "Vehari")
    band = predict._deployed()["band_change_pct"]["IRRI"]
    assert out["q10"] == round(out["current_price"] * (1 + band["q10"] / 100), 2)
    assert out["q90"] == round(out["current_price"] * (1 + band["q90"] / 100), 2)
    assert out["q10"] < out["predicted_price"] < out["q90"]
    assert out["volatility"] in {"STABLE", "MODERATE", "VOLATILE"}


def test_no_direction_for_crops_without_proven_skill():
    for option in ("Cotton", "IRRI", "SuperBasmati"):
        out = forecast(option, "Vehari")
        assert out["direction"] is None
        assert out["shap"] == []


@needs_xgboost
def test_wheat_gets_a_direction_call_with_reasons():
    out = forecast("Wheat", "Bahawalpur")
    assert out["direction"]["call"] in {"UP", "DOWN"}
    assert out["direction"]["validation_accuracy_pct"] > 50
    assert 1 <= len(out["shap"]) <= 5
    for reason in out["shap"]:
        assert {"feature", "rs_effect", "direction", "text_en", "text_ur"} <= reason.keys()
    # the model's price is never shown: the forecast stays the baseline
    assert out["predicted_price"] == out["current_price"]


@needs_xgboost
def test_direction_calls_on_the_demo_backup_weeks():
    # docs/DATA_NOTES.md A7: 2025-03-24 fell 19.7%, 2025-08-04 rose 48.6% (both validation weeks)
    assert forecast("Wheat", "Bahawalpur", as_of=date(2025, 3, 24))["direction"]["call"] == "DOWN"
    assert forecast("Wheat", "Bahawalpur", as_of=date(2025, 8, 4))["direction"]["call"] == "UP"


def test_direction_switches_off_without_a_model(monkeypatch):
    monkeypatch.setattr(predict, "_direction_model", lambda: None)
    out = forecast("Wheat", "Bahawalpur")
    assert out["direction"] is None
    assert out["shap"] == []


def test_display_and_amis_mandi_names_agree():
    assert forecast("Cotton", "Rahim Yar Khan") == forecast("Cotton", "RahimYarKhan")


def test_never_uses_prices_after_as_of():
    as_of = date(2024, 3, 13)
    out = forecast("Cotton", "Bahawalpur", as_of=as_of)
    assert date.fromisoformat(out["prices_as_of"]) <= as_of
    assert out["prices_as_of"] < forecast("Cotton", "Bahawalpur")["prices_as_of"]


def test_irri_has_no_rahim_yar_khan_series():
    assert forecast("IRRI", "Rahim Yar Khan") is None


def test_no_data_before_the_series_starts():
    assert forecast("Wheat", "Bahawalpur", as_of=date(2010, 1, 1)) is None


@pytest.mark.parametrize("crop_option, mandi", [("Maize", "Vehari"), ("Wheat", "Lahore")])
def test_unknown_inputs_raise(crop_option, mandi):
    with pytest.raises(ValueError):
        forecast(crop_option, mandi)


def test_prices_as_of_is_a_real_day_and_never_after_as_of():
    out = forecast("Wheat", "Bahawalpur", as_of=date(2025, 3, 26))
    assert out["week_start"] == "2025-03-24"
    assert "2025-03-24" <= out["prices_as_of"] <= "2025-03-26"


@needs_xgboost
def test_accepts_the_weather_services_aggregated_dict():
    from ml.features import weather_features

    daily = predict._daily_weather_for("BahawalPur", None)
    feats = weather_features(daily, date(2026, 9, 28))
    as_dict = forecast("Wheat", "Bahawalpur", weather={"features": feats, "cached": False})
    as_daily = forecast("Wheat", "Bahawalpur", weather=daily)
    assert as_dict["direction"]["call"] in {"UP", "DOWN"} and as_daily["direction"]["call"] in {"UP", "DOWN"}
    assert as_dict["current_price"] == as_daily["current_price"]
