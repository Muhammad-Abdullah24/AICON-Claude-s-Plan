"""Service layer (interface I6): the one place every channel gets its answers from (web, WhatsApp, chat).

Real AMIS prices, dates, costs, yields, transport and interest come from data/processed/. The 4-week forecast
is Owner B's `ml.forecast.predict.forecast` (interface I2): the labelled persistence-band baseline for the price
and range (the model did not beat it, NFR-01), plus the model's UP/DOWN direction call and SHAP reasons for wheat.
Without Owner B's module it falls back to the same baseline computed here. Every decision (SELL/WAIT and the
rupee impact, mandi ranking, offer check, margin, crop plan, selling window) is Owner B's engine `ml.decision`
(interface I3); this layer only gathers its inputs, honouring `as_of`, and shapes the answers for the channels.

Crop and mandi names here are the data names ("SuperBasmati", "RahimYarKhan"); backend/app/ids.py maps API ids.
`as_of` (a date) means "use only data on or before this day": the time-machine rule. Prices: Rs per 40 kg.
Written by Hamza while covering Owner C (docs/PLAN.md section 4.2).
"""

from __future__ import annotations

import bisect
import csv
import math
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from ml import decision
from ml.decision import inputs as engine_inputs
from ml.features import config as fcfg

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
RUNTIME = PROCESSED / "runtime"

