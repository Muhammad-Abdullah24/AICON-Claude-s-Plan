from datetime import date

import pytest

from ml.decision import (
    advise,
    alert_check,
    compare_mandis,
    confidence,
    config,
    crop_plan,
    fair_price_range,
    inputs,
    margin,
    offer_check,
    selling_window,
)

RATE = 16.5  # % a year, as in the blueprint example


# ---------------------------------------------------------------- advise (UC-03)

def test_wait_at_exactly_the_threshold():
    rise = 1000 * (1 + config.WAIT_THRESHOLD_PCT / 100)
    assert advise(1000, rise, 950, 1100, 100, RATE)["signal"] == "WAIT"


def test_sell_just_below_the_threshold():
    rise = 1000 * (1 + config.WAIT_THRESHOLD_PCT / 100) - 0.01
    assert advise(1000, rise, 950, 1100, 100, RATE)["signal"] == "SELL"


def test_sell_when_price_falls():
    out = advise(1000, 900, 850, 950, 100, RATE)
    assert out["signal"] == "SELL"
    assert out["rupee_impact"] < 0


def test_net_rupee_impact_subtracts_interest():
    out = advise(3820, 4050, 3700, 4300, 100, RATE)
    assert out["gross_gain"] == round(100 * (4050 - 3820))
    expected_interest = 100 * 3820 * 0.165 * 4 / 52
    assert out["interest_cost"] == round(expected_interest)
    assert out["rupee_impact"] == round(100 * 230 - expected_interest)
    assert out["signal"] == "WAIT"


def test_arhti_commission_applies_to_both_prices():
    out = advise(1000, 1100, 1000, 1200, 10, RATE, arhti_pct=2)
    assert out["gross_gain"] == round(10 * (1100 - 1000) * 0.98)
    assert out["interest_cost"] == round(10 * 1000 * 0.98 * 0.165 * 4 / 52)
    # the signal is about the market price, not what the commission leaves
    assert out["signal"] == "WAIT"


def test_no_commission_unless_entered():
    assert advise(1000, 1100, 1000, 1200, 10, RATE)["arhti_pct"] is None


@pytest.mark.parametrize("current, predicted, quantity", [(0, 100, 10), (100, -1, 10), (100, 100, 0)])
def test_advise_rejects_bad_inputs(current, predicted, quantity):
    with pytest.raises(ValueError):
        advise(current, predicted, None, None, quantity, RATE)


# ---------------------------------------------------------------- confidence

def test_confidence_from_range_width():
    assert confidence(1000, 960, 1040) == "HIGH"  # 8% wide
    assert confidence(1000, 920, 1080) == "MEDIUM"  # 16% wide
    assert confidence(1000, 850, 1150) == "LOW"  # 30% wide


def test_stale_prices_are_always_low_confidence():
    assert confidence(1000, 990, 1010, is_stale=True) == "LOW"


def test_missing_range_is_low_confidence():
    assert confidence(1000, None, None) == "LOW"


# ---------------------------------------------------------------- fair price and offer check (UC-07)

def test_fair_range_runs_from_today_to_the_forecast():
    assert fair_price_range(1000, 1080) == {"low": 1000, "high": 1080}


def test_fair_range_is_todays_price_when_forecast_falls():
    assert fair_price_range(1000, 900) == {"low": 1000, "high": 1000}


def test_offer_below_fair():
    out = offer_check(950, 1000, 1080, quantity_maund=100)
    assert out["status"] == "BELOW"
    assert out["gap_per_40kg"] == -50
    assert out["gap_total"] == -5000


def test_offer_inside_fair():
    assert offer_check(1040, 1000, 1080)["status"] == "FAIR"


def test_offer_above_fair():
    out = offer_check(1100, 1000, 1080)
    assert out["status"] == "ABOVE"
    assert out["gap_per_40kg"] == 20
    assert out["gap_total"] is None


def test_offer_must_be_a_price():
    with pytest.raises(ValueError):
        offer_check(0, 1000, 1080)


# ---------------------------------------------------------------- margin (UC-08)

