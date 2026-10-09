import sys
import types

import pytest

from backend.app import services


def test_advice_uses_the_latest_real_price():
    price, as_of = services.latest_price("Wheat", "BahawalPur")
    a = services.get_advice("Wheat", "BahawalPur", 100)
    assert (a["current_price"], a["prices_as_of"], a["unit"], a["data_source"]) == (price, as_of, "40kg", "amis")
    assert a["is_synthetic"] is False and a["model"] == services.BASELINE_MODEL
    assert a["range"]["low"] < a["current_price"] < a["range"]["high"]


def test_rupee_impact_is_gain_minus_interest_rounded_half_up():
    a = services.get_advice("Wheat", "BahawalPur", 100)
    interest = 100 * a["current_price"] * services._data()["interest_pct_month"] / 100
    assert a["interest_cost"] == services._round(interest)
    assert a["rupee_impact"] == a["gross_gain"] - a["interest_cost"]
    assert services._round(5252.5) == 5253


def test_baseline_never_says_wait():
    # "Price stays the same" can never clear the 5% WAIT bar; that is the honest baseline answer.
    assert {services.get_advice(c, m)["signal"] for c, m in
            [("Wheat", "BahawalPur"), ("Cotton", "Vehari"), ("IRRI", "Vehari")]} == {"SELL"}


def test_stale_series_have_low_confidence():
    a = services.get_advice("SuperBasmati", "Vehari")
    assert a["is_stale"] and a["confidence"] == "LOW"


def test_no_data_raises_lookup_error():
    with pytest.raises(LookupError):
        services.get_advice("IRRI", "RahimYarKhan")
    with pytest.raises(LookupError):
        services.get_advice("Wheat", "Lahore")


def test_compare_mandis_best_first_and_flags_missing():
    rows = services.compare_mandis("IRRI", "Vehari", 100)
    priced = [r for r in rows if r["has_data"]]
    assert [r["net_price"] for r in priced] == sorted((r["net_price"] for r in priced), reverse=True)
    assert next(r for r in priced if r["mandi"] == "Vehari")["gain_vs_preferred"] == 0
    assert {"mandi": "RahimYarKhan", "has_data": False} in rows


def test_explanation_is_facts_and_says_it_is_a_baseline():
    reasons = services.get_explanation("Wheat", "BahawalPur")
    assert reasons and all(r["text_ur"] for r in reasons)
    assert "سادہ اندازہ" in reasons[-1]["text_ur"]


def test_alerts_toggle():
    services.set_alerts("92300", False)
    assert services.alerts_enabled("92300") is False
    services.set_alerts("92300", True)
    assert services.alerts_enabled("92300") is True


def test_owner_b_model_is_used_when_it_exists(monkeypatch):
    fake = types.ModuleType("ml.forecast.predict")
    fake.forecast = lambda crop, mandi, as_of, weather: {
        "current_price": 1000.0, "predicted_price": 1100.0, "q10": 950.0, "q90": 1200.0,
        "model_version": "xgb-test", "data_source": "amis", "is_synthetic": False,
        "shap": [{"text_ur": "ماڈل کی وجہ", "direction": "UP"}]}
    monkeypatch.setitem(sys.modules, "ml.forecast.predict", fake)
    a = services.get_advice("Wheat", "BahawalPur", 10)
    assert (a["model"], a["signal"], a["trend"]) == ("xgb-test", "WAIT", "UP")
    assert services.get_explanation("Wheat", "BahawalPur") == [{"text_ur": "ماڈل کی وجہ", "direction": "UP"}]