WAIT_THRESHOLD_PCT = decision.config.WAIT_THRESHOLD_PCT   # blueprint UC-03 (the engine applies it)
TREND_FLAT_PCT = 3
HORIZON_WEEKS = decision.config.HORIZON_WEEKS
STALE_AFTER_DAYS = 56             # blueprint UC-01 A3: an 8-week-old price is shown in amber, confidence LOW
OFFER_WINDOW_DAYS = 14
HISTORY_WEEKS = 52
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

    frozen: dict[str, list[tuple[str, str]]] = {}
    for r in _csv(RUNTIME / "frozen_stretches.csv"):
        frozen.setdefault(r["series"], []).append((r["from_date"], r["to_date"]))
    return {
        "daily": daily, "weekly": weekly, "band": band, "frozen": frozen,
        "snapshot": max(v[-1][0] for v in daily.values()),
        "transport": {(r["from_district"], r["to_mandi"]): float(r["cost_per_40kg"])
                      for r in _csv(RUNTIME / "transport_costs.csv")},
        "season": {(r["series"], int(r["month"])): r for r in _csv(RUNTIME / "seasonal_index.csv")},
        "crops": {r["crop_option"]: r for r in _csv(RUNTIME / "crops.csv")},
        "calendar": {r["crop_option"]: r for r in _csv(RUNTIME / "crop_calendar.csv")},
        "sources": _csv(RUNTIME / "data_sources.csv"),
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


def history(crop_option: str, mandi: str, as_of: date | None = None, weeks: int = HISTORY_WEEKS) -> dict:
    """52 weeks of prices (None for a week without an AMIS price, flagged where AMIS repeated a price) and the
    seasonal pattern, from Owner B's `ml.forecast.history` (B9). "Prices as of" is the latest daily price."""
    _series(crop_option, mandi)
    from ml.forecast.history import history as weekly_history  # noqa: PLC0415 (Owner B)
    h = weekly_history(crop_option, mandi, as_of, weeks)
    if h is None:
        raise LookupError(f"no AMIS prices for {crop_option} at {mandi} on or before {as_of}")
    _, price_date = latest_price(crop_option, mandi, as_of)
    return {
        "weekly": [{"date": w["week_start"], "price": w["price"], "frozen": w["frozen"], "filled": w["filled"]}
                   for w in h["weeks"]],
        "seasonal": [{k: s[k] for k in ("month", "index_median", "index_min", "index_max", "n_years")}
                     for s in h["seasonal"]],
        "prices_as_of": price_date, **calendar(crop_option),
    }


# ---------------------------------------------------------------- the functions the channels call

def get_advice(crop_option: str, mandi: str, quantity_maund: float = 100, phone: str | None = None,
               as_of: date | None = None, arhti_pct: float | None = None) -> dict:
    """Blueprint advice (section 12) plus the fields the channels show. Raises LookupError if no data.
    The decision is Owner B's `ml.decision.advise`; a frozen AMIS price counts as stale for confidence."""
    f = forecast_view(crop_option, mandi, as_of)
    a = decision.advise(f["current_price"], f["predicted_price"], f["q10"], f["q90"], quantity_maund,
                        engine_inputs.interest_pct_per_year(), arhti_pct=arhti_pct,
                        is_stale=f["is_stale"] or f["price_unchanged_since"] is not None)
    return {
        "crop_option": crop_option, "mandi": mandi, "mandi_name": DISPLAY[mandi], "unit": "40kg",
        "current_price": a["current_price"], "predicted_price": a["expected_price"],
        "range": {"low": round(f["q10"], 2), "high": round(f["q90"], 2)},
        "trend": f["trend"], "volatility": f["volatility"], "signal": a["signal"], "signal_ur": SIGNAL_UR[a["signal"]],
        "confidence": a["confidence"], "quantity_maund": quantity_maund, "arhti_pct": arhti_pct,
        "gross_gain": a["gross_gain"], "interest_cost": a["interest_cost"], "rupee_impact": a["rupee_impact"],
        "prices_as_of": f["prices_as_of"], "is_stale": f["is_stale"],
        "price_unchanged_since": f["price_unchanged_since"], "direction": f.get("direction"),
        "model": f.get("model_version", BASELINE_MODEL),
        "data_source": f.get("data_source", "amis"), "is_synthetic": bool(f.get("is_synthetic", False)),
    }


def _reason(ur: str, en: str, direction: str = "") -> dict:
    return {"text_ur": ur, "text_en": en, "direction": direction}


def _baseline_note() -> dict:
    return _reason("یہ سادہ اندازہ ہے: ریٹ وہی رہنے کا مان کر، پچھلے برسوں کے اتار چڑھاؤ کی حد",
                   "This is a simple estimate: no change in price, with the range of past swings")


def get_explanation(crop_option: str, mandi: str, as_of: date | None = None) -> list[dict]:
    """Reasons in Urdu and English. From the model's SHAP values once Owner B ships them (B5); until then,
    plain facts from the data: the recent trend, the usual seasonal level, and any stale or frozen price."""
    f = forecast(crop_option, mandi, as_of)
    if f.get("shap"):
        reasons = [_reason(s["text_ur"], s.get("text_en", s["text_ur"]), s.get("direction", "")) for s in f["shap"][:3]]
        # The SHAP reasons explain the direction call; the price shown is still the baseline, so say so.
        return reasons + ([_baseline_note()] if f.get("model_version") == BASELINE_MODEL else [])
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
        reasons.append(_baseline_note())
    return reasons


def compare_mandis(crop_option: str, mandi: str, quantity_maund: float = 100,
                   as_of: date | None = None) -> list[dict]:
    """Net price at each mandi after transport from the farmer's mandi district, best first (Owner B's
    `ml.decision.compare_mandis`); mandis without a price for this crop come last."""
    _series(crop_option, mandi)  # the farmer's own mandi must exist
    found = {}
    for other in fcfg.CITY_ID:
        try:
            found[other] = latest_price(crop_option, other, as_of)
        except LookupError:
            pass
    ranked = decision.compare_mandis(
        [{"mandi": m, "current_price": found[m][0] if m in found else None,
          "transport_cost": _data()["transport"][(DISPLAY[mandi], m)]} for m in fcfg.CITY_ID],
        preferred_mandi=mandi, quantity_maund=quantity_maund)["mandis"]
    own = next(r["net_price"] for r in ranked if r["mandi"] == mandi)
    rows = []
    for r in ranked:
        if not r["has_price"]:
            rows.append({"mandi": r["mandi"], "has_data": False})
            continue
        price_date = found[r["mandi"]][1]
        rows.append({"mandi": r["mandi"], "price": r["current_price"], "transport_cost": r["transport_cost"] or 0.0,
                     "net_price": r["net_price"], "prices_as_of": price_date, "is_stale": is_stale(price_date, as_of),
                     "has_data": True, "gain_vs_preferred": _round((r["net_price"] - own) * quantity_maund)})
    return rows


def set_alerts(phone: str, enabled: bool) -> None:
    from backend.app import db  # noqa: PLC0415 (keeps this module importable without a database)
    db.set_alerts_by_phone(phone, enabled)


def alerts_enabled(phone: str) -> bool:
    from backend.app import db  # noqa: PLC0415
    return db.alerts_enabled_by_phone(phone)


# ---------------------------------------------------------------- offer check and margin

def offer_check(crop_option: str, mandi: str, offer: float, quantity_maund: float = 100,
                as_of: date | None = None) -> dict:
    """A buyer's offer against the fair range: the lowest to highest AMIS price at this mandi in the last 14
    days. The verdict is Owner B's `ml.decision.offer_check`."""
    series = _series(crop_option, mandi)
    points = _upto(_data()["daily"][series], as_of)
    if not points:
        raise LookupError("no prices")
    last = date.fromisoformat(points[-1][0])
    window = [p for d, p in points if (last - date.fromisoformat(d)).days < OFFER_WINDOW_DAYS]
    low, high = min(window), max(window)
    r = decision.offer_check(offer, low, high, quantity_maund)
    return {"fair_low": low, "fair_high": high, "verdict": r["status"].lower(),
            "difference_per_maund": r["gap_per_40kg"], "difference_total": r["gap_total"],
            "window_days": OFFER_WINDOW_DAYS, "prices_as_of": points[-1][0]}


def margin(crop_option: str, price: float, arhti_pct: float | None = None) -> dict:
    """Cost, the farmer's own arhti commission and profit (Owner B's `ml.decision.margin`), with the latest
    wheat support price as a reference line."""
    support = engine_inputs.support_price(crop_option)
    m = decision.margin(price, engine_inputs.production_cost_per_40kg(crop_option), arhti_pct,
                        support["price_per_40kg"] if support else None, support["status"] if support else None)
    return {
        "production_cost": m["production_cost"], "cost_confidence": _data()["crops"][crop_option]["cost_confidence"],
        "arhti_pct": arhti_pct or 0.0, "arhti_amount": m["arhti_commission"] or 0.0, "profit": m["profit"],
        "support_price": m["support_price"], "support_status": m["support_status"],
        "support_crop_year": support["crop_year"] if support else None,
    }


# ---------------------------------------------------------------- crop plan (What to Grow) and selling window

def crop_plan(mandi: str, land_area_acres: float = 10, as_of: date | None = None) -> dict:
    """Crop options ranked by expected profit at the next harvest (Owner B's `ml.decision.crop_plan`), each with
    its selling window after interest (`ml.decision.selling_window`). The inputs are Owner B's
    `crop_plan_inputs`, which honour `as_of` (H-C21); the seasonal ratios are A6's tables across all years.
    A stale starting price raises the risk badge one level (`ml.decision.risk_badge`)."""
    inputs = engine_inputs.crop_plan_inputs(mandi, as_of)
    for i in inputs:
        # One staleness rule on every screen (more than 56 days, as on Home and Sell): the engine's inputs
        # round to whole weeks, so a 57-62 day old price would be fresh here and stale there. See hand-off H-B16.
        i["is_stale"] = i["prices_as_of"] is not None and is_stale(i["prices_as_of"], as_of)
    plan = decision.crop_plan(inputs, land_area_acres)
    by_option = {i["crop_option"]: i for i in inputs}
    items, missing = [], []
    for c in plan["crops"]:
        option = c["crop_option"]
        if not c["has_data"]:
            missing.append(option)
            continue
        given = by_option[option]
        window = decision.selling_window(engine_inputs.post_harvest_ratios(option, mandi),
                                         engine_inputs.interest_pct_per_year())
        risk = c["risk"]   # already one level higher for a stale starting price (ml.decision.risk_badge, H-B15)
        items.append({
            "crop_option": option, "rank": c["rank"], "latest_price": given["latest_price"],
            "latest_price_date": given["prices_as_of"], "harvest_price_estimate": c["harvest_price_estimate"],
            "harvest_price_low": c["harvest_price_range"]["low"],
            "harvest_price_high": c["harvest_price_range"]["high"],
            "months_ahead": c["months_ahead"], "yield_maund_per_acre": c["sale_maund_per_acre"],
            "cost_per_acre": given["cost_per_acre"], "profit_per_acre": c["profit_per_acre"],
            "profit_per_acre_low": c["profit_per_acre_range"]["low"],
            "profit_per_acre_high": c["profit_per_acre_range"]["high"], "expected_profit": c["profit_total"],
            "risk_level": risk, "spread_pct": given["harvest_ratio"]["spread_pct"], "n_years": c["years_of_history"],
            "best_sell_month": window["best_month"] if window else None,
            "best_sell_gain_pct": window["best_net_pct"] if window else None,
            "sell_at_harvest": bool(window and window["sell_at_harvest"]),
            "sell_window_months": window["window_months"] if window else [],
            "is_stale": c["is_stale"], **calendar(option),
        })
    # A stale starting price never ranks first (F4): fresh crops lead, then stale ones, each by expected profit.
    items.sort(key=lambda i: (i["is_stale"], -i["expected_profit"]))
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
        "interest_pct_month": round(engine_inputs.interest_pct_per_year() / 12, 4),
        "sources": [{"name": s["name"], "url": s["url"], "covers": s["covers"]} for s in _data()["sources"]],
    }



