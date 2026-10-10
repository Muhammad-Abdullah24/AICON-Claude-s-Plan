"""The SMS number menu (task A11): what a farmer's bare number means on SMS, in front of the shared conversation.

    0 menu   1 buyer-offer check   2 compare mandis   3 why (reasons and data)   4 alerts on   5 alerts off

Everything else (a crop query, "stop", "بند", a free question) goes to the WhatsApp/SMS conversation unchanged
(`whatsapp.respond`). Options 2-5 are that conversation's own commands; option 1 is the existing offer check
(services.offer_check), which needs crop, mandi and the buyer's price per maund. It reuses the farmer's last query
and asks only for what is still missing, one short SMS at a time. Quantity is optional: without it, the reply gives
the per-maund gap only.

WhatsApp is not affected: there the numbers keep their old meaning (1 why, 2 compare, 3 stop), because WhatsApp
has buttons. Like the conversation memory, an offer in progress is kept in memory only: a restart forgets it, and the
farmer starts again with 1.
"""

from __future__ import annotations

import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field

from backend.app.channels import reply, whatsapp
from backend.app.channels.parse import Parsed, normalise, parse
from backend.app.channels.provider import AdviceProvider, NotReady
from backend.app.channels.sms import SMS_MENU

MENU = SMS_MENU   # a bare number (Urdu digits too) -> option
# The conversation's own words for options 2-5 (parse.COMMANDS), so they run exactly as on WhatsApp.
COMMAND_WORD = {"compare": "compare", "why": "why", "start": "start", "stop": "stop"}

PENDING_TTL_S = 30 * 60
MAX_OFFER = 1_000_000   # the web API's own limit for a price per 40 kg
_PRICE = re.compile(r"\d+(?:\.\d+)?")
_DIGITS = str.maketrans({**{d: str(i) for i, d in enumerate("۰۱۲۳۴۵۶۷۸۹")},
                         **{d: str(i) for i, d in enumerate("٠١٢٣٤٥٦٧٨٩")}, "٫": "."})


@dataclass
class Offer:
    """An offer check in progress: what we know so far."""
    crop_option: str | None = None
    mandi: str | None = None
    quantity_maund: float | None = None
    rice: bool = False   # "rice" was said, but not which: Super Basmati or IRRI
    at: float = field(default_factory=time.monotonic)

    def take(self, p: Parsed) -> None:
        self.crop_option = p.crop_option or self.crop_option
        self.mandi = p.mandi or self.mandi
        self.quantity_maund = p.quantity_maund or self.quantity_maund
        self.rice = self.rice or "variety" in p.missing

    @property
    def missing(self) -> list[str]:
        crop = [] if self.crop_option else ["variety" if self.rice else "crop"]
        return crop + ([] if self.mandi else ["mandi"])

    @property
    def ready(self) -> bool:
        return not self.missing


class Pending:
    """Offers in progress, per phone. In memory, capped, and forgotten after PENDING_TTL_S."""

    def __init__(self, size: int = 2000):
        self.size, self.items = size, OrderedDict[str, Offer]()

    def get(self, phone: str) -> Offer | None:
        o = self.items.get(phone)
        if o and time.monotonic() - o.at > PENDING_TTL_S:
            del self.items[phone]
            return None
        return o

    def put(self, phone: str, o: Offer) -> None:
        o.at = time.monotonic()
        self.items[phone] = o
        self.items.move_to_end(phone)
        while len(self.items) > self.size:
            self.items.popitem(last=False)

    def drop(self, phone: str) -> None:
        self.items.pop(phone, None)


PENDING = Pending()


def _text(body: str) -> dict:
    return whatsapp.text_message(body)


def _price(text: str) -> float | None:
    """The buyer's price from "3900", "Rs 3,900", "۳۹۰۰ روپے". None when there is no single sensible number."""
    t = re.sub(r"(?<=\d)[,،٬](?=\d{3})", "", text.translate(_DIGITS))   # thousands separators go
    numbers = _PRICE.findall(t)
    if len(numbers) != 1:
        return None
    value = float(numbers[0])
    return value if 0 < value <= MAX_OFFER else None


def _ask(o: Offer) -> dict:
    """The one question still open: crop and mandi together, else the one missing, else the buyer's price."""
    if o.missing == ["crop", "mandi"]:
        return _text(reply.OFFER_ASK_QUERY)
    if o.missing:
        return _text(reply.ASK[o.missing[0]])
    return _text(reply.OFFER_ASK_PRICE.format(crop=reply.CROP_UR.get(o.crop_option, o.crop_option),
                                              mandi=reply.MANDI_UR.get(o.mandi, o.mandi)))


def _check(phone: str, o: Offer, offer: float, provider: AdviceProvider) -> dict:
    PENDING.drop(phone)
    if not (o.crop_option and o.mandi):
        return _ask(o)
    try:
        result = provider.offer_check(o.crop_option, o.mandi, offer, o.quantity_maund, phone)
    except LookupError:
        return _text(reply.NO_DATA.format(mandi=reply.MANDI_UR.get(o.mandi, o.mandi),
                                          crop=reply.CROP_UR.get(o.crop_option, o.crop_option)))
    except NotReady:
        return _text(reply.NOT_READY)
    # Later "2" or "3" are about this crop and mandi, as after a query.
    whatsapp.MEMORY.remember(phone, Parsed("query", o.crop_option, o.mandi, o.quantity_maund))
    return whatsapp.buttons_message(reply.offer_text(o.crop_option, o.mandi, offer, result, o.quantity_maund))


def _start_offer(phone: str) -> dict:
    last = whatsapp.MEMORY.last.get(phone)
    o = Offer(last.crop_option, last.mandi, last.quantity_maund) if last else Offer()
    PENDING.put(phone, o)
    return _ask(o)


def _continue_offer(phone: str, text: str, o: Offer, provider: AdviceProvider) -> dict | None:
    """The next step of an offer in progress, or None when the message is something else (a command)."""
    p = parse(text)
    if o.ready:
        offer = _price(text)
        if offer is not None:
            return _check(phone, o, offer, provider)
        if p.kind == "query":   # another crop or mandi named: the questions start again from it
            o = Offer()
        elif p.kind == "unknown":
            return _text(reply.OFFER_ASK_PRICE_AGAIN)
    if p.kind == "query":
        o.take(p)
        PENDING.put(phone, o)
        return _ask(o)
    if p.kind == "unknown":
        return _ask(o)
    return None


def respond(msg: dict, provider: AdviceProvider, chat: whatsapp.ChatFn | None = None) -> dict:
    """The reply to one incoming SMS, as a WhatsApp-shaped message for `sms.render`."""
    phone, text = msg.get("from", ""), msg.get("text", {}).get("body", "")
    option = MENU.get(normalise(text))
    if option is not None:
        PENDING.drop(phone)   # a menu number always starts over
        if option == "menu":
            return _text(reply.SMS_MENU)
        if option == "offer":
            return _start_offer(phone)
        return whatsapp.respond({**msg, "text": {"body": COMMAND_WORD[option]}}, provider, chat=chat)
    o = PENDING.get(phone)
    if o is not None:
        step = _continue_offer(phone, text, o, provider)
        if step is not None:
            return step
        PENDING.drop(phone)   # "stop", "hi", "why"…: the farmer moved on
    return whatsapp.respond(msg, provider, chat=chat)
