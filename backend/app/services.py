"""Service layer (interface I6): the one place every channel gets its answers from (web, WhatsApp, chat).

Real AMIS prices, dates, costs, yields, transport and interest come from data/processed/. The 4-week forecast
uses Owner B's `ml.forecast.predict.forecast` when it exists; until then it is the labelled baseline the
evaluation gate validated (A5): the price stays the same, with the range of 4-week changes seen in training
(it held the real price 81% of the time on 2025 data). The SELL/WAIT rule is the blueprint's (5%, interest
subtracted). Crop-plan and selling-window logic (B7) also live here until Owner B's engine takes them over.

Crop and mandi names here are the data names ("SuperBasmati", "RahimYarKhan"); backend/app/ids.py maps API ids.
`as_of` (a date) means "use only data on or before this day": the time-machine rule. Prices: Rs per 40 kg.
Written by Hamza while covering Owner C (docs/PLAN.md section 4.2).
"""

from __future__ import annotations

import bisect
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
STALE_AFTER_DAYS = 56             # blueprint UC-01 A3: an 8-week-old price is shown in amber, confidence LOW
OFFER_WINDOW_DAYS = 14
HISTORY_WEEKS = 52
RISK_SPREAD_PCT = (30, 60)        # year-to-year spread of the harvest ratio: below 30 LOW, below 60 MEDIUM
MIN_YEARS = 3
BASELINE_MODEL = "baseline_persistence_band"
OPTION_TO_AMIS = {v: k for k, v in fcfg.CROP_OPTION.items()}   # "IRRI" -> ("Rice", "IRRI")
DISPLAY = {"BahawalPur": "Bahawalpur", "Vehari": "Vehari", "RahimYarKhan": "Rahim Yar Khan"}
SIGNAL_UR = {"SELL": "بیچ دیں", "WAIT": "رکیں"}


