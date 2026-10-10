"""The loan planner engine (task L1, docs/PIVOT.md section 3.4): what does the crop really need, and the cheapest
money to cover it.

Pure Python, no I/O. The API (`backend/app/services.py`) reads the input costs and the loan options, keeps only the
options this farmer is eligible for, caps each one (e.g. Kissan Card = min(30,000 x acres, 150,000)), and passes
plain numbers in. This module only does the arithmetic:

- need = sum of the cash inputs per acre x acres; borrow needed = need minus savings (never below zero).
- The ladder fills the borrow needed from the cheapest option up, each up to its cap. Equal rates keep the order
  they came in, so the API decides ties.
- Interest on each slice = amount x rate x months to harvest / 12. Everything falls due at harvest, which is the
  small farmer's real problem: the whole loan is due when prices are at their low.
- If the farmer says what they planned to borrow (and at what rate), the plan shows how much more that is than the
  crop needs and what it costs over the ladder.

Rupee amounts are whole rupees. Two safety rules (PR #8 review):
- **A cost is never shown as a negative cost.** `net_impact_rs` is planned interest minus ladder interest (positive =
  the plan costs more). When it is positive it is `extra_cost_rs`; when negative, `saving_rs` (the planned loan costs
  less, usually because it is smaller than the crop needs); the other is 0.
- **A missing rate is never taken as 0%.** A planned loan without a rate gives `plan_comparison:
  "INSUFFICIENT_INFORMATION"` and no cost figures; an option without a rate is left out of the ladder (listed in
  `unpriced_options`). Both are named in `missing_inputs`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def _interest(amount: float, annual_rate_pct: float, months: float) -> int:
    return round(amount * annual_rate_pct / 100 * months / 12)


def loan_plan(acres: float, input_items: Sequence[Mapping], savings_rs: float, options: Sequence[Mapping],
              months_to_harvest: int, planned_borrow_rs: float | None = None,
              planned_rate_pct: float | None = None) -> dict:
    """The LoanPlanResponse fields the engine owns (the API adds the items' names, the options' details, the months
    and the warnings).

    `input_items`: [{"item", "rs_per_acre"}, ...] for this crop. `options`: the eligible loan options, each
    {"id", "annual_rate_pct", "max_rs"}, already capped for this farmer; `max_rs` None means no limit (bank, arhti).
    `planned_borrow_rs` / `planned_rate_pct`: what the farmer meant to borrow and that lender's rate. Without the
    rate the plan still shows the over-borrowing, but the cost comparison is INSUFFICIENT_INFORMATION, never 0%.
    """
    if acres < 0 or savings_rs < 0 or months_to_harvest < 0:
        raise ValueError("acres, savings_rs and months_to_harvest must not be negative")
    if planned_borrow_rs is not None and planned_borrow_rs < 0:
        raise ValueError("planned_borrow_rs must not be negative")

    need = round(sum(i["rs_per_acre"] for i in input_items) * acres)
    borrow_needed = max(0, need - round(savings_rs))

    # An option without a rate can't be priced, so it is never assumed free: it is left out and reported.
    priced = [o for o in options if o.get("annual_rate_pct") is not None]
    unpriced = [o["id"] for o in options if o.get("annual_rate_pct") is None]
    for o in priced:
        if o["annual_rate_pct"] < 0:
            raise ValueError(f"negative rate for {o['id']!r}")

    ladder: list[dict] = []
    left = borrow_needed
    # sorted() is stable, so options with the same rate stay in the order the API gave them.
    for o in sorted(priced, key=lambda o: o["annual_rate_pct"]):
        if left <= 0:
            break
        cap = o.get("max_rs")
        amount = left if cap is None else min(left, round(cap))
        if amount <= 0:
            continue
        ladder.append({"id": o["id"], "amount_rs": amount,
                       "interest_rs": _interest(amount, o["annual_rate_pct"], months_to_harvest)})
        left -= amount

    borrowed = sum(s["amount_rs"] for s in ladder)
    ladder_interest = sum(s["interest_rs"] for s in ladder)

    missing = [f"annual_rate_pct:{i}" for i in unpriced]
    planned_interest = over_borrow = net_impact = extra_cost = saving = None
    comparison = "NOT_REQUESTED"
    if planned_borrow_rs is not None:
        over_borrow = max(0, round(planned_borrow_rs) - borrow_needed)
        if planned_rate_pct is None:
            comparison = "INSUFFICIENT_INFORMATION"
            missing.append("planned_rate_pct")
        else:
            if planned_rate_pct < 0:
                raise ValueError("planned_rate_pct must not be negative")
            comparison = "COMPARED"
            planned_interest = _interest(planned_borrow_rs, planned_rate_pct, months_to_harvest)
            net_impact = planned_interest - ladder_interest
            extra_cost, saving = max(0, net_impact), max(0, -net_impact)

    return {
        "input_need_rs": need,
        "savings_rs": round(savings_rs),
        "borrow_needed_rs": borrow_needed,
        "ladder": ladder,
        "ladder_interest_rs": ladder_interest,
        "harvest_due_rs": borrowed + ladder_interest,
        "planned_borrow_rs": None if planned_borrow_rs is None else round(planned_borrow_rs),
        "planned_interest_rs": planned_interest,
        "over_borrow_rs": over_borrow,
        "plan_comparison": comparison,      # NOT_REQUESTED | COMPARED | INSUFFICIENT_INFORMATION
        "net_impact_rs": net_impact,        # planned interest - ladder interest; None unless COMPARED
        "extra_cost_rs": extra_cost,        # max(0, net_impact): the plan costs more
        "saving_rs": saving,                # max(0, -net_impact): the plan costs less; never a negative cost
        "uncovered_rs": borrow_needed - borrowed,
        "unpriced_options": unpriced,       # options left out of the ladder because they have no rate
        "missing_inputs": missing,          # what would be needed for a complete answer; empty = complete
    }
