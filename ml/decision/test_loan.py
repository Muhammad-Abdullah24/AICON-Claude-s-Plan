"""Tests for the loan planner engine (L1). Pure: inputs and options are passed in, as the API will."""

import pytest

from ml.decision.loan import loan_plan

# 58,000 per acre in cash inputs; on 5 acres the crop needs Rs 290,000. Test figures, not the real cost table (D1).
ITEMS = [{"item": "seed", "rs_per_acre": 8000}, {"item": "fertilizer", "rs_per_acre": 21000},
         {"item": "land_prep_irrigation_harvest", "rs_per_acre": 29000}]
# Eligible options as the API would pass them for 5 acres: Kissan Card capped at min(30,000 x 5, 150,000).
KISSAN = {"id": "kissan_card", "annual_rate_pct": 0, "max_rs": 150000}
ZARKHEZ = {"id": "zarkhez_e", "annual_rate_pct": 18, "max_rs": 500000}
BANK = {"id": "bank", "annual_rate_pct": 16.5, "max_rs": None}
ARHTI = {"id": "arhti", "annual_rate_pct": 66, "max_rs": None}
MONTHS = 6


def test_cheapest_first_ladder_whatever_the_input_order():
    p = loan_plan(5, ITEMS, 0, [ARHTI, ZARKHEZ, BANK, KISSAN], MONTHS)
    assert p["input_need_rs"] == 290000 and p["savings_rs"] == 0 and p["borrow_needed_rs"] == 290000
    # Kissan Card 0% up to its cap, then the bank at 16.5% (cheaper than Zarkhez-e at 18%); the arhti is never reached.
    assert p["ladder"] == [{"id": "kissan_card", "amount_rs": 150000, "interest_rs": 0},
                           {"id": "bank", "amount_rs": 140000, "interest_rs": 11550}]   # 140,000 x 16.5% x 6/12
    assert p["ladder_interest_rs"] == 11550
    assert p["harvest_due_rs"] == 290000 + 11550
    assert p["uncovered_rs"] == 0


def test_the_cap_is_respected_and_the_next_option_takes_the_rest():
    p = loan_plan(5, ITEMS, 0, [KISSAN, ZARKHEZ], MONTHS)
    assert [s["amount_rs"] for s in p["ladder"]] == [150000, 140000]
    assert all(s["amount_rs"] <= o["max_rs"] for s, o in zip(p["ladder"], [KISSAN, ZARKHEZ], strict=True))
    assert p["ladder"][1]["interest_rs"] == 12600                                     # 140,000 x 18% x 6/12


def test_equal_rates_keep_the_order_the_api_gave():
    akhuwat = {"id": "akhuwat", "annual_rate_pct": 0, "max_rs": 50000}
    first = loan_plan(5, ITEMS, 0, [akhuwat, KISSAN, BANK], MONTHS)
    assert [s["id"] for s in first["ladder"]] == ["akhuwat", "kissan_card", "bank"]
    second = loan_plan(5, ITEMS, 0, [KISSAN, akhuwat, BANK], MONTHS)
    assert [s["id"] for s in second["ladder"]] == ["kissan_card", "akhuwat", "bank"]


def test_over_borrowing_from_the_arhti():
    p = loan_plan(5, ITEMS, 0, [KISSAN, BANK, ARHTI], MONTHS, planned_borrow_rs=400000, planned_rate_pct=66)
    assert p["planned_borrow_rs"] == 400000
    assert p["planned_interest_rs"] == 132000                                         # 400,000 x 66% x 6/12
    assert p["over_borrow_rs"] == 400000 - 290000
    assert p["extra_cost_rs"] == 132000 - 11550


def test_a_planned_loan_below_the_need_is_not_over_borrowing():
    p = loan_plan(5, ITEMS, 0, [KISSAN, BANK], MONTHS, planned_borrow_rs=100000, planned_rate_pct=0)
    assert p["over_borrow_rs"] == 0
    assert p["extra_cost_rs"] == -11550     # cheaper than the ladder only because it is smaller than the need


def test_planned_amount_without_a_rate_shows_over_borrowing_but_no_cost():
    p = loan_plan(5, ITEMS, 0, [KISSAN, BANK], MONTHS, planned_borrow_rs=400000)
    assert p["over_borrow_rs"] == 110000
    assert p["planned_interest_rs"] is None and p["extra_cost_rs"] is None


def test_no_plan_given():
    p = loan_plan(5, ITEMS, 0, [KISSAN, BANK], MONTHS)
    assert p["planned_borrow_rs"] is None and p["planned_interest_rs"] is None
    assert p["over_borrow_rs"] is None and p["extra_cost_rs"] is None


def test_uncovered_when_the_eligible_options_run_out():
    p = loan_plan(5, ITEMS, 0, [KISSAN], MONTHS)
    assert p["ladder"] == [{"id": "kissan_card", "amount_rs": 150000, "interest_rs": 0}]
    assert p["uncovered_rs"] == 140000
    assert p["harvest_due_rs"] == 150000    # only what was actually borrowed falls due
    assert loan_plan(5, ITEMS, 0, [], MONTHS)["uncovered_rs"] == 290000


def test_zero_savings_and_savings_that_cover_part_or_all():
    assert loan_plan(5, ITEMS, 0, [KISSAN], MONTHS)["borrow_needed_rs"] == 290000
    part = loan_plan(5, ITEMS, 200000, [KISSAN, BANK], MONTHS)
    assert part["borrow_needed_rs"] == 90000 and part["ladder"] == [
        {"id": "kissan_card", "amount_rs": 90000, "interest_rs": 0}]
    rich = loan_plan(5, ITEMS, 400000, [KISSAN, BANK], MONTHS, planned_borrow_rs=50000, planned_rate_pct=66)
    assert rich["borrow_needed_rs"] == 0 and rich["ladder"] == [] and rich["harvest_due_rs"] == 0
    assert rich["uncovered_rs"] == 0 and rich["over_borrow_rs"] == 50000    # every rupee borrowed is extra


def test_interest_scales_with_months_to_harvest():
    assert loan_plan(5, ITEMS, 0, [KISSAN, BANK], 0)["ladder_interest_rs"] == 0
    assert loan_plan(5, ITEMS, 0, [KISSAN, BANK], 3)["ladder_interest_rs"] == 5775   # half of the 6-month figure


def test_options_with_no_room_are_skipped():
    empty = {"id": "akhuwat", "annual_rate_pct": 0, "max_rs": 0}
    p = loan_plan(5, ITEMS, 0, [empty, KISSAN, BANK], MONTHS)
    assert [s["id"] for s in p["ladder"]] == ["kissan_card", "bank"]


@pytest.mark.parametrize("kwargs", [dict(acres=-1), dict(savings_rs=-1), dict(months_to_harvest=-1),
                                    dict(planned_borrow_rs=-1)])
def test_negative_inputs_are_rejected(kwargs):
    args = dict(acres=5, input_items=ITEMS, savings_rs=0, options=[KISSAN], months_to_harvest=MONTHS) | kwargs
    with pytest.raises(ValueError):
        loan_plan(**args)