def test_margin_without_commission():
    out = margin(4000, 3761)
    assert out["profit"] == 239
    assert out["arhti_commission"] is None


def test_margin_with_commission_and_support_line():
    out = margin(4000, 3000, arhti_pct=2.5, support_price=3500, support_status="PROCURED")
    assert out["arhti_commission"] == 100
    assert out["profit"] == 900
    assert out["support_price"] == 3500
    assert out["support_status"] == "PROCURED"


# ---------------------------------------------------------------- compare mandis (UC-04)

def test_ranks_by_net_price_after_transport():
    out = compare_mandis(
        [
            {"mandi": "Bahawalpur", "current_price": 3820, "transport_cost": 0},
            {"mandi": "Vehari", "current_price": 4000, "transport_cost": 165.1},
            {"mandi": "Rahim Yar Khan", "current_price": 3900, "transport_cost": 291.2},
        ],
        preferred_mandi="Bahawalpur",
        quantity_maund=100,
    )
    assert [m["mandi"] for m in out["mandis"]] == ["Vehari", "Bahawalpur", "Rahim Yar Khan"]
    assert out["best_mandi"] == "Vehari"
    assert out["transport_included"] is True
    assert out["gain_over_preferred_per_40kg"] == pytest.approx(14.9)
    assert out["gain_over_preferred_total"] == 1490


def test_irri_has_no_price_at_rahim_yar_khan():
    out = compare_mandis(
        [
            {"mandi": "Bahawalpur", "current_price": 4625, "transport_cost": 0},
            {"mandi": "Vehari", "current_price": 4700, "transport_cost": 165.1},
            {"mandi": "Rahim Yar Khan", "current_price": None, "transport_cost": 291.2},
        ],
        preferred_mandi="Rahim Yar Khan",
    )
    last = out["mandis"][-1]
    assert last["mandi"] == "Rahim Yar Khan"
    assert last["has_price"] is False
    assert last["rank"] is None
    assert out["best_mandi"] == "Bahawalpur"
    # the preferred mandi has no price, so there is no gain to report
    assert out["gain_over_preferred_per_40kg"] is None


def test_unknown_district_ranks_by_gross_price():
    out = compare_mandis(
        [
            {"mandi": "Bahawalpur", "current_price": 3820, "transport_cost": None},
            {"mandi": "Vehari", "current_price": 3700, "transport_cost": None},
        ]
    )
    assert out["transport_included"] is False
    assert out["best_mandi"] == "Bahawalpur"
    assert all(m["transport_cost"] is None for m in out["mandis"])


def test_no_prices_at_all():
    out = compare_mandis([{"mandi": "Vehari", "current_price": None, "transport_cost": 0}])
    assert out["best_mandi"] is None
    assert out["mandis"][0]["has_price"] is False


# ---------------------------------------------------------------- inputs from the runtime tables

def test_inputs_come_from_the_runtime_tables():
    assert inputs.interest_pct_per_year() > 0
    assert inputs.production_cost_per_40kg("Wheat") > 0
    assert inputs.transport_cost("Bahawalpur", "Bahawalpur") == 0
    assert inputs.transport_cost("Bahawalpur", "Vehari") > 0
    assert inputs.transport_cost("Lahore", "Vehari") is None
    assert inputs.amis_name("Rahim Yar Khan") == "RahimYarKhan"
    assert inputs.display_name("RahimYarKhan") == "Rahim Yar Khan"


def test_only_wheat_has_a_support_price():
    assert inputs.support_price("Wheat") is not None
    assert inputs.support_price("Cotton") is None


def test_staleness_flags():
    assert inputs.is_stale("SuperBasmati", "Vehari") is True
    assert inputs.is_stale("Wheat", "Bahawalpur") is False
    assert inputs.is_stale("IRRI", "Rahim Yar Khan") is True  # no series at all


# ---------------------------------------------------------------- What to Grow (B7)

