"""Understand a farmer's WhatsApp or SMS message (task A8): crop, mandi, quantity, or a command.

Plain rules, no LLM: the farmer's own words decide, and nothing is guessed. Urdu, Roman Urdu and English,
with Urdu or Western digits. "گندم بہاولپور 100 من" -> Wheat at BahawalPur, 100 maund.

TODO(native speaker): check the alias lists against how farmers in these districts actually write.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Normalise Arabic letter forms to their Urdu forms, and Urdu/Arabic digits to 0-9.
_CHAR_MAP = str.maketrans({
    "ي": "ی", "ى": "ی", "ك": "ک", "ه": "ہ", "ۀ": "ہ", "ة": "ہ",
    **{d: str(i) for i, d in enumerate("۰۱۲۳۴۵۶۷۸۹")},
    **{d: str(i) for i, d in enumerate("٠١٢٣٤٥٦٧٨٩")},
})
_PUNCT = re.compile(r"[؟،۔?!.,;:()\[\]\"'“”‘’\-_/]+")

CROPS = {
    "Wheat": ["گندم", "کنک", "gandum", "gandam", "kanak", "wheat"],
    "Cotton": ["کپاس", "پھٹی", "نرما", "kapas", "phutti", "phuti", "narma", "cotton"],
}
RICE_WORDS = ["چاول", "دھان", "منجی", "chawal", "chaawal", "chawel", "dhaan", "munji", "rice", "paddy"]
SUPER_BASMATI_WORDS = ["سپر", "باسمتی", "super", "basmati"]
IRRI_WORDS = ["اری", "ایری", "irri", "iri"]

MANDIS = {
    "BahawalPur": ["بہاولپور", "بہاول پور", "bahawalpur", "bahawal pur", "bwp"],
    "Vehari": ["وہاڑی", "ویہاڑی", "vehari", "wehari", "vihari"],
    "RahimYarKhan": ["رحیم یار خان", "رحیم یارخان", "rahim yar khan", "rahimyarkhan", "rahim yaar khan", "ryk"],
}

COMMANDS = {
    "why": ["کیوں", "وجہ", "kyun", "kyon", "kyu", "why", "1"],
    "compare": ["منڈیاں", "منڈی", "موازنہ", "mandiyan", "mandian", "compare", "2"],
    "stop": ["بند", "روکو", "stop", "band", "3"],
    "wait": ["رکھیں", "رکھنا", "رکنا", "انتظار", "wait", "hold", "rakhna", "rakho", "intezaar"],
    "start": ["شروع", "start", "shuru"],
    "help": ["مدد", "help", "hi", "hello", "salam", "سلام", "السلام علیکم", "aoa"],
}

_QTY = re.compile(r"(\d+(?:\.\d+)?)\s*(من|منڈ|maund|maunds|mann|mun|man|کلو|kg|kgs)?")
KG_PER_MAUND = 40


@dataclass
class Parsed:
    kind: str                     # query | why | compare | wait | stop | start | help | unknown
    crop_option: str | None = None
    mandi: str | None = None
    quantity_maund: float | None = None
    missing: list[str] = field(default_factory=list)   # which of crop / variety / mandi we still need


def normalise(text: str) -> str:
    t = text.translate(_CHAR_MAP).lower()
    t = _PUNCT.sub(" ", t)
    return " ".join(t.split())


def _has(text: str, words: list[str]) -> bool:
    padded = f" {text} "
    return any(f" {w} " in padded or (len(w) > 3 and w in text) for w in words)


def _crop(text: str) -> tuple[str | None, list[str]]:
    for option, words in CROPS.items():
        if _has(text, words):
            return option, []
    is_rice = _has(text, RICE_WORDS)
    if _has(text, SUPER_BASMATI_WORDS):
        return "SuperBasmati", []
    if _has(text, IRRI_WORDS):
        return "IRRI", []
    if is_rice:
        return None, ["variety"]   # rice, but which: Super Basmati or IRRI? We ask; we never guess.
    return None, ["crop"]


def _mandi(text: str) -> str | None:
    # Longest alias first, so "rahim yar khan" wins over any shorter overlap.
    for mandi, words in sorted(MANDIS.items(), key=lambda kv: -max(len(w) for w in kv[1])):
        if _has(text, words):
            return mandi
    return None


def _quantity(text: str) -> float | None:
    for number, unit in _QTY.findall(text):
        value = float(number)
        if value <= 0:
            continue
        return value / KG_PER_MAUND if unit in ("کلو", "kg", "kgs") else value
    return None


def parse(text: str) -> Parsed:
    t = normalise(text)
    if not t:
        return Parsed("help")
    # A bare command ("کیوں", "2", a button title) only counts when it is the whole message.
    for kind, words in COMMANDS.items():
        if t in words:
            return Parsed(kind)

    crop, missing = _crop(t)
    mandi = _mandi(t)
    if mandi is None:
        missing.append("mandi")
    if crop is None and mandi is None and "variety" not in missing:
        return Parsed("unknown")
    return Parsed("query", crop_option=crop, mandi=mandi, quantity_maund=_quantity(t), missing=missing)