def model_available() -> bool:
    """True once Owner B's ml/forecast/predict.py is importable."""
    try:
        from ml.forecast.predict import forecast as _  # noqa: F401, PLC0415
    except ImportError:
        return False
    return True


# ---------------------------------------------------------------- pivot: wait plan, news, policy (docs/PIVOT.md)
# The wait engine (ml/decision/wait.py), the news package (backend/app/news/) and the policy timeline, wired in.
# News never flips the advice (PIVOT rule 8): it only adds a warning (NEWS_PRICE_CONFLICT / POLICY_UNCERTAIN) and
# lowers confidence. News is always today's and is skipped when replaying a past week (as_of set); the dated policy
# timeline still works in replay.

def _news_price_check(crop_option: str, mandi: str, amis_price: float, amis_date: str) -> dict | None:
    """A NewsPriceCheck dict when a news price for this crop, published in the last 14 days, is more than
    NEWS_CONFLICT_PCT away from today's AMIS price; else None. Newest qualifying item wins."""
    from backend.app.ids import CROP_FROM_DATA  # noqa: PLC0415
    from backend.app.news.service import get_news  # noqa: PLC0415
    crop_id = CROP_FROM_DATA.get(crop_option)
    try:
        items = get_news(crop_id)["items"]
    except Exception:  # noqa: BLE001 (a news failure must never break the advice)
        return None
    today = date.today()
    hits = []
    for it in items:
        price = it.get("price_rs_per_40kg")
        if price is None or it.get("crop") != crop_id:
            continue
        try:
            pub = date.fromisoformat(it["published"])
        except (TypeError, ValueError):
            continue
        if (today - pub).days > decision.config.POLICY_RECENT_DAYS:
            continue
        diff = (price - amis_price) / amis_price * 100
        if abs(diff) > decision.config.NEWS_CONFLICT_PCT:
            hits.append((it["published"], it, price, diff))
    if not hits:
        return None
    _, it, price, diff = max(hits)
    return {"amis_price": amis_price, "amis_date": amis_date, "news_price": price, "news_date": it["published"],
            "news_source": it["source"], "news_url": it["url"], "difference_pct": round(diff, 1)}


