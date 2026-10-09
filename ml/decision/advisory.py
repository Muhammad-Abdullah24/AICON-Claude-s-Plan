"""Interface I3 (Owner B): the advisory engine from the blueprint (UC-03, UC-04, UC-07, UC-08).

Pure Python with no third-party imports. Every price is Rs per 40 kg and every quantity is in maund (40 kg),
so quantity x price is rupees. The functions take plain numbers; `ml/decision/inputs.py` reads the ones
that come from the runtime tables (interest rate, costs, transport, support prices, staleness).

The engine returns numbers and codes only. Turning them into Urdu or English is the caller's job.
crop_plan(), selling_window() (B7) and alert_check() (B8) are added in later tasks.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from ml.decision import config

WEEKS_PER_YEAR = 52


def _check_price(name: str, value: float) -> None:
    if value is None or value <= 0:
        raise ValueError(f"{name} must be a positive price, got {value!r}")


def _after_arhti(price: float, arhti_pct: float | None) -> float:
    """What the farmer receives per 40 kg after their own commission. No commission unless they entered one."""
    return price * (1 - (arhti_pct or 0) / 100)


def confidence(current_price: float, q10: float | None, q90: float | None, is_stale: bool = False) -> str:
    """HIGH / MEDIUM / LOW from the width of the forecast range. Stale prices are always LOW (hand-off H-B5)."""
    if is_stale or q10 is None or q90 is None:
        return "LOW"
    width_pct = (q90 - q10) / current_price * 100
    if width_pct <= config.HIGH_CONFIDENCE_MAX_WIDTH_PCT:
        return "HIGH"
    if width_pct <= config.MEDIUM_CONFIDENCE_MAX_WIDTH_PCT:
        return "MEDIUM"
    return "LOW"


def fair_price_range(current_price: float, predicted_price: float) -> dict:
    """The range a farmer should accept today: from today's mandi price up to the expected price in 4 weeks.

    An offer below today's AMIS mandi price is below the market. An offer above the expected price beats
    waiting. When the forecast is flat or falling, the range is just today's price.
    """
    _check_price("current_price", current_price)
    _check_price("predicted_price", predicted_price)
    return {"low": round(current_price, 2), "high": round(max(current_price, predicted_price), 2)}


def advise(
    current_price: float,
    predicted_price: float,
    q10: float | None,
    q90: float | None,
    quantity_maund: float,
    interest_pct_per_year: float,
    arhti_pct: float | None = None,
    is_stale: bool = False,
    horizon_weeks: int = config.HORIZON_WEEKS,
) -> dict:
    """SELL or WAIT for one crop at one mandi, with the net rupee impact of waiting (UC-03).

    gross_gain    = quantity x (forecast - today), both after the farmer's arhti commission if entered
    interest_cost = quantity x today's price (after commission) x yearly rate x weeks / 52
    rupee_impact  = gross_gain - interest_cost
    """
    _check_price("current_price", current_price)
    _check_price("predicted_price", predicted_price)
    if quantity_maund <= 0:
        raise ValueError(f"quantity_maund must be positive, got {quantity_maund!r}")

    change_pct = (predicted_price - current_price) / current_price * 100
    signal = "WAIT" if change_pct >= config.WAIT_THRESHOLD_PCT else "SELL"

    now, later = _after_arhti(current_price, arhti_pct), _after_arhti(predicted_price, arhti_pct)
    gross_gain = quantity_maund * (later - now)
    interest_cost = quantity_maund * now * interest_pct_per_year / 100 * horizon_weeks / WEEKS_PER_YEAR

    return {
        "signal": signal,
        "confidence": confidence(current_price, q10, q90, is_stale),
        "change_pct": round(change_pct, 2),
        "current_price": round(current_price, 2),
        "expected_price": round(predicted_price, 2),
        "quantity_maund": quantity_maund,
        "arhti_pct": arhti_pct,
        "gross_gain": round(gross_gain),
        "interest_cost": round(interest_cost),
        "rupee_impact": round(gross_gain - interest_cost),
        "horizon_weeks": horizon_weeks,
        "fair_price_range": fair_price_range(current_price, predicted_price),
    }


def offer_check(offer_price: float, fair_low: float, fair_high: float, quantity_maund: float | None = None) -> dict:
    """Compare a buyer's offer with the fair range (UC-07). BELOW, FAIR or ABOVE, with the gap in rupees."""
    _check_price("offer_price", offer_price)
    if offer_price < fair_low:
        status, gap = "BELOW", offer_price - fair_low
    elif offer_price > fair_high:
        status, gap = "ABOVE", offer_price - fair_high
    else:
        status, gap = "FAIR", 0.0
    return {
        "status": status,
        "offer_price": round(offer_price, 2),
        "fair_price_range": {"low": round(fair_low, 2), "high": round(fair_high, 2)},
        "gap_per_40kg": round(gap, 2),
        "gap_total": round(gap * quantity_maund) if quantity_maund else None,
    }


def margin(
    price: float,
    production_cost_per_40kg: float,
    arhti_pct: float | None = None,
    support_price: float | None = None,
    support_status: str | None = None,
) -> dict:
    """Split a price into production cost, the farmer's own arhti commission and profit (UC-08).

    The support price is a reference line only (wheat). `support_status` is passed through so the UI can
    say "announced, not procured" (hand-off H-B4).
    """
    _check_price("price", price)
    commission = price * (arhti_pct or 0) / 100
    profit = price - commission - production_cost_per_40kg
    return {
        "price": round(price, 2),
        "production_cost": round(production_cost_per_40kg, 2),
        "arhti_commission": round(commission, 2) if arhti_pct else None,
        "profit": round(profit, 2),
        "profit_pct": round(profit / price * 100, 1),
        "support_price": support_price,
        "support_status": support_status,
    }


def compare_mandis(
    mandis: Iterable[Mapping],
    preferred_mandi: str | None = None,
    quantity_maund: float | None = None,
) -> dict:
    """Rank mandis by net price today after transport (UC-04).

    Each item has `mandi`, `current_price` (None when the mandi has no price for this crop) and
    `transport_cost` (Rs per 40 kg from the farmer's district; None when the district is unknown).
    If any transport cost is missing, every mandi is ranked by gross price and `transport_included` is False.
    Mandis without a price come last, marked `has_price: False`.
    """
    items = list(mandis)
    priced = [m for m in items if m.get("current_price") is not None]
    transport_included = bool(priced) and all(m.get("transport_cost") is not None for m in priced)

    rows = []
    for m in priced:
        transport = m["transport_cost"] if transport_included else None
        net = m["current_price"] - (transport or 0)
        rows.append({"mandi": m["mandi"], "has_price": True, "current_price": round(m["current_price"], 2),
                     "transport_cost": transport, "net_price": round(net, 2)})
    rows.sort(key=lambda r: r["net_price"], reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    rows += [{"mandi": m["mandi"], "has_price": False, "current_price": None, "transport_cost": None,
              "net_price": None, "rank": None} for m in items if m.get("current_price") is None]

    best = rows[0] if priced else None
    preferred = next((r for r in rows if r["mandi"] == preferred_mandi and r["has_price"]), None)
    gain_per_40kg = round(best["net_price"] - preferred["net_price"], 2) if best and preferred else None
    return {
        "mandis": rows,
        "best_mandi": best["mandi"] if best else None,
        "transport_included": transport_included,
        "gain_over_preferred_per_40kg": gain_per_40kg,
        "gain_over_preferred_total": (
            round(gain_per_40kg * quantity_maund) if gain_per_40kg is not None and quantity_maund else None
        ),
    }
