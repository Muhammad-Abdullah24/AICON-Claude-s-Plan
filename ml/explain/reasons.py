"""SHAP contributions -> the top reasons, with rupee effects, in Urdu and English (task B5).

Pure Python, no third-party imports: ml/forecast/predict.py computes the contributions (XGBoost's exact
TreeSHAP, `pred_contribs=True`) and passes them here as {feature: contribution in % change points}.

Single features mean little to a farmer ("month_cos"), so related features are summed into one reason
(SHAP values are additive, so a group's effect is the sum of its features'). Each reason's rupee effect is
its share of the predicted change applied to today's price: contribution / 100 x price, Rs per 40 kg.

No LLM writes these sentences. The Urdu wording needs the native-speaker review in docs/PLAN.md P4.2.
"""

from __future__ import annotations

from collections.abc import Mapping

# feature -> reason group. Every model input must be listed (a test checks this against the trained model).
GROUPS: dict[str, str] = {
    "momentum_1w_pct": "recent_trend",
    "momentum_4w_pct": "recent_trend",
    "momentum_8w_pct": "recent_trend",
    "price_vs_ma_8w_pct": "recent_trend",
    "volatility_4w": "price_swings",
    "volatility_8w": "price_swings",
    "month": "season",
    "week_of_year": "season",
    "month_sin": "season",
    "month_cos": "season",
    "is_sowing": "crop_calendar",
    "is_harvest": "crop_calendar",
    "precip_mm_wk": "rain",
    "precip_mm_4w": "rain",
    "precip_mm_12w": "rain",
    "tmax_c": "heat",
    "tmin_c": "heat",
    "hot_days_wk": "heat",
    "tmax_c_4w": "heat",
    "rh_pct": "heat",
    "et0_mm_wk": "heat",
    "city_id": "market",
    "crop_id": "market",
    "variety_id": "market",
    "crop_option_id": "market",
    "price_was_filled": "data_gap",
}

# Both languages say "because of <label>". Urdu labels are in the oblique form, since "کی وجہ سے" follows them.
LABELS: dict[str, dict[str, str]] = {
    "recent_trend": {"en": "the recent price trend", "ur": "قیمتوں کے حالیہ رجحان"},
    "price_swings": {"en": "recent price swings", "ur": "قیمتوں کے حالیہ اتار چڑھاؤ"},
    "season": {"en": "the time of year", "ur": "سال کے اس وقت"},
    "crop_calendar": {"en": "the sowing or harvest season", "ur": "بوائی یا کٹائی کے موسم"},
    "rain": {"en": "rainfall", "ur": "بارش"},
    "heat": {"en": "heat and weather", "ur": "گرمی اور موسم"},
    "market": {"en": "the usual pattern for this crop at this mandi", "ur": "اس منڈی میں اس فصل کے عام رجحان"},
    "data_gap": {"en": "a gap in the price record", "ur": "قیمت کے ریکارڈ میں خلا"},
}

TEMPLATES = {
    ("en", "UP"): "Because of {label}, the price may rise by about Rs {rs} per 40 kg.",
    ("en", "DOWN"): "Because of {label}, the price may fall by about Rs {rs} per 40 kg.",
    ("ur", "UP"): "{label} کی وجہ سے ریٹ تقریباً {rs} روپے فی من بڑھ سکتا ہے۔",
    ("ur", "DOWN"): "{label} کی وجہ سے ریٹ تقریباً {rs} روپے فی من کم ہو سکتا ہے۔",
}

DEFAULT_TOP_N = 3
MAX_TOP_N = 5


def reasons(contributions: Mapping[str, float], current_price: float, top_n: int = DEFAULT_TOP_N) -> list[dict]:
    """The biggest `top_n` reasons (3 to 5), largest rupee effect first.

    `contributions` maps model features to SHAP contributions in % change points; the bias term, if
    present, is ignored. Reasons whose rupee effect rounds to zero are left out, so the list can be short.
    Raises KeyError for a feature with no group, so a new model input cannot silently go unexplained.
    """
    if current_price <= 0:
        raise ValueError(f"current_price must be positive, got {current_price!r}")
    top_n = max(1, min(top_n, MAX_TOP_N))

    by_group: dict[str, float] = {}
    members: dict[str, list[str]] = {}
    for feature, value in contributions.items():
        if feature == "bias":
            continue
        group = GROUPS[feature]
        by_group[group] = by_group.get(group, 0.0) + value
        members.setdefault(group, []).append(feature)

    out = []
    for group, pct in sorted(by_group.items(), key=lambda kv: abs(kv[1]), reverse=True):
        rs = round(abs(pct) / 100 * current_price)
        if rs == 0:
            continue
        direction = "UP" if pct > 0 else "DOWN"
        label = LABELS[group]
        out.append({
            "feature": group,
            "features": sorted(members[group]),
            "rs_effect": rs if direction == "UP" else -rs,
            "direction": direction,
            "text_en": TEMPLATES[("en", direction)].format(label=label["en"], rs=f"{rs:,}"),
            "text_ur": TEMPLATES[("ur", direction)].format(label=label["ur"], rs=f"{rs:,}"),
        })
        if len(out) == top_n:
            break
    return out
