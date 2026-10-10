"""Rules for the advisory engine (ml/decision/advisory.py), from the blueprint.

Each value says where it comes from. Rates, costs and prices are not here: they come from the data
(ml/decision/inputs.py).
"""


# Blueprint section 7: WAIT when the 4-week forecast is at least this much above today, otherwise SELL.
# A 5% rise in 4 weeks happens in only 14-19% of real weeks, so SELL is the usual answer, by design.
WAIT_THRESHOLD_PCT = 5.0

# The forecast horizon the signal and the interest cost refer to.
HORIZON_WEEKS = 4

# Confidence from the q10-q90 width as % of today's price. First draft: re-check against the
# coverage A5's gate reports after B4, and write the final values in docs/MODEL_CARD.md.
HIGH_CONFIDENCE_MAX_WIDTH_PCT = 10.0
MEDIUM_CONFIDENCE_MAX_WIDTH_PCT = 20.0

# Crop plan risk badge (B7): year-to-year spread of the harvest ratio, (max - min) / median, in %.
# Set at the thirds of the real spreads (99 harvest_ratios.csv rows with enough years: 33rd percentile 31%,
# 67th 55%), so each badge covers about a third of cases. The first draft (20 / 40) made almost every crop
# HIGH. A crop with fewer than ENOUGH_YEARS of history (A6's flag) is always HIGH; a stale price adds a level.
LOW_RISK_MAX_SPREAD_PCT = 30.0
MEDIUM_RISK_MAX_SPREAD_PCT = 55.0

# Selling window (B7): months whose price after interest is within this many % points of the best month.
SELLING_WINDOW_TOLERANCE_PCT = 1.0

# Alerts (B8). At most one alert per farmer in this many days, across all their crops.
ALERT_MIN_DAYS_BETWEEN = 7


# ---------------------------------------------------------------- pivot: the wait engine (ml/decision/wait.py)
# "Can you afford to wait, and with whose money?" Rates and storage losses, with sources in docs/FACTS.md.
# The annual cost of the money tied up while the crop is held, by source (%/year).
DEFAULT_RATE_PCT = {"own": 0.0, "bank": 16.5, "arhti": 66.0}
# Grain lost over the wait, by store. Assumptions inside a documented 2-18% band (docs/FACTS.md H4): treat as estimates.
LOSS_PCT = {"godown": 3.5, "bags": 10.0}
# Holding the rest is advised only when it paid in at least this share of past seasons AND the median season gained
# at least HOLD_MIN_MEDIAN_PCT of today's price. E1 (docs/PIVOT.md, review of 10 Oct): the first rule (half the
# seasons, any positive median) said HOLD on +Rs 13/maund (0.3%), which is noise, not an edge.
HOLD_MIN_WIN_RATE = 0.6
HOLD_MIN_MEDIAN_PCT = 1.0
# A news price this far (%) from the AMIS price, or closer, is not flagged as a conflict.
NEWS_CONFLICT_PCT = 10.0
# A policy/news item within this many days counts as "recent" (POLICY_UNCERTAIN, confidence down one level).
POLICY_RECENT_DAYS = 14