def _policy_recent(crop_option: str, as_of: date | None) -> bool:
    """True when a SUPPORT_PRICE, CAP_OR_BAN or IMPORT policy event falls in the last POLICY_RECENT_DAYS (as of
    `as_of`, so it works in replay)."""
    from backend.app.ids import CROP_FROM_DATA  # noqa: PLC0415
    from backend.app.news.policy import get_policy_events  # noqa: PLC0415
    ref = as_of or date.today()
    cutoff = (ref - timedelta(days=decision.config.POLICY_RECENT_DAYS)).isoformat()
    events = get_policy_events(CROP_FROM_DATA.get(crop_option), ref)
    return any(e["tag"] in ("SUPPORT_PRICE", "CAP_OR_BAN", "IMPORT") and e["date"] >= cutoff for e in events)


def wait_plan(crop_option: str, mandi: str, quantity_maund: float = 100, cash_need_rs: float = 0,
              wait_months: int = 4, money: str = "own", annual_rate: float | None = None,
              storage: str = "godown", offer: float | None = None, phone: str | None = None,
              as_of: date | None = None, household_spend_rs_month: float = 0,
              other_income_rs_month: float = 0) -> dict:
    """Can this farmer afford to wait? Sell enough now for the cash they need; hold the rest only if, with their
    money and their storage, holding paid in most past seasons (ml/backtest + ml/decision/wait.py). Returns the
    WaitPlanResponse fields except crop and mandi (`exits[].mandi` is a data name).

    `household_spend_rs_month`, `other_income_rs_month` and `loans_due_rs` are echoed for the screens. Deriving
    the cash need from a logged-in farmer's loans and household budget is card B2 (docs/PIVOT.md 3.4); until then
    `cash_need_rs` is taken as given and `loans_due_rs` is 0."""
    from ml.backtest.hold import hold_history  # noqa: PLC0415
    from ml.decision import wait as wait_engine  # noqa: PLC0415
    _series(crop_option, mandi)
    price, price_date = latest_price(crop_option, mandi, as_of)
    stale = is_stale(price_date, as_of)
    priced = [r for r in compare_mandis(crop_option, mandi, quantity_maund, as_of) if r.get("has_data")]
    non_stale = [r for r in priced if not r["is_stale"]]
    best = (non_stale or priced)[0]   # compare_mandis is sorted by net price, best first
    rate = decision.config.DEFAULT_RATE_PCT[money] if annual_rate is None else annual_rate
    loss = decision.config.LOSS_PCT[storage]
    is_wheat = crop_option == "Wheat"
    hold = (hold_history(crop_option, mandi, date.fromisoformat(price_date).month, wait_months, rate, loss, as_of)
            if is_wheat else None)
    news_check = _news_price_check(crop_option, mandi, price, price_date) if as_of is None else None
    plan = wait_engine.wait_plan(
        quantity_maund=quantity_maund, cash_need_rs=cash_need_rs, best_mandi=best["mandi"],
        best_net_price=best["net_price"], hold=hold, is_wheat=is_wheat, wait_months=wait_months, money=money,
        annual_rate_pct=rate, storage=storage, loss_pct=loss, offer=offer, is_stale=stale,
        news_conflict=news_check is not None, policy_recent=_policy_recent(crop_option, as_of))
    return {**plan, "data_source": "amis", "is_synthetic": False, "prices_as_of": price_date, "is_stale": stale,
            "news_check": news_check, "household_spend_rs_month": household_spend_rs_month,
            "other_income_rs_month": other_income_rs_month, "loans_due_rs": 0.0}


