"""The numbered-menu conversation shared by WhatsApp and SMS (task A11): one deterministic state machine.

It decides what a farmer's message means and what to answer, as a reply *intent* (a kind, the service layer's
data and the numbered choices to show). Each channel renders the intent in its own words (WhatsApp Urdu in
reply.py, SMS Roman Urdu), so the advice, numbers and warnings are the same everywhere. It never computes a
number: advice, reasons and mandi comparisons come from the shared AdviceProvider (services.py, interface I6).

Main menu:  0 menu   1 rate and advice   2 compare mandis   3 why   4 alerts on   5 alerts off
Guided:     crop -> rice variety (rice only) -> mandi -> quantity (not for "why") -> answer
After it:   1 why   2 compare   3 alerts on/off   0 menu

Rules:
- A bare number means something only in the farmer's current step, and every reply that expects a number lists
  them. With no live session, a bare number (other than 0) gets the main menu: it is never guessed.
- Free text works at any step as before ("گندم بہاولپور 100 من", "gandum vehari 50 mann", "why", "بند").
  A full query answers at once; part of one ("gandum") fills in the step it answers.
- The session lasts SESSION_MINUTES; an expired one counts as none. Only codes and numbers are kept, never text.
- Turning alerts on or off is returned as `alert_action` for the channel to apply; the engine does not write.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

from backend.app.channels.parse import _CHAR_MAP, _quantity, normalise, parse
from backend.app.channels.provider import AdviceProvider, NotReady
from backend.app.ids import CROP_TO_DATA, MANDI_TO_DATA

SESSION_MINUTES = int(os.environ.get("FS_CHANNEL_SESSION_MINUTES", "30"))
DEFAULT_QUANTITY_MAUND = 100   # only for a full free-text query without a quantity, as before; the reply says so
MAX_QUANTITY_MAUND = 100_000

MENU, CROP, RICE_VARIETY, MANDI, QUANTITY, POST_ADVICE = (
    "menu", "crop", "rice_variety", "mandi", "quantity", "post_advice")
STEPS = (MENU, CROP, RICE_VARIETY, MANDI, QUANTITY, POST_ADVICE)
ADVICE, COMPARE, WHY = "advice", "compare", "why"
RICE = "rice"   # draft crop while the variety is still unknown

_NUMBER = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[.)]?\s*$")
_NEGATIVE = re.compile(r"^\s*[-−]\s*[\d۰-۹٠-٩]")


@dataclass(frozen=True)
class Options:
    """What the menus list, in order (the numbers follow it). Data names, as the service layer uses."""
    crops: tuple[str, ...]           # top level: single crops plus RICE when there are rice varieties
    rice_varieties: tuple[str, ...]
    mandis: tuple[str, ...]


def default_options() -> Options:
    varieties = tuple(v for v in ("SuperBasmati", "IRRI") if v in CROP_TO_DATA.values())
    singles = tuple(c for c in CROP_TO_DATA.values() if c not in varieties)
    return Options(crops=singles + ((RICE,) if varieties else ()), rice_varieties=varieties,
                   mandis=tuple(MANDI_TO_DATA.values()))


@dataclass(frozen=True)
class State:
    step: str = MENU
    pending: str | None = None              # advice | compare | why: what the guided flow ends in
    draft_crop: str | None = None
    draft_mandi: str | None = None
    draft_quantity: float | None = None
    last_crop: str | None = None            # the last answered query, for "why" and "compare" after it
    last_mandi: str | None = None
    last_quantity: float | None = None
    expires_at: datetime | None = None      # set by the store when saved

    def __post_init__(self):
        if self.step not in STEPS:
            raise ValueError(f"unknown step {self.step!r}")

    @property
    def has_last(self) -> bool:
        return bool(self.last_crop and self.last_mandi)


@dataclass(frozen=True)
class Reply:
    kind: str     # menu | post_menu | ask_crop | ask_variety | ask_mandi | ask_quantity | advice | why | compare
                  # | alerts | no_data | not_ready | not_understood | chat
    data: dict[str, Any] = field(default_factory=dict)
    choices: tuple[tuple[str, str], ...] = ()   # (number, code) the farmer can reply with, in order


@dataclass(frozen=True)
class Outcome:
    reply: Reply
    state: State | None           # None: nothing to keep
    persist: str                  # "save" (with a fresh expiry) | "clear"
    expired: bool = False         # the stored session had expired (the store may delete it)
    alert_action: bool | None = None   # True: turn alerts on, False: off, None: no change


# ---------------------------------------------------------------- choices

MAIN_CHOICES = (("1", ADVICE), ("2", COMPARE), ("3", WHY), ("4", "alerts_on"), ("5", "alerts_off"), ("0", MENU))


def _numbered(items: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    return tuple((str(i), item) for i, item in enumerate(items, 1)) + (("0", MENU),)


def post_choices(alerts_enabled: bool) -> tuple[tuple[str, str], ...]:
    return (("1", WHY), ("2", COMPARE), ("3", "alerts_off" if alerts_enabled else "alerts_on"), ("0", MENU))


# ---------------------------------------------------------------- the engine

def handle(text: str, state: State | None, provider: AdviceProvider, *, phone: str, now: datetime,
           alerts_enabled: bool = False, options: Options | None = None) -> Outcome:
    """The reply to one message and the session after it. `state` is what the store had (None if nothing)."""
    return _Engine(provider, phone, alerts_enabled, options or default_options()).run(text, state, now)


class _Engine:
    def __init__(self, provider: AdviceProvider, phone: str, alerts_enabled: bool, options: Options):
        self.provider, self.phone, self.alerts_enabled, self.o = provider, phone, alerts_enabled, options

    # ------------------------------------------------ entry
    def run(self, text: str, state: State | None, now: datetime) -> Outcome:
        expired = state is not None and state.expires_at is not None and state.expires_at <= now
        if expired:
            state = None
        out = self._dispatch(text or "", state, expired)
        return replace(out, expired=expired) if expired else out

    def _dispatch(self, text: str, state: State | None, expired: bool) -> Outcome:
        if _NEGATIVE.match(text):   # "-5": the parser drops the sign as punctuation, so refuse it here
            return self._invalid(state) if state is not None else self._menu(None, note="no_session")
        number = _NUMBER.match(text.translate(_CHAR_MAP))
        if number:
            if number.group(1) == "0":
                return self._menu(state)
            if state is None:
                return self._menu(None, note="expired" if expired else "no_session")
            return self._number(state, number.group(1))
        if state is not None and state.step == QUANTITY:
            qty = _quantity(normalise(text))
            if qty is not None and normalise(text).split()[0][0].isdigit():   # "100 man", "2000 kg"
                return self._set_quantity(state, qty)
        return self._words(text, state)

    # ------------------------------------------------ bare numbers, read by the current step
    def _number(self, s: State, raw: str) -> Outcome:
        if s.step == QUANTITY:
            return self._set_quantity(s, float(raw))
        if "." in raw:
            return self._invalid(s)
        n = int(raw)
        if s.step == MENU:
            if n in (1, 2, 3):
                pending = {1: ADVICE, 2: COMPARE, 3: WHY}[n]
                return self._advance(replace(s, pending=pending, draft_crop=None, draft_mandi=None,
                                             draft_quantity=None))
            if n in (4, 5):
                return self._alerts(s, n == 4)
            return self._invalid(s)
        if s.step == CROP:
            if 1 <= n <= len(self.o.crops):
                return self._advance(replace(s, draft_crop=self.o.crops[n - 1]))
            return self._invalid(s)
        if s.step == RICE_VARIETY:
            if 1 <= n <= len(self.o.rice_varieties):
                return self._advance(replace(s, draft_crop=self.o.rice_varieties[n - 1]))
            return self._invalid(s)
        if s.step == MANDI:
            if 1 <= n <= len(self.o.mandis):
                return self._advance(replace(s, draft_mandi=self.o.mandis[n - 1]))
            return self._invalid(s)
        # POST_ADVICE
        if n == 1:
            return self._from_last(s, WHY)
        if n == 2:
            return self._from_last(s, COMPARE)
        if n == 3:
            return self._alerts(s, not self.alerts_enabled)
        return self._invalid(s)

    # ------------------------------------------------ words: the existing free-text behaviour
    def _words(self, text: str, s: State | None) -> Outcome:
        p = parse(text)
        if p.kind == "help":
            return self._menu(s)
        if p.kind in ("stop", "start"):
            return self._alerts(s, p.kind == "start")
        if p.kind in (WHY, COMPARE):
            if s is not None and s.has_last:
                return self._from_last(s, p.kind)
            return self._advance(replace(s or State(), step=MENU, pending=p.kind, draft_crop=None,
                                         draft_mandi=None, draft_quantity=None))
        if p.kind == "query":
            crop = RICE if "variety" in p.missing else p.crop_option
            if crop and p.mandi:   # a full query answers at once, as before
                assumed = p.quantity_maund is None
                qty = DEFAULT_QUANTITY_MAUND if assumed else p.quantity_maund
                base = replace(s or State(), pending=ADVICE, draft_crop=crop, draft_mandi=p.mandi,
                               draft_quantity=qty)
                return self._advance(base, quantity_assumed=assumed)
            guided = s is not None and s.step in (CROP, RICE_VARIETY, MANDI, QUANTITY)
            base = s if guided else replace(s or State(), pending=ADVICE, draft_crop=None, draft_mandi=None,
                                            draft_quantity=None)
            if crop and not (crop == RICE and base.draft_crop in self.o.rice_varieties):
                base = replace(base, draft_crop=crop)
            if p.mandi:
                base = replace(base, draft_mandi=p.mandi)
            if p.quantity_maund is not None:
                base = replace(base, draft_quantity=p.quantity_maund)
            return self._advance(base)
        # not understood
        if s is not None and s.step in (CROP, RICE_VARIETY, MANDI, QUANTITY):
            return self._invalid(s)
        if s is not None and s.has_last:
            return Outcome(Reply("chat", {"question": text, "crop_option": s.last_crop, "mandi": s.last_mandi,
                                          "quantity_maund": s.last_quantity}, post_choices(self.alerts_enabled)),
                           replace(s, step=POST_ADVICE), "save")
        return Outcome(Reply("not_understood", {}, MAIN_CHOICES), replace(s or State(), step=MENU), "save")

    # ------------------------------------------------ steps
    def _menu(self, s: State | None, note: str | None = None) -> Outcome:
        base = s or State()
        state = replace(base, step=MENU, pending=None, draft_crop=None, draft_mandi=None, draft_quantity=None)
        return Outcome(Reply("menu", {"note": note} if note else {}, MAIN_CHOICES), state, "save")

    def _ask(self, s: State, invalid: bool = False) -> Outcome:
        data = {"invalid": invalid, "pending": s.pending}
        if s.step == CROP:
            return Outcome(Reply("ask_crop", data, _numbered(self.o.crops)), s, "save")
        if s.step == RICE_VARIETY:
            return Outcome(Reply("ask_variety", data, _numbered(self.o.rice_varieties)), s, "save")
        if s.step == MANDI:
            return Outcome(Reply("ask_mandi", {**data, "crop_option": s.draft_crop}, _numbered(self.o.mandis)),
                           s, "save")
        return Outcome(Reply("ask_quantity", {**data, "crop_option": s.draft_crop, "mandi": s.draft_mandi},
                             (("0", MENU),)), s, "save")

    def _invalid(self, s: State) -> Outcome:
        if s.step == MENU:
            return Outcome(Reply("menu", {"invalid": True}, MAIN_CHOICES), s, "save")
        if s.step == POST_ADVICE:
            return Outcome(Reply("post_menu", {"invalid": True, "crop_option": s.last_crop, "mandi": s.last_mandi},
                                 post_choices(self.alerts_enabled)), s, "save")
        return self._ask(s, invalid=True)

    def _set_quantity(self, s: State, qty: float) -> Outcome:
        if not 0 < qty <= MAX_QUANTITY_MAUND:
            return self._invalid(s)
        return self._advance(replace(s, draft_quantity=qty))

    def _advance(self, s: State, quantity_assumed: bool = False) -> Outcome:
        """Ask for the next missing piece, or answer when nothing is missing."""
        if s.draft_crop is None:
            return self._ask(replace(s, step=CROP))
        if s.draft_crop == RICE:
            return self._ask(replace(s, step=RICE_VARIETY))
        if s.draft_mandi is None:
            return self._ask(replace(s, step=MANDI))
        if s.pending != WHY and s.draft_quantity is None:
            return self._ask(replace(s, step=QUANTITY))
        return self._answer(s, s.pending or ADVICE, s.draft_crop, s.draft_mandi, s.draft_quantity,
                            quantity_assumed)

    def _from_last(self, s: State, action: str) -> Outcome:
        if action == COMPARE and s.last_quantity is None:
            return self._ask(replace(s, step=QUANTITY, pending=COMPARE, draft_crop=s.last_crop,
                                     draft_mandi=s.last_mandi, draft_quantity=None))
        return self._answer(s, action, s.last_crop, s.last_mandi, s.last_quantity, False)

    def _answer(self, s: State, action: str, crop: str, mandi: str, qty: float | None,
                quantity_assumed: bool) -> Outcome:
        after = State(step=POST_ADVICE, last_crop=crop, last_mandi=mandi, last_quantity=qty)
        choices = post_choices(self.alerts_enabled)
        try:
            if action == ADVICE:
                a = self.provider.advice(crop, mandi, qty, self.phone)
                return Outcome(Reply("advice", {"advice": a, "quantity_assumed": quantity_assumed}, choices),
                               after, "save")
            if action == COMPARE:
                rows = self.provider.compare(crop, mandi, qty, self.phone)
                return Outcome(Reply("compare", {"crop_option": crop, "mandi": mandi, "rows": rows}, choices),
                               after, "save")
            a = self.provider.advice(crop, mandi, qty or DEFAULT_QUANTITY_MAUND, self.phone)
            reasons = self.provider.explain(crop, mandi, self.phone)
            return Outcome(Reply("why", {"advice": a, "reasons": reasons}, choices), after, "save")
        except LookupError:
            # No price for this crop at this mandi: keep the crop, ask for another mandi.
            retry = State(step=MANDI, pending=action, draft_crop=crop, draft_quantity=qty,
                          last_crop=s.last_crop, last_mandi=s.last_mandi, last_quantity=s.last_quantity)
            return Outcome(Reply("no_data", {"crop_option": crop, "mandi": mandi}, _numbered(self.o.mandis)),
                           retry, "save")
        except NotReady:
            return Outcome(Reply("not_ready", {}, (("0", MENU),)),
                           replace(s, step=MENU, pending=None, draft_crop=None, draft_mandi=None,
                                   draft_quantity=None), "save")

    def _alerts(self, s: State | None, enabled: bool) -> Outcome:
        if s is not None and s.step == POST_ADVICE:   # stay with the advice, the "3" label flips
            return Outcome(Reply("alerts", {"enabled": enabled}, post_choices(enabled)), s, "save",
                           alert_action=enabled)
        return Outcome(Reply("alerts", {"enabled": enabled}, (("0", MENU),)), None, "clear", alert_action=enabled)


# ---------------------------------------------------------------- persistence (backend/app/db.py)

def to_fields(state: State) -> dict:
    return {k: getattr(state, k) for k in ("step", "pending", "draft_crop", "draft_mandi", "draft_quantity",
                                           "last_crop", "last_mandi", "last_quantity")}


def from_fields(row: dict | None, options: Options | None = None) -> State | None:
    """A stored row as a State. A row that no longer makes sense (an unknown step or crop, e.g. after a code
    change) counts as no session, so the farmer is sent back to the main menu instead of a broken step."""
    if row is None:
        return None
    o = options or default_options()
    crops = {*o.crops, *o.rice_varieties, None}
    try:
        state = State(**{k: row.get(k) for k in (*to_fields(State()), "expires_at")})
    except (TypeError, ValueError):
        return None
    if state.pending not in (None, ADVICE, COMPARE, WHY) or state.draft_crop not in crops \
            or state.last_crop not in crops or state.draft_mandi not in (*o.mandis, None) \
            or state.last_mandi not in (*o.mandis, None):
        return None
    return state


def load(channel: str, phone: str) -> State | None:
    from backend.app import db  # noqa: PLC0415 (the engine itself stays free of storage)
    return from_fields(db.get_conversation(channel, phone))


def store(channel: str, phone: str, outcome: Outcome, at: datetime | None = None) -> None:
    """Save or clear the session after a reply, with a fresh SESSION_MINUTES expiry."""
    from backend.app import db  # noqa: PLC0415
    if outcome.persist == "save" and outcome.state is not None:
        db.save_conversation(channel, phone, to_fields(outcome.state), SESSION_MINUTES, at)
    else:
        db.clear_conversation(channel, phone)


# ---------------------------------------------------------------- one turn, as every channel runs it

def _alerts_status(provider: AdviceProvider, phone: str) -> bool | None:
    status = getattr(provider, "alerts_enabled", None)   # older providers do not report it
    try:
        return status(phone) if status else None
    except NotReady:
        return None


def converse(channel: str, phone: str, text: str, provider: AdviceProvider, now: datetime) -> Reply:
    """Load the session, decide the reply, apply an alert change, save the session. WhatsApp and SMS both call
    this, so they cannot drift apart; only the wording differs."""
    status = _alerts_status(provider, phone)
    out = handle(text, load(channel, phone), provider, phone=phone, now=now, alerts_enabled=bool(status))
    r = out.reply
    if out.alert_action is not None:
        try:
            done = provider.set_alerts(phone, out.alert_action)
        except NotReady:
            done = False
        if done is False:   # not a registered farmer (or no service): nothing changed, so say that
            post = out.state is not None and out.state.step == POST_ADVICE
            r = Reply("not_registered", {}, post_choices(bool(status)) if post else r.choices)
    store(channel, phone, out, now)
    return r
