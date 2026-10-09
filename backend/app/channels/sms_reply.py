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
CHOICE_RU = {"advice": "Rate/mashwara", "compare": "Mandiyan", "why": "Kyun", "alerts_on": "Alert on",
             "alerts_off": "Alert band", "menu": "Menu"}

BRAND = "FarmSight"
MENU_TAIL = "Ya likhein: gandum bahawalpur 100 man"
MENU_NOTE = {"expired": "Pichli baat ka waqt khatam.", "no_session": "Yeh number kis sawal ka hai, maloom nahi."}
INVALID = "Ghalat number."
ASK = {"ask_crop": "Fasal?", "ask_variety": "Kon se chawal?", "ask_mandi": "Mandi?",
       "ask_quantity": "Kitne man? Sirf number likhein, jaise 100."}
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
    text = join(required, kept, note, [footer])
    if len(text) > limit:   # only if the required parts alone are too long: cut them, keep the choices
        head = join(required, note)[: limit - len(footer) - 2].rstrip()
        text = f"{head}. {footer}".strip() if footer else head
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
    if k == "not_ready":
        return NOT_READY
    # "chat": SMS has no AI chat (it would answer in Urdu script and cost a model call per text)
    return fit([SORRY], (), ch)
