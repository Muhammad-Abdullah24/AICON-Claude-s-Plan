"""SMS channel, provider-neutral (task A11): phone numbers, the SMS form of a reply, and the outbound interface.

SMS shares WhatsApp's conversation (`whatsapp.respond`: parser, memory, replies). In front of it sits the SMS
number menu (channels/sms_menu.py: 0 menu, 1 buyer offer, 2 compare, 3 why, 4 alerts on, 5 alerts off), and
`render` turns a reply into plain text, the WhatsApp quick-reply buttons becoming those menu numbers.

The provider is picked by SMS_PROVIDER: `textbee` (backend/app/channels/textbee.py) or `simpapp` (the "SMS Gateway
API" Android app, backend/app/channels/simpapp.py); both send from an Android phone's SIM. Unset, SMS is off.

A provider's "accepted" is not "delivered": it means the gateway took the message. Delivery is never promised.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Literal, Protocol

from backend.app.channels import reply
from backend.app.channels.provider import AdviceProvider

log = logging.getLogger("farmsight.sms")

# Urdu goes as UCS-2: 67 characters per part of a long SMS. Ten parts at most; longer replies are clipped.
SMS_MAX_CHARS = 670

SendStatus = Literal["ACCEPTED", "FAILED", "UNKNOWN"]   # UNKNOWN: it may or may not have gone (e.g. a timeout)


class SmsConfigError(RuntimeError):
    """SMS is off or a required setting is missing. The message names the setting, never its value."""


@dataclass(frozen=True)
class SendResult:
    status: SendStatus
    http_status: int | None = None
    reference: str | None = None      # the provider's id for the send, to look up delivery later

    @property
    def accepted(self) -> bool:
        return self.status == "ACCEPTED"


class SmsProvider(Protocol):
    name: str

    def send(self, to: str, text: str) -> SendResult: ...   # `to` in E.164; never retried by the caller


# ---------------------------------------------------------------- phone numbers

_PK_MOBILE = re.compile(r"^923\d{9}$")


def normalize_pk_phone(phone: str) -> str | None:
    """A Pakistani mobile number in E.164 ("+923001234567"), or None when it is not one.

    Accepts "+92 300 1234567", "923001234567", "00923001234567", "03001234567" and "3001234567". Short codes,
    landlines and foreign numbers give None, so we never reply to a carrier's or bank's service message.
    """
    if not isinstance(phone, str) or len(phone) > 32 or re.search(r"[^\d+\-\s()]", phone):
        return None
    d = re.sub(r"\D", "", phone)
    if d.startswith("0092"):
        d = d[2:]
    elif d.startswith("03") and len(d) == 11:
        d = "92" + d[1:]
    elif d.startswith("3") and len(d) == 10:
        d = "92" + d
    return "+" + d if _PK_MOBILE.match(d) else None


def mask_phone(phone: str) -> str:
    """For logs: only the last 3 digits."""
    d = re.sub(r"\D", "", phone or "")
    return f"…{d[-3:]}" if len(d) >= 3 else "…"


# ---------------------------------------------------------------- the SMS form of a reply

# The SMS number menu (channels/sms_menu.py). Kept here so the hint line below every reply uses the same numbers.
SMS_MENU = {"0": "menu", "1": "offer", "2": "compare", "3": "why", "4": "start", "5": "stop"}
_DIGIT = {command: digit for digit, command in SMS_MENU.items()}

# The WhatsApp buttons as SMS menu numbers, then the menu itself: "2 منڈیاں | 3 کیوں؟ | 5 الرٹ بند | 0 مینو".
_BUTTONS = sorted(reply.BUTTONS, key=lambda b: _DIGIT[b[0]])
COMMAND_LINE = " | ".join([*(f"{_DIGIT[cmd]} {title}" for cmd, title in _BUTTONS), f"0 {reply.SMS_MENU_WORD}"])


def render(message: dict) -> str:
    """Plain SMS text from a reply built for WhatsApp (`whatsapp.respond`): the same words, buttons as numbers."""
    if message.get("type") == "interactive":
        body = message["interactive"]["body"]["text"]
        return reply.clip(body, SMS_MAX_CHARS - len(COMMAND_LINE) - 1) + "\n" + COMMAND_LINE
    return reply.clip(message.get("text", {}).get("body", ""), SMS_MAX_CHARS)


# ---------------------------------------------------------------- choosing the provider

def get_sms_provider() -> SmsProvider:
    """The configured provider. Raises SmsConfigError when SMS is off or misconfigured (fail closed)."""
    name = os.environ.get("SMS_PROVIDER", "").strip().lower()
    if not name:
        raise SmsConfigError("SMS is off: SMS_PROVIDER is not set")
    if name == "textbee":
        from backend.app.channels import textbee  # noqa: PLC0415 (only when chosen)
        return textbee.TextBeeSmsProvider(textbee.get_textbee_settings())
    if name == "simpapp":
        from backend.app.channels import simpapp  # noqa: PLC0415 (only when chosen)
        return simpapp.SimpappSmsProvider(simpapp.get_simpapp_settings())
    raise SmsConfigError("SMS_PROVIDER must be 'textbee' or 'simpapp'")


# ---------------------------------------------------------------- one incoming SMS, one reply

def answer(event_key: str, phone: str, text: str, advice: AdviceProvider, outbound: SmsProvider) -> SendResult:
    """The reply to one incoming SMS, from the shared WhatsApp/SMS conversation, sent once through `outbound`.

    `phone` is the sender in E.164 and `event_key` the event's already-claimed de-duplication key. Records the
    outcome on the event. Never raises: a farmer gets no stack trace, and the event is not tried again.
    """
    from backend.app import db  # noqa: PLC0415
    from backend.app.channels import sms_menu, whatsapp  # noqa: PLC0415 (whatsapp imports the chat stack)

    msg = {"from": db.digits(phone), "id": event_key, "type": "text", "text": {"body": text}}
    try:
        body = render(sms_menu.respond(msg, advice, chat=whatsapp.default_chat(advice)))
    except Exception as e:  # noqa: BLE001
        log.warning("SMS event …%s: no reply built (%s)", event_key[-8:], type(e).__name__)
        db.finish_sms_event(event_key, "ERROR")
        return SendResult("FAILED")
    result = outbound.send(phone, body)
    db.finish_sms_event(event_key, result.status)
    log.info("SMS event …%s: reply to %s through %s: %s", event_key[-8:], mask_phone(phone), outbound.name,
             result.status)
    return result
