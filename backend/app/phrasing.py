"""Turns the engine's reason codes into Urdu or English sentences (PLAN.md 7.8 and 13).

Every number in a sentence comes from the engine. The templates only arrange
it. If an LLM is added later to smooth the wording, it rephrases these
sentences and never adds or changes a number.

TODO(native speaker): read every Urdu string here aloud before the freeze.
"""

from __future__ import annotations

from ml.decision.engine import Reason

MAX_REASONS = 3

VERDICT_TEXT = {
    "ur": {
        "sell_now": "ابھی بیچیں",
        "sell_elsewhere": "دوسری منڈی میں بیچیں",
        "store": "ذخیرہ کریں، بعد میں بیچیں",
        "split": "کچھ ابھی بیچیں، کچھ ذخیرہ کریں",
    },
    "en": {
        "sell_now": "Sell now",
        "sell_elsewhere": "Sell at another mandi",
        "store": "Store and sell later",
        "split": "Sell part now, store part",
    },
}

REASONS = {
    "ur": {
        "trend_up": "اگلے {weeks} ہفتوں میں ریٹ تقریباً {pct}% بڑھنے کا اندازہ ہے",
        "trend_down": "اگلے {weeks} ہفتوں میں ریٹ تقریباً {pct}% گرنے کا اندازہ ہے",
        "trend_flat": "اگلے {weeks} ہفتوں میں ریٹ میں بڑی تبدیلی کا اندازہ نہیں",
        "elsewhere_better": "{mandi} منڈی میں کرایہ نکال کر Rs {net_price} فی من، یعنی Rs {gain} زیادہ",
        "wait_gain": "{weeks} ہفتے رکھنے پر خرچ نکال کر تقریباً Rs {gain} فی من زیادہ",
        "downside_large": "رکھنے میں خطرہ زیادہ ہے: ریٹ Rs {low} تک گر سکتا ہے",
        "band_wide": "{weeks} ہفتے بعد ریٹ Rs {low} سے Rs {high} کے بیچ کہیں بھی ہو سکتا ہے",
        "no_clear_gain": "رکھنے سے خرچ نکال کر کوئی واضح فائدہ نہیں",
        "cannot_store": "آپ کے پاس ذخیرہ کرنے کی سہولت نہیں",
        "alert_active": "اس فصل کے لیے الرٹ جاری ہے",
    },
    "en": {
        "trend_up": "Price expected to rise about {pct}% over the next {weeks_en}",
        "trend_down": "Price expected to fall about {pct}% over the next {weeks_en}",
        "trend_flat": "No big price change expected over the next {weeks_en}",
        "elsewhere_better": "{mandi} pays Rs {net_price} per maund after transport, Rs {gain} more",
        "wait_gain": "Holding {weeks_en} could earn about Rs {gain} more per maund after costs",
        "downside_large": "Holding is risky: the price could fall to Rs {low}",
        "band_wide": "In {weeks_en} the price could be anywhere from Rs {low} to Rs {high}",
        "no_clear_gain": "Holding gives no clear gain after costs",
        "cannot_store": "You have no storage",
        "alert_active": "There is an active alert for this crop",
    },
}

RISK_LINE = {
    "ur": "ریٹ {weeks} ہفتے میں Rs {low} تک بھی گر سکتا ہے",
    "en": "The price could fall as low as Rs {low} within {weeks_en}",
}

def _fmt(value: float | int | str) -> str:
    """Western digits with thousands separators, as on receipts (PLAN.md 13)."""
    if isinstance(value, int | float):
        return f"{round(value):,}" if float(value).is_integer() or abs(value) >= 100 else f"{value:g}"
    return value


def _weeks_en(n: int) -> str:
    return "1 week" if n == 1 else f"{n} weeks"


def verdict_text(verdict: str, lang: str) -> str:
    return VERDICT_TEXT[lang][verdict]


def reasons_text(reasons: list[Reason], lang: str, mandi_names: dict[str, str]) -> list[str]:
    out = []
    for r in reasons[:MAX_REASONS]:
        params = {k: _fmt(v) for k, v in r.params.items()}
        if "weeks" in r.params:
            params["weeks_en"] = _weeks_en(int(r.params["weeks"]))
        if "mandi" in params:
            params["mandi"] = mandi_names.get(str(r.params["mandi"]), str(r.params["mandi"]))
        out.append(REASONS[lang][r.code].format(**params))
    return out


def risk_line(low: float, weeks: int, lang: str) -> str:
    return RISK_LINE[lang].format(low=_fmt(low), weeks=weeks, weeks_en=_weeks_en(weeks))
