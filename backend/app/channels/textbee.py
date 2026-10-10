"""TextBee SMS gateway (task A11): an Android phone's SIM sends our SMS and forwards the farmers' SMS to us.

    POST /api/channels/sms/textbee/webhook   TextBee's webhook; X-Signature is checked before anything is parsed

Outbound: POST {TEXTBEE_BASE_URL}/gateway/send-sms with the x-api-key header (https://textbee.dev/openapi.json).
Inbound:  TextBee POSTs a flat JSON event and signs the raw body with the subscription's signing secret:
          X-Signature = lowercase hex HMAC-SHA256 (https://textbee.dev/docs/webhooks).

Environment (.env, never committed):
    SMS_PROVIDER=textbee
    TEXTBEE_API_KEY          from the TextBee dashboard
    TEXTBEE_DEVICE_ID        the phone to send from; when set, events from any other phone are refused
    TEXTBEE_BASE_URL         default https://api.textbee.dev/api/v1
    TEXTBEE_WEBHOOK_SECRET   the webhook's signing secret, 20 characters or more

An incoming SMS gets exactly one reply, from the same conversation as WhatsApp (`whatsapp.respond`), rendered as
SMS by `sms.render`. TextBee retries a webhook until it gets a 2xx, so each event's idempotencyKey is stored
before we answer, and a key we have seen never gets a second reply. A send is never retried either: after a
timeout we cannot tell whether the phone sent it, and a second SMS is worse than none.

Logs never hold the API key, the secret, a message's text or a whole phone number. Setup: docs/TEXTBEE_SMS.md.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app import db
from backend.app.channels import sms
from backend.app.channels.provider import AdviceProvider, get_provider

log = logging.getLogger("farmsight.textbee")
router = APIRouter(prefix="/api/channels/sms/textbee", tags=["channels"])

DEFAULT_BASE_URL = "https://api.textbee.dev/api/v1"
TIMEOUT_S = 10            # one attempt; the phone only has to accept the job, not send it
MIN_SECRET_LEN = 20       # TextBee's own minimum for a signing secret
RECEIVED = "MESSAGE_RECEIVED"


# ---------------------------------------------------------------- settings

@dataclass(frozen=True)
class TextBeeSettings:
    api_key: str
    device_id: str
    base_url: str
    webhook_secret: str


def get_textbee_settings() -> TextBeeSettings:
    return TextBeeSettings(
        api_key=os.environ.get("TEXTBEE_API_KEY", "").strip(),
        device_id=os.environ.get("TEXTBEE_DEVICE_ID", "").strip(),
        base_url=(os.environ.get("TEXTBEE_BASE_URL", "").strip() or DEFAULT_BASE_URL).rstrip("/"),
        webhook_secret=os.environ.get("TEXTBEE_WEBHOOK_SECRET", "").strip(),
    )


def signature_ok(raw_body: bytes, header: str | None, secret: str) -> bool:
    """TextBee signs the raw body: X-Signature is the lowercase hex HMAC-SHA256 with the signing secret."""
    if not secret or not header:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.strip().lower())


# ---------------------------------------------------------------- sending

Opener = Callable[..., Any]   # urllib.request.urlopen's shape: (request, timeout=...) -> response


class TextBeeSmsProvider:
    """Sends one SMS through TextBee. Standard library only, one attempt, no retry."""

    name = "textbee"

    def __init__(self, settings: TextBeeSettings, opener: Opener = urllib.request.urlopen):
        if not settings.api_key:
            raise sms.SmsConfigError("TextBee is not configured: TEXTBEE_API_KEY is not set")
        if not settings.base_url.startswith("https://"):
            raise sms.SmsConfigError("TEXTBEE_BASE_URL must start with https://")
        self.s = settings
        self.opener = opener

    def send(self, to: str, text: str) -> sms.SendResult:
        e164 = sms.normalize_pk_phone(to)
        if e164 is None:
            log.warning("TextBee: not sent, %s is not a Pakistani mobile number", sms.mask_phone(to))
            return sms.SendResult("FAILED")
        body: dict[str, Any] = {"recipients": [e164], "message": text}
        if self.s.device_id:
            body["deviceId"] = self.s.device_id
        req = urllib.request.Request(
            f"{self.s.base_url}/gateway/send-sms", data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            method="POST", headers={"x-api-key": self.s.api_key, "Content-Type": "application/json",
                                    "Accept": "application/json"})
        try:
            with self.opener(req, timeout=TIMEOUT_S) as resp:
                status, raw = resp.status, resp.read()
        except urllib.error.HTTPError as e:
            # 4xx: TextBee refused it (bad key, no device, plan limit), so nothing went. 5xx: we cannot tell.
            outcome = "FAILED" if 400 <= e.code < 500 else "UNKNOWN"
            log.warning("TextBee send to %s: HTTP %s (%s)", sms.mask_phone(e164), e.code, outcome)
            return sms.SendResult(outcome, e.code)
        except urllib.error.URLError as e:
            # Refused or unresolved: the request never arrived. A timeout: it may have.
            timed_out = isinstance(e.reason, TimeoutError)
            log.warning("TextBee send to %s: %s", sms.mask_phone(e164), type(e.reason).__name__)
            return sms.SendResult("UNKNOWN" if timed_out else "FAILED")
        except Exception as e:  # noqa: BLE001 (a timeout mid-read and the like: it may have been accepted)
            log.warning("TextBee send to %s: %s", sms.mask_phone(e164), type(e).__name__)
            return sms.SendResult("UNKNOWN")
        try:
            data = (json.loads(raw) or {}).get("data") or {}
        except (ValueError, AttributeError):
            data = {}
        accepted = data.get("success") is True or (data.get("successCount") or 0) >= 1
        if not (200 <= status < 300 and accepted):
            log.warning("TextBee send to %s: HTTP %s, not accepted", sms.mask_phone(e164), status)
            return sms.SendResult("FAILED", status)
        if isinstance(data.get("warning"), dict):
            log.warning("TextBee send to %s accepted with warning %s", sms.mask_phone(e164),
                        data["warning"].get("code"))
        return sms.SendResult("ACCEPTED", status, data.get("smsBatchId"))


# ---------------------------------------------------------------- the conversation

class ReceivedSms(BaseModel):
    """A MESSAGE_RECEIVED event. Unknown fields are allowed (TextBee may add some); these must be right."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    webhookEvent: str = Field(pattern=f"^{RECEIVED}$")
    idempotencyKey: str = Field(min_length=8, max_length=200)
    deviceId: str = Field(min_length=1, max_length=100)
    sender: str = Field(min_length=3, max_length=32)
    message: str = Field(max_length=2000)
    smsId: str | None = Field(default=None, max_length=100)
    receivedAt: str | None = Field(default=None, max_length=40)


