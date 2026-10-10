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
_PER_UNIT = re.compile(r"per\s*(?:40\s*-?\s*kg|maund|mann)|/\s*40\s*kg|per\s*md", re.IGNORECASE)


def extract_price(text: str) -> int | None:
    """A per-40kg (per-maund) price stated in the text, or None. Prefers a number next to 'per maund/40 kg'."""
    candidates: list[int] = []
    for m in _PRICE.finditer(text):
        digits = (m.group(1) or m.group(2)).replace(",", "")
        if not digits.isdigit():
            continue
        value = int(digits)
        if config.PRICE_MIN_RS_PER_40KG <= value <= config.PRICE_MAX_RS_PER_40KG:
            # A price right next to "per maund / 40 kg" wins over a bare "Rs X".
            near = text[max(0, m.start() - 15): m.end() + 15]
            candidates.append((2 if _PER_UNIT.search(near) else 1, value))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


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
        price = tag.get("price_rs_per_40kg")
        # Trust the model's price only if it is really in the headline (no invented numbers) and in the sane band.
        in_text = isinstance(price, int) and str(price) in item["title"].replace(",", "")
        in_band = isinstance(price, int) and config.PRICE_MIN_RS_PER_40KG <= price <= config.PRICE_MAX_RS_PER_40KG
        if not (in_text and in_band):
            price = extract_price(item["title"])
        out.append({
            **item,
            "tag": tag["tag"] if tag.get("tag") in config.TAGS else "OTHER",
            "crop": tag["crop"] if tag.get("crop") in config.CROP_IDS else None,
            "summary_en": (tag.get("summary_en") or item["title"]).strip(),
            "summary_ur": (tag.get("summary_ur") or item["title"]).strip(),
            "price_rs_per_40kg": price,
        })
    return out


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
    return out, ("llm" if used_llm else "rules")