# ---------------------------------------------------------------- loan planner (docs/PIVOT.md 3.4)
# L2a: a clearly-labelled placeholder so the screens (L3) and WhatsApp (B3) can build against the contract.
# The real per-acre costs (data/processed/input_costs.json, card D1), the verified options
# (data/processed/loan_options.json, card D2) and the ml.decision.loan engine (card L1) are wired in by B2.

_PLACEHOLDER_INPUT_ITEMS = [
    {"item": "seed", "name_ur": "بیج", "name_en": "Seed", "rs_per_acre": 6000.0},
    {"item": "fertilizer", "name_ur": "کھاد", "name_en": "Fertiliser", "rs_per_acre": 21000.0},
    {"item": "sprays", "name_ur": "دوائی", "name_en": "Sprays", "rs_per_acre": 3000.0},
    {"item": "land_prep", "name_ur": "زمین کی تیاری", "name_en": "Land preparation", "rs_per_acre": 7000.0},
    {"item": "irrigation", "name_ur": "آبپاشی", "name_en": "Irrigation", "rs_per_acre": 8000.0},
    {"item": "harvest", "name_ur": "کٹائی اور گہائی", "name_en": "Harvesting and threshing", "rs_per_acre": 5000.0},
]
# id, name_ur, name_en, rate %, per-acre cap, overall cap, conditions (ur, en), source
_PLACEHOLDER_OPTIONS = [
    ("kissan_card", "کسان کارڈ", "Kissan Card", 0.0, 30000.0, 150000.0,
     "صرف اِن پٹ؛ 1 سے 12.5 ایکڑ", "Inputs only; 1–12.5 acres", "https://punjab.gov.pk/node/5690"),
    ("pm_youth", "پی ایم یوتھ قرض", "PM Youth Loan", 0.0, None, 500000.0,
     "عمر 21 سے 45 سال", "Age 21–45", "https://ztbl.com.pk"),
    ("akhuwat", "اخوت قرض", "Akhuwat Loan", 0.0, None, 80000.0,
     "دو ضامن؛ شاخ پر درخواست", "Two guarantors; apply at a branch", "https://akhuwat.org.pk"),
    ("zarkhez_e", "زرخیز-ای", "Zarkhez-e", 18.0, 100000.0, 1000000.0,
     "12.5 ایکڑ تک", "Up to 12.5 acres", "https://ztbl.com.pk"),
    ("bank", "بینک قرض", "Bank loan", 16.5, None, None,
     "عام زرعی قرض", "Ordinary agri loan", "https://www.sbp.org.pk"),
    ("arhti", "آڑھتی", "Arhti", 66.0, None, None,
     "فصل بیچنے کی شرط", "Tied to selling the crop", "https://www.sbp.org.pk/research"),
]
SMALL_FARMER_MAX_ACRES = 12.5


