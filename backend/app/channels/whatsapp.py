"""WhatsApp channel (task A8): Meta WhatsApp Cloud API webhook and replies.

    GET  /webhooks/whatsapp   Meta's verification handshake (hub.mode, hub.verify_token, hub.challenge)
    POST /webhooks/whatsapp   incoming messages; X-Hub-Signature-256 is checked before anything is parsed

Environment (.env, never committed):
    FS_WA_VERIFY_TOKEN     any string you also type into the Meta app's webhook settings
    FS_WA_APP_SECRET       Meta app secret, used to check X-Hub-Signature-256
    FS_WA_ACCESS_TOKEN     Cloud API access token
    FS_WA_PHONE_NUMBER_ID  the test number's phone-number id
    FS_WA_API_VERSION      Graph API version, default v23.0

Advice comes from the same service layer as the web app (interface I6, backend/app/services.py, Owner C),
so WhatsApp and the web always give the same answer. Until that module exists, replies say so honestly.
Phone numbers are never logged.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import urllib.request
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from backend.app.channels import reply
from backend.app.channels.parse import Parsed, parse
from backend.app.channels.provider import AdviceProvider, NotReady, get_provider
from backend.app.chat import service as chat_service
from backend.app.chat.llm import get_llm

log = logging.getLogger("farmsight.whatsapp")
router = APIRouter(prefix="/webhooks", tags=["channels"])


# ---------------------------------------------------------------- settings

@dataclass(frozen=True)
class WhatsAppSettings:
    verify_token: str
    app_secret: str
    access_token: str
    phone_number_id: str
    api_version: str = "v23.0"


def get_wa_settings() -> WhatsAppSettings:
    return WhatsAppSettings(
        verify_token=os.environ.get("FS_WA_VERIFY_TOKEN", ""),
        app_secret=os.environ.get("FS_WA_APP_SECRET", ""),
        access_token=os.environ.get("FS_WA_ACCESS_TOKEN", ""),
        phone_number_id=os.environ.get("FS_WA_PHONE_NUMBER_ID", ""),
        api_version=os.environ.get("FS_WA_API_VERSION", "v23.0"),
    )


def signature_ok(raw_body: bytes, header: str | None, app_secret: str) -> bool:
    """Meta signs the raw request body with the app secret: 'sha256=<hex HMAC-SHA256>'."""
    if not app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))





# ---------------------------------------------------------------- sending

class Sender(Protocol):
    def send(self, to: str, message: dict) -> bool | None: ...   # False when it could not be delivered


class GraphSender:
    """Posts to the WhatsApp Cloud API with the standard library (no extra dependency)."""

    def __init__(self, settings: WhatsAppSettings):
        self.s = settings

    def send(self, to: str, message: dict) -> bool:
        if not (self.s.access_token and self.s.phone_number_id):
            log.warning("WhatsApp reply not sent: FS_WA_ACCESS_TOKEN or FS_WA_PHONE_NUMBER_ID is not set")
            return False
        url = f"https://graph.facebook.com/{self.s.api_version}/{self.s.phone_number_id}/messages"
        body = json.dumps({"messaging_product": "whatsapp", "to": to, **message}).encode()
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Authorization": f"Bearer {self.s.access_token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        except Exception as e:  # noqa: BLE001 (a failed reply must not crash the webhook)
            log.warning("WhatsApp reply failed: %s", type(e).__name__)
            return False
        return True


def get_sender(settings: WhatsAppSettings = Depends(get_wa_settings)) -> Sender:  # noqa: B008 (FastAPI idiom)
    return GraphSender(settings)


def text_message(body: str) -> dict:
    return {"type": "text", "text": {"body": reply.clip(body, 4096)}}


def buttons_message(body: str) -> dict:
    return {"type": "interactive", "interactive": {
        "type": "button",
        "body": {"text": reply.clip(body)},
        "action": {"buttons": [{"type": "reply", "reply": {"id": i, "title": t}} for i, t in reply.BUTTONS]},
    }}


# ---------------------------------------------------------------- conversation

class Memory:
    """The last query per sender, so "کیوں؟" and "منڈیاں" know what they refer to. In memory only (MVP):
    a restart forgets, and the farmer simply sends the query again. Also remembers seen message ids,
    because Meta retries deliveries."""

    def __init__(self, size: int = 2000):
        self.size = size
        self.last: OrderedDict[str, Parsed] = OrderedDict()
        self.seen: OrderedDict[str, None] = OrderedDict()

    def remember(self, phone: str, q: Parsed) -> None:
        self.last[phone] = q
        self.last.move_to_end(phone)
        while len(self.last) > self.size:
            self.last.popitem(last=False)

    def first_time(self, message_id: str) -> bool:
        if message_id in self.seen:
            return False
        self.seen[message_id] = None
        while len(self.seen) > self.size:
            self.seen.popitem(last=False)
        return True


MEMORY = Memory()


def message_text(msg: dict) -> str | None:
    """Text of a message, including taps on our quick-reply buttons (their id is the command)."""
    kind = msg.get("type")
    if kind == "text":
        return msg.get("text", {}).get("body", "")
    if kind == "interactive":
        it = msg.get("interactive", {})
        picked = it.get("button_reply") or it.get("list_reply") or {}
        return {"why": "why", "compare": "compare", "stop": "stop"}.get(picked.get("id", ""), picked.get("title"))
    if kind == "button":
        return msg.get("button", {}).get("payload") or msg.get("button", {}).get("text")
    return None


ChatFn = Callable[[str, Parsed, str], str]   # (question, remembered query, phone) -> answer text


def default_chat(provider: AdviceProvider) -> ChatFn:
    """Free questions go to the same guarded chat as the web app (task A9)."""
    def run(question: str, q: Parsed, phone: str) -> str:
        return chat_service.answer(question, q.crop_option, q.mandi, q.quantity_maund, provider, get_llm(),
                                   phone=phone).answer
    return run


def respond(msg: dict, provider: AdviceProvider, memory: Memory = MEMORY, chat: ChatFn | None = None) -> dict:
    """The reply to one incoming message, as a Cloud API message object. Pure apart from `provider`."""
    phone = msg.get("from", "")
    if msg.get("type") in ("audio", "voice"):
        return text_message(reply.VOICE_SOON)  # task A10
    text = message_text(msg)
    if text is None:
        return text_message(reply.HELP)
    p = parse(text)
    ctx = p  # the query a "no data" reply refers to
    try:
        if p.kind == "help":
            return text_message(reply.HELP)
        if p.kind == "unknown":
            q = memory.last.get(phone)
            if chat and q:
                return buttons_message(chat(text, q, phone))
            return text_message(reply.NOT_UNDERSTOOD)
        if p.kind in ("stop", "start"):
            provider.set_alerts(phone, p.kind == "start")
            return text_message(reply.STOPPED if p.kind == "stop" else reply.STARTED)
        if p.kind == "wait":
            q = memory.last.get(phone)
            if q is None:
                return text_message(reply.NEED_QUERY_FIRST)
            ctx = q
            return buttons_message(reply.wait_text(provider.wait_plan(q.crop_option, q.mandi, q.quantity_maund, phone)))
        if p.kind == "loan":
            q = memory.last.get(phone)
            crop = (q.crop_option if q else None) or "Wheat"   # the loan planner needs only the crop (+ profile acres)
            try:
                return buttons_message(reply.loan_text(provider.loan_plan(crop, phone)))
            except LookupError:
                return text_message(reply.NEED_LAND_AREA)   # not registered, or no land area on file
        if p.kind in ("why", "compare"):
            q = memory.last.get(phone)
            if q is None:
                return text_message(reply.NEED_QUERY_FIRST)
            ctx = q
            if p.kind == "why":
                a = provider.advice(q.crop_option, q.mandi, q.quantity_maund, phone)
                return buttons_message(reply.why_text(a, provider.explain(q.crop_option, q.mandi, phone)))
            rows = provider.compare(q.crop_option, q.mandi, q.quantity_maund, phone)
            return buttons_message(reply.compare_text(q.crop_option, rows))
        # a query
        if p.missing:
            return text_message(reply.ASK[p.missing[0]])
        assumed = p.quantity_maund is None
        if assumed:
            p.quantity_maund = reply.DEFAULT_QUANTITY_MAUND
        a = provider.advice(p.crop_option, p.mandi, p.quantity_maund, phone)
        memory.remember(phone, p)
        return buttons_message(reply.advice_text(a, quantity_assumed=assumed))
    except LookupError:
        return text_message(reply.NO_DATA.format(mandi=reply.MANDI_UR.get(ctx.mandi or "", ctx.mandi),
                                                 crop=reply.CROP_UR.get(ctx.crop_option or "", ctx.crop_option)))
    except NotReady as e:
        log.warning("WhatsApp: service not ready: %s", e)
        return text_message(reply.NOT_READY)


def _handle(msg: dict, provider: AdviceProvider, sender: Sender) -> None:
    sender.send(msg.get("from", ""), respond(msg, provider, chat=default_chat(provider)))


# ---------------------------------------------------------------- routes

@router.get("/whatsapp", response_class=PlainTextResponse)
def verify(
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
    settings: WhatsAppSettings = Depends(get_wa_settings),  # noqa: B008
) -> str:
    if settings.verify_token and mode == "subscribe" and hmac.compare_digest(token, settings.verify_token):
        return challenge
    raise HTTPException(403, "verification failed")


@router.post("/whatsapp")
async def receive(
    request: Request,
    background: BackgroundTasks,
    settings: WhatsAppSettings = Depends(get_wa_settings),  # noqa: B008
    provider: AdviceProvider = Depends(get_provider),  # noqa: B008
    sender: Sender = Depends(get_sender),  # noqa: B008
) -> dict:
    raw = await request.body()
    if not settings.app_secret:
        raise HTTPException(503, "WhatsApp is not configured (FS_WA_APP_SECRET)")
    if not signature_ok(raw, request.headers.get("X-Hub-Signature-256"), settings.app_secret):
        raise HTTPException(403, "bad signature")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(400, "not JSON") from e
    queued = 0
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):  # delivery statuses are ignored
                message_id = msg.get("id", "")
                if not message_id or MEMORY.first_time(message_id):
                    background.add_task(_handle, msg, provider, sender)
                    queued += 1
    return {"status": "ok", "queued": queued}  # Meta only needs a quick 200; replies go out after it
