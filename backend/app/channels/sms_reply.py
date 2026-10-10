"""SMS replies in short Roman Urdu (task A11), for basic phones.

Plain GSM-7 characters only, so one SMS part holds 160 characters (Urdu script would need Unicode SMS: 70).
Each reply aims at one or two parts (MAX_CHARS). Like reply.py, templates only arrange numbers the service layer
gave; they never compute one. Stale, frozen and synthetic warnings are never dropped to save space: when a reply
is too long, the optional parts go first and the reply says where the rest is.

TODO(native speaker): check the Roman Urdu spellings with farmers in these districts.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from backend.app.channels.conversation import RICE, Reply

MAX_CHARS = 306          # two GSM-7 parts (153 characters each once split)
SINGLE_PART = 160

CROP_RU = {"Wheat": "Gandum", "Cotton": "Kapas", "IRRI": "Chawal IRRI", "SuperBasmati": "Chawal Super Basmati",
           RICE: "Chawal"}
MANDI_RU = {"BahawalPur": "Bahawalpur", "Vehari": "Vehari", "RahimYarKhan": "Rahim Yar Khan"}
SIGNAL_RU = {"SELL": "bech dein", "WAIT": "ruk jayen"}
CONFIDENCE_RU = {"HIGH": "zyada", "MEDIUM": "darmiyana", "LOW": "kam"}
CHOICE_RU = {"offer": "Offer check", "advice": "Rate/mashwara", "compare": "Mandiyan", "why": "Kyun/Data",
             "alerts_on": "Alert on",
             "alerts_off": "Alert band", "menu": "Menu", "confirm": "Theek hai", "correct": "Durust karein"}

BRAND = "FarmSight"
MENU_TAIL = "Ya likhein: gandum bahawalpur 100 man offer 3514"
MENU_NOTE = {"expired": "Pichli baat ka waqt khatam.", "no_session": "Yeh number kis sawal ka hai, maloom nahi.",
             "voice_unclear": "Awaz saaf samajh nahi aayi."}
INVALID = "Ghalat number."
ASK = {"ask_crop": "Fasal?", "ask_variety": "Kon se chawal?", "ask_mandi": "Mandi?",
       "ask_quantity": "Kitne man? Sirf number likhein, jaise 100.",
       "ask_offer": "Khareedar ne fi man kitna diya? Sirf raqam likhein, jaise 3514."}
SORRY = "Samajh nahi aya."
NOT_READY = "Service abhi tayyar nahi. Thori der baad koshish karein."
NOT_REGISTERED = "Yeh number FarmSight par register nahi. Alert ke liye app mein profile banayein."
STARTED = "Alerts chalu."
STOPPED = "Alerts band. Dobara chalu: 'shuru' likhein."
NO_DATA = "{mandi} mein {crop} ka rate nahi. Doosri mandi chunein."
GUESS = "Andaza hai, guarantee nahi."
MORE_IN_APP = "Mukammal tafseel WhatsApp/app par."
ALERT_STOP = "Band karne ke liye 'band' likhein."

# GSM 03.38 basic character set: anything else forces a Unicode SMS (70 characters a part).
GSM7 = set("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿"
           "abcdefghijklmnopqrstuvwxyzäöñüà")


def is_gsm7(text: str) -> bool:
    return set(text) <= GSM7


def parts(text: str) -> int:
    """How many SMS parts a text takes."""
    single, multi = (160, 153) if is_gsm7(text) else (70, 67)
    return 1 if len(text) <= single else math.ceil(len(text) / multi)


def rs(x: float) -> str:
    return f"Rs{round(x)}"


def signed_rs(x: float) -> str:
    return f"+{rs(x)}" if x >= 0 else f"-{rs(-x)}"


def name(code: str | None) -> str:
    return CHOICE_RU.get(code or "") or CROP_RU.get(code or "") or MANDI_RU.get(code or "") or (code or "")


def choices_line(choices) -> str:
    return " ".join(f"{n} {name(code)}" for n, code in choices)


def fit(required: Sequence[str], optional: Sequence[str] = (), choices=(), more: str = MORE_IN_APP,
        limit: int = MAX_CHARS) -> str:
    """Required parts, as many optional parts as fit (in order), then the numbered choices. If an optional part
    had to go, `more` says where the rest is. Required parts come first, so warnings in them always survive."""
    footer = choices_line(choices)

    def join(*groups) -> str:
        return " ".join(p for g in groups for p in g if p)

    kept = list(optional)
    while kept and len(join(required, kept, [footer])) > limit:
        kept.pop()
    note = [more] if len(kept) < len(optional) else []
    if note and len(join(required, kept, note, [footer])) > limit:
        note = []   # the "rest is in the app" note never pushes out a required part
    text = join(required, kept, note, [footer])
    if len(text) > limit:
        # Only if the required parts alone are too long. Keep whole parts, in order, never a cut sentence: a cut
        # can reverse a meaning ("shamil nahi" -> "shamil"). Warnings come first, so they are the last to go.
        keep, budget = [], limit - len(footer) - len(more) - 2
        for part in required:
            if len(join(keep, [part])) > budget:
                break
            keep.append(part)
        text = join(keep, [more] if len(keep) < len(required) else [], [footer])
    return text


def warnings(a: Mapping) -> list[str]:
    out = []
    if a.get("price_unchanged_since"):
        out.append(f"DHYAN: AMIS rate {a['price_unchanged_since']} se nahi badla.")
    elif a.get("is_stale"):
        out.append(f"DHYAN: purana rate ({a['prices_as_of']}).")
    if a.get("is_synthetic"):
        out.append("MASNOI DATA, asal rate nahi.")
    return out


def _head(a: Mapping) -> str:
    return f"{BRAND} {name(a['crop_option'])} {name(a['mandi'])}"


def advice_sms(a: Mapping, quantity_assumed: bool, choices=()) -> str:
    required = [
        f"{_head(a)}: {SIGNAL_RU[a['signal']]}.", *warnings(a),
        f"Aaj {rs(a['current_price'])}/man (AMIS {a['prices_as_of']}).",
        f"4 hafte baad {rs(a['predicted_price'])} ({rs(a['range']['low'])}-{rs(a['range']['high'])}). {GUESS}",
    ]
    qty = a["quantity_maund"]
    optional = [
        f"{qty:g} man{' (maan kar)' if quantity_assumed else ''} rukne ka farq {signed_rs(a['rupee_impact'])}"
        f" sood ke baad.",
        f"Aitmaad {CONFIDENCE_RU.get(a['confidence'], a['confidence'])}.",
    ]
    return fit(required, optional, choices)


def why_sms(a: Mapping, reasons: Sequence[Mapping], choices=()) -> str:
    # The reasons exist in Urdu and English only (ml/explain); English keeps the SMS in plain characters.
    lines = [f"- {r.get('text_en') or ''}".rstrip() for r in reasons[:3] if r.get("text_en")]
    return fit([f"{_head(a)} wajah:", *warnings(a)], lines or ["Abhi wajah maujood nahi."], choices)


def compare_sms(crop_option: str, rows: Sequence[Mapping], choices=()) -> str:
    items = []
    for r in rows:
        if not r.get("has_data", True):
            items.append(f"{name(r['mandi'])} rate nahi;")
            continue
        gain = r.get("gain_vs_preferred")
        old = " (purana)" if r.get("is_stale") else ""
        items.append(f"{name(r['mandi'])} {rs(r['net_price'])}{f' {signed_rs(gain)}' if gain else ''}{old};")
    return fit([f"{BRAND} {name(crop_option)} rate kiraya ke baad/man:"], [*items, "Kiraya andaza."], choices)


def alert_sms(event: Mapping, a: Mapping) -> str:
    """The SMS form of a price alert (alerts.py), from the same event and advice as the WhatsApp alert."""
    if event["type"] == "SELL_SIGNAL":
        why = "mashwara badal gaya"
    else:
        moved = "barha" if event["direction"] == "UP" else "gira"
        why = f"rate 4 hafte mein {abs(event['change_4w_pct']):.0f}% {moved}, aam se zyada"
    return fit([f"{BRAND} alert: {name(a['crop_option'])} {name(a['mandi'])}: {why}. {SIGNAL_RU[a['signal']]}.",
                *warnings(a), f"Aaj {rs(a['current_price'])}/man ({a['prices_as_of']}). {GUESS}", ALERT_STOP])


def render(r: Reply) -> str:
    """A conversation reply (conversation.py) as one SMS text."""
    k, d, ch = r.kind, r.data, r.choices
    invalid = [INVALID] if d.get("invalid") else []
    if k in ("menu", "not_understood"):
        note = [MENU_NOTE[d["note"]]] if d.get("note") else []
        lead = [SORRY] if k == "not_understood" else []
        return " ".join([*lead, *note, *invalid, f"{BRAND}: {choices_line(ch)}.", MENU_TAIL])
    if k in ASK:
        return fit([*invalid, ASK[k]], (), ch)
    if k == "advice":
        return advice_sms(d["advice"], d["quantity_assumed"], ch)
    if k == "why":
        return why_sms(d["advice"], d["reasons"], ch)
    if k == "compare":
        return compare_sms(d["crop_option"], d["rows"], ch)
    if k == "post_menu":
        return fit([INVALID], (), ch)
    if k == "alerts":
        return fit([STARTED if d["enabled"] else STOPPED], (), ch)
    if k == "not_registered":
        return fit([NOT_REGISTERED], (), ch)
    if k == "no_data":
        return fit([NO_DATA.format(mandi=name(d["mandi"]), crop=name(d["crop_option"]))], (), ch)
    if k == "offer":
        return offer_sms(d["crop_option"], d["mandi"], d["result"], ch)
    if k == "offer_compare":
        return offer_compare_sms(d["crop_option"], d["result"], ch)
    if k == "not_ready":
        return NOT_READY
    if k == "voice_confirm":   # SMS has no voice notes; kept so every reply kind has an SMS form
        qty = f"{d['quantity_maund']:g} man" if d.get("quantity_maund") else "?"
        heard = f"Suna: {name(d.get('crop_option')) or '?'}, {name(d.get('mandi')) or '?'}, {qty}. Theek hai?"
        return fit([*invalid, heard], (), ch)
    # "chat": SMS has no AI chat (it would answer in Urdu script and cost a model call per text)
    return fit([SORRY], (), ch)


# ---------------------------------------------------------------- buyer offer check

# Short names for the offer SMS, the way farmers text them ("Gandum BWP"), so a whole check fits in two parts.
SHORT_RU = {"Wheat": "Gandum", "Cotton": "Kapas", "IRRI": "IRRI", "SuperBasmati": "Basmati",
            "BahawalPur": "BWP", "Vehari": "Vehari", "RahimYarKhan": "RYK"}

OFFER_STATUS_RU = {
    "BELOW_REFERENCE_RANGE": "Reference range se kam",
    "WITHIN_REFERENCE_RANGE": "Reference range ke andar",
    "ABOVE_REFERENCE_RANGE": "Reference range se zyada",
    "REFERENCE_DATA_LIMITED": "Reference data mehdood",
}
LIMITED_RU = {
    "LIMITED_SAME_PRICE": "AMIS: sab {days} din aik hi rate, pakki range nahi.",
    "LIMITED_STALE": "DHYAN: purana rate ({date}), pakki range nahi.",
    "LIMITED_FROZEN": "DHYAN: rate {date} se nahi badla, pakki range nahi.",
    "LIMITED_FEW_DAYS": "Sirf {days}/{window} din rate, pakki range nahi.",
}
OFFER_CAVEAT_RU = "Waada nahi; grade/sharait shamil nahi."
ALT_RU = {"better": "behtar (andaza)", "notBetter": "behtar nahi",
          "higherNotBetter": "rate zyada, kiraye baad behtar nahi", "unknown": "data kamzor", "noData": "rate nahi"}


def offer_sms(crop_option: str, mandi: str, r: Mapping, choices=()) -> str:
    per, qty = r["difference_vs_reference_per_maund"], r["quantity_maund"]
    crop, place = SHORT_RU.get(crop_option, crop_option), SHORT_RU.get(mandi, mandi)
    required = [f"{BRAND} {crop} {place}: {OFFER_STATUS_RU[r['result_status']]}."]
    if r["reference_strength"] != "STRONG":
        when = r.get("price_unchanged_since") or r["reference_price_as_of"]
        required.append(LIMITED_RU[r["reference_strength"]].format(days=r["reference_days"], window=r["window_days"],
                                                                 date=when))
    required += [
        f"Offer {rs(r['buyer_offer_price'])}, reference {rs(r['reference_price'])}/man "
        f"(AMIS {r['reference_price_as_of']}, {r['reference_days']}/{r['window_days']} din).",
        OFFER_CAVEAT_RU,
        f"Farq {signed_rs(per)}/man, {qty:g} man par {signed_rs(r['total_difference_vs_reference'])}.",
    ]
    optional = [f"Range {rs(r['reference_range_low'])}-{rs(r['reference_range_high'])}."]
    c = r.get("estimated_commission")
    if c:
        optional.append(f"Aap ka commission {c['pct']:g}%: ~{rs(c['per_maund'])}/man (aap ka andaza).")
    return fit(required, optional, choices)


def offer_compare_sms(crop_option: str, r: Mapping, choices=()) -> str:
    from backend.app.channels.reply import alternative_verdict  # noqa: PLC0415 (one mapping for both channels)
    items = []
    for a in r["alternative_mandis"]:
        v = alternative_verdict(a)
        if v == "noData":
            items.append(f"{SHORT_RU.get(a['mandi'], a['mandi'])} {ALT_RU[v]};")
            continue
        old = " (purana)" if a.get("is_stale") else ""
        items.append(f"{SHORT_RU.get(a['mandi'], a['mandi'])} net {rs(a['net_after_transport'])}, "
                     f"{signed_rs(a['difference_vs_offer_total'])}{old}, {ALT_RU[v]};")
    crop = SHORT_RU.get(crop_option, crop_option)
    head = f"{BRAND} {crop} offer {rs(r['buyer_offer_price'])} vs mandiyan (kiraya andaza):"
    return fit([head], [*items, "Jane se pehle khareedar/sharait tasdeeq karein."], choices)
