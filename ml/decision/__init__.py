"""Interface I3 (Owner B): the advisory engine. See docs/PLAN.md section 4."""

from ml.decision.advisory import (
    advise,
    alert_check,
    compare_mandis,
    confidence,
    crop_plan,
    fair_price_range,
    margin,
    offer_check,
    risk_badge,
    selling_window,
)

__all__ = [
    "advise", "alert_check", "compare_mandis", "confidence", "crop_plan", "fair_price_range", "margin", "offer_check",
    "risk_badge", "selling_window",
]
