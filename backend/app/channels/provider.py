"""The advice source shared by every channel (WhatsApp, SMS, chat): interface I6, Owner C's service layer.

One adapter, so every channel gives the same answer as the web app.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class NotReady(Exception):
    """The service layer the channel needs does not exist yet."""


class AdviceProvider(Protocol):
    def advice(self, crop_option: str, mandi: str, quantity_maund: float, phone: str) -> dict: ...
    def explain(self, crop_option: str, mandi: str, phone: str) -> list[dict]: ...
    def compare(self, crop_option: str, mandi: str, quantity_maund: float, phone: str) -> list[dict]: ...
    def wait_plan(self, crop_option: str, mandi: str, quantity_maund: float, phone: str) -> dict: ...
    def loan_plan(self, crop_option: str, phone: str) -> dict: ...
    def offer_check(self, crop_option: str, mandi: str, offer: float, quantity_maund: float | None,
                    phone: str) -> dict: ...
    def set_alerts(self, phone: str, enabled: bool) -> None: ...


class ServicesProvider:
    """Adapter over backend/app/services.py (I6). The function names are hand-off H-C12 in docs/PLAN.md.

    services.get_advice(crop_option, mandi, quantity_maund, phone=...)  -> blueprint advice dict
    services.get_explanation(crop_option, mandi)                         -> [{text_ur, direction}]
    services.compare_mandis(crop_option, mandi, quantity_maund)          -> [{mandi, net_price, transport_cost,
                                                                             gain_vs_preferred, has_data}]
    services.set_alerts(phone, enabled)
    A LookupError means "no price data for this crop at this mandi".
    """

    def _fn(self, name: str) -> Callable[..., Any]:
        try:
            from backend.app import services  # noqa: PLC0415 (lazy: Owner C's module may not exist yet)
        except ImportError as e:
            raise NotReady("backend/app/services.py") from e
        fn = getattr(services, name, None)
        if fn is None:
            raise NotReady(f"services.{name}")
        return fn

    def advice(self, crop_option, mandi, quantity_maund, phone):
        return self._fn("get_advice")(crop_option, mandi, quantity_maund, phone=phone)

    def explain(self, crop_option, mandi, phone):
        return self._fn("get_explanation")(crop_option, mandi)

    def compare(self, crop_option, mandi, quantity_maund, phone):
        return self._fn("compare_mandis")(crop_option, mandi, quantity_maund)

    def wait_plan(self, crop_option, mandi, quantity_maund, phone):
        plan = self._fn("wait_plan")(crop_option, mandi, quantity_maund, phone=phone)
        return {**plan, "crop_option": crop_option, "mandi": mandi}

    def loan_plan(self, crop_option, phone):
        """The loan planner needs the farmer's land area, which lives in their profile. Raises LookupError when
        the sender is not registered or has no land area on file (the channel then asks them to set it)."""
        from backend.app import db  # noqa: PLC0415 (lazy, like set_alerts)
        f = db.get_farmer_by_phone(phone) if phone else None
        acres = (f or {}).get("land_area_acres")
        if not acres:
            raise LookupError("no land area on file")
        plan = self._fn("loan_plan")(crop_option, acres)
        return {**plan, "crop_option": crop_option}

    def offer_check(self, crop_option, mandi, offer, quantity_maund, phone):
        """services.offer_check: the offer against the mandi's last 14 days. Without a quantity only the per-maund
        gap is meaningful (the service's default total is not shown)."""
        fn = self._fn("offer_check")
        r = fn(crop_option, mandi, offer, quantity_maund) if quantity_maund else fn(crop_option, mandi, offer)
        return {**r, "evidence": self._offer_evidence(crop_option, mandi, r)}

    def _offer_evidence(self, crop_option, mandi, r) -> list[str]:
        """Why the 14-day range may not be a real fair range, from the checks the app's other screens use. Read
        only: the offer check's numbers are untouched. FROZEN: AMIS repeated this price; STALE: older than the
        staleness rule; LIMITED: one price for the whole window, so low and high are the same number."""
        from backend.app import services  # noqa: PLC0415 (lazy, as in _fn)
        flags = []
        if services.frozen_since(services._series(crop_option, mandi), r["prices_as_of"]) is not None:
            flags.append("FROZEN")
        if services.is_stale(r["prices_as_of"]):
            flags.append("STALE")
        if r["fair_low"] == r["fair_high"]:
            flags.append("LIMITED")
        return flags

    def set_alerts(self, phone, enabled):
        self._fn("set_alerts")(phone, enabled)


def get_provider() -> AdviceProvider:
    return ServicesProvider()
