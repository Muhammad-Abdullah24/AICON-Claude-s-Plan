"""Service layer (interface I6): the one place every channel gets its answers from (web, WhatsApp, chat).

Real AMIS prices, dates, transport costs and interest come from data/processed/. The 4-week forecast uses
Owner B's `ml.forecast.predict.forecast` when it exists; until then it is the labelled baseline the evaluation
gate validated (A5): the price stays the same, with the range of 4-week changes seen in training (it held the
real price 81% of the time on 2025 data). The SELL/WAIT rule is the blueprint's (5%, interest subtracted).

Written by Hamza while covering Owner C (docs/PLAN.md section 2). Prices are Rs per 40 kg.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import date
from functools import lru_cache
from pathlib import Path

from ml.features import config as fcfg

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
RUNTIME = PROCESSED / "runtime"

WAIT_THRESHOLD_PCT = 5            # blueprint UC-03: WAIT if the 4-week forecast is at least 5% above today
TREND_FLAT_PCT = 3
HORIZON_WEEKS = 4
BASELINE_MODEL = "baseline_persistence_band"
OPTION_TO_AMIS = {v: k for k, v in fcfg.CROP_OPTION.items()}   # "IRRI" -> ("Rice", "IRRI")
DISPLAY = {"BahawalPur": "Bahawalpur", "Vehari": "Vehari", "RahimYarKhan": "Rahim Yar Khan"}


# ---------------------------------------------------------------- data (read once)

def _csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def _data() -> dict:
    daily: dict[str, list[tuple[str, float]]] = {}
    for r in _csv(PROCESSED / "farmsight_prices_clean_daily.csv"):
        daily.setdefault(f"{r['city']}|{r['crop']}|{r['variety']}", []).append(
            (r["date"], float(r["price_rs_per_40kg"])))
    for v in daily.values():
        v.sort()
    weekly: dict[str, list[tuple[str, float]]] = {}
    for r in _csv(PROCESSED / "farmsight_prices_clean_weekly.csv"):
        if r["filled"] == "0":
            weekly.setdefault(f"{r['city']}|{r['crop']}|{r['variety']}", []).append(
                (r["week_start"], float(r["price_rs_per_40kg"])))
    for v in weekly.values():
        v.sort()

    from ml.eval.gate import change_quantiles, load_rows  # noqa: PLC0415 (only needed once, at load)
    band = change_quantiles([r for r in load_rows() if r["split"] == "train"])

    econ = json.loads((PROCESSED / "economics_inputs.json").read_text(encoding="utf-8"))
    transport = {(r["from_district"], r["to_mandi"]): float(r["cost_per_40kg"])
                 for r in _csv(RUNTIME / "transport_costs.csv")}
    coverage = {r["series"]: r for r in _csv(RUNTIME / "series_coverage.csv")}
    frozen: dict[str, list[tuple[str, str]]] = {}
    for r in _csv(RUNTIME / "frozen_stretches.csv"):
        frozen.setdefault(r["series"], []).append((r["from_date"], r["to_date"]))
    season = {(r["series"], int(r["month"])): r for r in _csv(RUNTIME / "seasonal_index.csv")}
    return {
        "daily": daily, "weekly": weekly, "band": band, "transport": transport, "coverage": coverage,
        "frozen": frozen, "season": season,
        "interest_pct_month": econ["storage_and_holding"]["interest_cost_per_month_pct"]["value"],
    }


def _series(crop_option: str, mandi: str) -> str:
    if crop_option not in OPTION_TO_AMIS or mandi not in fcfg.CITY_ID:
        raise LookupError(f"unknown crop option or mandi: {crop_option}, {mandi}")
    crop, variety = OPTION_TO_AMIS[crop_option]
    key = f"{mandi}|{crop}|{variety}"
    if key not in _data()["daily"]:
        raise LookupError(f"no AMIS prices for {crop_option} at {mandi}")
    return key


def latest_price(crop_option: str, mandi: str) -> tuple[float, str]:
    """(Rs per 40 kg, date) of the latest real AMIS price."""
    d, p = _data()["daily"][_series(crop_option, mandi)][-1]
    return p, d


def _frozen_since(series: str, on: str) -> str | None:
    for start, end in _data()["frozen"].get(series, []):
        if start <= on <= end:
            return start
    return None


# ---------------------------------------------------------------- forecast

def forecast(crop_option: str, mandi: str) -> dict:
    """Owner B's model when available (interface I2), else the labelled baseline."""
    series = _series(crop_option, mandi)
    price, as_of = latest_price(crop_option, mandi)
    try:
        from ml.forecast.predict import forecast as model_forecast  # noqa: PLC0415 (Owner B, may not exist)
    except ImportError:
        model_forecast = None
    if model_forecast is not None:
        out = dict(model_forecast(crop_option, mandi, date.fromisoformat(as_of), None))
        out.setdefault("prices_as_of", as_of)
        return out
    lo, hi = _data()["band"][crop_option]
    return {
        "current_price": price, "predicted_price": price,
        "q10": price * (1 + lo / 100), "q90": price * (1 + hi / 100),
        "prices_as_of": as_of, "model_version": BASELINE_MODEL, "series": series,
        "data_source": "amis", "is_synthetic": False, "shap": [],
    }


def _round(x: float) -> int:
    """Half up (5,252.5 -> 5,253), not Python's half to even."""
    return math.floor(x + 0.5)


def _confidence(width_pct: float, stale: bool, frozen: bool) -> str:
    if stale or frozen:
        return "LOW"
    return "HIGH" if width_pct < 10 else "MEDIUM" if width_pct < 20 else "LOW"


# ---------------------------------------------------------------- the four functions the channels call