def _round(x: float) -> int:
    """Half up (5,252.5 -> 5,253), not Python's half to even."""
    return math.floor(x + 0.5)


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
    weekly: dict[str, list[tuple[str, float]]] = {}
    for r in _csv(PROCESSED / "farmsight_prices_clean_weekly.csv"):
        weekly.setdefault(f"{r['city']}|{r['crop']}|{r['variety']}", []).append(
            (r["week_start"], float(r["price_rs_per_40kg"])))
    for table in (daily, weekly):
        for v in table.values():
            v.sort()

    from ml.eval.gate import change_quantiles, load_rows  # noqa: PLC0415 (only needed once, at load)
    band = change_quantiles([r for r in load_rows() if r["split"] == "train"])

    econ = json.loads((PROCESSED / "economics_inputs.json").read_text(encoding="utf-8"))
    frozen: dict[str, list[tuple[str, str]]] = {}
    for r in _csv(RUNTIME / "frozen_stretches.csv"):
        frozen.setdefault(r["series"], []).append((r["from_date"], r["to_date"]))
    return {
        "daily": daily, "weekly": weekly, "band": band, "frozen": frozen,
        "snapshot": max(v[-1][0] for v in daily.values()),
        "transport": {(r["from_district"], r["to_mandi"]): float(r["cost_per_40kg"])
                      for r in _csv(RUNTIME / "transport_costs.csv")},
        "season": {(r["series"], int(r["month"])): r for r in _csv(RUNTIME / "seasonal_index.csv")},
        "harvest": {(r["series"], int(r["ref_month"])): r for r in _csv(RUNTIME / "harvest_ratios.csv")},
        "post_harvest": [r for r in _csv(RUNTIME / "post_harvest_ratios.csv")],
        "crops": {r["crop_option"]: r for r in _csv(RUNTIME / "crops.csv")},
        "calendar": {r["crop_option"]: r for r in _csv(RUNTIME / "crop_calendar.csv")},
        "support": _csv(RUNTIME / "support_prices.csv"),
        "sources": _csv(RUNTIME / "data_sources.csv"),
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


def _upto(points: list[tuple[str, float]], as_of: date | None) -> list[tuple[str, float]]:
    """Points dated on or before as_of (all of them when as_of is None)."""
    if as_of is None:
        return points
    return points[: bisect.bisect_right(points, (as_of.isoformat(), float("inf")))]


def latest_price(crop_option: str, mandi: str, as_of: date | None = None) -> tuple[float, str]:
    """(Rs per 40 kg, date) of the latest real AMIS price on or before as_of."""
    points = _upto(_data()["daily"][_series(crop_option, mandi)], as_of)
    if not points:
        raise LookupError(f"no AMIS price for {crop_option} at {mandi} on or before {as_of}")
    d, p = points[-1]
    return p, d


def reference_date(as_of: date | None) -> date:
    return as_of or date.fromisoformat(_data()["snapshot"])


def is_stale(prices_as_of: str, as_of: date | None = None) -> bool:
    return (reference_date(as_of) - date.fromisoformat(prices_as_of)).days > STALE_AFTER_DAYS


def frozen_since(series: str, on: str) -> str | None:
    for start, end in _data()["frozen"].get(series, []):
        if start <= on <= end:
            return start
    return None


def calendar(crop_option: str) -> dict:
    c = _data()["calendar"][crop_option]
    return {"sowing_months": (int(c["sowing_start_month"]), int(c["sowing_end_month"])),
            "harvest_months": (int(c["harvest_start_month"]), int(c["harvest_end_month"]))}


# ---------------------------------------------------------------- forecast

def forecast(crop_option: str, mandi: str, as_of: date | None = None, weather: dict | None = None) -> dict:
    """Owner B's model when available (interface I2), else the labelled baseline."""
    series = _series(crop_option, mandi)
    price, price_date = latest_price(crop_option, mandi, as_of)
    try:
        from ml.forecast.predict import forecast as model_forecast  # noqa: PLC0415 (Owner B, may not exist)
    except ImportError:
        model_forecast = None
    if model_forecast is not None:
        out = dict(model_forecast(crop_option, mandi, date.fromisoformat(price_date), weather))
        out.setdefault("prices_as_of", price_date)
        out.setdefault("series", series)
        return out
    lo, hi = _data()["band"][crop_option]
    return {
        "current_price": price, "predicted_price": price,
        "q10": price * (1 + lo / 100), "q90": price * (1 + hi / 100),
        "prices_as_of": price_date, "model_version": BASELINE_MODEL, "series": series,
        "data_source": "amis", "is_synthetic": False, "shap": [],
    }


def _confidence(width_pct: float, stale: bool, frozen: bool) -> str:
    if stale or frozen:
        return "LOW"
    return "HIGH" if width_pct < 10 else "MEDIUM" if width_pct < 20 else "LOW"


def forecast_view(crop_option: str, mandi: str, as_of: date | None = None, weather: dict | None = None) -> dict:
    f = forecast(crop_option, mandi, as_of, weather)
    now, then = f["current_price"], f["predicted_price"]
    change_pct = (then / now - 1) * 100
    width_pct = (f["q90"] - f["q10"]) / now * 100
    stale = is_stale(f["prices_as_of"], as_of)
    frozen = frozen_since(f["series"], f["prices_as_of"])
    return {
        **f,
        "change_pct": change_pct,
        "trend": "UP" if change_pct > TREND_FLAT_PCT else "DOWN" if change_pct < -TREND_FLAT_PCT else "STABLE",
        "volatility": "STABLE" if width_pct < 10 else "MODERATE" if width_pct < 20 else "VOLATILE",
        "confidence": _confidence(width_pct, stale, frozen is not None),
        "is_stale": stale, "price_unchanged_since": frozen,
    }


def _num(row: dict, key: str) -> float | None:
    return float(row[key]) if row.get(key) else None


def history(crop_option: str, mandi: str, as_of: date | None = None, weeks: int = HISTORY_WEEKS) -> dict:
    series = _series(crop_option, mandi)
    points = _upto(_data()["weekly"].get(series, []), as_of)[-weeks:]
    seasonal = []
    for m in range(1, 13):
        s = _data()["season"].get((series, m), {})
        seasonal.append({"month": m, "index_median": _num(s, "index_median"), "index_min": _num(s, "index_min"),
                         "index_max": _num(s, "index_max"), "n_years": int(s.get("n_years") or 0)})
    _, price_date = latest_price(crop_option, mandi, as_of)
    return {"weekly": points, "seasonal": seasonal, "prices_as_of": price_date, **calendar(crop_option)}


# ---------------------------------------------------------------- the functions the channels call

def get_advice(crop_option: str, mandi: str, quantity_maund: float = 100, phone: str | None = None,
               as_of: date | None = None) -> dict:
    """Blueprint advice (section 12) plus the fields the channels show. Raises LookupError if no data."""
    f = forecast_view(crop_option, mandi, as_of)
    now, then = f["current_price"], f["predicted_price"]
    interest = quantity_maund * now * _data()["interest_pct_month"] / 100
    gross = quantity_maund * (then - now)
    signal = "WAIT" if f["change_pct"] >= WAIT_THRESHOLD_PCT else "SELL"
    return {
        "crop_option": crop_option, "mandi": mandi, "mandi_name": DISPLAY[mandi], "unit": "40kg",
        "current_price": round(now, 2), "predicted_price": round(then, 2),
        "range": {"low": round(f["q10"], 2), "high": round(f["q90"], 2)},
        "trend": f["trend"], "volatility": f["volatility"], "signal": signal, "signal_ur": SIGNAL_UR[signal],
        "confidence": f["confidence"], "quantity_maund": quantity_maund,
        "gross_gain": _round(gross), "interest_cost": _round(interest),
        "rupee_impact": _round(gross) - _round(interest),
        "prices_as_of": f["prices_as_of"], "is_stale": f["is_stale"],
        "price_unchanged_since": f["price_unchanged_since"],
        "model": f.get("model_version", BASELINE_MODEL),
        "data_source": f.get("data_source", "amis"), "is_synthetic": bool(f.get("is_synthetic", False)),
    }


def _reason(ur: str, en: str, direction: str = "") -> dict:
    return {"text_ur": ur, "text_en": en, "direction": direction}


def get_explanation(crop_option: str, mandi: str, as_of: date | None = None) -> list[dict]:
    """Reasons in Urdu and English. From the model's SHAP values once Owner B ships them (B5); until then,
    plain facts from the data: the recent trend, the usual seasonal level, and any stale or frozen price."""
    f = forecast(crop_option, mandi, as_of)
    if f.get("shap"):
        return [_reason(s["text_ur"], s.get("text_en", s["text_ur"]), s.get("direction", "")) for s in f["shap"][:3]]
    series = f["series"]
    reasons = []
    weeks = [w for w in _upto(_data()["weekly"].get(series, []), as_of)]
    if len(weeks) >= 5:
        (_, p_then), (_, p_now) = weeks[-5], weeks[-1]
        pct = (p_now / p_then - 1) * 100
        if abs(pct) >= 1:
            up = pct > 0
            reasons.append(_reason(f"پچھلے 4 ہفتوں میں ریٹ {abs(pct):.0f}% {'بڑھا' if up else 'گرا'}",
                                   f"The price {'rose' if up else 'fell'} {abs(pct):.0f}% over the last 4 weeks",
                                   "UP" if up else "DOWN"))
        else:
            reasons.append(_reason("پچھلے 4 ہفتوں میں ریٹ تقریباً ایک جیسا رہا",
                                   "The price stayed about the same over the last 4 weeks"))
    month = date.fromisoformat(f["prices_as_of"]).month
    s = _data()["season"].get((series, month))
    if s and s["enough_years"] == "1" and s["index_median"]:
        idx = float(s["index_median"])
        reasons.append(_reason(f"اس مہینے ریٹ عام طور پر سال کے رجحان کا {idx:.0f}% ہوتا ہے",
                               f"In this month the price is usually {idx:.0f}% of its yearly trend",
                               "UP" if idx > 101 else "DOWN" if idx < 99 else ""))
    since = frozen_since(series, f["prices_as_of"])
    if since:
        reasons.append(_reason(f"AMIS پر یہ ریٹ {since} سے تبدیل نہیں ہوا، اس لیے اعتماد کم ہے",
                               f"AMIS has reported the same price since {since}, so confidence is low"))
    elif is_stale(f["prices_as_of"], as_of):
        reasons.append(_reason(f"آخری ریٹ {f['prices_as_of']} کا ہے، اس لیے اعتماد کم ہے",
                               f"The latest price is from {f['prices_as_of']}, so confidence is low"))
    if f.get("model_version") == BASELINE_MODEL:
        reasons.append(_reason("یہ سادہ اندازہ ہے: ریٹ وہی رہنے کا مان کر، پچھلے برسوں کے اتار چڑھاؤ کی حد",
                               "This is a simple estimate: no change in price, with the range of past swings"))
    return reasons


def compare_mandis(crop_option: str, mandi: str, quantity_maund: float = 100,
                   as_of: date | None = None) -> list[dict]:
    """Net price at each mandi after transport from the farmer's mandi district, best first."""
    _series(crop_option, mandi)  # the farmer's own mandi must exist
    rows, missing = [], []
    for other in fcfg.CITY_ID:
        try:
            price, price_date = latest_price(crop_option, other, as_of)
        except LookupError:
            missing.append({"mandi": other, "has_data": False})
            continue
        cost = _data()["transport"][(DISPLAY[mandi], other)]
        rows.append({"mandi": other, "price": price, "transport_cost": cost, "net_price": round(price - cost, 2),
                     "prices_as_of": price_date, "is_stale": is_stale(price_date, as_of), "has_data": True})
    own = next((r["net_price"] for r in rows if r["mandi"] == mandi), None)
    for r in rows:
        r["gain_vs_preferred"] = _round((r["net_price"] - own) * quantity_maund) if own is not None else None
    rows.sort(key=lambda r: -r["net_price"])
    return rows + missing


def set_alerts(phone: str, enabled: bool) -> None:
    from backend.app import db  # noqa: PLC0415 (keeps this module importable without a database)
    db.set_alerts_by_phone(phone, enabled)


def alerts_enabled(phone: str) -> bool:
    from backend.app import db  # noqa: PLC0415
    return db.alerts_enabled_by_phone(phone)


# ---------------------------------------------------------------- offer check and margin

def offer_check(crop_option: str, mandi: str, offer: float, quantity_maund: float = 100,
                as_of: date | None = None) -> dict:
    """Compares a buyer's offer with what AMIS reported at this mandi in the last 14 days."""
    series = _series(crop_option, mandi)
    points = _upto(_data()["daily"][series], as_of)
    if not points:
        raise LookupError("no prices")
    last = date.fromisoformat(points[-1][0])
    window = [p for d, p in points if (last - date.fromisoformat(d)).days < OFFER_WINDOW_DAYS]
    low, high = min(window), max(window)
    if offer < low:
        verdict, diff = "below", offer - low
    elif offer > high:
        verdict, diff = "above", offer - high
    else:
        verdict, diff = "fair", 0.0
    return {"fair_low": low, "fair_high": high, "verdict": verdict, "difference_per_maund": round(diff, 2),
            "difference_total": _round(diff * quantity_maund), "window_days": OFFER_WINDOW_DAYS,
            "prices_as_of": points[-1][0]}


def margin(crop_option: str, price: float, arhti_pct: float | None = None) -> dict:
    crop = _data()["crops"][crop_option]
    cost = float(crop["production_cost_per_40kg"])
    pct = arhti_pct or 0.0
    arhti = price * pct / 100
    support = None
    if crop_option == "Wheat" and _data()["support"]:
        support = max(_data()["support"], key=lambda r: int(r["year"]))
    return {
        "production_cost": cost, "cost_confidence": crop["cost_confidence"],
        "arhti_pct": pct, "arhti_amount": round(arhti, 2), "profit": round(price - cost - arhti, 2),
        "support_price": float(support["price_per_40kg"]) if support else None,
        "support_status": support["status"] if support else None,
        "support_crop_year": support["crop_year"] if support else None,
    }


# ---------------------------------------------------------------- crop plan (What to Grow) and selling window

def _harvest_ratio(series: str, ref_month: int) -> tuple[dict, int] | None:
    """The harvest-ratio row for the month of the latest price, or the nearest earlier month with data
    (a month with too few prices has no ratio)."""
    for back in range(12):
        m = (ref_month - 1 - back) % 12 + 1
        row = _data()["harvest"].get((series, m))
        if row and row["ratio_median"]:
            return row, m
    return None


def selling_window(series: str) -> tuple[int | None, float | None]:
    """The month after the harvest starts with the best median price gain, after interest per month held."""
    best_month, best_gain = None, None
    for r in _data()["post_harvest"]:
        if r["series"] != series or not r["ratio_median"] or int(r["n_years"]) < MIN_YEARS:
            continue
        k = int(r["offset_months"])
        gain = (float(r["ratio_median"]) - 1) * 100 - _data()["interest_pct_month"] * k
        if best_gain is None or gain > best_gain:
            best_month, best_gain = int(r["month"]), round(gain, 1)
    return best_month, best_gain


def crop_plan(mandi: str, land_area_acres: float = 10, as_of: date | None = None) -> dict:
    items, missing = [], []
    for option in fcfg.CROP_OPTION_ID:
        try:
            series = _series(option, mandi)
            price, price_date = latest_price(option, mandi, as_of)
        except LookupError:
            missing.append(option)
            continue
        found = _harvest_ratio(series, date.fromisoformat(price_date).month)
        if found is None:
            missing.append(option)
            continue
        row, _ = found
        crop = _data()["crops"][option]
        yield_maund = float(crop["yield_maund_per_acre"])
        if crop["milling_yield"]:
            yield_maund *= float(crop["milling_yield"])   # rice yield is paddy; the price is milled rice
        median, low, high = (float(row[k]) for k in ("ratio_median", "ratio_min", "ratio_max"))
        estimate = price * median
        cost_acre = float(crop["production_cost_per_acre"])
        profit_acre = estimate * yield_maund - cost_acre
        n = int(row["n_years"])
        spread = float(row["spread_pct"]) if row["spread_pct"] else None
        risk = ("HIGH" if n < MIN_YEARS or spread is None or spread >= RISK_SPREAD_PCT[1]
                else "MEDIUM" if spread >= RISK_SPREAD_PCT[0] else "LOW")
        best_month, best_gain = selling_window(series)
        items.append({
            "crop_option": option, "latest_price": price, "latest_price_date": price_date,
            "harvest_price_estimate": round(estimate, 2), "harvest_price_low": round(price * low, 2),
            "harvest_price_high": round(price * high, 2), "months_ahead": int(row["months_ahead"]),
            "yield_maund_per_acre": round(yield_maund, 2), "cost_per_acre": cost_acre,
            "profit_per_acre": round(profit_acre, 2), "expected_profit": round(profit_acre * land_area_acres, 2),
            "risk_level": risk, "spread_pct": spread, "n_years": n,
            "best_sell_month": best_month, "best_sell_gain_pct": best_gain,
            "is_stale": is_stale(price_date, as_of), **calendar(option),
        })
    items.sort(key=lambda i: -i["expected_profit"])
    for rank, item in enumerate(items, start=1):
        item["rank"] = rank
    return {"items": items, "not_available": missing}


# ---------------------------------------------------------------- meta

def meta() -> dict:
    series = []
    for key, points in _data()["daily"].items():
        city, crop, variety = key.split("|")
        d, p = points[-1]
        series.append({"crop_option": fcfg.CROP_OPTION[(crop, variety)], "mandi": city, "prices_as_of": d,
                       "latest_price": p, "is_stale": is_stale(d)})
    crops = []
    for option, row in _data()["crops"].items():
        crops.append({"crop_option": option, "season": row["season"], **calendar(option)})
    return {
        "crops": crops, "series": series, "prices_as_of": _data()["snapshot"],
        "interest_pct_month": _data()["interest_pct_month"],
        "sources": [{"name": s["name"], "url": s["url"], "covers": s["covers"]} for s in _data()["sources"]],
    }



def model_available() -> bool:
    """True once Owner B's ml/forecast/predict.py is importable."""
    try:
        from ml.forecast.predict import forecast as _  # noqa: F401, PLC0415
    except ImportError:
        return False
    return True
