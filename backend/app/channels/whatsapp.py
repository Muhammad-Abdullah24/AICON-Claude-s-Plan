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
Phone numbers and message text are never logged.

Conversation (task A11): free text ("گندم بہاولپور 100 من") answers at once; "0" opens a numbered menu
(1 advice, 2 compare, 3 why, 4/5 alerts on/off) that guides crop, rice variety, mandi and quantity. Bare numbers
are read against the farmer's current step, kept in SQLite for 30 minutes (backend/app/channels/conversation.py).
Meta's retried deliveries are recognised by message id, also in SQLite, so a restart does not answer twice.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from backend.app import db
from backend.app.channels import conversation as conv
from backend.app.channels import reply, voice
from backend.app.channels.provider import AdviceProvider, get_provider
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


def buttons_message(body: str, buttons: list[tuple[str, str]] | None = None) -> dict:
    """Body with up to 3 quick-reply buttons (Meta's limit; titles at most 20 characters)."""
    return {"type": "interactive", "interactive": {
        "type": "button",
        "body": {"text": reply.clip(body)},
        "action": {"buttons": [{"type": "reply", "reply": {"id": i, "title": t[:20]}}
                               for i, t in (buttons or reply.BUTTONS)[:3]]},
    }}


# ---------------------------------------------------------------- conversation

CHANNEL = "whatsapp"
# Quick-reply button ids are the command words the conversation engine understands ("menu" opens the menu).
BUTTON_TEXT = {"why": "why", "compare": "compare", "stop": "stop", "start": "start", "menu": "0"}


def message_text(msg: dict) -> str | None:
    """Text of a message, including taps on our quick-reply buttons (their id is the command)."""
    kind = msg.get("type")
    if kind == "text":
        return msg.get("text", {}).get("body", "")
    if kind == "interactive":
        it = msg.get("interactive", {})
        picked = it.get("button_reply") or it.get("list_reply") or {}
        return BUTTON_TEXT.get(picked.get("id", ""), picked.get("title"))
    if kind == "button":
        return msg.get("button", {}).get("payload") or msg.get("button", {}).get("text")
    return None


ChatFn = Callable[[str, str, str, "float | None", str], str]   # (question, crop, mandi, quantity, phone) -> answer


def default_chat(provider: AdviceProvider) -> ChatFn:
    """Free questions after an answer go to the same guarded chat as the web app (task A9)."""
    def run(question: str, crop: str, mandi: str, quantity: float | None, phone: str) -> str:
        return chat_service.answer(question, crop, mandi, quantity or conv.DEFAULT_QUANTITY_MAUND, provider,
                                   get_llm(), phone=phone).answer
    return run


def _with_footer(body: str, choices, limit: int = reply.MAX_BODY) -> str:
    """The answer, then its numbered next steps; the answer is clipped first so the choices always show."""
    footer = reply.choice_footer(choices) if choices else ""
    if not footer:
        return reply.clip(body, limit)
    return reply.clip(body, limit - len(footer) - 1) + "\n" + footer


def _answer(body: str, choices) -> dict:
    buttons = reply.buttons_for(choices)
    text = _with_footer(body, choices)
    return buttons_message(text, buttons) if buttons else text_message(text)


