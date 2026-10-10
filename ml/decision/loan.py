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

Rupee amounts are whole rupees. A negative `extra_cost_rs` means the planned loan is cheaper than the ladder (it is
smaller than what the crop needs); the engine reports it as is and the screens decide how to word it.
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
    `planned_borrow_rs` / `planned_rate_pct`: what the farmer meant to borrow and that lender's rate; leave the rate
    out and the plan still shows the over-borrowing but no cost comparison.
    """
    if acres < 0 or savings_rs < 0 or months_to_harvest < 0:
        raise ValueError("acres, savings_rs and months_to_harvest must not be negative")
    if planned_borrow_rs is not None and planned_borrow_rs < 0:
        raise ValueError("planned_borrow_rs must not be negative")

    need = round(sum(i["rs_per_acre"] for i in input_items) * acres)
    borrow_needed = max(0, need - round(savings_rs))

    ladder: list[dict] = []
    left = borrow_needed
    # sorted() is stable, so options with the same rate stay in the order the API gave them.
    for o in sorted(options, key=lambda o: o["annual_rate_pct"]):
        if left <= 0:
            break
        if o["annual_rate_pct"] < 0:
            raise ValueError(f"negative rate for {o['id']!r}")
        cap = o.get("max_rs")
        amount = left if cap is None else min(left, round(cap))
        if amount <= 0:
            continue
        ladder.append({"id": o["id"], "amount_rs": amount,
                       "interest_rs": _interest(amount, o["annual_rate_pct"], months_to_harvest)})
        left -= amount

    borrowed = sum(s["amount_rs"] for s in ladder)
    ladder_interest = sum(s["interest_rs"] for s in ladder)

    planned_interest = over_borrow = extra_cost = None
    if planned_borrow_rs is not None:
        over_borrow = max(0, round(planned_borrow_rs) - borrow_needed)
        if planned_rate_pct is not None:
            planned_interest = _interest(planned_borrow_rs, planned_rate_pct, months_to_harvest)
            extra_cost = planned_interest - ladder_interest

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
        "extra_cost_rs": extra_cost,
        "uncovered_rs": borrow_needed - borrowed,
    }
