"""SMS channel (task A11): two-way SMS for basic phones, without assuming an SMS provider.

The team has not chosen an SMS vendor yet (the blueprint names "an Android phone running an open-source SMS
gateway app", not which one). So this module is the provider-neutral part only:

    SmsSender     sends one text; NullSmsSender (nothing configured: logs and returns False), FakeSmsSender (tests)
    SmsAdapter    one per vendor: checks the vendor's signature, reads its webhook payload into InboundSms,
                  returns the acknowledgement the vendor expects, and gives the vendor's SmsSender
    respond()     one inbound SMS -> the shared conversation engine -> one Roman Urdu reply (sms_reply.py)

    POST /webhooks/sms   answers 503 until an adapter is registered for FS_SMS_PROVIDER. It is not ready for any
                         vendor as it stands: adding one means writing its adapter, including the vendor's own
                         signature or token check, and registering it in ADAPTERS.

Environment (.env, never committed):
    FS_SMS_PROVIDER          the adapter name in ADAPTERS; empty = SMS off (no adapter exists yet)
    FS_SMS_REPLIES_PER_MIN   replies to one number per minute, default 5 (stops reply loops with auto-responders)

Advice comes from the same service layer and conversation engine as WhatsApp, so the answer is the same.
Phone numbers and message text are never logged.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response

from backend.app import db
from backend.app.channels import conversation as conv
from backend.app.channels import sms_reply
from backend.app.channels.provider import AdviceProvider, get_provider
from backend.app.chat.llm import RateLimiter

log = logging.getLogger("farmsight.sms")
router = APIRouter(prefix="/webhooks", tags=["channels"])
CHANNEL = "sms"


# ---------------------------------------------------------------- settings and senders

@dataclass(frozen=True)
class SmsSettings:
    provider: str = ""
    replies_per_minute: int = 5


def get_sms_settings() -> SmsSettings:
    return SmsSettings(provider=os.environ.get("FS_SMS_PROVIDER", "").strip().lower(),
                       replies_per_minute=int(os.environ.get("FS_SMS_REPLIES_PER_MIN", "5")))


class SmsSender(Protocol):
    def send(self, to: str, text: str) -> bool: ...   # False when it could not be handed to the provider


class NullSmsSender:
    """No SMS provider is configured: nothing is sent, and the caller is told so."""

    def send(self, to: str, text: str) -> bool:
        log.warning("SMS not sent: no SMS provider is configured (FS_SMS_PROVIDER)")
        return False


@dataclass
class FakeSmsSender:
    """Records what would be sent (tests). Never touches a network."""
    ok: bool = True
    sent: list[tuple[str, str]] = field(default_factory=list)

    def send(self, to: str, text: str) -> bool:
        self.sent.append((to, text))
        return self.ok


# ---------------------------------------------------------------- the vendor boundary

@dataclass(frozen=True)
class InboundSms:
    phone: str
    text: str
    message_id: str = ""   # the vendor's id, to ignore its retries; empty if it has none


class SmsAdapter(Protocol):
    """Everything vendor-specific. Write one per vendor, from that vendor's official documentation."""

    def verify(self, raw: bytes, headers: Mapping[str, str]) -> bool: ...    # the vendor's signature/token check
    def parse(self, raw: bytes, headers: Mapping[str, str]) -> list[InboundSms]: ...   # ValueError if malformed
    def acknowledge(self, queued: int) -> Response: ...                     # what the vendor expects back
    def sender(self) -> SmsSender: ...


# Registered vendor adapters, by FS_SMS_PROVIDER name. Empty on purpose: no vendor has been chosen.
ADAPTERS: dict[str, Callable[[SmsSettings], SmsAdapter]] = {}


def get_adapter(settings: SmsSettings = Depends(get_sms_settings)) -> SmsAdapter | None:  # noqa: B008
    if not settings.provider:
        return None
    factory = ADAPTERS.get(settings.provider)
    if factory is None:
        log.warning("SMS off: FS_SMS_PROVIDER names an adapter that does not exist")
        return None
    return factory(settings)


def configured(settings: SmsSettings | None = None) -> bool:
    return get_adapter(settings or get_sms_settings()) is not None


def get_sms_sender(settings: SmsSettings | None = None) -> SmsSender:
    adapter = get_adapter(settings or get_sms_settings())
    return adapter.sender() if adapter else NullSmsSender()


# ---------------------------------------------------------------- conversation

def respond(inbound: InboundSms, provider: AdviceProvider, now: datetime | None = None) -> str:
    """The Roman Urdu reply to one inbound SMS; the session is kept in SQLite like WhatsApp's."""
    r = conv.converse(CHANNEL, inbound.phone, inbound.text, provider, now or datetime.now(UTC))
    return sms_reply.render(r)


_limiters: dict[int, RateLimiter] = {}


def limiter_for(settings: SmsSettings) -> RateLimiter:
    return _limiters.setdefault(settings.replies_per_minute, RateLimiter(settings.replies_per_minute))


def handle(inbound: InboundSms, provider: AdviceProvider, sender: SmsSender, limiter: RateLimiter) -> bool:
    """Reply to one inbound SMS. Returns whether a reply was sent. Over the rate limit nothing is sent (each SMS
    costs money, and two auto-responders could otherwise text each other forever)."""
    phone = db.digits(inbound.phone)
    if not phone:
        return False
    if not limiter.allow(phone):
        log.info("SMS reply skipped: rate limit")
        return False
    db.expire_old_conversations()
    return bool(sender.send(phone, respond(inbound, provider)))


@router.post("/sms")
async def receive(
    request: Request,
    background: BackgroundTasks,
    adapter: SmsAdapter | None = Depends(get_adapter),  # noqa: B008 (FastAPI idiom)
    provider: AdviceProvider = Depends(get_provider),  # noqa: B008
    settings: SmsSettings = Depends(get_sms_settings),  # noqa: B008
) -> Response:
    if adapter is None:
        raise HTTPException(503, "SMS is not configured: no SMS provider adapter (FS_SMS_PROVIDER)")
    raw = await request.body()
    if not adapter.verify(raw, request.headers):
        raise HTTPException(403, "bad signature")
    try:
        messages = adapter.parse(raw, request.headers)
    except ValueError as e:
        raise HTTPException(400, "malformed SMS payload") from e
    queued, sender, limiter = 0, adapter.sender(), limiter_for(settings)
    for m in messages:
        if not db.digits(m.phone):
            continue
        if m.message_id and not db.first_time_seen(CHANNEL, m.message_id):
            continue
        background.add_task(handle, m, provider, sender, limiter)
        queued += 1
    return adapter.acknowledge(queued)   # replies go out after it, as separate SMS


# ---------------------------------------------------------------- alerts (backend/app/alerts.py)

def alert_sender() -> Callable[[str, str, str], bool] | None:
    """The SMS fallback for price alerts, or None when SMS is not configured (then there is no fallback)."""
    if not configured():
        return None
    sender = get_sms_sender()
    return lambda phone, text, summary: sender.send(phone, text)
