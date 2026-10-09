"""Interface I3 (Owner B): the advisory engine. See docs/PLAN.md section 4."""

from ml.decision.advisory import advise, compare_mandis, confidence, fair_price_range, margin, offer_check

__all__ = ["advise", "compare_mandis", "confidence", "fair_price_range", "margin", "offer_check"]
