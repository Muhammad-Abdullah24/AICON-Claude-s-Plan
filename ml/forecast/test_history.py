from datetime import date

import pytest

from ml.forecast.history import WEEKS, _weekly, history


def test_shape_and_52_consecutive_weeks():
    h = history("Wheat", "Bahawalpur")
    assert h["unit"] == "40kg" and h["data_source"] == "amis" and h["is_synthetic"] is False
    weeks = [date.fromisoformat(p["week_start"]) for p in h["weeks"]]
    assert len(weeks) == WEEKS
    assert all((b - a).days == 7 for a, b in zip(weeks, weeks[1:], strict=False))
    assert h["weeks"][-1]["week_start"] == h["prices_as_of"]


def test_prices_are_the_real_weekly_amis_prices():
    h = history("Wheat", "BahawalPur")
    real = {r["week_start"].isoformat(): r["price"] for r in _weekly()[("BahawalPur", "Wheat", "none")]}
    for p in h["weeks"]:
        if p["price"] is not None:
            assert p["price"] == round(real[p["week_start"]], 2)
    priced = [p["price"] for p in h["weeks"] if p["price"] is not None]
    assert (h["low"], h["high"]) == (min(priced), max(priced))


def test_missing_weeks_are_gaps_not_invented_prices():
    h = history("Cotton", "Bahawalpur")
    assert h["weeks_with_price"] < WEEKS
    assert any(p["price"] is None for p in h["weeks"])
    assert all(not p["filled"] and not p["frozen"] for p in h["weeks"] if p["price"] is None)


def test_frozen_weeks_are_flagged():
    assert any(p["frozen"] for p in history("IRRI", "Vehari")["weeks"])


def test_seasonal_pattern_and_calendar():
    h = history("Wheat", "Bahawalpur")
    assert [s["month"] for s in h["seasonal"]] == list(range(1, 13))
    assert all(s["index_min"] <= s["index_median"] <= s["index_max"] for s in h["seasonal"] if s["index_median"])
    assert h["calendar"]["harvest_start_month"] == 4


def test_never_uses_prices_after_as_of():
    h = history("Wheat", "Bahawalpur", as_of=date(2025, 3, 26))
    assert h["prices_as_of"] <= "2025-03-26"
    assert all(p["week_start"] <= "2025-03-26" for p in h["weeks"])


def test_stale_series_are_flagged():
    assert history("SuperBasmati", "Vehari")["is_stale"] is True


def test_no_series():
    assert history("IRRI", "Rahim Yar Khan") is None
    assert history("Wheat", "Bahawalpur", as_of=date(2010, 1, 1)) is None


@pytest.mark.parametrize("crop_option, mandi", [("Maize", "Vehari"), ("Wheat", "Lahore")])
def test_unknown_inputs_raise(crop_option, mandi):
    with pytest.raises(ValueError):
        history(crop_option, mandi)
