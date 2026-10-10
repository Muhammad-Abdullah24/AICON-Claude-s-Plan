"""Tag each news item with a topic, a crop, a price (if any) and a one-line Urdu/English summary (task H2).

Gemini does the tagging when it is available (one call for the whole batch, JSON back); otherwise keyword rules
fill the tag and crop, the title becomes the summary, and a regex pulls out a price. A price is kept only when it
actually appears in the headline text (docs/PIVOT.md: never invent a price). Standard library only, except Gemini
through backend/app/chat/llm.py.
"""

from __future__ import annotations

import json
import re

from backend.app.news import config

# "Rs 5,300", "Rs. 3500", "5,300 rupees" ... captured as a group of digits with optional commas.
_PRICE = re.compile(r"(?:rs\.?|rupees?)\s*([\d,]{3,7})|([\d,]{3,7})\s*(?:rupees?|/-)", re.IGNORECASE)
_PER_UNIT = re.compile(r"per\s*(?:40\s*-?\s*kg|maund|mann)|/\s*40\s*kg|per\s*md|فی\s*من|40\s*کلو", re.IGNORECASE)
_PER_KG = re.compile(r"per\s*kg|/\s*kg|per\s*kilo|فی\s*کلو", re.IGNORECASE)
# The raw crop at a mandi, not a product made from it. A flour/atta price is NOT the wheat mandi price (N1).
_GRAIN = re.compile(r"\b(?:wheat|gandum|cotton|phutti|kapas|rice|paddy|basmati|irri)\b"
                    r"|گندم|کپاس|پھٹی|چاول|دھان|باسمتی|اری", re.IGNORECASE)
_PRODUCT = re.compile(r"\b(?:flour|atta|maida|bread|bran)\b|آٹا|میدہ|روٹی|چوکر", re.IGNORECASE)


def extract_price(text: str) -> int | None:
    """A crop's per-40kg (per-maund) mandi price stated in the text, or None (N1).

    Kept only when the headline is about the raw crop (`wheat`/`gandum`/...) and gives a per-40kg / per-maund figure.
    A price tied to flour or atta, a per-kg or per-bag price, or a bare "Rs X" with no unit is skipped, so a
    "flour hits Rs 5,200 per 40 kg" headline no longer counts as a wheat price and raises a false conflict.
    """
    if not _GRAIN.search(text):
        return None
    for m in _PRICE.finditer(text):
        digits = (m.group(1) or m.group(2)).replace(",", "")
        if not digits.isdigit():
            continue
        value = int(digits)
        if not (config.PRICE_MIN_RS_PER_40KG <= value <= config.PRICE_MAX_RS_PER_40KG):
            continue
        near = text[max(0, m.start() - 30): m.end() + 30]
        if _PER_KG.search(near) or not _PER_UNIT.search(near):
            continue                      # must be per 40 kg / maund, never per kg or an unqualified "Rs X"
        if _PRODUCT.search(text[max(0, m.start() - 20): m.start()]):
            continue                      # flour/atta sits right before the figure: it is the price's subject
        return value
    return None


def tag_by_rules(title: str, summary: str = "") -> tuple[str, str | None]:
    """(tag, crop) from keywords. The first matching tag in config order wins; OTHER if none match."""
    text = f"{title} {summary}".lower()
    tag = next((t for t, words in config.TAG_KEYWORDS.items() if any(w in text for w in words)), "OTHER")
    crop = next((cid for word, cid in config.CROP_KEYWORDS.items() if word in text), None)
    return tag, crop


def _rules_item(item: dict) -> dict:
    tag, crop = tag_by_rules(item["title"])
    return {**item, "tag": tag, "crop": crop, "summary_ur": item["title"], "summary_en": item["title"],
            "price_rs_per_40kg": extract_price(item["title"])}


def tag_with_rules(items: list[dict]) -> list[dict]:
    return [_rules_item(i) for i in items]


# Gemini's answer is capped at a few hundred tokens (backend/app/chat/llm.py), so tag a few at a time.
LLM_BATCH = 2


