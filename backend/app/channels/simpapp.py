"""The "SMS Gateway API" Android app (Simpapp) as our SMS gateway (task A11): the phone's SIM sends our SMS, and the
app forwards the SMS it receives to our webhook.

    POST /api/channels/sms/simpapp/webhook?token=<SIMPAPP_WEBHOOK_SECRET>

Following the vendor's REST API reference (SMS Gateway API docs):
- Send: POST to SIMPAPP_SMS_API_URL with {"phoneNumber": E.164, "message": text}. `/api_sms_send` (V1) takes the
  key in X-API-Key; `/api_v2_sms_send` (V2) as "Authorization: Bearer <key>". 200 {"success": true, "messageId",
  "status": "queued"} means queued on the phone, not delivered.
- Incoming SMS: the app POSTs {"type": "incoming_sms", "sender", "message", "timestamp" (Unix seconds)}.
  Delivery reports come as {"type": "delivery_status", ...}; we acknowledge them and do nothing.
- A webhook answer with "sms_text" makes the app reply by itself. We never include it: the reply goes out once,
  through SimpappSmsProvider, so it is sent and recorded like every other SMS.

The vendor documents no webhook signature and no message id, so:
- the webhook URL carries a secret token (SIMPAPP_WEBHOOK_SECRET, 20+ characters), checked in constant time;
- an event's de-duplication key is a hash of (sender, timestamp, text), stored before we answer.

Environment (deployment only, never committed):
    SMS_PROVIDER=simpapp
    SIMPAPP_SMS_API_URL      https://europe-west1-sms-gateway-api-simpapp.cloudfunctions.net/api_sms_send
    SIMPAPP_SMS_API_KEY      from the app: API Gateway -> Generate API Key
    SIMPAPP_WEBHOOK_SECRET   the token in the webhook URL typed into the app

Logs never hold the key, the token, a message's text or a whole phone number.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app import db
from backend.app.channels import sms
from backend.app.channels.provider import AdviceProvider, get_provider

log = logging.getLogger("farmsight.simpapp")
router = APIRouter(prefix="/api/channels/sms/simpapp", tags=["channels"])

DEFAULT_API_URL = "https://europe-west1-sms-gateway-api-simpapp.cloudfunctions.net/api_sms_send"
TIMEOUT_S = 10            # one attempt; the phone only has to queue it
MIN_SECRET_LEN = 20


# ---------------------------------------------------------------- settings

@dataclass(frozen=True)
class SimpappSettings:
    api_url: str
    api_key: str
    webhook_secret: str


def get_simpapp_settings() -> SimpappSettings:
    return SimpappSettings(
        api_url=os.environ.get("SIMPAPP_SMS_API_URL", "").strip() or DEFAULT_API_URL,
        api_key=os.environ.get("SIMPAPP_SMS_API_KEY", "").strip(),
        webhook_secret=os.environ.get("SIMPAPP_WEBHOOK_SECRET", "").strip(),
    )


def token_ok(given: str | None, secret: str) -> bool:
    return bool(secret) and bool(given) and hmac.compare_digest(given.encode(), secret.encode())


_TOKEN_IN_URL = re.compile(r"([?&]token=)[^&\s\"]*")


class RedactToken(logging.Filter):
    """The token rides in the webhook URL, and access logs print URLs: blank it out of every log line."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and record.args:
            record.args = tuple(_TOKEN_IN_URL.sub(r"\1***", str(a)) if _TOKEN_IN_URL.search(str(a)) else a
                                for a in record.args)
        if isinstance(record.msg, str):
            record.msg = _TOKEN_IN_URL.sub(r"\1***", record.msg)
        return True


for _name in ("uvicorn.access", "uvicorn.error", "httpx", "httpx2"):
    logging.getLogger(_name).addFilter(RedactToken())


# ---------------------------------------------------------------- sending

Opener = Callable[..., Any]   # urllib.request.urlopen's shape