def months_to_harvest(crop_option: str, as_of: date | None = None) -> int:
    """Whole months from the reference date to the crop's next harvest start (crop calendar), at least 1."""
    start = calendar(crop_option)["harvest_months"][0]
    gap = (start - reference_date(as_of).month) % 12
    return gap or 12


def loan_plan(crop_option: str, acres: float, savings_rs: float = 0, age: int | None = None,
              planned_borrow_rs: float | None = None, planned_lender: str | None = None,
              as_of: date | None = None) -> dict:
    """Placeholder loan plan (L2a): the full LoanPlanResponse shape with clearly labelled, not-yet-verified
    numbers. Real costs, verified options and the ladder engine arrive in D1, D2 and B2."""
    months = months_to_harvest(crop_option, as_of)
    items = [dict(i) for i in _PLACEHOLDER_INPUT_ITEMS]
    input_need = _round(sum(i["rs_per_acre"] for i in items) * acres)
    borrow_needed = max(0.0, input_need - savings_rs)
    small = acres <= SMALL_FARMER_MAX_ACRES

    options = []
    for oid, ur, en, rate, per_acre_cap, overall_cap, cond_ur, cond_en, url in _PLACEHOLDER_OPTIONS:
        cap = None
        if per_acre_cap is not None or overall_cap is not None:
            cap = min(c for c in (per_acre_cap * acres if per_acre_cap else None, overall_cap) if c is not None)
        eligible, why_ur, why_en = True, None, None
        if oid in ("kissan_card", "zarkhez_e") and not small:
            eligible, why_ur, why_en = False, "12.5 ایکڑ سے زیادہ", "Over 12.5 acres"
        elif oid == "pm_youth" and age is None:
            eligible, why_ur, why_en = False, "عمر درکار ہے", "Age needed"
        elif oid == "pm_youth" and not (21 <= age <= 45):
            eligible, why_ur, why_en = False, "عمر 21 سے 45 سال ہونی چاہیے", "Must be aged 21–45"
        options.append({"id": oid, "name_ur": ur, "name_en": en, "annual_rate_pct": rate, "max_rs": cap,
                        "eligible": eligible, "why_not_ur": why_ur, "why_not_en": why_en,
                        "conditions_ur": cond_ur, "conditions_en": cond_en, "source_url": url, "verified": False})

    # Ladder: fill borrow_needed from the cheapest eligible option up (ties keep the table order).
    ladder, remaining = [], borrow_needed
    for o in sorted([o for o in options if o["eligible"]], key=lambda o: o["annual_rate_pct"]):
        if remaining <= 0:
            break
        room = remaining if o["max_rs"] is None else min(remaining, o["max_rs"])
        if room <= 0:
            continue
        interest = _round(room * o["annual_rate_pct"] / 100 * months / 12)
        ladder.append({"id": o["id"], "amount_rs": float(_round(room)), "interest_rs": float(interest)})
        remaining -= room
    ladder_interest = float(sum(s["interest_rs"] for s in ladder))
    uncovered = max(0.0, remaining)

    warnings = ["COST_ESTIMATE"]
    if not small:
        warnings.append("NOT_SMALL_FARMER")
    if uncovered > 0:
        warnings.append("UNCOVERED")

    planned_interest = over_borrow = extra_cost = None
    if planned_borrow_rs is not None:
        rate = next((o["annual_rate_pct"] for o in options if o["id"] == planned_lender), None)
        if rate is not None:
            planned_interest = float(_round(planned_borrow_rs * rate / 100 * months / 12))
            extra_cost = planned_interest - ladder_interest
        over_borrow = max(0.0, planned_borrow_rs - borrow_needed)
        if over_borrow > 0:
            warnings.append("OVER_BORROWING")

    return {
        "data_source": "placeholder", "is_synthetic": True,
        "acres": acres, "savings_rs": savings_rs, "age": age, "months_to_harvest": months,
        "input_items": items,
        "input_cost_note": "Placeholder figures. Real per-acre costs come from the official wheat cost table "
                            "(data/processed/input_costs.json, card D1).",
        "input_need_rs": float(input_need), "borrow_needed_rs": float(borrow_needed),
        "options": options, "ladder": ladder, "ladder_interest_rs": ladder_interest,
        "harvest_due_rs": float(_round(borrow_needed + ladder_interest)), "uncovered_rs": uncovered,
        "planned_borrow_rs": planned_borrow_rs, "planned_lender": planned_lender,
        "planned_interest_rs": planned_interest, "over_borrow_rs": over_borrow, "extra_cost_rs": extra_cost,
        "warnings": warnings,
    }


