"""Urdu WhatsApp/SMS replies (task A8). Templates only arrange numbers the advisory engine gave us;
they never compute or invent one. Prices are Rs per 40 kg (one maund).

TODO(native speaker): read every Urdu string here aloud before the freeze.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

CROP_UR = {"Wheat": "گندم", "Cotton": "کپاس (پھٹی)", "IRRI": "چاول (اری)", "SuperBasmati": "چاول (سپر باسمتی)"}
MANDI_UR = {"BahawalPur": "بہاولپور", "Vehari": "وہاڑی", "RahimYarKhan": "رحیم یار خان"}
SIGNAL = {"SELL": ("🟢", "بیچ دیں"), "WAIT": ("🟡", "رکیں")}
CONFIDENCE_UR = {"HIGH": "زیادہ", "MEDIUM": "درمیانہ", "LOW": "کم"}

# WhatsApp interactive buttons: at most 3, titles at most 20 characters, body at most 1024.
BUTTONS = [("why", "کیوں؟"), ("compare", "منڈیاں"), ("stop", "الرٹ بند")]
MAX_BODY = 1024

HELP = ("السلام علیکم! اپنی فصل، منڈی اور مقدار لکھیں۔\n"
        "مثال: گندم بہاولپور 100 من\n"
        "فصلیں: گندم، کپاس، چاول (سپر باسمتی یا اری)\n"
        "منڈیاں: بہاولپور، وہاڑی، رحیم یار خان")
ASK = {
    "crop": "کون سی فصل؟ گندم، کپاس، یا چاول (سپر باسمتی یا اری)",
    "variety": "کون سے چاول؟ سپر باسمتی یا اری",
    "mandi": "کون سی منڈی؟ بہاولپور، وہاڑی یا رحیم یار خان",
}
SORRY = "معاف کیجیے، بات سمجھ نہیں آئی۔"
NOT_UNDERSTOOD = SORRY + "\n" + HELP
NEED_QUERY_FIRST = "پہلے فصل اور منڈی بتائیں، مثلاً: گندم بہاولپور 100 من"
NO_DATA = "{mandi} منڈی میں {crop} کا ریٹ ہمارے پاس موجود نہیں۔ کوئی اور منڈی آزمائیں۔"
NOT_READY = "یہ سروس ابھی تیار ہو رہی ہے۔ تھوڑی دیر بعد دوبارہ کوشش کریں۔"
STOPPED = "الرٹس بند کر دیے گئے۔ دوبارہ شروع کرنے کے لیے 'شروع' لکھیں۔"
STARTED = "الرٹس دوبارہ شروع کر دیے گئے۔"
VOICE_SOON = "وائس نوٹ کی سہولت جلد آ رہی ہے۔ ابھی لکھ کر بھیجیں، مثلاً: گندم بہاولپور 100 من"
SYNTHETIC = "⚠️ مصنوعی ڈیٹا (synthetic)، اصل قیمت نہیں"
DISCLAIMER = "یہ اندازہ ہے، گارنٹی نہیں۔"
DEFAULT_QUANTITY_MAUND = 100


def rs(x: float) -> str:
    return f"Rs {round(x):,}"


def signed_rs(x: float) -> str:
    return f"+{rs(x)}" if x >= 0 else f"−{rs(-x)}"


def advice_text(a: Mapping, quantity_assumed: bool = False) -> str:
    """One reply from the blueprint advice shape (docs/BLUEPRINT.md section 12, GET /api/advice)."""
    icon, word = SIGNAL[a["signal"]]
    crop = CROP_UR.get(a["crop_option"], a["crop_option"])
    mandi = MANDI_UR.get(a["mandi"], a["mandi"])
    qty = a["quantity_maund"]
    lines = [
        f"{icon} {crop}، {mandi}: {word}",
        f"آج: {rs(a['current_price'])} فی من (AMIS، {a['prices_as_of']} تک)",
        f"4 ہفتے بعد اندازہ: {rs(a['predicted_price'])} ({rs(a['range']['low'])} سے {rs(a['range']['high'])})",
        f"{qty:g} من پر رکنے کا فرق: {signed_rs(a['rupee_impact'])} ({rs(a['interest_cost'])} سود نکال کر)",
        f"اعتماد: {CONFIDENCE_UR.get(a['confidence'], a['confidence'])}",
    ]
    if quantity_assumed:
        lines.append(f"(مقدار نہیں بتائی، اس لیے {qty:g} من مان کر حساب کیا)")
    if a.get("is_synthetic"):
        lines.append(SYNTHETIC)
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def why_text(a: Mapping, reasons: Sequence[Mapping]) -> str:
    """Reasons come from the model's SHAP explanation, already as Urdu sentences (Owner B, B5)."""
    head = f"{CROP_UR.get(a['crop_option'], a['crop_option'])}، {MANDI_UR.get(a['mandi'], a['mandi'])}: وجہ"
    arrows = {"UP": "⬆️", "DOWN": "⬇️"}
    body = [f"{arrows.get(r.get('direction', ''), '•')} {r['text_ur']}" for r in reasons[:3]]
    return "\n".join([head, *body]) if body else head + "\nابھی وجہ دستیاب نہیں۔"