SYSTEM = """You tag Pakistani farm-news headlines for a farmer app. For each headline, return one JSON object with:
- "tag": one of SUPPORT_PRICE, PROCUREMENT, CAP_OR_BAN, IMPORT, PRICE_REPORT, OTHER
- "crop": one of "wheat", "cotton", "irri", "super_basmati", or null if no single crop
- "summary_en": the headline in at most 12 plain English words
- "summary_ur": the same in simple Urdu script (never Hindi/Devanagari)
- "price_rs_per_40kg": an integer ONLY if the headline states a price per 40 kg / per maund for the crop,
  else null. Never invent or convert a number that is not written in the headline.
Return ONLY a JSON array, one object per headline, in the same order. No prose, no code fences."""


def _llm_batch(items: list[dict], llm) -> list[dict]:
    """One Gemini call for the whole batch. Raises on any problem so the caller can fall back to the rules."""
    numbered = "\n".join(f"{i + 1}. {it['title']}" for i, it in enumerate(items))
    text = llm.generate(SYSTEM, numbered).strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.index("["): text.rindex("]") + 1] if "[" in text else text
    parsed = json.loads(text)
    if not isinstance(parsed, list) or len(parsed) != len(items):
        raise ValueError("LLM returned the wrong number of tags")
    out = []
    for item, tag in zip(items, parsed, strict=True):
        # The price is always the flour-safe rules extractor's (N1), never the model's own number. Gemini reads a
        # flour/atta price ("...as flour hits Rs 5,200 per 40 kg") as the crop's and raises a false conflict;
        # extract_price keeps a price only when the headline is about the raw grain and gives it per 40 kg / maund.
        out.append({
            **item,
            "tag": _checked_tag(tag.get("tag"), item["title"]),
            "crop": tag["crop"] if tag.get("crop") in config.CROP_IDS else None,
            "summary_en": (tag.get("summary_en") or item["title"]).strip(),
            "summary_ur": (tag.get("summary_ur") or item["title"]).strip(),
            "price_rs_per_40kg": extract_price(item["title"]),
        })
    return out


# Tags that change the advice (POLICY_UNCERTAIN lowers confidence). Gemini's call on these must be backed by the
# headline's own words: it tagged "Punjab approves Rs 10bn subsidy for affordable flour" as SUPPORT_PRICE (10 Oct).
_POLICY_TAGS = ("SUPPORT_PRICE", "CAP_OR_BAN", "IMPORT", "PROCUREMENT")


def _checked_tag(llm_tag: str | None, title: str) -> str:
    """Gemini's tag, unless it claims a policy tag the headline's words don't support: then the keyword rules'."""
    if llm_tag not in config.TAGS:
        return tag_by_rules(title)[0]
    if llm_tag in _POLICY_TAGS and not any(w in title.lower() for w in config.TAG_KEYWORDS[llm_tag]):
        return tag_by_rules(title)[0]
    return llm_tag


_STOP = {"the", "and", "for", "with", "from", "into", "over", "per", "has", "have", "are", "was", "will", "its"}


def _words(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 2 and w not in _STOP}


def dedupe(items: list[dict], overlap: float = 0.5) -> list[dict]:
    """Drop a headline that shares at least `overlap` of its words with an earlier (newer) one: the same story from
    several outlets fills the banner otherwise (four 'Rs 10bn flour subsidy' items on 10 Oct)."""
    kept: list[dict] = []
    seen: list[set[str]] = []
    for item in items:
        w = _words(item["title"])
        duplicate = w and any(len(w & s) / min(len(w), len(s)) >= overlap for s in seen if s)
        seen.append(w)   # compare with every earlier headline, so a chain of rewordings of one story collapses
        if not duplicate:
            kept.append(item)
    return kept


def tag_items(items: list[dict], get_llm) -> tuple[list[dict], str]:
    """Tag every item: Gemini in small batches (to fit its token budget), keyword rules for any batch it cannot do.

    `get_llm` is a zero-argument factory (backend.app.chat.llm.get_llm). Never raises: a failing batch, a missing
    key or malformed JSON just falls back to the rules for that batch. tagged_by is "llm" if any batch used Gemini.
    """
    out: list[dict] = []
    used_llm = False
    for start in range(0, len(items), LLM_BATCH):
        batch = items[start: start + LLM_BATCH]
        try:
            out.extend(_llm_batch(batch, get_llm()))
            used_llm = True
        except Exception:  # noqa: BLE001 (any LLM/JSON issue falls back to rules for this batch)
            out.extend(tag_with_rules(batch))
    return dedupe(out), ("llm" if used_llm else "rules")
