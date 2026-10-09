"""Interface I3 (Owner B): the advisory engine from the blueprint (UC-03, UC-04, UC-07, UC-08).

Pure Python with no third-party imports. Every price is Rs per 40 kg and every quantity is in maund (40 kg),
so quantity x price is rupees. The functions take plain numbers; `ml/decision/inputs.py` reads the ones
that come from the runtime tables (interest rate, costs, transport, support prices, staleness).

The engine returns numbers and codes only. Turning them into Urdu or English is the caller's job.
alert_check() (B8) is added in a later task.
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


# ---------------------------------------------------------------- What to Grow (UC-05, UC-06; task B7)

def risk_badge(spread_pct: float, enough_years: bool) -> str:
    """LOW / MEDIUM / HIGH from the year-to-year spread of the harvest ratio. Too little history is HIGH."""
    if not enough_years:
        return "HIGH"
    if spread_pct <= config.LOW_RISK_MAX_SPREAD_PCT:
        return "LOW"
    if spread_pct <= config.MEDIUM_RISK_MAX_SPREAD_PCT:
        return "MEDIUM"
    return "HIGH"


def crop_plan(crops: Iterable[Mapping], land_area_acres: float) -> dict:
    """Rank crop options by expected profit at the next harvest (UC-05). Labelled "estimate" throughout.

    Each item (see ml.decision.inputs.crop_plan_inputs) has `crop_option`, `latest_price` (Rs per 40 kg),
    `harvest_ratio` ({ratio_median, ratio_min, ratio_max, spread_pct, enough_years, months_ahead} or None),
    `cost_per_acre`, `yield_maund_per_acre` and `milling_yield` (rice: paddy to milled rice; else None).
    `prices_as_of` and `is_stale` pass through, so the screen can show old prices in amber.

    harvest price estimate = latest price x median ratio (range: x min and x max ratio, across years)
    profit per acre        = harvest price x sale maund per acre - cost per acre
    Crop options without a price or ratio are listed last with `has_data: False`.
    """
    if land_area_acres <= 0:
        raise ValueError(f"land_area_acres must be positive, got {land_area_acres!r}")
    ranked, missing = [], []
    for c in crops:
        ratio, price = c.get("harvest_ratio"), c.get("latest_price")
        if not ratio or not price:
            missing.append({"crop_option": c["crop_option"], "has_data": False, "rank": None})
            continue
        sale_maund = c["yield_maund_per_acre"] * (c.get("milling_yield") or 1)

        def profit(r: float, price=price, sale_maund=sale_maund, cost=c["cost_per_acre"]) -> float:
            return price * r * sale_maund - cost

        ranked.append({
            "crop_option": c["crop_option"],
            "has_data": True,
            "harvest_price_estimate": round(price * ratio["ratio_median"], 2),
            "harvest_price_range": {"low": round(price * ratio["ratio_min"], 2),
                                    "high": round(price * ratio["ratio_max"], 2)},
            "months_ahead": ratio.get("months_ahead"),
            "sale_maund_per_acre": round(sale_maund, 2),
            "profit_per_acre": round(profit(ratio["ratio_median"])),
            "profit_per_acre_range": {"low": round(profit(ratio["ratio_min"])),
                                      "high": round(profit(ratio["ratio_max"]))},
            "profit_total": round(profit(ratio["ratio_median"]) * land_area_acres),
            "risk": risk_badge(ratio["spread_pct"], ratio["enough_years"]),
            "years_of_history": ratio.get("n_years"),
            "prices_as_of": c.get("prices_as_of"),
            "is_stale": bool(c.get("is_stale")),
            "is_estimate": True,
        })
    ranked.sort(key=lambda r: r["profit_per_acre"], reverse=True)
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    return {"land_area_acres": land_area_acres, "crops": ranked + missing,
            "best_crop": ranked[0]["crop_option"] if ranked else None}


def selling_window(post_harvest: Iterable[Mapping], interest_pct_per_year: float) -> dict | None:
    """Best months to sell after harvest, net of the interest cost of holding (UC-06).

    Each item has `offset_months` (k months after harvest starts), `month` and `ratio_median` (price then /
    price at harvest start). Net value of waiting k months, as % of the harvest-start price:
        net_pct = (ratio_median - 1) x 100 - interest per month x k
    The window is the best month plus its neighbours within SELLING_WINDOW_TOLERANCE_PCT of it.
    Returns None without data.
    """
    rows = sorted(post_harvest, key=lambda r: r["offset_months"])
    if not rows:
        return None
    monthly_interest = interest_pct_per_year / 12
    months = [{
        "month": r["month"],
        "offset_months": r["offset_months"],
        "price_change_pct": round((r["ratio_median"] - 1) * 100, 2),
        "interest_pct": round(monthly_interest * r["offset_months"], 2),
        "net_pct": round((r["ratio_median"] - 1) * 100 - monthly_interest * r["offset_months"], 2),
    } for r in rows]
    best = max(range(len(months)), key=lambda i: months[i]["net_pct"])
    lo = hi = best
    while lo > 0 and months[best]["net_pct"] - months[lo - 1]["net_pct"] <= config.SELLING_WINDOW_TOLERANCE_PCT:
        lo -= 1
    while (hi < len(months) - 1
           and months[best]["net_pct"] - months[hi + 1]["net_pct"] <= config.SELLING_WINDOW_TOLERANCE_PCT):
        hi += 1
    return {
        "best_month": months[best]["month"],
        "best_net_pct": months[best]["net_pct"],
        "window_months": [m["month"] for m in months[lo:hi + 1]],
        "sell_at_harvest": months[best]["offset_months"] == 0,
        "months": months,
        "is_estimate": True,
    }