def render(r: conv.Reply, chat: ChatFn | None, phone: str) -> dict:
    """A conversation reply as a Cloud API message, in Urdu. Numbers come only from r.data (the service layer)."""
    k, d, ch = r.kind, r.data, r.choices
    invalid = [reply.INVALID] if d.get("invalid") else []
    if k == "menu":
        note = [reply.MENU_NOTE[d["note"]]] if d.get("note") else []
        return text_message("\n".join([*note, *invalid, reply.MENU_HEAD, reply.choice_lines(ch), reply.MENU_TAIL]))
    if k == "not_understood":
        return text_message("\n".join([reply.SORRY, reply.MENU_HEAD, reply.choice_lines(ch), reply.MENU_TAIL]))
    if k in reply.ASK_NUMBERED:
        return text_message("\n".join([*invalid, reply.ASK_NUMBERED[k], reply.choice_lines(ch)]))
    if k == "ask_quantity":
        return text_message("\n".join([*invalid, reply.ASK_QUANTITY, reply.choice_lines(ch)]))
    if k == "ask_offer":
        return text_message("\n".join([*invalid, reply.ASK_OFFER, reply.choice_lines(ch)]))
    if k == "offer":
        return _answer(reply.offer_text(d["crop_option"], d["mandi"], d["result"]), ch)
    if k == "offer_compare":
        return _answer(reply.offer_compare_text(d["crop_option"], d["result"]), ch)
    if k == "advice":
        return _answer(reply.advice_text(d["advice"], quantity_assumed=d["quantity_assumed"]), ch)
    if k == "why":
        return _answer(reply.why_text(d["advice"], d["reasons"]), ch)
    if k == "compare":
        return _answer(reply.compare_text(d["crop_option"], d["rows"]), ch)
    if k == "post_menu":
        return _answer(reply.INVALID, ch)
    if k == "alerts":
        return _answer(reply.STARTED if d["enabled"] else reply.STOPPED, ch)
    if k == "not_registered":
        return _answer(reply.NOT_REGISTERED, ch)
    if k == "no_data":
        head = reply.NO_DATA.format(mandi=reply.MANDI_UR.get(d["mandi"], d["mandi"]),
                                    crop=reply.CROP_UR.get(d["crop_option"], d["crop_option"]))
        return text_message("\n".join([head, reply.ASK_NUMBERED["ask_mandi"], reply.choice_lines(ch)]))
    if k == "not_ready":
        return text_message(reply.NOT_READY)
    if k == "voice_confirm":
        heard = reply.heard_text(d["crop_option"], d["mandi"], d["quantity_maund"])
        return text_message("\n".join([*invalid, heard, reply.choice_lines(ch)]))
    if k == "chat" and chat is not None:
        return _answer(chat(d["question"], d["crop_option"], d["mandi"], d["quantity_maund"], phone), ch)
    return _answer(reply.SORRY, ch)   # a free question, but no chat function was given


def respond(msg: dict, provider: AdviceProvider, chat: ChatFn | None = None, now: datetime | None = None) -> dict:
    """The reply to one incoming message, as a Cloud API message object. The conversation engine decides; the
    session is read from and saved to the database (backend/app/db.py), so a restart does not lose it."""
    phone = msg.get("from", "")
    if not db.digits(phone):
        return text_message(reply.HELP)
    now = now or datetime.now(UTC)
    if msg.get("type") in ("audio", "voice"):
        return _voice(msg, phone, provider, chat, now)
    r = conv.converse(CHANNEL, phone, message_text(msg) or "", provider, now)
    return render(r, chat, phone)


def _voice(msg: dict, phone: str, provider: AdviceProvider, chat: ChatFn | None, now: datetime) -> dict:
    """Task A10, off unless FS_VOICE_NOTES=1 and a transcriber is registered (channels/voice.py). Either way the
    farmer is never answered from an unconfirmed transcript."""
    settings = voice.get_voice_settings()
    pair, media = voice.pipeline(settings), voice.media_id(msg)
    if pair is None:
        return text_message(reply.VOICE_SOON)
    if media is None:
        return text_message(reply.VOICE_FAILED)
    try:
        t = voice.transcribe_note(media, *pair, settings)
    except voice.VoiceFailed as e:
        log.warning("WhatsApp voice note not transcribed: %s", e)
        return text_message(reply.VOICE_FAILED)
    r = conv.converse(CHANNEL, phone, t.text, provider, now, from_voice=True, voice_confidence=t.confidence,
                      min_confidence=settings.min_confidence)
    return render(r, chat, phone)


def _handle(msg: dict, provider: AdviceProvider, sender: Sender) -> None:
    db.expire_old_conversations()
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
                if not message_id or db.first_time_seen(CHANNEL, message_id):
                    background.add_task(_handle, msg, provider, sender)
                    queued += 1
    return {"status": "ok", "queued": queued}  # Meta only needs a quick 200; replies go out after it