def reply_to(event: ReceivedSms, phone: str, provider: AdviceProvider, outbound: sms.SmsProvider) -> sms.SendResult:
    """One SMS reply from the shared WhatsApp/SMS conversation. `phone` is the sender in E.164."""
    return sms.answer(event.idempotencyKey, phone, event.message, provider, outbound)


def get_outbound() -> sms.SmsProvider | None:
    """The configured SMS provider, or None when SMS is off or misconfigured (the webhook then answers 503)."""
    try:
        return sms.get_sms_provider()
    except sms.SmsConfigError as e:
        log.warning("%s", e)
        return None


@router.post("/webhook")
async def receive(
    request: Request,
    background: BackgroundTasks,
    settings: TextBeeSettings = Depends(get_textbee_settings),  # noqa: B008 (FastAPI idiom)
    provider: AdviceProvider = Depends(get_provider),  # noqa: B008
    outbound: sms.SmsProvider | None = Depends(get_outbound),  # noqa: B008
) -> dict:
    raw = await request.body()
    if len(settings.webhook_secret) < MIN_SECRET_LEN:
        raise HTTPException(503, "SMS webhook is not configured")
    if not signature_ok(raw, request.headers.get("X-Signature"), settings.webhook_secret):
        raise HTTPException(401, "bad signature")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPException(400, "not JSON") from e
    if not isinstance(payload, dict) or not isinstance(payload.get("webhookEvent"), str):
        raise HTTPException(400, "no webhookEvent")
    if payload["webhookEvent"] != RECEIVED:
        return {"status": "ignored"}   # sent/delivered/failed reports: acknowledged, nothing to answer
    try:
        event = ReceivedSms.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(422, "invalid MESSAGE_RECEIVED event") from e
    if settings.device_id and not hmac.compare_digest(event.deviceId, settings.device_id):
        raise HTTPException(403, "unexpected device")
    phone = sms.normalize_pk_phone(event.sender)
    if phone is None:
        log.info("TextBee event %s: sender is not a Pakistani mobile number, no reply", event.idempotencyKey[:8])
        return {"status": "ignored"}   # a short code or service message: never answer it
    if outbound is None:
        raise HTTPException(503, "SMS sending is not configured")   # nothing claimed: TextBee will retry
    if not db.claim_sms_event(event.idempotencyKey, "textbee"):
        return {"status": "duplicate"}
    background.add_task(reply_to, event, phone, provider, outbound)
    return {"status": "accepted"}   # the reply goes out after this quick 2xx
