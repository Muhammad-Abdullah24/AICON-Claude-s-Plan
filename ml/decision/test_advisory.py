import pytest

from ml.decision import advise, compare_mandis, confidence, config, fair_price_range, inputs, margin, offer_check

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
