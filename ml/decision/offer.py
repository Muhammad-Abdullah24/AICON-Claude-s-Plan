"""Check a buyer's offer against recent mandi reference prices (UC-07, reframed as a pre-sale reference check).

Pure Python, no third-party imports. Prices are Rs per 40 kg (one maund), quantities in maund.

The offer is compared with what AMIS reported at the farmer's mandi in a recent window. That is a *reference*,
not a fair, true or guaranteed price: grade, quality, moisture, buyer terms, timing, transport, tied credit and the
actual auction can all change what a farmer can get. So the numbers are always returned, and a separate
`reference_strength` says how far the reference can be leaned on. When it is weak, `result_status` is
REFERENCE_DATA_LIMITED instead of a below / within / above judgement.

The offer is treated as a gross quoted price per 40 kg (before any commission the farmer pays). A commission is
shown only when the farmer entered their own rate; it never changes the classification.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from ml.decision import config

OFFER_PRICE_BASIS = "GROSS_QUOTED"

STRONG = "STRONG"
LIMITED_STALE = "LIMITED_STALE"
LIMITED_FROZEN = "LIMITED_FROZEN"
LIMITED_FEW_DAYS = "LIMITED_FEW_DAYS"
LIMITED_SAME_PRICE = "LIMITED_SAME_PRICE"

BELOW, WITHIN, ABOVE = "BELOW_REFERENCE_RANGE", "WITHIN_REFERENCE_RANGE", "ABOVE_REFERENCE_RANGE"
DATA_LIMITED = "REFERENCE_DATA_LIMITED"

# Strength codes and the limitation code each one raises, in order of precedence (the first that applies wins).
_STRENGTH_LIMITATION = {
    LIMITED_STALE: "STALE_REFERENCE",
    LIMITED_FROZEN: "FROZEN_REFERENCE",
    LIMITED_FEW_DAYS: "FEW_REFERENCE_DAYS",
    LIMITED_SAME_PRICE: "SAME_PRICE_ALL_WINDOW",
}
ALWAYS = ("QUALITY_GRADE_NOT_INCLUDED", "BUYER_TERMS_NOT_INCLUDED")


def _positive(name: str, value: float | None) -> float:
    if value is None or value <= 0:
        raise ValueError(f"{name} must be positive, got {value!r}")
    return float(value)


def reference_strength(window_prices: Sequence[float], is_stale: bool, price_unchanged_since: str | None,
                       min_days: int = config.OFFER_MIN_REFERENCE_DAYS) -> tuple[str, list[str]]:
    """(strength, every weakness found). Strength is the first weakness by precedence, or STRONG."""
    weak = []
    if is_stale:
        weak.append(LIMITED_STALE)
    if price_unchanged_since:
        weak.append(LIMITED_FROZEN)
    if len(window_prices) < min_days:
        weak.append(LIMITED_FEW_DAYS)
    if len(set(window_prices)) == 1:
        weak.append(LIMITED_SAME_PRICE)
    return (weak[0] if weak else STRONG), weak


def _position(offer: float, low: float, high: float) -> tuple[str, float]:
    """Where the offer sits against the reported range, and the gap to its nearest edge (0 inside)."""
    if offer < low:
        return BELOW, offer - low
    if offer > high:
        return ABOVE, offer - high
    return WITHIN, 0.0


def _alternative(alt: Mapping, offer: float, quantity: float, min_days: int) -> dict:
    if alt.get("reference_price") is None:
        return {"mandi": alt["mandi"], "has_data": False}
    price, transport = float(alt["reference_price"]), float(alt.get("transport_cost") or 0.0)
    net = price - transport
    window = alt.get("window_prices") or [price]   # the same rules as the farmer's own mandi
    strength, _ = reference_strength(window, bool(alt.get("is_stale")), alt.get("price_unchanged_since"), min_days)
    per = net - offer
    return {
        "mandi": alt["mandi"], "has_data": True,
        "reference_price": round(price, 2), "prices_as_of": alt.get("prices_as_of"),
        "is_stale": bool(alt.get("is_stale")), "price_unchanged_since": alt.get("price_unchanged_since"),
        "reference_days": len(window), "transport_cost": round(transport, 2), "net_after_transport": round(net, 2),
        "difference_vs_offer_per_maund": round(per, 2), "difference_vs_offer_total": round(per * quantity),
        "reference_strength": strength,
        # Only a strong reference can say "better after transport"; otherwise we do not know.
        "better_after_transport": (net > offer) if strength == STRONG else None,
        # The trap the comparison exists for: a higher mandi price that transport eats up.
        "higher_quote_not_better": price > offer and net <= offer,
    }


def offer_reference(offer_price: float, quantity_maund: float, window_prices: Sequence[float],
                    reference_price: float, *, is_stale: bool, price_unchanged_since: str | None = None,
                    is_synthetic: bool = False, own_transport_cost: float = 0.0, arhti_pct: float | None = None,
                    alternatives: Iterable[Mapping] = (),
                    min_days: int = config.OFFER_MIN_REFERENCE_DAYS) -> dict:
    """The offer against recent reference prices at the farmer's mandi, plus the other mandis after transport.

    window_prices: every AMIS price reported at this mandi in the window (one per reported day).
    reference_price: the latest of them. alternatives: other mandis as {mandi, reference_price (None if no data),
    prices_as_of, is_stale, price_unchanged_since, transport_cost, window_prices}.
    """
    offer = _positive("offer_price", offer_price)
    qty = _positive("quantity_maund", quantity_maund)
    ref = _positive("reference_price", reference_price)
    if not window_prices:
        raise ValueError("window_prices is empty: no reference price")
    low, high = float(min(window_prices)), float(max(window_prices))
    strength, weaknesses = reference_strength(window_prices, is_stale, price_unchanged_since, min_days)
    position, gap = _position(offer, low, high)

    alts = [_alternative(a, offer, qty, min_days) for a in alternatives]
    limitations = [_STRENGTH_LIMITATION[w] for w in weaknesses]
    commission = None
    if arhti_pct is not None:
        per = offer * arhti_pct / 100
        commission = {"pct": arhti_pct, "per_maund": round(per, 2), "total": round(per * qty), "source": "farmer"}
        limitations.append("COMMISSION_FARMER_ESTIMATE")
    else:
        limitations.append("COMMISSION_NOT_INCLUDED")
    if alts:
        limitations.append("TRANSPORT_IS_ESTIMATE")
    if is_synthetic:
        limitations.append("SYNTHETIC_DATA")
    limitations += ALWAYS

    return {
        "buyer_offer_price": round(offer, 2),
        "offer_price_basis": OFFER_PRICE_BASIS,
        "quantity_maund": qty,
        "reference_price": round(ref, 2),
        "reference_range_low": round(low, 2),
        "reference_range_high": round(high, 2),
        "reference_days": len(window_prices),
        "reference_strength": strength,
        "range_position": position,   # always computed, so the numbers are never hidden
        "result_status": position if strength == STRONG else DATA_LIMITED,
        "difference_vs_reference_per_maund": round(offer - ref, 2),
        "total_difference_vs_reference": round((offer - ref) * qty),
        "difference_vs_range_per_maund": round(gap, 2),
        "total_difference_vs_range": round(gap * qty),
        "estimated_transport_cost": round(own_transport_cost, 2),
        "estimated_commission": commission,
        "alternative_mandis": alts,
        "limitations": limitations,
    }
