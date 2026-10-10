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
    def offer(self, crop_option: str, mandi: str, quantity_maund: float, offer_price: float, phone: str) -> dict: ...
    def set_alerts(self, phone: str, enabled: bool) -> bool | None: ...   # False: not a registered farmer
    def alerts_enabled(self, phone: str) -> bool | None: ...             # None: not a registered farmer


class ServicesProvider:
    """Adapter over backend/app/services.py (I6). The function names are hand-off H-C12 in docs/PLAN.md.

    services.get_advice(crop_option, mandi, quantity_maund, phone=...)  -> blueprint advice dict
    services.get_explanation(crop_option, mandi)                         -> [{text_ur, direction}]
    services.compare_mandis(crop_option, mandi, quantity_maund)          -> [{mandi, net_price, transport_cost,
                                                                             gain_vs_preferred, has_data}]
    services.offer_check(crop_option, mandi, offer, quantity_maund)      -> the offer against recent AMIS reference
                                                                            prices (the same answer as the web)
    services.set_alerts(phone, enabled)                                  -> False if the phone is not registered
    services.alerts_status(phone)                                        -> True / False, None if not registered
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

    def offer(self, crop_option, mandi, quantity_maund, offer_price, phone):
        return self._fn("offer_check")(crop_option, mandi, offer_price, quantity_maund)

    def set_alerts(self, phone, enabled):
        return self._fn("set_alerts")(phone, enabled)

    def alerts_enabled(self, phone):
        return self._fn("alerts_status")(phone)


def get_provider() -> AdviceProvider:
    return ServicesProvider()
