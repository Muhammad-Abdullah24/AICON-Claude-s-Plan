import pytest

from ml.decision import config
from ml.decision.engine import BandPoint, Costs, DecisionInput, OtherMandi, decide, value_of_waiting

FREE = Costs(storage_cost_per_maund_week=0, spoilage_pct_week=0, finance_cost_pct_month=0)


def band(p: float, q50_change: float, spread: float = 0.02) -> list[BandPoint]:
    """A 4-week band whose middle moves by q50_change (fraction) by week 4."""
    out = []
    for h in range(1, 5):
        q50 = p * (1 + q50_change * h / 4)
        out.append(BandPoint(h, q50 * (1 - spread), q50, q50 * (1 + spread)))
    return out


def test_value_of_waiting_matches_plan_formula():
    costs = Costs(storage_cost_per_maund_week=10, spoilage_pct_week=1, finance_cost_pct_month=2)
    # q50 * (1 - spoilage*weeks) - storage*weeks - finance*weeks  (PLAN.md 10.2)
    finance_week = 1000 * 0.02 / config.WEEKS_PER_MONTH
    expected = 1100 * (1 - 0.01 * 2) - 10 * 2 - finance_week * 2
    assert value_of_waiting(1100, 2, 1000, costs) == pytest.approx(expected)


def test_rising_prices_with_cheap_storage_says_store():
    d = decide(DecisionInput(price_now=1000, band=band(1000, 0.10), can_store=True, costs=FREE))
    assert d.verdict == "store"
    assert d.best_week == 4
    assert d.gain_per_maund == pytest.approx(100)
    assert d.reasons[0].code == "wait_gain"


def test_no_storage_never_says_store():
    d = decide(DecisionInput(price_now=1000, band=band(1000, 0.10), can_store=False, costs=FREE))
    assert d.verdict == "sell_now"
    assert d.gain_per_maund == 0
    assert d.reasons[0].code == "cannot_store"


def test_falling_prices_say_sell_now():
    d = decide(DecisionInput(price_now=1000, band=band(1000, -0.08), can_store=True, costs=FREE))
    assert d.verdict == "sell_now"
    assert {r.code for r in d.reasons} >= {"trend_down", "no_clear_gain"}


def test_costs_can_wipe_out_a_small_rise():
    costly = Costs(storage_cost_per_maund_week=20, spoilage_pct_week=0.5, finance_cost_pct_month=1.5)
    d = decide(DecisionInput(price_now=1000, band=band(1000, 0.04), can_store=True, costs=costly))
    assert d.verdict == "sell_now"


def test_much_better_mandi_says_sell_elsewhere():
    other = OtherMandi("vehari", price_now=1200, transport_cost_per_maund=50)
    d = decide(DecisionInput(
        price_now=1000, band=band(1000, 0.0), can_store=True, costs=FREE, other_mandis=[other],
    ))
    assert d.verdict == "sell_elsewhere"
    assert d.gain_per_maund == pytest.approx(150)
    assert d.best_other == other


def test_transport_cost_can_cancel_a_price_gap():
    other = OtherMandi("vehari", price_now=1100, transport_cost_per_maund=95)
    d = decide(DecisionInput(
        price_now=1000, band=band(1000, 0.0), can_store=True, costs=FREE, other_mandis=[other],
    ))
    assert d.verdict == "sell_now"


def test_wide_band_says_split():
    d = decide(DecisionInput(price_now=1000, band=band(1000, 0.10, spread=0.12), can_store=True, costs=FREE))
    assert d.verdict == "split"
    assert d.gain_per_maund == pytest.approx(100 * config.SPLIT_STORE_SHARE)


def test_active_alert_says_split_instead_of_store():
    d = decide(DecisionInput(
        price_now=1000, band=band(1000, 0.10), can_store=True, costs=FREE, alert_active=True,
    ))
    assert d.verdict == "split"
    assert d.reasons[-1].code == "alert_active"


def test_large_downside_says_sell_now():
    risky = [BandPoint(h, 800, 1000 + 30 * h, 1300) for h in range(1, 5)]
    d = decide(DecisionInput(price_now=1000, band=risky, can_store=True, costs=FREE))
    assert d.verdict == "sell_now"
    assert any(r.code == "downside_large" for r in d.reasons)


def test_risk_line_uses_lowest_q10():
    b = [BandPoint(1, 950, 1000, 1050), BandPoint(2, 900, 1000, 1100)]
    d = decide(DecisionInput(price_now=1000, band=b, can_store=True, costs=FREE))
    assert (d.lowest_price, d.lowest_price_week) == (900, 2)


@pytest.mark.parametrize("bad", [
    DecisionInput(price_now=0, band=band(1000, 0.1), can_store=True, costs=FREE),
    DecisionInput(price_now=1000, band=[], can_store=True, costs=FREE),
])
def test_rejects_invalid_input(bad):
    with pytest.raises(ValueError):
        decide(bad)
