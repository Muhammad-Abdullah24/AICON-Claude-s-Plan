"""The wait engine (task B1, docs/PIVOT.md section 3.3): "can you afford to wait, and with whose money?"

Pure Python, no I/O. It takes already-computed inputs — the best net price today, the hold backtest
(`ml/backtest/hold.py`), the farmer's cash need, their money and their store — and decides how much to sell now and
how much, if any, to hold. The service layer (`backend/app/services.py`) gathers the inputs and adds the data label.

Rules (docs/PIVOT.md B1):
- Sell now = ceil(cash need / best net price), capped at the quantity.
- Hold the rest **only for wheat**, and only if holding paid in at least 60% of past seasons AND the median season
  gained at least 1% of today's price, for this farmer's money and storage (E1). Otherwise sell everything.
- The decision never comes from a forecast or a news item (rule 8); news and policy only add warnings and lower
  confidence.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from ml.decision import config


def wait_plan(
    *,
    quantity_maund: float,
    cash_need_rs: float,
    best_mandi: str,
    best_net_price: float,
    hold: Mapping | None,
    is_wheat: bool,
    wait_months: int,
    money: str,
    annual_rate_pct: float,
    storage: str,
    loss_pct: float,
    offer: float | None = None,
    is_stale: bool = False,
    news_conflict: bool = False,
    policy_recent: bool = False,
) -> dict:
    """The WaitPlanResponse fields the engine owns (the service adds the label, prices_as_of, is_stale, news_check,
    and the crop/mandi ids). `hold` is the `hold_history` dict, or None when it is not worked out."""
    warnings: list[str] = []
    if is_stale:
        warnings.append("STALE_PRICE")
    if cash_need_rs > best_net_price * quantity_maund:
        warnings.append("CASH_NEED_EXCEEDS_CROP")   # selling everything today still does not cover the cash need
    if not is_wheat:
        warnings.append("HOLD_WHEAT_ONLY")
    elif hold is None:
        warnings.append("TOO_FEW_SEASONS")

    holding_offered = is_wheat and hold is not None
    holding_pays = (holding_offered
                    and hold["wins"] / hold["n"] >= config.HOLD_MIN_WIN_RATE
                    and hold["median_net_per_maund"] >= best_net_price * config.HOLD_MIN_MEDIAN_PCT / 100)

    need_maund = min(quantity_maund, math.ceil(cash_need_rs / best_net_price)) if cash_need_rs > 0 else 0
    sell_now = float(need_maund) if holding_pays else float(quantity_maund)
    hold_maund = round(quantity_maund - sell_now, 2)
    verdict = "SPLIT" if 0 < sell_now < quantity_maund else ("HOLD_ALL" if sell_now == 0 else "SELL_ALL")

    exits = [{"kind": "SELL_NOW", "mandi": best_mandi, "per_maund": round(best_net_price, 2),
              "total_rs": round(best_net_price * quantity_maund)}]
    if offer is not None:
        exits.append({"kind": "ARHTI_OFFER", "mandi": None, "per_maund": round(offer, 2),
                      "total_rs": round(offer * quantity_maund)})
    if holding_offered:
        median, worst = hold["median_net_per_maund"], hold["worst_p10_net_per_maund"]
        cost = best_net_price * quantity_maund * (annual_rate_pct / 100 * wait_months / 12 + loss_pct / 100)
        exits.append({"kind": "HOLD", "mandi": None, "per_maund": round(best_net_price + median, 2),
                      "total_rs": round((best_net_price + median) * quantity_maund),
                      "worst_total_rs": round((best_net_price + worst) * quantity_maund), "cost_rs": round(cost)})

    if news_conflict:
        warnings.append("NEWS_PRICE_CONFLICT")
    if policy_recent:
        warnings.append("POLICY_UNCERTAIN")

    confidence = "LOW" if (is_stale or not holding_offered) else "MEDIUM"
    if news_conflict or policy_recent:
        confidence = {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "LOW"}[confidence]

    return {
        "unit": "40kg", "quantity_maund": quantity_maund, "cash_need_rs": cash_need_rs, "wait_months": wait_months,
        "money": money, "annual_rate_pct": annual_rate_pct, "storage": storage, "loss_pct": loss_pct,
        "verdict": verdict, "sell_now_maund": sell_now, "hold_maund": hold_maund, "exits": exits,
        "history": dict(hold) if holding_offered else None, "confidence": confidence, "warnings": warnings,
    }
