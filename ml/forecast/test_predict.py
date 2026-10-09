from datetime import date

import pytest

from ml.forecast import forecast
from ml.forecast.predict import _observed_prices

I2_KEYS = {
    "current_price", "predicted_price", "q10", "q90", "trend", "volatility", "prices_as_of",
    "model_version", "shap", "data_source", "is_synthetic",
}


def test_returns_the_i2_shape():
    out = forecast("Wheat", "Bahawalpur")
    assert I2_KEYS <= out.keys()
    assert out["unit"] == "40kg"
    assert out["is_synthetic"] is True
    assert out["model_version"].startswith("stub")
    assert out["shap"] == []
    assert out["trend"] == "STABLE"


def test_current_price_is_the_latest_observed_amis_price():
    out = forecast("Wheat", "BahawalPur")
    week, price = _observed_prices()[("BahawalPur", "Wheat", "none")][-1]
    assert out["prices_as_of"] == week.isoformat()
    assert out["current_price"] == round(price, 2)
    assert out["predicted_price"] == out["current_price"]


def test_range_brackets_the_forecast():
    for option in ("Wheat", "Cotton", "IRRI", "SuperBasmati"):
        out = forecast(option, "Vehari")
        assert out["q10"] <= out["predicted_price"] <= out["q90"]
        assert out["volatility"] in {"STABLE", "MODERATE", "VOLATILE"}


def test_display_and_amis_mandi_names_agree():
    assert forecast("Cotton", "Rahim Yar Khan") == forecast("Cotton", "RahimYarKhan")


def test_never_uses_prices_after_as_of():
    as_of = date(2024, 3, 13)
    out = forecast("Wheat", "Bahawalpur", as_of=as_of)
    assert date.fromisoformat(out["prices_as_of"]) <= as_of
    later = forecast("Wheat", "Bahawalpur")
    assert out["prices_as_of"] < later["prices_as_of"]


def test_irri_has_no_rahim_yar_khan_series():
    assert forecast("IRRI", "Rahim Yar Khan") is None


def test_no_data_before_the_series_starts():
    assert forecast("Wheat", "Bahawalpur", as_of=date(2010, 1, 1)) is None


@pytest.mark.parametrize("crop_option, mandi", [("Maize", "Vehari"), ("Wheat", "Lahore")])
def test_unknown_inputs_raise(crop_option, mandi):
    with pytest.raises(ValueError):
        forecast(crop_option, mandi)