def get_advice(crop_option: str, mandi: str, quantity_maund: float = 100, phone: str | None = None) -> dict:
    """Blueprint advice (section 12) plus the fields the channels show. Raises LookupError if no data."""
    f = forecast(crop_option, mandi)
    series = _series(crop_option, mandi)
    cov = _data()["coverage"].get(series, {})
    now, then = f["current_price"], f["predicted_price"]
    change_pct = (then / now - 1) * 100
    width_pct = (f["q90"] - f["q10"]) / now * 100
    stale = cov.get("is_stale") == "1"
    frozen_since = _frozen_since(series, f["prices_as_of"])
    interest = quantity_maund * now * _data()["interest_pct_month"] / 100
    gross = quantity_maund * (then - now)
    return {
        "crop_option": crop_option, "mandi": mandi, "mandi_name": DISPLAY[mandi], "unit": "40kg",
        "current_price": round(now, 2), "predicted_price": round(then, 2),
        "range": {"low": round(f["q10"], 2), "high": round(f["q90"], 2)},
        "trend": "UP" if change_pct > TREND_FLAT_PCT else "DOWN" if change_pct < -TREND_FLAT_PCT else "STABLE",
        "volatility": "STABLE" if width_pct < 10 else "MODERATE" if width_pct < 20 else "VOLATILE",
        "signal": "WAIT" if change_pct >= WAIT_THRESHOLD_PCT else "SELL",
        "confidence": _confidence(width_pct, stale, frozen_since is not None),
        "quantity_maund": quantity_maund,
        "gross_gain": _round(gross), "interest_cost": _round(interest),
        "rupee_impact": _round(gross) - _round(interest),
        "prices_as_of": f["prices_as_of"], "is_stale": stale, "price_unchanged_since": frozen_since,
        "model": f.get("model_version", BASELINE_MODEL),
        "data_source": f.get("data_source", "amis"), "is_synthetic": bool(f.get("is_synthetic", False)),
    }


def get_explanation(crop_option: str, mandi: str) -> list[dict]:
    """Reasons as Urdu sentences. From the model's SHAP values once Owner B ships them (B5); until then,
    plain facts from the data: the recent trend, the usual seasonal level, and any stale or frozen price."""
    f = forecast(crop_option, mandi)
    if f.get("shap"):
        return [{"text_ur": s["text_ur"], "direction": s.get("direction", "")} for s in f["shap"][:3]]
    series = _series(crop_option, mandi)
    reasons = []
    weeks = _data()["weekly"].get(series, [])
    if len(weeks) >= 5:
        (_, p_then), (_, p_now) = weeks[-5], weeks[-1]
        pct = (p_now / p_then - 1) * 100
        if abs(pct) >= 1:
            word = "بڑھا" if pct > 0 else "گرا"
            reasons.append({"text_ur": f"پچھلے 4 ہفتوں میں ریٹ {abs(pct):.0f}% {word}",
                            "direction": "UP" if pct > 0 else "DOWN"})
        else:
            reasons.append({"text_ur": "پچھلے 4 ہفتوں میں ریٹ تقریباً ایک جیسا رہا", "direction": ""})
    month = date.fromisoformat(f["prices_as_of"]).month
    s = _data()["season"].get((series, month))
    if s and s["enough_years"] == "1" and s["index_median"]:
        idx = float(s["index_median"])
        reasons.append({"text_ur": f"اس مہینے ریٹ عام طور پر سال کے رجحان کا {idx:.0f}% ہوتا ہے",
                        "direction": "UP" if idx > 101 else "DOWN" if idx < 99 else ""})
    since = _frozen_since(series, f["prices_as_of"])
    if since:
        reasons.append({"text_ur": f"AMIS پر یہ ریٹ {since} سے تبدیل نہیں ہوا، اس لیے اعتماد کم ہے",
                        "direction": ""})
    elif _data()["coverage"].get(series, {}).get("is_stale") == "1":
        reasons.append({"text_ur": f"آخری ریٹ {f['prices_as_of']} کا ہے، اس لیے اعتماد کم ہے", "direction": ""})
    if f.get("model_version") == BASELINE_MODEL:
        reasons.append({"text_ur": "یہ سادہ اندازہ ہے: ریٹ وہی رہنے کا مان کر، پچھلے برسوں کے اتار چڑھاؤ کی حد",
                        "direction": ""})
    return reasons


def compare_mandis(crop_option: str, mandi: str, quantity_maund: float = 100) -> list[dict]:
    """Net price at each mandi after transport from the farmer's mandi district, best first."""
    _series(crop_option, mandi)  # the farmer's own mandi must exist
    rows, missing = [], []
    for other in fcfg.CITY_ID:
        try:
            price, as_of = latest_price(crop_option, other)
        except LookupError:
            missing.append({"mandi": other, "has_data": False})
            continue
        cost = _data()["transport"][(DISPLAY[mandi], other)]
        rows.append({"mandi": other, "price": price, "transport_cost": cost, "net_price": round(price - cost, 2),
                     "prices_as_of": as_of, "has_data": True})
    own = next(r["net_price"] for r in rows if r["mandi"] == mandi)
    for r in rows:
        r["gain_vs_preferred"] = _round((r["net_price"] - own) * quantity_maund)
    rows.sort(key=lambda r: -r["net_price"])
    return rows + missing


# Alert opt-outs. In memory until the SQLite farmer table (C2) exists.
_ALERTS: dict[str, bool] = {}


def set_alerts(phone: str, enabled: bool) -> None:
    _ALERTS[phone] = enabled


def alerts_enabled(phone: str) -> bool:
    return _ALERTS.get(phone, True)
