"""SMS channel, provider-neutral (task A11): phone numbers, the SMS form of a reply, and the outbound interface.

SMS has no conversation of its own. An incoming SMS goes through the same parser, memory and replies as WhatsApp
(`whatsapp.respond`), and `render` turns that reply into plain text: the WhatsApp quick-reply buttons become the
numeric commands the parser already understands (1 why, 2 compare, 3 stop alerts).

The provider is picked by SMS_PROVIDER; `textbee` (an Android phone's SIM, backend/app/channels/textbee.py) is the
only one so far. With SMS_PROVIDER unset, SMS is off.

A provider's "accepted" is not "delivered": it means the gateway took the message. Delivery is never promised.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Literal, Protocol

from backend.app.channels import reply
from backend.app.channels.parse import COMMANDS

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

def _digit(command: str) -> str:
    return next(w for w in COMMANDS[command] if w.isdigit())


# The WhatsApp buttons as the parser's own number commands, e.g. "1 کیوں؟ | 2 منڈیاں | 3 الرٹ بند".
COMMAND_LINE = " | ".join(f"{_digit(cmd)} {title}" for cmd, title in reply.BUTTONS)


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
    raise SmsConfigError("SMS_PROVIDER must be 'textbee'")
