"""POST /api/chat (task A9). Mount with app.include_router(chat.router.router): hand-off H-C13.

The response shapes live here until Owner C moves them into backend/app/schemas.py (blueprint section 12).
"""

from __future__ import annotations

import os
from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.app.channels.provider import AdviceProvider, get_provider
from backend.app.chat.llm import LLM, RateLimiter, get_llm
from backend.app.chat.service import answer

router = APIRouter(prefix="/api", tags=["chat"])

CropOption = Literal["Wheat", "Cotton", "IRRI", "SuperBasmati"]
Mandi = Literal["BahawalPur", "Vehari", "RahimYarKhan"]

# Per caller, so one person cannot use up everyone's Gemini quota.
CLIENT_LIMITER = RateLimiter(int(os.environ.get("FS_CHAT_RATE_PER_MIN", "20")))


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    crop_option: CropOption | None = None
    mandi: Mandi | None = None
    quantity_maund: float | None = Field(None, gt=0, le=1_000_000)


class ChatResponse(BaseModel):
    answer: str
    used_fallback: bool
    fallback_reason: Literal["need_crop_and_mandi", "no_data", "service_not_ready", "rate_limited",
                             "llm_unavailable", "unverified_numbers"] | None
    crop_option: str | None
    mandi: str | None
    data_source: str
    is_synthetic: bool


def get_client_limiter() -> RateLimiter:
    return CLIENT_LIMITER


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    request: Request,
    provider: AdviceProvider = Depends(get_provider),  # noqa: B008 (FastAPI idiom)
    llm: LLM = Depends(get_llm),  # noqa: B008
    limiter: RateLimiter = Depends(get_client_limiter),  # noqa: B008
) -> ChatResponse:
    caller = request.client.host if request.client else "unknown"
    if not limiter.allow(caller):
        raise HTTPException(429, "Too many questions. Please wait a minute.")
    result = answer(body.question, body.crop_option, body.mandi, body.quantity_maund, provider, llm)
    return ChatResponse(**asdict(result))
