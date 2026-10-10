"""Tests for the wait engine (B1). Pure: the hold backtest is passed in as a dict."""

from ml.decision import wait

# A hold result where waiting paid most years (good) and one where it rarely did (bad).
GOOD_HOLD = {"start_month": 5, "later_month": 9, "annual_rate_pct": 0.0, "loss_pct": 3.5, "n": 9, "wins": 7,
             "median_net_per_maund": 120, "worst_p10_net_per_maund": -150, "seasons": []}
BAD_HOLD = {**GOOD_HOLD, "wins": 2, "median_net_per_maund": -80}

BASE = dict(quantity_maund=100, best_mandi="BahawalPur", best_net_price=3655.0, is_wheat=True,
            wait_months=4, money="own", annual_rate_pct=0.0, storage="godown", loss_pct=3.5)


def test_split_when_holding_pays_and_cash_is_needed():
    p = wait.wait_plan(cash_need_rs=73100, hold=GOOD_HOLD, **BASE)   # ceil(73100/3655) = 20 maund
    assert p["verdict"] == "SPLIT" and p["sell_now_maund"] == 20 and p["hold_maund"] == 80
    kinds = [e["kind"] for e in p["exits"]]
    assert kinds == ["SELL_NOW", "HOLD"]
    hold_exit = p["exits"][-1]
    assert hold_exit["per_maund"] == 3655 + 120 and hold_exit["total_rs"] == round((3655 + 120) * 100)
    assert hold_exit["worst_total_rs"] == round((3655 - 150) * 100) and hold_exit["cost_rs"] > 0
    assert p["history"] is GOOD_HOLD or p["history"] == GOOD_HOLD


def test_hold_all_when_holding_pays_and_no_cash_needed():
    p = wait.wait_plan(cash_need_rs=0, hold=GOOD_HOLD, **BASE)
    assert p["verdict"] == "HOLD_ALL" and p["sell_now_maund"] == 0 and p["hold_maund"] == 100


def test_sell_all_when_holding_does_not_pay_but_still_shows_the_history():
    p = wait.wait_plan(cash_need_rs=0, hold=BAD_HOLD, **BASE)
    assert p["verdict"] == "SELL_ALL" and p["sell_now_maund"] == 100
    assert p["history"] == BAD_HOLD                  # we still show why: holding rarely paid
    assert [e["kind"] for e in p["exits"]] == ["SELL_NOW", "HOLD"]


def test_non_wheat_is_sell_all_with_no_hold_option():
    p = wait.wait_plan(cash_need_rs=0, hold=None, **{**BASE, "is_wheat": False})
    assert p["verdict"] == "SELL_ALL" and p["history"] is None
    assert "HOLD_WHEAT_ONLY" in p["warnings"] and [e["kind"] for e in p["exits"]] == ["SELL_NOW"]


def test_wheat_with_too_few_seasons_cannot_recommend_holding():
    p = wait.wait_plan(cash_need_rs=0, hold=None, **BASE)
    assert p["verdict"] == "SELL_ALL" and p["history"] is None and "TOO_FEW_SEASONS" in p["warnings"]


def test_cash_need_exceeding_the_whole_crop_is_flagged():
    p = wait.wait_plan(cash_need_rs=10_000_000, hold=GOOD_HOLD, **BASE)
    assert "CASH_NEED_EXCEEDS_CROP" in p["warnings"] and p["sell_now_maund"] == 100 and p["verdict"] == "SELL_ALL"


def test_an_offer_adds_an_arhti_exit():
    p = wait.wait_plan(cash_need_rs=0, hold=GOOD_HOLD, offer=3400.0, **BASE)
    arhti = next(e for e in p["exits"] if e["kind"] == "ARHTI_OFFER")
    assert arhti["per_maund"] == 3400 and arhti["total_rs"] == 340000


def test_stale_news_and_policy_lower_confidence_and_add_warnings():
    assert wait.wait_plan(cash_need_rs=0, hold=GOOD_HOLD, is_stale=True, **BASE)["confidence"] == "LOW"
    p = wait.wait_plan(cash_need_rs=0, hold=GOOD_HOLD, news_conflict=True, policy_recent=True, **BASE)
    assert p["confidence"] == "LOW" and "NEWS_PRICE_CONFLICT" in p["warnings"] and "POLICY_UNCERTAIN" in p["warnings"]


def test_noise_level_gain_or_a_coin_flip_is_not_enough_to_hold():
    # E1: +Rs 13/maund on Rs 3,655 (0.4%) is noise; 5 wins in 10 is a coin flip. Both mean sell.
    noise = {**GOOD_HOLD, "median_net_per_maund": 13}
    coin = {**GOOD_HOLD, "n": 10, "wins": 5}
    for hold in (noise, coin):
        assert wait.wait_plan(cash_need_rs=0, hold=hold, **BASE)["verdict"] == "SELL_ALL"
    edge = {**GOOD_HOLD, "n": 10, "wins": 6, "median_net_per_maund": 37}   # 60% and 1.01% of the price: hold
    assert wait.wait_plan(cash_need_rs=0, hold=edge, **BASE)["verdict"] == "HOLD_ALL"
