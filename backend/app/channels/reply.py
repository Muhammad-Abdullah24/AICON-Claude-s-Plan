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
VOICE_SOON = ("وائس نوٹ کی سہولت ابھی دستیاب نہیں۔ لکھ کر بھیجیں، مثلاً: گندم بہاولپور 100 من\n"
              "یا مینو کے لیے 0 لکھیں۔")
VOICE_FAILED = "وائس نوٹ سنا نہیں جا سکا۔ لکھ کر بھیجیں، یا مینو کے لیے 0 لکھیں۔"
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
    "offer": "خریدار کی آفر چیک کریں", "advice": "ریٹ اور مشورہ", "compare": "منڈیوں کا موازنہ",
    "why": "وجہ اور ڈیٹا کی تفصیل", "alerts_on": "الرٹ شروع کریں", "alerts_off": "الرٹ بند کریں", "menu": "مینو",
    "rice": "چاول",
    "confirm": "درست ہے", "correct": "درست کریں",
}
SHORT_UR = {"why": "کیوں؟", "compare": "منڈیاں", "alerts_on": "الرٹ چالو", "alerts_off": "الرٹ بند", "menu": "مینو",
            "offer": "آفر چیک"}
MENU_HEAD = "فارم سائٹ مینو: نمبر لکھ کر بھیجیں"
MENU_TAIL = "یا سیدھا لکھیں، مثلاً: گندم بہاولپور 100 من آفر 3514"
MENU_NOTE = {
    "expired": "پچھلی بات چیت کا وقت ختم ہو گیا، دوبارہ شروع کریں۔",
    "no_session": "یہ نمبر کس سوال کا جواب ہے، معلوم نہیں۔ مینو سے چنیں:",
    "voice_unclear": "وائس نوٹ صاف سمجھ نہیں آیا۔ لکھ کر بھیجیں یا مینو سے چنیں:",
}
HEARD = "میں نے سنا: {heard}۔ کیا یہ درست ہے؟"
NOT_HEARD = "؟"  # a piece the voice note did not contain
INVALID = "یہ انتخاب درست نہیں۔"
ASK_NUMBERED = {"ask_crop": "کون سی فصل؟", "ask_variety": "کون سے چاول؟", "ask_mandi": "کون سی منڈی؟"}
ASK_QUANTITY = "کتنے من؟ صرف تعداد لکھیں، مثلاً 100"
ASK_OFFER = "خریدار نے فی من کتنا دیا؟ صرف رقم لکھیں، مثلاً 3514"
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


def heard_text(crop_option: str | None, mandi: str | None, quantity_maund: float | None) -> str:
    """What the voice note was understood to say, before anything is done with it."""
    qty = f"{quantity_maund:g} من" if quantity_maund else NOT_HEARD
    parts = [choice_label(crop_option) if crop_option else NOT_HEARD,
             choice_label(mandi) if mandi else NOT_HEARD, qty]
    return HEARD.format(heard="، ".join(parts))


# ---------------------------------------------------------------- buyer offer check
# The offer against recent AMIS *reference* prices (services.offer_check), never a fair or guaranteed price.
# The words match the web app's (frontend/src/locales/ur.json, "offer").

OFFER_STATUS_UR = {
    "BELOW_REFERENCE_RANGE": "حالیہ حوالہ حد سے کم",
    "WITHIN_REFERENCE_RANGE": "حالیہ حوالہ حد کے اندر",
    "ABOVE_REFERENCE_RANGE": "حالیہ حوالہ حد سے زیادہ",
    "REFERENCE_DATA_LIMITED": "حوالہ ڈیٹا محدود ہے",
}
LIMITED_UR = {
    "LIMITED_SAME_PRICE": "AMIS نے رپورٹ ہونے والے تمام {days} دن ایک ہی حوالہ ریٹ بتایا۔",
    "LIMITED_STALE": "آخری رپورٹ شدہ ریٹ {date} کا ہے، 8 ہفتے سے زیادہ پرانا۔",
    "LIMITED_FROZEN": "AMIS {date} سے ایک ہی ریٹ دکھا رہا ہے، جس کا اکثر مطلب ہے کہ ریٹ تازہ نہیں کیا گیا۔",
    "LIMITED_FEW_DAYS": "AMIS نے پچھلے {window} دن میں سے صرف {days} دن ریٹ رپورٹ کیا۔",
}
NOT_A_RANGE = "اس لیے فارم سائٹ اسے بازار کی قابلِ اعتماد حد نہیں مان سکتا۔"
OFFER_CAVEAT = "کوالٹی، گریڈ اور خریدار کی شرائط شامل نہیں۔ یہ رپورٹ شدہ ریٹ حوالہ ہیں، وعدہ نہیں۔"
ALT_VERDICT_UR = {
    "better": "کرایہ نکال کر بہتر ہونے کا اندازہ", "notBetter": "کرایہ نکال کر بہتر ہونے کا اندازہ نہیں",
    "higherNotBetter": "ریٹ زیادہ، لیکن کرایہ نکال کر بہتر نہیں", "unknown": "حوالہ ریٹ کمزور، موازنہ ممکن نہیں",
    "noData": "ریٹ رپورٹ نہیں ہوا",
}
VERIFY_UR = "کرایہ اندازہ ہے۔ جانے سے پہلے تصدیق کریں کہ خریدار موجود ہے اور اس کی شرائط کیا ہیں۔"


