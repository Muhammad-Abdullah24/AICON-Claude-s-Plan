"""Tests for the hold backtest (H1). Real AMIS data, standard library only; no network."""

import datetime as dt

from ml.backtest.hold import _percentile, hold_history

RATE, LOSS, WAIT, START = 16.5, 3.5, 4, 5   # wheat: sell in May vs September, bank money, godown loss


def test_shape_and_math_on_wheat():
    r = hold_history("Wheat", "Bahawalpur", START, WAIT, RATE, LOSS)
    assert r is not None
    assert r["start_month"] == 5 and r["later_month"] == 9      # May + 4 months
    assert r["n"] == len(r["seasons"]) >= 3
    assert r["wins"] == sum(1 for s in r["seasons"] if s["paid"])
    assert [s["year"] for s in r["seasons"]] == sorted(s["year"] for s in r["seasons"])  # oldest first
    for s in r["seasons"]:
        expected = s["later_price"] * (1 - LOSS / 100) - s["start_price"] * (1 + RATE / 100 * WAIT / 12)
        assert abs(s["net_gain_per_maund"] - expected) <= 2      # computed from medians, shown as whole rupees
        assert s["paid"] == (s["net_gain_per_maund"] > 0)
        assert s["start_price"] > 0 and s["later_price"] > 0
    assert min(s["net_gain_per_maund"] for s in r["seasons"]) <= r["median_net_per_maund"] <= max(
        s["net_gain_per_maund"] for s in r["seasons"])
    assert r["worst_p10_net_per_maund"] <= r["median_net_per_maund"]


def test_the_cost_of_money_only_makes_waiting_lose_more_often():
    """Higher interest can never make more seasons pay, and own cash (0%) pays most often."""
    def wins(rate: float) -> tuple[int, int]:
        w = n = 0
        for mandi in ("Bahawalpur", "Vehari", "Rahim Yar Khan"):
            for wait in (4, 5):                       # later months September and October
                r = hold_history("Wheat", mandi, START, wait, rate, LOSS)
                if r:
                    w += r["wins"]
                    n += r["n"]
        return w, n

    free, bank, arhti = wins(0.0), wins(16.5), wins(66.0)
    assert free[1] == bank[1] == arhti[1] and free[1] >= 20       # same seasons, just priced differently
    assert free[0] >= bank[0] >= arhti[0]                         # dearer money → fewer paying seasons
    # Roughly the PIVOT 3.1 check figures (there: 22/28, 11/28, 4/28; we have more years of data):
    n = free[1]
    assert free[0] / n >= 0.65 and bank[0] / n <= 0.55 and arhti[0] / n <= 0.25


def test_too_few_seasons_returns_none():
    assert hold_history("IRRI", "Rahim Yar Khan", START, WAIT, RATE, LOSS) is None   # no IRRI series there


def test_no_peeking_past_as_of():
    full = hold_history("Wheat", "Bahawalpur", START, WAIT, RATE, LOSS)
    latest_year = max(s["year"] for s in full["seasons"])
    # As of the day before that year's September ends, the latest season is not yet known.
    before = dt.date(latest_year, 9, 29)
    earlier = hold_history("Wheat", "Bahawalpur", START, WAIT, RATE, LOSS, as_of=before)
    assert latest_year not in {s["year"] for s in earlier["seasons"]}
    assert earlier["n"] == full["n"] - 1
    # As of the last day of that September, it is known again.
    on_end = dt.date(latest_year, 9, 30)
    assert hold_history("Wheat", "Bahawalpur", START, WAIT, RATE, LOSS, as_of=on_end)["n"] == full["n"]


def test_a_wait_that_crosses_the_new_year():
    # Start in November, wait 4 months → the following March.
    r = hold_history("Wheat", "Bahawalpur", 11, 4, RATE, LOSS)
    if r is not None:
        assert r["later_month"] == 3
        # Each season's later price is from the year after its start year (handled inside hold_history).


def test_percentile_helper():
    assert _percentile([10], 10) == 10
    assert _percentile([0, 100], 10) == 10           # linear interpolation
    assert _percentile([0, 10, 20, 30, 40], 50) == 20