def _crop(option, price, median, lo, hi, spread=10.0, enough=True, cost=1000.0, yield_maund=10.0, milling=None):
    return {
        "crop_option": option, "latest_price": price, "prices_as_of": "2026-10-05", "is_stale": False,
        "harvest_ratio": {"ratio_median": median, "ratio_min": lo, "ratio_max": hi, "spread_pct": spread,
                          "enough_years": enough, "n_years": 5, "months_ahead": 6},
        "cost_per_acre": cost, "yield_maund_per_acre": yield_maund, "milling_yield": milling,
    }


def test_crop_plan_profit_per_acre_and_ranking():
    plan = crop_plan([_crop("Wheat", 100, 1.1, 1.0, 1.2), _crop("Cotton", 300, 1.0, 0.9, 1.1)], land_area_acres=2)
    wheat = next(c for c in plan["crops"] if c["crop_option"] == "Wheat")
    assert wheat["harvest_price_estimate"] == pytest.approx(110)
    assert wheat["profit_per_acre"] == round(110 * 10 - 1000)
    assert wheat["profit_per_acre_range"] == {"low": 0, "high": 200}
    assert wheat["profit_total"] == 200
    assert [c["crop_option"] for c in plan["crops"]] == ["Cotton", "Wheat"]
    assert plan["best_crop"] == "Cotton"
    assert all(c["is_estimate"] for c in plan["crops"])


def test_rice_yield_is_converted_from_paddy():
    plan = crop_plan([_crop("IRRI", 100, 1.0, 1.0, 1.0, yield_maund=50, milling=0.65)], land_area_acres=1)
    assert plan["crops"][0]["sale_maund_per_acre"] == 32.5
    assert plan["crops"][0]["profit_per_acre"] == round(100 * 32.5 - 1000)


def test_crop_without_data_is_listed_last():
    missing = {**_crop("IRRI", None, 1, 1, 1), "harvest_ratio": None}
    plan = crop_plan([missing, _crop("Wheat", 100, 1.1, 1.0, 1.2)], land_area_acres=1)
    assert plan["crops"][-1] == {"crop_option": "IRRI", "has_data": False, "rank": None}


def test_risk_badge():
    from ml.decision import risk_badge

    assert risk_badge(config.LOW_RISK_MAX_SPREAD_PCT, True) == "LOW"
    assert risk_badge(config.MEDIUM_RISK_MAX_SPREAD_PCT, True) == "MEDIUM"
    assert risk_badge(config.MEDIUM_RISK_MAX_SPREAD_PCT + 1, True) == "HIGH"
    assert risk_badge(0, False) == "HIGH"  # too little history


def test_land_area_must_be_positive():
    with pytest.raises(ValueError):
        crop_plan([], land_area_acres=0)


def _month(k, ratio):
    return {"offset_months": k, "month": 4 + k, "ratio_median": ratio}


def test_selling_window_subtracts_interest():
    # +5% two months after harvest, minus 2 x 1% interest = +3%; better than selling at harvest
    w = selling_window([_month(0, 1.0), _month(1, 1.01), _month(2, 1.05), _month(3, 1.04)], 12.0)
    assert w["best_month"] == 6
    assert w["best_net_pct"] == pytest.approx(3.0)
    assert w["sell_at_harvest"] is False
    assert w["window_months"] == [6]


def test_selling_window_includes_close_neighbours():
    w = selling_window([_month(0, 1.0), _month(1, 1.02), _month(2, 1.0)], 0.0)
    assert w["best_month"] == 5
    assert w["window_months"] == [5]
    w = selling_window([_month(0, 1.0), _month(1, 1.005)], 0.0)
    assert w["window_months"] == [4, 5]


def test_falling_prices_mean_sell_at_harvest():
    w = selling_window([_month(0, 1.0), _month(1, 0.97), _month(2, 0.99)], 16.5)
    assert w["sell_at_harvest"] is True
    assert w["best_month"] == 4


def test_selling_window_without_data():
    assert selling_window([], 16.5) is None


