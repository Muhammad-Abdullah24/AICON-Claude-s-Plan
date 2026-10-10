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
NOT_UNDERSTOOD = "معاف کیجیے، بات سمجھ نہیں آئی۔\n" + HELP
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


# ---------------------------------------------------------------- wait plan (task H6; docs/PIVOT.md section 3.3)

# The wait plan returns lowercase API ids; accept those and the data names ("Wheat", "BahawalPur") either way.
CROP_UR_ANY = {**CROP_UR, "wheat": "گندم", "cotton": "کپاس (پھٹی)",
               "irri": "چاول (اری)", "super_basmati": "چاول (سپر باسمتی)"}
MANDI_UR_ANY = {**MANDI_UR, "bahawalpur": "بہاولپور", "vehari": "وہاڑی", "rahim_yar_khan": "رحیم یار خان"}

VERDICT_UR = {
    "SELL_ALL": "ابھی سب بیچ دیں",
    "SPLIT": "کچھ ابھی بیچیں، باقی روک لیں",
    "HOLD_REST": "فی الحال روک لیں",
}
EXIT_UR = {"SELL_NOW": "ابھی بیچنے پر", "ARHTI_OFFER": "آڑھتی کی پیشکش پر", "HOLD": "روکنے پر"}
WARNING_UR = {
    "NEWS_PRICE_CONFLICT": "⚠️ خبروں میں ریٹ مختلف آ رہا ہے، احتیاط کریں",
    "STALE_PRICE": "⚠️ ریٹ پرانا ہے، احتیاط کریں",
    "POLICY_UNCERTAIN": "⚠️ سرکاری پالیسی ابھی غیر یقینی ہے",
    "HOLD_WHEAT_ONLY": "نوٹ: روکنے کا مشورہ صرف گندم کے لیے ہے",
}


def wait_text(plan: Mapping) -> str:
    """One WhatsApp reply from the wait plan (docs/PIVOT.md 3.3): sell now or hold, with each way out in rupees,
    how often holding paid in the past, and any warnings. Every number comes from the plan; this only lays it out."""
    crop = CROP_UR_ANY.get(plan["crop_option"], plan["crop_option"])
    mandi = MANDI_UR_ANY.get(plan["mandi"], plan["mandi"])
    lines = [f"{crop}، {mandi}: {VERDICT_UR.get(plan['verdict'], plan['verdict'])}"]
    if plan.get("sell_now_maund"):
        lines.append(f"ابھی بیچیں: {plan['sell_now_maund']:g} من")
    if plan.get("hold_maund"):
        lines.append(f"روک لیں: {plan['hold_maund']:g} من")
    if plan.get("best_net_price") is not None:
        best = MANDI_UR_ANY.get(plan.get("best_mandi"), plan.get("best_mandi"))
        lines.append(f"بہترین منڈی: {best} ({rs(plan['best_net_price'])} فی من اصل)")
    for e in plan.get("exits", []):
        label = EXIT_UR.get(e["kind"], e["kind"])
        if e["kind"] == "HOLD":
            lines.append(f"• {label}: اندازاً {rs(e['expected_total_rs'])}، برے سال میں {rs(e['worst_total_rs'])}")
        else:
            lines.append(f"• {label}: {rs(e['net_total_rs'])}")
    h = plan.get("history") or {}
    if h.get("n"):
        lines.append(f"پچھلے {h['n']} سالوں میں رکنا {h['wins']} بار فائدہ مند رہا")
    lines += [WARNING_UR[w] for w in plan.get("warnings", []) if w in WARNING_UR]
    lines.append(DISCLAIMER)
    return clip("\n".join(lines))
