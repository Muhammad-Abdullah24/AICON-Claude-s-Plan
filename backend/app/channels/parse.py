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
    "start": ["شروع", "start", "shuru"],
    "offer": ["آفر", "افر", "پیشکش", "offer", "aafar", "afar", "peshkash"],
    "help": ["مدد", "help", "hi", "hello", "salam", "سلام", "السلام علیکم", "aoa"],
}

_QTY = re.compile(r"(\d+(?:\.\d+)?)\s*(من|منڈ|maund|maunds|mann|mun|man|کلو|kg|kgs)?")
KG_PER_MAUND = 40


@dataclass
class Parsed:
    kind: str                     # query | why | compare | stop | start | offer | help | unknown
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


# ---------------------------------------------------------------- buyer offers (task A11, offer check)

# A price only counts as the buyer's offer when one of these words comes right before it ("آفر 3514",
# "offer Rs 3514"). Anything else is never read as an offer: we ask instead.
OFFER_WORDS = ["آفر", "افر", "پیشکش", "offer", "aafar", "afar", "aufer", "peshkash", "pesh kash"]
_CURRENCY = {"rs", "روپے", "روپیہ", "روپئے", "rupay", "rupees", "rupee"}
_PER = {"فی", "fi", "per", "man", "من", "maund", "mann", "mun", "40kg"}
_AMOUNT = re.compile(r"^\d+(?:\.\d+)?$")


@dataclass
class OfferClause:
    mentioned: bool            # an offer word appears
    offer: float | None        # the price after it, if exactly one clear number follows
    rest: str                  # the message without the offer clause (crop, mandi, quantity)


def extract_offer(text: str) -> OfferClause:
    words = normalise(text).split()
    starts = [i for i, w in enumerate(words) if w in OFFER_WORDS]
    if not starts:
        return OfferClause(False, None, text)
    found, drop = [], set()
    for i in starts:
        j = i + 1
        drop.add(i)
        while j < len(words) and words[j] in _CURRENCY:
            drop.add(j)
            j += 1
        if j < len(words) and _AMOUNT.match(words[j]):
            found.append(float(words[j]))
            drop.add(j)
            j += 1
            while j < len(words) and (words[j] in _PER or words[j] in _CURRENCY):   # "روپے فی من" after it
                drop.add(j)
                j += 1
    rest = " ".join(w for k, w in enumerate(words) if k not in drop)
    offer = found[0] if len(set(found)) == 1 and found[0] > 0 else None   # two different prices: ask
    return OfferClause(True, offer, rest)


def amount(text: str) -> float | None:
    """One price on its own ("3514", "Rs 3514", "3514 روپے فی من"), or None."""
    words = [w for w in normalise(text).split() if w not in _CURRENCY and w not in _PER]
    if len(words) == 1 and _AMOUNT.match(words[0]):
        return float(words[0])
    return None