def news(crop_option: str | None = None, mandi: str | None = None) -> dict:
    """Today's Pakistan farm news (NewsResponse fields; `items[].crop` is a data name or None). With crop and
    mandi, `price_check` flags a news price more than 10% from today's AMIS price."""
    from backend.app.ids import CROP_FROM_DATA, CROP_TO_DATA  # noqa: PLC0415
    from backend.app.news.service import get_news  # noqa: PLC0415
    n = get_news(CROP_FROM_DATA.get(crop_option) if crop_option else None)
    items = [{**i, "crop": CROP_TO_DATA.get(i["crop"]) if i.get("crop") else None} for i in n["items"]]
    price_check = None
    if crop_option and mandi:
        try:
            price, price_date = latest_price(crop_option, mandi)
            price_check = _news_price_check(crop_option, mandi, price, price_date)
        except LookupError:
            pass
    return {"data_source": "google_news", "is_synthetic": False, "items": items, "fetched_at": n["fetched_at"],
            "is_snapshot": n["is_snapshot"], "tagged_by": n["tagged_by"], "price_check": price_check}


def policy_events(crop_option: str, as_of: date | None = None) -> dict:
    """Dated, sourced policy events for the crop, newest first, none after as_of, with their data label
    (the PolicyResponse fields except crop)."""
    from backend.app.ids import CROP_FROM_DATA  # noqa: PLC0415
    from backend.app.news.policy import get_policy_events  # noqa: PLC0415
    return {"data_source": "curated", "is_synthetic": False,
            "events": get_policy_events(CROP_FROM_DATA.get(crop_option), as_of)}
