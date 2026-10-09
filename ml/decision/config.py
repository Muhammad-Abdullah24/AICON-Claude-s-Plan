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
