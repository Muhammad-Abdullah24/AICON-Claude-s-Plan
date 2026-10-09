from datetime import date

import pytest

from ml.decision import action_plan, break_even_price, config, hold_gate, inputs

RATE = 16.5
TODAY = date(2026, 10, 9)
UP = {"call": "UP", "validation_accuracy_pct": 72.0}
PASSING = {"beat_carry_pct_min": config.HOLD_GATE_MIN_BEAT_CARRY_PCT + 10, "source": "test"}


def plan(**kw):
    args = dict(crop_option="Wheat", quantity_maund=100, current_price=3820, q10=3606.54, direction=UP,
                is_stale=False, is_frozen=False, interest_pct_per_year=RATE, prices_as_of=TODAY,
                storage_available=True)
    args.update(kw)
    return action_plan(**args)


# ---------------------------------------------------------------- always SELL_NOW when holding is unsafe

@pytest.mark.parametrize("flag, code", [("is_stale", "STALE_DATA"), ("is_frozen", "FROZEN_PRICE")])
def test_stale_or_frozen_data_is_sell_now_even_if_the_gate_passed(flag, code):
    out = plan(**{flag: True}, hold_evidence=PASSING)
    assert out["recommended_action"] == "SELL_NOW"
    assert code in out["reason_codes"]
    assert out["upside_watch"] is None


def test_urgent_cash_need_is_sell_now():
    out = plan(urgent_cash_need=True, hold_evidence=PASSING)
    assert out["recommended_action"] == "SELL_NOW"
    assert "URGENT_CASH" in out["reason_codes"]


def test_no_storage_is_the_safe_default_and_means_no_watch():
    out = action_plan("Wheat", 100, 3820, 3606.54, UP, False, False, RATE, TODAY)
    assert out["constraints"] == {"urgent_cash_need": False, "storage_available": False, "source": "default"}
    assert out["recommended_action"] == "SELL_NOW" and out["mode"] == "SELL_NOW"
    assert out["upside_watch"] is None


def test_no_direction_signal_or_down_is_plain_sell_now():
    assert plan(crop_option="Cotton", direction=None)["mode"] == "SELL_NOW"
    out = plan(direction={"call": "DOWN"})
    assert out["mode"] == "SELL_NOW" and "DIRECTION_DOWN" in out["reason_codes"]


# ---------------------------------------------------------------- an UP signal never becomes advice to wait

def test_wheat_up_with_fresh_data_and_storage_adds_a_watch_but_still_sells_now():
    out = plan()
    assert out["recommended_action"] == "SELL_NOW"
    assert out["mode"] == "SELL_NOW_UPSIDE_WATCH"
    w = out["upside_watch"]
    assert w["market_signal"] == "UP" and w["evidence"] == "SIGNAL_DOES_NOT_SHOW_WAITING_PAYS"
    assert w["break_even_price"] == out["break_even_price"]
    assert w["monitoring_on"] is False


def test_no_quantity_is_suggested_unless_the_farmer_chooses_one():
    out = plan()
    assert out["retained_quantity"] == 0 and out["sell_now_quantity"] == 100
    assert out["retained_by_farmer_choice"] is False
    assert out["triggers"] == []


def test_direction_signal_alone_never_recommends_holding():
    assert plan(hold_evidence=None)["recommended_action"] == "SELL_NOW"
    out = plan(hold_evidence={"beat_carry_pct_min": 42.6, "source": "test"})
    assert out["recommended_action"] == "SELL_NOW"
    assert out["hold_gate"]["enabled"] is False and "HOLD_GATE_NOT_MET" in out["reason_codes"]


def test_hold_needs_the_gate_and_an_up_call_and_nothing_blocking():
    assert plan(hold_evidence=PASSING)["recommended_action"] == "HOLD_AND_MONITOR"
    assert plan(hold_evidence=PASSING, direction={"call": "DOWN"})["recommended_action"] == "SELL_NOW"
    assert plan(hold_evidence=PASSING, storage_available=False)["recommended_action"] == "SELL_NOW"


def test_the_real_evidence_keeps_the_hold_gate_off():
    evidence = inputs.hold_gate_evidence()
    assert evidence is not None, "run python -m ml.forecast.policy_eval"
    gate = hold_gate(evidence)
    assert gate["enabled"] is False
    assert gate["observed_beat_carry_pct"] < gate["required_beat_carry_pct"]


# ---------------------------------------------------------------- farmer-chosen retention and monitoring

@pytest.mark.parametrize("total, kept", [(100, 30), (37.5, 12.25), (1, 1), (80, 0)])
def test_quantities_sum_exactly(total, kept):
    out = plan(quantity_maund=total, retained_quantity=kept)
    assert out["sell_now_quantity"] + out["retained_quantity"] == total


def test_farmer_retention_is_recorded_as_their_choice_with_triggers():
    out = plan(retained_quantity=20, monitoring_on=True)
    assert out["recommended_action"] == "SELL_NOW"
    assert out["mode"] == "FARMER_RETAINED_MONITORING" and out["retained_by_farmer_choice"] is True
    assert [t["meaning"] for t in out["triggers"]] == ["BREAK_EVEN_REACHED", "RANGE_LOW_REACHED", "HORIZON_ENDS"]
    assert out["triggers"][-1]["date"] == "2026-11-06"
    assert out["carrying_cost_on_retained"] == round(out["carrying_cost_per_40kg"] * 20)
    assert out["monitoring_on"] is True


def test_monitoring_is_only_on_when_the_farmer_turns_it_on():
    assert plan()["monitoring_on"] is False
    assert plan(monitoring_on=True)["monitoring_on"] is True
    # nothing to monitor without a watch or a retained amount
    assert plan(direction=None, monitoring_on=True)["monitoring_on"] is False


def test_retaining_on_a_stale_price_is_allowed_but_warned():
    out = plan(retained_quantity=10, is_stale=True)
    assert out["recommended_action"] == "SELL_NOW"
    assert "TRIGGERS_UNRELIABLE_STALE_PRICE" in out["warnings"]


@pytest.mark.parametrize("kw", [{"quantity_maund": 0}, {"current_price": 0}, {"retained_quantity": 101},
                                {"retained_quantity": -1}])
def test_bad_inputs_raise(kw):
    with pytest.raises(ValueError):
        plan(**kw)


# ---------------------------------------------------------------- break-even

def test_break_even_is_today_plus_four_weeks_of_interest():
    assert break_even_price(3820, 16.5, 4) == pytest.approx(3820 * (1 + 0.165 * 4 / 52))
    out = plan()
    assert out["break_even_price"] == round(3820 * (1 + 0.165 * 4 / 52), 2)
    assert out["carrying_cost_per_40kg"] == round(3820 * 0.165 * 4 / 52, 2)


def test_break_even_matches_the_advice_interest_cost():
    from ml.decision import advise

    a = advise(3820, 3820, 3606.54, 4071.05, 100, RATE)
    assert round((plan()["break_even_price"] - 3820) * 100) == a["interest_cost"]