def test_crop_plan_on_the_real_tables():
    plan = crop_plan(inputs.crop_plan_inputs("Rahim Yar Khan"), land_area_acres=1)
    by_option = {c["crop_option"]: c for c in plan["crops"]}
    assert by_option["IRRI"]["has_data"] is False  # no IRRI series at Rahim Yar Khan
    assert by_option["Wheat"]["has_data"] is True
    assert by_option["SuperBasmati"]["is_stale"] is True
    w = selling_window(inputs.post_harvest_ratios("Wheat", "Bahawalpur"), inputs.interest_pct_per_year())
    assert w["months"][0]["offset_months"] == 0


# ---------------------------------------------------------------- alerts (B8)

TODAY = date(2026, 10, 10)


def _cand(option="Wheat", signal="SELL", previous="SELL", change=0.0, frozen=False, stale=False):
    return {"crop_option": option, "mandi": "BahawalPur", "signal": signal, "previous_signal": previous,
            "prices_as_of": "2026-10-05", "change_4w_pct": change, "band_q10_pct": -5.0, "band_q90_pct": 6.0,
            "is_frozen": frozen, "is_stale": stale}


def test_no_event_no_alert():
    out = alert_check([_cand()], None, TODAY)
    assert out == {"send": False, "status": None, "alert": None, "suppressed": [], "reason": "NO_EVENT"}


def test_signal_change_alerts():
    out = alert_check([_cand(signal="WAIT", previous="SELL")], None, TODAY)
    assert out["send"] is True and out["status"] == "CREATED"
    assert out["alert"]["type"] == "SELL_SIGNAL"
    assert (out["alert"]["previous_signal"], out["alert"]["signal"]) == ("SELL", "WAIT")


def test_first_signal_is_not_a_change():
    assert alert_check([_cand(previous=None)], None, TODAY)["send"] is False


def test_unusual_moves_alert_both_ways():
    up = alert_check([_cand(change=8.0)], None, TODAY)["alert"]
    assert (up["type"], up["direction"], up["size"]) == ("PRICE_SPIKE", "UP", 2.0)
    down = alert_check([_cand(change=-9.0)], None, TODAY)["alert"]
    assert (down["direction"], down["size"]) == ("DOWN", 4.0)


def test_moves_inside_the_band_do_not_alert():
    assert alert_check([_cand(change=5.9), _cand(change=-4.9)], None, TODAY)["send"] is False


def test_frozen_or_stale_prices_never_raise_a_price_alert():
    assert alert_check([_cand(change=20.0, frozen=True)], None, TODAY)["send"] is False
    assert alert_check([_cand(change=-20.0, stale=True)], None, TODAY)["send"] is False


def test_one_alert_per_farmer_signal_change_first():
    out = alert_check([_cand("Cotton", change=-30.0), _cand("Wheat", signal="WAIT"), None], None, TODAY)
    assert out["alert"]["type"] == "SELL_SIGNAL" and out["alert"]["crop_option"] == "Wheat"
    assert [e["crop_option"] for e in out["suppressed"]] == ["Cotton"]


def test_biggest_unusual_move_wins():
    out = alert_check([_cand("Wheat", change=7.0), _cand("Cotton", change=-15.0)], None, TODAY)
    assert out["alert"]["crop_option"] == "Cotton"


def test_at_most_one_alert_a_week():
    out = alert_check([_cand(signal="WAIT")], date(2026, 10, 4), TODAY)
    assert out["send"] is False and out["status"] == "SUPPRESSED" and out["reason"] == "ALERTED_THIS_WEEK"
    assert out["suppressed"][0]["type"] == "SELL_SIGNAL"
    assert alert_check([_cand(signal="WAIT")], date(2026, 10, 3), TODAY)["send"] is True


def test_alert_candidates_from_the_real_data():
    wheat = inputs.alert_candidate("Wheat", "Bahawalpur", "SELL", None)
    assert wheat["mandi"] == "BahawalPur" and wheat["band_q10_pct"] < 0 < wheat["band_q90_pct"]
    assert inputs.alert_candidate("IRRI", "Rahim Yar Khan", "SELL", None) is None
    assert inputs.alert_candidate("SuperBasmati", "Vehari", "SELL", None)["is_stale"] is True