class SimpappSmsProvider:
    """Sends one SMS through the SMS Gateway API. Standard library only, one attempt, no retry."""

    name = "simpapp"

    def __init__(self, settings: SimpappSettings, opener: Opener = urllib.request.urlopen):
        if not settings.api_key:
            raise sms.SmsConfigError("Simpapp is not configured: SIMPAPP_SMS_API_KEY is not set")
        if not settings.api_url.startswith("https://"):
            raise sms.SmsConfigError("SIMPAPP_SMS_API_URL must start with https://")
        self.s = settings
        self.opener = opener

    def _auth(self) -> dict[str, str]:
        if self.s.api_url.rstrip("/").endswith("/api_v2_sms_send"):
            return {"Authorization": f"Bearer {self.s.api_key}"}   # V2
        return {"X-API-Key": self.s.api_key}                         # V1 (/api_sms_send)

    def send(self, to: str, text: str) -> sms.SendResult:
        e164 = sms.normalize_pk_phone(to)
        if e164 is None:
            log.warning("Simpapp: not sent, %s is not a Pakistani mobile number", sms.mask_phone(to))
            return sms.SendResult("FAILED")
        req = urllib.request.Request(
            self.s.api_url, method="POST",
            data=json.dumps({"phoneNumber": e164, "message": text}, ensure_ascii=False).encode("utf-8"),
            headers={**self._auth(), "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with self.opener(req, timeout=TIMEOUT_S) as resp:
                status, raw = resp.status, resp.read()
        except urllib.error.HTTPError as e:
            # 400/401/403/429 refused, 503 "device offline": nothing was sent. 500 and others: we cannot tell.
            outcome = "FAILED" if 400 <= e.code < 500 or e.code == 503 else "UNKNOWN"
            log.warning("Simpapp send to %s: HTTP %s (%s)", sms.mask_phone(e164), e.code, outcome)
            return sms.SendResult(outcome, e.code)
        except urllib.error.URLError as e:
            timed_out = isinstance(e.reason, TimeoutError)
            log.warning("Simpapp send to %s: %s", sms.mask_phone(e164), type(e.reason).__name__)
            return sms.SendResult("UNKNOWN" if timed_out else "FAILED")
        except Exception as e:  # noqa: BLE001 (a timeout mid-read and the like: it may have been queued)
            log.warning("Simpapp send to %s: %s", sms.mask_phone(e164), type(e).__name__)
            return sms.SendResult("UNKNOWN")
        try:
            data = json.loads(raw) or {}
        except ValueError:
            data = {}
        if not (200 <= status < 300 and isinstance(data, dict) and data.get("success") is True):
            log.warning("Simpapp send to %s: HTTP %s, not queued", sms.mask_phone(e164), status)
            return sms.SendResult("FAILED", status)
        ref = data.get("messageId")
        return sms.SendResult("ACCEPTED", status, ref if isinstance(ref, str) else None)


# ---------------------------------------------------------------- the webhook

class IncomingSms(BaseModel):
    """The app's incoming_sms payload. Unknown fields are ignored; these four must be right."""

    model_config = ConfigDict(extra="ignore", strict=True)

    type: Literal["incoming_sms"]
    sender: str = Field(min_length=3, max_length=32)
    message: str = Field(max_length=2000)
    timestamp: int = Field(gt=1_500_000_000, lt=4_000_000_000)   # Unix seconds


def event_key(e: IncomingSms, phone: str) -> str:
    """No message id is sent, so a retry is recognised by the same sender, second and text."""
    return "simpapp:" + hashlib.sha256(f"{phone}\n{e.timestamp}\n{e.message}".encode()).hexdigest()


def get_simpapp_outbound() -> sms.SmsProvider | None:
    """The Simpapp sender when SMS_PROVIDER=simpapp and it is configured, else None (the webhook answers 503)."""
    try:
        p = sms.get_sms_provider()
    except sms.SmsConfigError as e:
        log.warning("%s", e)
        return None
    return p if p.name == "simpapp" else None


@router.post("/webhook")
async def receive(
    request: Request,
    background: BackgroundTasks,
    token: str | None = Query(None, max_length=200),
    settings: SimpappSettings = Depends(get_simpapp_settings),  # noqa: B008 (FastAPI idiom)
    provider: AdviceProvider = Depends(get_provider),  # noqa: B008
    outbound: sms.SmsProvider | None = Depends(get_simpapp_outbound),  # noqa: B008
) -> dict:
    if len(settings.webhook_secret) < MIN_SECRET_LEN:
        raise HTTPException(503, "SMS webhook is not configured")
    if not token_ok(token, settings.webhook_secret):
        raise HTTPException(401, "bad token")
    raw = await request.body()
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPException(400, "not JSON") from e
    if not isinstance(payload, dict) or not isinstance(payload.get("type"), str):
        raise HTTPException(400, "no type")
    if payload["type"] != "incoming_sms":
        return {"status": "ignored"}   # delivery_status and the like: acknowledged, no reply, no sms_text
    try:
        event = IncomingSms.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(422, "invalid incoming_sms event") from e
    phone = sms.normalize_pk_phone(event.sender)
    if phone is None:
        log.info("Simpapp: sender is not a Pakistani mobile number, no reply")
        return {"status": "ignored"}   # a short code or service message: never answer it
    if outbound is None:
        raise HTTPException(503, "SMS sending is not configured")
    key = event_key(event, phone)
    if not db.claim_sms_event(key, "simpapp"):
        return {"status": "duplicate"}
    background.add_task(sms.answer, key, phone, event.message, provider, outbound)
    return {"status": "accepted"}   # no "sms_text": the app must not send a second reply of its own
