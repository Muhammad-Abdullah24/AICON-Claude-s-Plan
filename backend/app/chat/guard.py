"""The number guard (task A9): the LLM may not show a farmer any number we did not give it.

Every number in the model's answer must appear in the context or in the farmer's question. Otherwise the
answer is thrown away and the template reply is sent. Numbers written out in words cannot be checked, so the
prompt tells the model to use digits.
"""

from __future__ import annotations

import re

_DIGITS = str.maketrans({**{d: str(i) for i, d in enumerate("۰۱۲۳۴۵۶۷۸۹")},
                         **{d: str(i) for i, d in enumerate("٠١٢٣٤٥٦٧٨٩")}, "٫": ".", "٬": ","})
_NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def numbers(text: str) -> set[str]:
    """Numbers in text, in one canonical form: '3,820' -> '3820', '6.0' -> '6', '09' -> '9'."""
    out = set()
    for raw in _NUMBER.findall(text.translate(_DIGITS)):
        value = raw.replace(",", "")
        if "." in value:
            value = value.rstrip("0").rstrip(".")
        out.add(value.lstrip("0") or "0")
    return out


def has_devanagari(text: str) -> bool:
    """Hindi script slipped into an Urdu answer (seen in a live test: "ممکنہ طور पर")."""
    return any("ऀ" <= ch <= "ॿ" for ch in text)


def unexpected_numbers(answer: str, *allowed_texts: str) -> set[str]:
    allowed: set[str] = set()
    for t in allowed_texts:
        allowed |= numbers(t)
    return numbers(answer) - allowed
