"""Decision engine: forecast band + the farmer's costs -> verdict (PLAN.md section 10).

Pure Python with no third-party imports. The backend imports it to answer
/api/advice and ml/precompute.py imports it to build replay steps, so the web
app, WhatsApp and the replay all use the same logic.

The engine returns numbers and reason codes only. Turning them into Urdu or
English sentences is the backend's job (backend/app/phrasing.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ml.decision import config

Verdict = Literal["sell_now", "sell_elsewhere", "store", "split"]


@dataclass(frozen=True)
class BandPoint:
    weeks_ahead: int
    q10: float
    q50: float
    q90: float


@dataclass(frozen=True)
class Costs:
    storage_cost_per_maund_week: float  # Rs per maund per week
    spoilage_pct_week: float  # percent of the crop lost per week, e.g. 0.5
    finance_cost_pct_month: float  # percent of the crop's value per month


@dataclass(frozen=True)
class OtherMandi:
    mandi: str
    price_now: float
    transport_cost_per_maund: float

    @property
    def net_price(self) -> float:
        return self.price_now - self.transport_cost_per_maund


@dataclass(frozen=True)
class DecisionInput:
    price_now: float
    band: list[BandPoint]
    can_store: bool
    costs: Costs
    other_mandis: list[OtherMandi] = field(default_factory=list)
    alert_active: bool = False


@dataclass(frozen=True)
class Reason:
    code: str
    params: dict[str, float | int | str] = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    gain_per_maund: float  # extra Rs per maund compared with selling here today
    best_week: int  # 0 unless the verdict involves storing
    lowest_price: float  # the lowest q10 in the band: the risk line
    lowest_price_week: int
    best_other: OtherMandi | None
    reasons: list[Reason]


def value_of_waiting(price: float, weeks: int, price_now: float, costs: Costs) -> float:
    """Rs per maund the farmer ends up with by selling `weeks` from now at `price` (10.2)."""
    kept = 1 - costs.spoilage_pct_week / 100 * weeks
    storage = costs.storage_cost_per_maund_week * weeks
    finance = price_now * costs.finance_cost_pct_month / 100 / config.WEEKS_PER_MONTH * weeks
    return price * kept - storage - finance


def decide(inp: DecisionInput) -> Decision:
    if inp.price_now <= 0:
        raise ValueError("price_now must be positive")
    if not inp.band:
        raise ValueError("band must have at least one horizon")

    p = inp.price_now
    clear = config.MIN_CLEAR_GAIN_FRACTION * p
    band = sorted(inp.band, key=lambda b: b.weeks_ahead)

    gains = {b.weeks_ahead: value_of_waiting(b.q50, b.weeks_ahead, p, inp.costs) - p for b in band}
    best = max(band, key=lambda b: gains[b.weeks_ahead])
    store_gain = gains[best.weeks_ahead]
    downside = value_of_waiting(best.q10, best.weeks_ahead, p, inp.costs) - p
    band_width = (best.q90 - best.q10) / best.q50

    lowest = min(band, key=lambda b: b.q10)
    best_other = max(inp.other_mandis, key=lambda m: m.net_price, default=None)
    elsewhere_gain = best_other.net_price - p if best_other else float("-inf")

    store_ok = inp.can_store and store_gain >= clear
    elsewhere_ok = elsewhere_gain >= clear

    reasons: list[Reason] = []
    last = band[-1]
    trend = (last.q50 - p) / p
    if trend >= config.MIN_CLEAR_GAIN_FRACTION:
        reasons.append(Reason("trend_up", {"weeks": last.weeks_ahead, "pct": round(trend * 100, 1)}))
    elif trend <= -config.MIN_CLEAR_GAIN_FRACTION:
        reasons.append(Reason("trend_down", {"weeks": last.weeks_ahead, "pct": round(-trend * 100, 1)}))
    else:
        reasons.append(Reason("trend_flat", {"weeks": last.weeks_ahead}))

    if elsewhere_ok and (not store_ok or elsewhere_gain >= store_gain):
        verdict: Verdict = "sell_elsewhere"
        gain = elsewhere_gain
        best_week = 0
        reasons.insert(0, Reason("elsewhere_better", {
            "mandi": best_other.mandi, "net_price": round(best_other.net_price), "gain": round(gain),
        }))
    elif store_ok and downside < -config.MAX_DOWNSIDE_FRACTION * p:
        verdict, gain, best_week = "sell_now", 0.0, 0
        reasons.append(Reason("downside_large", {"weeks": best.weeks_ahead, "low": round(best.q10)}))
    elif store_ok:
        wide = band_width > config.WIDE_BAND_FRACTION
        best_week = best.weeks_ahead
        if wide or inp.alert_active:
            verdict = "split"
            gain = store_gain * config.SPLIT_STORE_SHARE
        else:
            verdict = "store"
            gain = store_gain
        reasons.insert(0, Reason("wait_gain", {"weeks": best_week, "gain": round(store_gain)}))
        if wide:
            reasons.append(Reason("band_wide", {
                "weeks": best_week, "low": round(best.q10), "high": round(best.q90),
            }))
    else:
        verdict, gain, best_week = "sell_now", 0.0, 0
        if inp.can_store:
            reasons.append(Reason("no_clear_gain"))
        else:
            reasons.insert(0, Reason("cannot_store"))

    if inp.alert_active:
        reasons.append(Reason("alert_active"))

    return Decision(
        verdict=verdict,
        gain_per_maund=gain,
        best_week=best_week,
        lowest_price=lowest.q10,
        lowest_price_week=lowest.weeks_ahead,
        best_other=best_other,
        reasons=reasons,
    )
