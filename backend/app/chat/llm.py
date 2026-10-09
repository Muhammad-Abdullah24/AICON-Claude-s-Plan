"""Gemini client (task A9), standard library only. Key: FS_LLM_API_KEY (never ANTHROPIC_API_KEY).

Only the farmer's question and the forecast context are sent: no phone number, name or location pin.
The Gemini free tier may use prompts to improve Google's models (blueprint section 10), so demo data only.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Protocol

from backend.app.chat.prompt import MAX_OUTPUT_TOKENS, MODEL_DEFAULT, TEMPERATURE

API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class LLMUnavailable(Exception):
    """No key, a network or quota error, a timeout, or an empty or blocked answer."""


class LLM(Protocol):
    def generate(self, system: str, user: str) -> str: ...


@dataclass(frozen=True)
class LLMSettings:
    api_key: str
    model: str = MODEL_DEFAULT
    timeout_s: float = 12.0


def get_llm_settings() -> LLMSettings:
    return LLMSettings(api_key=os.environ.get("FS_LLM_API_KEY", ""),
                       model=os.environ.get("FS_LLM_MODEL", MODEL_DEFAULT))


class GeminiClient:
    def __init__(self, settings: LLMSettings):
        self.s = settings

    def request_body(self, system: str, user: str) -> dict:
        return {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": TEMPERATURE, "maxOutputTokens": MAX_OUTPUT_TOKENS},
        }

    def generate(self, system: str, user: str) -> str:
        if not self.s.api_key:
            raise LLMUnavailable("FS_LLM_API_KEY is not set")
        req = urllib.request.Request(
            f"{API_BASE}/models/{self.s.model}:generateContent",
            data=json.dumps(self.request_body(system, user)).encode(),
            method="POST",
            headers={"x-goog-api-key": self.s.api_key, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.s.timeout_s) as resp:
                data = json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            raise LLMUnavailable(type(e).__name__) from e
        candidates = data.get("candidates") or []
        parts = (candidates[0].get("content") or {}).get("parts", []) if candidates else []
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            raise LLMUnavailable("empty or blocked answer")
        return text


def get_llm() -> LLM:
    return GeminiClient(get_llm_settings())


class RateLimiter:
    """At most `per_minute` calls per key in any 60-second window. In memory: one server process (MVP)."""

    def __init__(self, per_minute: int, clock=time.monotonic):
        self.per_minute, self.clock = per_minute, clock
        self.calls: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now, q = self.clock(), self.calls[key]
        while q and now - q[0] >= 60:
            q.popleft()
        if len(q) >= self.per_minute:
            return False
        q.append(now)
        return True