def alternative_verdict(a: Mapping) -> str:
    """The API's own flags in one word (the same mapping as the web app's lib/offer.ts)."""
    if not a.get("has_data"):
        return "noData"
    if a.get("better_after_transport") is None:
        return "unknown"
    if a["better_after_transport"]:
        return "better"
    return "higherNotBetter" if a.get("higher_quote_not_better") else "notBetter"


def limited_reason_ur(r: Mapping) -> str | None:
    if r["reference_strength"] == "STRONG":
        return None
    when = r.get("price_unchanged_since") or r["reference_price_as_of"]
    return LIMITED_UR[r["reference_strength"]].format(days=r["reference_days"], window=r["window_days"],
                                                      date=when)


def offer_text(crop_option: str, mandi: str, r: Mapping) -> str:
    crop, place = CROP_UR.get(crop_option, crop_option), MANDI_UR.get(mandi, mandi)
    per, qty = r["difference_vs_reference_per_maund"], r["quantity_maund"]
    side = "کم" if per < 0 else "زیادہ" if per > 0 else "برابر"
    gap = f"آفر اس ریٹ سے {rs(abs(per))} فی من {side}؛ {qty:g} من پر {signed_rs(r['total_difference_vs_reference'])}" \
        if per else "آفر آخری رپورٹ شدہ ریٹ کے برابر ہے۔"
    lines = [
        f"⚖️ {crop}، {place}: {OFFER_STATUS_UR[r['result_status']]}",
        f"خریدار کی آفر: {rs(r['buyer_offer_price'])} فی من",
        f"منڈی کا آخری رپورٹ شدہ ریٹ: {rs(r['reference_price'])} (AMIS، {r['reference_price_as_of']})",
        f"حالیہ حوالہ حد: {rs(r['reference_range_low'])} سے {rs(r['reference_range_high'])} "
        f"({r['window_days']} میں سے {r['reference_days']} دن رپورٹ)",
        gap,
    ]
    reason = limited_reason_ur(r)
    if reason:
        lines.append(f"⚠️ {reason} {NOT_A_RANGE}")
    c = r.get("estimated_commission")
    if c:
        lines.append(f"آپ کے بتائے ہوئے کمیشن ({c['pct']:g}%) پر تقریباً {rs(c['per_maund'])} فی من (آپ کا اپنا اندازہ)")
    lines.append(OFFER_CAVEAT)
    return "\n".join(lines)


def offer_compare_text(crop_option: str, r: Mapping) -> str:
    """Every mandi after estimated transport (the farmer's own first), against the buyer's offer."""
    crop = CROP_UR.get(crop_option, crop_option)
    lines = [f"{crop}: آفر {rs(r['buyer_offer_price'])} کے مقابلے میں منڈیاں (کرایہ نکال کر)"]
    for a in r["alternative_mandis"]:
        name, v = MANDI_UR.get(a["mandi"], a["mandi"]), alternative_verdict(a)
        if a.get("is_own_mandi"):
            name += " (آپ کی منڈی)"
        if v == "noData":
            lines.append(f"• {name}: {ALT_VERDICT_UR[v]}")
            continue
        old = f" (پرانا ریٹ، {a['prices_as_of']})" if a.get("is_stale") else ""
        lines.append(f"• {name}: {ALT_VERDICT_UR[v]}۔ {rs(a['reference_price'])} − کرایہ {rs(a['transport_cost'])} = "
                     f"{rs(a['net_after_transport'])}؛ {r['quantity_maund']:g} من پر "
                     f"{signed_rs(a['difference_vs_offer_total'])}{old}")
    lines.append(VERIFY_UR)
    return "\n".join(lines)
