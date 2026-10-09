"""Constants for the feature pipeline (Owner A).

Crop calendar and id encodings are model-schema constants: the trained models depend on these exact ids,
so they live here, next to the code that writes them. A2's runtime tables are generated to agree with them.
"""

HORIZON_WEEKS = 4
DIRECTION_THRESHOLD_PCT = 3

# Legacy label rule kept so features.csv stays reproducible. The blueprint's own SELL/WAIT rule lives in
# ml/decision/ (Owner B); treat `action` as a reference label, not the product rule.
STORAGE_RS_PER_40KG_MONTH = 15
INTEREST_PCT_PER_MONTH = 1.375
NET_GAIN_WAIT_PCT = 3
SELL_DROP_PCT = -3

# Split by the target week, so no training row can see a validation or test price.
TRAIN_TARGET_BEFORE = "2025-01-01"
VAL_START = "2025-01-01"
VAL_TARGET_BEFORE = "2026-01-01"
TEST_START = "2026-01-01"

# Weather aggregation rules (shared by training and the runtime weather service).
MIN_DAYS_PER_WEEK = 5
HOT_DAY_TMAX_C = 40
MIN_WEEKS_4W = 3
MIN_WEEKS_12W = 9

CITY_ID = {"BahawalPur": 0, "Vehari": 1, "RahimYarKhan": 2}
CROP_ID = {"Wheat": 0, "Rice": 1, "Cotton": 2}
VARIETY_ID = {"none": 0, "IRRI": 1, "SuperBasmati": 2}
CROP_OPTION = {("Wheat", "none"): "Wheat", ("Cotton", "none"): "Cotton",
               ("Rice", "IRRI"): "IRRI", ("Rice", "SuperBasmati"): "SuperBasmati"}
CROP_OPTION_ID = {"Wheat": 0, "Cotton": 1, "IRRI": 2, "SuperBasmati": 3}

# Weather file district names -> AMIS city names.
WEATHER_CITY = {"Bahawalpur": "BahawalPur", "Vehari": "Vehari", "Rahim_Yar_Khan": "RahimYarKhan"}

# (start month, end month); start > end means the season wraps over the new year.
CROP_CALENDAR = {
    "Wheat": {"sow": (10, 12), "harvest": (4, 6)},
    "Rice": {"sow": (6, 7), "harvest": (10, 11)},
    "Cotton": {"sow": (4, 6), "harvest": (9, 12)},
}

AMIS_PER_100KG_TO_PER_40KG = 0.4
