"""Decision thresholds (PLAN.md section 10.3).

Owner B: these are first-draft values, not tuned. Set them from the rupee
backtest and write down why in the comment next to each one.

All thresholds are fractions of today's price, so they work the same for a
Rs 3,000 crop and a Rs 9,000 crop.
"""

# "Clearly" more: a gain smaller than this is noise once the farmer's time and
# risk are counted, so we do not tell them to change what they would do.
MIN_CLEAR_GAIN_FRACTION = 0.02

# "Limited" downside: if the pessimistic (q10) outcome of waiting loses more
# than this, waiting is too risky to recommend in full.
MAX_DOWNSIDE_FRACTION = 0.05

# A band (q90 - q10) wider than this share of the middle estimate means the
# forecast is too uncertain to bet the whole harvest on.
WIDE_BAND_FRACTION = 0.20

# Share of the harvest the "split" verdict tells the farmer to store.
SPLIT_STORE_SHARE = 0.5

# Converts a monthly finance cost to a weekly one.
WEEKS_PER_MONTH = 52 / 12

# ---------------------------------------------------------------- blueprint rules (B2, ml/decision/advisory.py)
# The constants above belong to the superseded engine.py and go when C3 retires it.

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
# First draft; a crop with fewer than ENOUGH_YEARS of history (A6's flag) is always HIGH.
LOW_RISK_MAX_SPREAD_PCT = 20.0
MEDIUM_RISK_MAX_SPREAD_PCT = 40.0

# Selling window (B7): months whose price after interest is within this many % points of the best month.
SELLING_WINDOW_TOLERANCE_PCT = 1.0
