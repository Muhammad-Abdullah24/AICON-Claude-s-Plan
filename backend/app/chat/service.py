"""Answer a farmer's free question from their own forecast (task A9, blueprint UC-09).

Gemini only rephrases the advice in the farmer's words. If Gemini is unavailable, over its rate limit, or
puts a number in its answer that the advice did not contain, the farmer gets the template reply instead.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from backend.app.channels import reply
from backend.app.channels.parse import parse
from backend.app.channels.provider import AdviceProvider, NotReady
from backend.app.chat import guard
from backend.app.chat.llm import LLM, LLMUnavailable, RateLimiter
from backend.app.chat.prompt import SYSTEM_PROMPT, build_context, user_message

log = logging.getLogger("farmsight.chat")

# Protects the Gemini free-tier quota across all farmers. Over the limit, the template answers.
LLM_LIMITER = RateLimiter(int(os.environ.get("FS_LLM_RATE_PER_MIN", "10")))


@dataclass
class ChatAnswer:
    answer: str
    used_fallback: bool
    fallback_reason: str | None = None
    crop_option: str | None = None
    mandi: str | None = None
    data_source: str = "none"
    is_synthetic: bool = False


def _template(a: dict, reason: str, crop: str, mandi: str) -> ChatAnswer:
    return ChatAnswer(reply.advice_text(a), True, reason, crop, mandi,
                      a.get("data_source", "amis"), bool(a.get("is_synthetic")))


def answer(question: str, crop_option: str | None, mandi: str | None, quantity_maund: float | None,
           provider: AdviceProvider, llm: LLM, limiter: RateLimiter = LLM_LIMITER, phone: str = "") -> ChatAnswer:
    parsed = parse(question)
    crop = crop_option or parsed.crop_option
    mandi = mandi or parsed.mandi
    qty = quantity_maund or parsed.quantity_maund or reply.DEFAULT_QUANTITY_MAUND
    if not crop:
        need = "variety" if "variety" in parsed.missing else "crop"
        return ChatAnswer(reply.ASK[need], True, "need_crop_and_mandi", crop, mandi)
    if not mandi:
        return ChatAnswer(reply.ASK["mandi"], True, "need_crop_and_mandi", crop, mandi)

    try:
        a = provider.advice(crop, mandi, qty, phone)
    except LookupError:
        text = reply.NO_DATA.format(mandi=reply.MANDI_UR.get(mandi, mandi), crop=reply.CROP_UR.get(crop, crop))
        return ChatAnswer(text, True, "no_data", crop, mandi)
    except NotReady:
        return ChatAnswer(reply.NOT_READY, True, "service_not_ready", crop, mandi)
    try:
        reasons = provider.explain(crop, mandi, phone)
    except (LookupError, NotReady):
        reasons = []

    if not limiter.allow("gemini"):
        return _template(a, "rate_limited", crop, mandi)
    context = build_context(a, reasons)
    try:
        text = llm.generate(SYSTEM_PROMPT, user_message(context, question))
    except LLMUnavailable as e:
        log.warning("chat: LLM unavailable (%s); template used", e)
        return _template(a, "llm_unavailable", crop, mandi)

    bad = guard.unexpected_numbers(text, context, question)
    if bad:
        log.warning("chat: answer had numbers not in the advice (%s); template used", sorted(bad))
        return _template(a, "unverified_numbers", crop, mandi)
    if a.get("is_synthetic") and reply.SYNTHETIC not in text:
        text = f"{text}\n{reply.SYNTHETIC}"
    return ChatAnswer(text, False, None, crop, mandi, a.get("data_source", "amis"), bool(a.get("is_synthetic")))