def compare_text(crop_option: str, rows: Sequence[Mapping]) -> str:
    """Rows: {mandi, net_price, transport_cost, gain_vs_preferred, has_data}, best first."""
    lines = [f"{CROP_UR.get(crop_option, crop_option)}: منڈیوں کا موازنہ (کرایہ نکال کر، فی من)"]
    for i, r in enumerate(rows):
        name = MANDI_UR.get(r["mandi"], r["mandi"])
        if not r.get("has_data", True):
            lines.append(f"• {name}: ریٹ موجود نہیں")
            continue
        mark = "✅ " if i == 0 else "• "
        gain = r.get("gain_vs_preferred")
        extra = f" ({signed_rs(gain)})" if gain else ""
        as_of = f" ({r['prices_as_of']} کا ریٹ)" if r.get("prices_as_of") else ""
        lines.append(f"{mark}{name}: {rs(r['net_price'])}{extra}, کرایہ تقریباً {rs(r['transport_cost'])}{as_of}")
    lines.append("کرایہ اندازہ ہے۔")
    return "\n".join(lines)


def clip(text: str, limit: int = MAX_BODY) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


# ---------------------------------------------------------------- numbered menu (task A11)
# The conversation engine (conversation.py) decides what to answer; these turn its reply intent into Urdu.

CHOICE_UR = {
    "advice": "ریٹ اور مشورہ", "compare": "منڈیوں کا موازنہ", "why": "مشورے کی وجہ",
    "alerts_on": "الرٹ چالو", "alerts_off": "الرٹ بند", "menu": "مینو", "rice": "چاول",
}
SHORT_UR = {"why": "کیوں؟", "compare": "منڈیاں", "alerts_on": "الرٹ چالو", "alerts_off": "الرٹ بند", "menu": "مینو"}
MENU_HEAD = "فارم سائٹ مینو: نمبر لکھ کر بھیجیں"
MENU_TAIL = "یا سیدھا لکھیں، مثلاً: گندم بہاولپور 100 من"
MENU_NOTE = {
    "expired": "پچھلی بات چیت کا وقت ختم ہو گیا، دوبارہ شروع کریں۔",
    "no_session": "یہ نمبر کس سوال کا جواب ہے، معلوم نہیں۔ مینو سے چنیں:",
}
INVALID = "یہ انتخاب درست نہیں۔"
ASK_NUMBERED = {"ask_crop": "کون سی فصل؟", "ask_variety": "کون سے چاول؟", "ask_mandi": "کون سی منڈی؟"}
ASK_QUANTITY = "کتنے من؟ صرف تعداد لکھیں، مثلاً 100"
NOT_REGISTERED = "الرٹ کے لیے یہ نمبر فارم سائٹ پر رجسٹر نہیں۔ پہلے ایپ میں اپنا پروفائل بنائیں۔"
ALERT_BUTTON = {"alerts_on": ("start", "الرٹ چالو"), "alerts_off": ("stop", "الرٹ بند")}


def choice_label(code: str) -> str:
    return CHOICE_UR.get(code) or CROP_UR.get(code) or MANDI_UR.get(code) or code


def choice_lines(choices) -> str:
    """One numbered line per choice, for menus the farmer answers with a number."""
    return "\n".join(f"{n}  {choice_label(code)}" for n, code in choices)


def choice_footer(choices) -> str:
    """The short next-step line under an answer: '1 کیوں؟ · 2 منڈیاں · 3 الرٹ بند · 0 مینو'."""
    return " · ".join(f"{n} {SHORT_UR.get(code, choice_label(code))}" for n, code in choices)


def buttons_for(choices) -> list[tuple[str, str]]:
    """WhatsApp quick-reply buttons for an answer's next steps (at most 3, ids are the command words)."""
    out = []
    for _, code in choices:
        if code in ("why", "compare"):
            out.append((code, SHORT_UR[code]))
        elif code in ALERT_BUTTON:
            out.append(ALERT_BUTTON[code])
    return out[:3]
