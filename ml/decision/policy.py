"""The selling action plan: a recommendation kept separate from the market signal.

Pure Python, no third-party imports. Prices are Rs per 40 kg, quantities in maund (40 kg).

FarmSight's recommendation is SELL_NOW unless the evidence shows that holding pays. It does not: when the wheat
model says UP, holding four weeks beat the interest cost in only 42-46% of out-of-sample weeks, with a negative
median (artifacts/models/policy_eval.json, docs/MODEL_CARD.md). So:

- recommended_action is SELL_NOW. HOLD_AND_MONITOR exists but stays off until the hold gate passes: holding must
  have beaten the carrying cost in at least config.HOLD_GATE_MIN_BEAT_CARRY_PCT of out-of-sample weeks.
- For fresh wheat data, storage available and an UP signal, an `upside_watch` is added. It shows the signal, the
  break-even price and the evidence, and offers monitoring the farmer can switch on. It never suggests a quantity.
- If the farmer chooses to keep some crop (`retained_quantity`), the plan shows the triggers for that amount. It
  is the farmer's choice, recorded as such; the recommendation stays SELL_NOW.
- Monitoring alerts are only for farmers who switched them on, and only on transparent price triggers
  (break-even reached, the range's low reached), never on the direction call alone.

The experience has three modes: SELL_NOW, SELL_NOW_UPSIDE_WATCH, FARMER_RETAINED_MONITORING.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta

from ml.decision import config

WEEKS_PER_YEAR = 52
ACTIONS = ("SELL_NOW", "HOLD_AND_MONITOR")
MODES = ("SELL_NOW", "SELL_NOW_UPSIDE_WATCH", "FARMER_RETAINED_MONITORING")

# What FarmSight cannot know; the screen lists these next to every plan.
CANNOT_KNOW = (
    "SIZE_OF_PRICE_MOVE",       # the direction model has no reliable size or probability
    "OPEN_MARKET_RATE",         # AMIS can lag the open market
    "FARMER_CASH_AND_STORAGE",  # unless the farmer tells us
    "STORAGE_LOSS_AND_COST",    # only interest is counted; spoilage and godown fees are not
)


def break_even_price(current_price: float, interest_pct_per_year: float, horizon_weeks: int) -> float:
    """Price needed after `horizon_weeks` for holding to beat selling now, after interest.

    The farmer's own arhti commission applies to both prices, so it cancels out:
    later x (1 - a) - now x (1 - a) > now x (1 - a) x rate x weeks / 52  <=>  later > now x (1 + rate x weeks / 52).
    """
    return current_price * (1 + interest_pct_per_year / 100 * horizon_weeks / WEEKS_PER_YEAR)


def hold_gate(evidence: Mapping | None) -> dict:
    """Whether HOLD_AND_MONITOR may be recommended, from out-of-sample evidence. Off without evidence."""
    required = config.HOLD_GATE_MIN_BEAT_CARRY_PCT
    observed = evidence.get("beat_carry_pct_min") if evidence else None
    enabled = observed is not None and observed >= required
    return {
        "enabled": enabled,
        "required_beat_carry_pct": required,
        "observed_beat_carry_pct": observed,
        "reason": "GATE_PASSED" if enabled else ("NO_EVIDENCE" if observed is None else "HOLD_GATE_NOT_MET"),
        "source": evidence.get("source") if evidence else None,
    }


def action_plan(
    crop_option: str,
    quantity_maund: float,
    current_price: float,
    q10: float | None,
    direction: Mapping | None,
    is_stale: bool,
    is_frozen: bool,
    interest_pct_per_year: float,
    prices_as_of: date,
    hold_evidence: Mapping | None = None,
    urgent_cash_need: bool = False,
    storage_available: bool = False,
    retained_quantity: float | None = None,
    monitoring_on: bool = False,
    constraints_source: str = "default",
    horizon_weeks: int = config.HORIZON_WEEKS,
) -> dict:
    """The selling plan for one crop at one mandi. See the module docstring for the rules."""
    if quantity_maund <= 0:
        raise ValueError(f"quantity_maund must be positive, got {quantity_maund!r}")
    if current_price <= 0:
        raise ValueError(f"current_price must be positive, got {current_price!r}")
    if retained_quantity is not None and not 0 <= retained_quantity <= quantity_maund:
        raise ValueError(f"retained_quantity must be between 0 and {quantity_maund}, got {retained_quantity!r}")

    gate = hold_gate(hold_evidence)
    breakeven = break_even_price(current_price, interest_pct_per_year, horizon_weeks)
    carry_per_40kg = breakeven - current_price
    call = (direction or {}).get("call")

    # Why SELL_NOW, most important first. Holding is never recommended on stale or frozen prices.
    reasons = []
    if is_stale:
        reasons.append("STALE_DATA")
    if is_frozen:
        reasons.append("FROZEN_PRICE")
    if urgent_cash_need:
        reasons.append("URGENT_CASH")
    if not storage_available:
        reasons.append("NO_STORAGE")
    if call is None:
        reasons.append("NO_DIRECTION_SIGNAL")
    elif call == "DOWN":
        reasons.append("DIRECTION_DOWN")
    else:
        reasons.append("DIRECTION_UP_SIZE_UNRELIABLE")
    if not gate["enabled"]:
        reasons.append(gate["reason"])

    blocked = is_stale or is_frozen or urgent_cash_need or not storage_available
    recommend_hold = gate["enabled"] and call == "UP" and not blocked
    action = "HOLD_AND_MONITOR" if recommend_hold else "SELL_NOW"

    review_by = prices_as_of + timedelta(weeks=horizon_weeks)
    triggers = [{"type": "AT_OR_ABOVE", "price": round(breakeven, 2), "meaning": "BREAK_EVEN_REACHED"}]
    if q10 is not None:
        triggers.append({"type": "AT_OR_BELOW", "price": round(q10, 2), "meaning": "RANGE_LOW_REACHED"})
    triggers.append({"type": "REVIEW_BY", "date": review_by.isoformat(), "meaning": "HORIZON_ENDS"})

    watch = None
    if call == "UP" and storage_available and not (is_stale or is_frozen):
        watch = {
            "market_signal": "UP",
            "validation_accuracy_pct": (direction or {}).get("validation_accuracy_pct"),
            "evidence": "SIGNAL_DOES_NOT_SHOW_WAITING_PAYS" if not gate["enabled"] else "HOLD_GATE_PASSED",
            "break_even_price": round(breakeven, 2),
            "triggers": triggers,
            "monitoring_on": monitoring_on,
        }

    retained = retained_quantity or 0.0
    if retained > 0:
        mode = "FARMER_RETAINED_MONITORING"
    elif watch is not None:
        mode = "SELL_NOW_UPSIDE_WATCH"
    else:
        mode = "SELL_NOW"

    warnings = []
    if retained > 0 and (is_stale or is_frozen):
        warnings.append("TRIGGERS_UNRELIABLE_STALE_PRICE")
    if retained > 0 and urgent_cash_need:
        warnings.append("RETAINING_DESPITE_URGENT_CASH")

    return {
        "crop_option": crop_option,
        "recommended_action": action,
        "mode": mode,
        "reason_codes": reasons,
        "warnings": warnings,
        "quantity_maund": quantity_maund,
        "sell_now_quantity": quantity_maund - retained,  # sums exactly with retained_quantity
        "retained_quantity": retained,
        "retained_by_farmer_choice": retained > 0,
        "horizon_weeks": horizon_weeks,
        "current_price": round(current_price, 2),
        "break_even_price": round(breakeven, 2),
        "carrying_cost_per_40kg": round(carry_per_40kg, 2),
        "carrying_cost_on_retained": round(carry_per_40kg * retained),
        "triggers": triggers if retained > 0 else [],
        "monitoring_on": monitoring_on and (retained > 0 or watch is not None),
        "upside_watch": watch,
        "hold_gate": gate,
        "constraints": {"urgent_cash_need": urgent_cash_need, "storage_available": storage_available,
                        "source": constraints_source},
        "cannot_know": list(CANNOT_KNOW),
    }
