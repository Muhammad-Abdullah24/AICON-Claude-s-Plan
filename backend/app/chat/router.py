"""POST /api/chat (task A9). Shapes live in backend/app/schemas.py; ids are the API's lowercase ids."""

from __future__ import annotations

import os
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app import db
from backend.app.auth import optional_farmer
from backend.app.channels.provider import AdviceProvider, get_provider
from backend.app.chat.llm import LLM, RateLimiter, get_llm
from backend.app.chat.service import answer
from backend.app.ids import CROP_FROM_DATA, CROP_TO_DATA, MANDI_FROM_DATA, MANDI_TO_DATA
from backend.app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["chat"])

# Per caller, so one person cannot use up everyone's Gemini quota.
CLIENT_LIMITER = RateLimiter(int(os.environ.get("FS_CHAT_RATE_PER_MIN", "20")))


def get_client_limiter() -> RateLimiter:
    return CLIENT_LIMITER


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    request: Request,
    provider: AdviceProvider = Depends(get_provider),  # noqa: B008 (FastAPI idiom)
    llm: LLM = Depends(get_llm),  # noqa: B008
    limiter: RateLimiter = Depends(get_client_limiter),  # noqa: B008
    farmer: dict | None = Depends(optional_farmer),  # noqa: B008
) -> ChatResponse:
    caller = farmer["id"] if farmer else (request.client.host if request.client else "unknown")
    if not limiter.allow(caller):
        raise HTTPException(429, "Too many questions. Please wait a minute.")
    crop = CROP_TO_DATA.get(body.crop) if body.crop else None
    mandi = MANDI_TO_DATA.get(body.mandi) if body.mandi else None
    if farmer and not mandi:
        mandi = MANDI_TO_DATA[farmer["district"]]
    result = asdict(answer(body.question, crop, mandi, body.quantity_maund, provider, llm,
                           phone=farmer["phone"] if farmer else ""))
    if farmer:
        db.log_chat(farmer["id"], "FARMER", body.question)
        db.log_chat(farmer["id"], "ASSISTANT", result["answer"], result["used_fallback"])
    result["crop"] = CROP_FROM_DATA.get(result.pop("crop_option") or "")
    result["mandi"] = MANDI_FROM_DATA.get(result["mandi"] or "")
    return ChatResponse(**result)
