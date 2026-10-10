"""The API contract as code (docs/BLUEPRINT.md section 12).

FastAPI shapes every response with these models and the front end's TypeScript types are generated from the
resulting OpenAPI schema (`python -m backend.app.export_openapi && npm --prefix frontend run gen:api`).
Change a shape here and in blueprint section 12 in the same commit.

Every price is Rs per 40 kg (`unit: "40kg"`). Every data-bearing response says where its numbers came from
(`data_source`, `is_synthetic`). `extra="forbid"` on requests: a misspelt field is an error.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CropId = Literal["wheat", "cotton", "irri", "super_basmati"]
MandiId = Literal["bahawalpur", "vehari", "rahim_yar_khan"]
Lang = Literal["ur", "en"]
Unit = Literal["40kg"]
Signal = Literal["SELL", "WAIT"]
Trend = Literal["UP", "DOWN", "STABLE"]
Volatility = Literal["STABLE", "MODERATE", "VOLATILE"]
Confidence = Literal["HIGH", "MEDIUM", "LOW"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]
Direction = Literal["UP", "DOWN", ""]
Season = Literal["RABI", "KHARIF"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Labelled(Strict):
    data_source: str
    is_synthetic: bool


class Health(Strict):
    status: Literal["ok"]


# ---------------------------------------------------------------- meta

class NamedItem(Strict):
    id: str
    name_ur: str
    name_en: str


class CropInfo(NamedItem):
    season: Season
    sowing_months: tuple[int, int]
    harvest_months: tuple[int, int]


class SeriesInfo(Strict):
    crop: CropId
    mandi: MandiId
    prices_as_of: dt.date
    latest_price: float
    is_stale: bool


class DataSourceInfo(Strict):
    name: str
    url: str
    covers: str


class Meta(Labelled):
    unit: Unit
    price_type: Literal["wholesale"]
    crops: list[CropInfo]
    mandis: list[NamedItem]
    series: list[SeriesInfo]
    prices_as_of: dt.date          # the newest price in the data; each series has its own date too
    horizon_weeks: int
    wait_threshold_pct: float
    interest_pct_per_month: float
    sources: list[DataSourceInfo]


# ---------------------------------------------------------------- forecast, explain, history

class PriceRange(Strict):
    low: float
    high: float


class PricePoint(Strict):
    """One week. `price` is None for a week with no AMIS price: draw a gap, never join across it."""
    date: dt.date
    price: float | None
    frozen: bool = False            # inside a stretch where AMIS repeated the same price ("price unchanged")
    filled: bool = False            # a short gap forward-filled by the cleaning step


class DirectionCall(Strict):
    """Owner B's model: likely up or down over 4 weeks, with no price number (docs/MODEL_CARD.md). Wheat only."""
    call: Literal["UP", "DOWN"]
    validation_accuracy_pct: float | None   # share of 2025 moves over 3% it called right
    model_version: str | None


class WeatherNow(Strict):
    week_start: dt.date
    tmax_c: float | None
    tmin_c: float | None
    precip_mm_wk: float | None
    rh_pct: float | None
    precip_mm_4w: float | None
    hot_days_wk: int | None
    cached: bool
    source: str                     # "open-meteo" (live) or "offline file"
    fetched_at: dt.datetime
    attribution: str


class ForecastResponse(Labelled):
    crop: CropId
    mandi: MandiId
    unit: Unit
    prices_as_of: dt.date
    current_price: float
    predicted_price: float
    range: PriceRange               # q10 to q90
    horizon_weeks: int
    trend: Trend
    volatility: Volatility
    confidence: Confidence
    model: str
    is_stale: bool
    price_unchanged_since: dt.date | None
    direction: DirectionCall | None = None
    history: list[PricePoint]       # weekly, at most 52 weeks, never after prices_as_of


class Reason(Strict):
    text_ur: str
    text_en: str
    direction: Direction


class ExplainResponse(Labelled):
    crop: CropId
    mandi: MandiId
    prices_as_of: dt.date
    source: Literal["shap", "facts"]   # "shap" where Owner B's model explains its direction call (wheat)
    direction: DirectionCall | None = None
    reasons: list[Reason]


class SeasonalPoint(Strict):
    month: int
    index_median: float | None      # % of the 12-month moving average
    index_min: float | None
    index_max: float | None
    n_years: int


class HistoryResponse(Labelled):
    crop: CropId
    mandi: MandiId
    unit: Unit
    prices_as_of: dt.date
    weekly: list[PricePoint]
    seasonal: list[SeasonalPoint]
    sowing_months: tuple[int, int]
    harvest_months: tuple[int, int]


# ---------------------------------------------------------------- advice, compare, offer, margin

class AdviceResponse(Labelled):
    crop: CropId
    mandi: MandiId
    unit: Unit
    quantity_maund: float
    signal: Signal
    signal_ur: str
    confidence: Confidence
    trend: Trend
    current_price: float
    predicted_price: float
    range: PriceRange
    gross_gain: int                 # quantity x (forecast - today), after the farmer's arhti if they set one
    interest_cost: int              # quantity x today x yearly rate x 4 / 52
    rupee_impact: int               # gross_gain - interest_cost
    arhti_pct: float | None = None  # the farmer's own commission, from their profile
    prices_as_of: dt.date
    is_stale: bool
    price_unchanged_since: dt.date | None
    direction: DirectionCall | None = None
    model: str


class CompareRow(Strict):
    mandi: MandiId
    has_data: bool
    price: float | None = None
    transport_cost: float | None = None
    net_price: float | None = None
    gain_vs_preferred: int | None = None
    prices_as_of: dt.date | None = None
    is_stale: bool | None = None


class CompareResponse(Labelled):
    crop: CropId
    from_mandi: MandiId
    unit: Unit
    quantity_maund: float
    rows: list[CompareRow]          # best net price first; mandis without data last
    transport_is_estimate: bool


class OfferCheckRequest(Strict):
    crop: CropId
    mandi: MandiId
    offer_price: float = Field(gt=0, le=1_000_000)
    quantity_maund: float = Field(100, gt=0, le=1_000_000)


class OfferCheckResponse(Labelled):
    crop: CropId
    mandi: MandiId
    unit: Unit
    offer_price: float
    fair_low: float                 # lowest price AMIS reported at this mandi in the last 14 days
    fair_high: float                # highest
    verdict: Literal["below", "fair", "above"]
    difference_per_maund: float     # offer minus the nearest edge of the fair range; 0 when fair
    difference_total: int
    window_days: int
    prices_as_of: dt.date


class MarginResponse(Labelled):
    crop: CropId
    unit: Unit
    price: float
    production_cost: float
    cost_confidence: str
    arhti_pct: float
    arhti_amount: float
    profit: float
    support_price: float | None
    support_status: str | None
    support_crop_year: str | None


# ---------------------------------------------------------------- crop plan

class CropPlanItem(Strict):
    crop: CropId
    rank: int
    latest_price: float
    latest_price_date: dt.date
    harvest_price_estimate: float
    harvest_price_low: float
    harvest_price_high: float
    months_ahead: int
    yield_maund_per_acre: float     # in the unit the price is quoted in (milled rice for IRRI, Super Basmati)
    cost_per_acre: float
    profit_per_acre: float
    expected_profit: float          # for the farmer's land area
    risk_level: RiskLevel
    spread_pct: float | None
    n_years: int
    sowing_months: tuple[int, int]
    harvest_months: tuple[int, int]
    best_sell_month: int | None
    best_sell_gain_pct: float | None    # median price gain at that month vs the harvest month, after interest
    sell_at_harvest: bool               # holding past the harvest month usually does not beat the interest
    sell_window_months: list[int]       # the best month and its neighbours within 1 point of it
    profit_per_acre_low: float          # with the lowest and highest harvest ratio seen across years
    profit_per_acre_high: float
    is_stale: bool


class CropPlanResponse(Labelled):
    mandi: MandiId
    land_area_acres: float
    items: list[CropPlanItem]       # best expected profit first
    not_available: list[CropId]     # crop options with no price data at this mandi
    is_estimate: bool


# ---------------------------------------------------------------- wait plan, news, policy (docs/PIVOT.md)

Money = Literal["own", "bank", "arhti"]         # whose money pays for waiting
Storage = Literal["godown", "bags"]             # a proper store, or bags at home
WaitVerdict = Literal["SELL_ALL", "SPLIT", "HOLD_ALL"]
WaitWarning = Literal[
    "STALE_PRICE",              # the farmer's mandi price is over 56 days old
    "NEWS_PRICE_CONFLICT",      # a news price is more than 10% away from AMIS (news_check says which)
    "POLICY_UNCERTAIN",         # a support-price, cap/ban or import item in the last 14 days
    "HOLD_WHEAT_ONLY",          # holding is only worked out for wheat; other crops get SELL_ALL
    "CASH_NEED_EXCEEDS_CROP",   # selling everything today does not cover the cash the farmer needs
    "TOO_FEW_SEASONS",          # under 3 past seasons to judge holding, so no HOLD advice
]
NewsTag = Literal["SUPPORT_PRICE", "PROCUREMENT", "CAP_OR_BAN", "IMPORT", "PRICE_REPORT", "OTHER"]


class WaitExit(Strict):
    kind: Literal["SELL_NOW", "ARHTI_OFFER", "HOLD"]
    mandi: MandiId | None = None    # SELL_NOW: the best mandi after transport
    per_maund: float                # net per 40 kg: after transport (SELL_NOW); the offer (ARHTI_OFFER);
                                    # the median past outcome after interest and storage loss (HOLD)
    total_rs: int                   # per_maund x the whole quantity
    worst_total_rs: int | None = None   # HOLD only: the 1-in-10 bad year
    cost_rs: int | None = None          # HOLD only: interest + storage loss on the whole quantity


class HoldSeason(Strict):
    year: int
    start_price: float
    later_price: float
    net_gain_per_maund: int         # later x (1 - loss) - start x (1 + rate x months / 12)
    paid: bool


class HoldHistory(Strict):
    start_month: int
    later_month: int
    annual_rate_pct: float
    loss_pct: float
    n: int
    wins: int
    median_net_per_maund: int
    worst_p10_net_per_maund: int
    seasons: list[HoldSeason]       # oldest first: also feeds the "liquidity tax" chart


class NewsPriceCheck(Strict):
    amis_price: float
    amis_date: dt.date
    news_price: float
    news_date: dt.date
    news_source: str
    news_url: str
    difference_pct: float           # (news - amis) / amis x 100


class WaitPlanResponse(Labelled):
    crop: CropId
    mandi: MandiId
    unit: Unit
    quantity_maund: float
    cash_need_rs: float
    wait_months: int
    money: Money
    annual_rate_pct: float          # the rate used: the farmer's own, else the default for `money`
    storage: Storage
    loss_pct: float                 # storage loss used for `storage`
    verdict: WaitVerdict
    sell_now_maund: float
    hold_maund: float
    exits: list[WaitExit]           # SELL_NOW always; ARHTI_OFFER when an offer was given; HOLD for wheat
    history: HoldHistory | None     # None when holding is not worked out (not wheat, or too few seasons)
    confidence: Confidence
    warnings: list[WaitWarning]
    news_check: NewsPriceCheck | None = None
    prices_as_of: dt.date
    is_stale: bool


class NewsItem(Strict):
    title: str
    url: str
    source: str
    published: dt.date
    tag: NewsTag
    crop: CropId | None
    summary_ur: str
    summary_en: str
    price_rs_per_40kg: float | None     # only when the text itself states a price for the crop


class NewsResponse(Labelled):
    items: list[NewsItem]           # newest first
    fetched_at: dt.datetime
    is_snapshot: bool               # served from the saved copy (offline, or the live feed failed)
    tagged_by: Literal["llm", "rules"]
    price_check: NewsPriceCheck | None = None   # when crop and mandi are given and a news price disagrees with AMIS


class PolicyEvent(Strict):
    date: dt.date
    tag: NewsTag
    text_ur: str
    text_en: str
    source: str
    url: str


class PolicyResponse(Labelled):
    crop: CropId
    events: list[PolicyEvent]       # newest first, none after as_of


# ---------------------------------------------------------------- weather

class WeatherResponse(Strict):
    mandi: MandiId
    weather: WeatherNow


# ---------------------------------------------------------------- farmers and auth

class FarmerCropIn(Strict):
    crop: CropId
    preferred_mandi: MandiId
    harvest_quantity_maund: float = Field(gt=0, le=1_000_000)


class FarmerIn(Strict):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=7, max_length=20, pattern=r"^\+?[0-9 -]+$")
    language: Lang = "ur"
    district: MandiId
    land_area_acres: float | None = Field(None, gt=0, le=100_000)
    arhti_commission_pct: float | None = Field(None, ge=0, le=50)
    alerts_enabled: bool = False   # opt-in: a new farmer gets no alerts until they turn them on
    crops: list[FarmerCropIn] = Field(default_factory=list, max_length=4)


class FarmerUpdate(Strict):
    name: str | None = Field(None, min_length=1, max_length=100)
    language: Lang | None = None
    district: MandiId | None = None
    land_area_acres: float | None = Field(None, gt=0, le=100_000)
    arhti_commission_pct: float | None = Field(None, ge=0, le=50)
    alerts_enabled: bool | None = None
    crops: list[FarmerCropIn] | None = Field(None, max_length=4)


class Farmer(Strict):
    id: str
    name: str
    phone: str
    language: Lang
    district: MandiId
    land_area_acres: float | None
    arhti_commission_pct: float | None
    alerts_enabled: bool
    crops: list[FarmerCropIn]
    created_at: dt.datetime


class LoginRequest(Strict):
    phone: str = Field(min_length=7, max_length=20, pattern=r"^\+?[0-9 -]+$")


class TokenResponse(Strict):
    token: str
    farmer: Farmer


# ---------------------------------------------------------------- chat

class ChatRequest(Strict):
    question: str = Field(min_length=1, max_length=500)
    crop: CropId | None = None
    mandi: MandiId | None = None
    quantity_maund: float | None = Field(None, gt=0, le=1_000_000)


class ChatResponse(Strict):
    answer: str
    used_fallback: bool
    fallback_reason: Literal["need_crop_and_mandi", "no_data", "service_not_ready", "rate_limited",
                             "llm_unavailable", "unverified_numbers", "wrong_script"] | None
    crop: CropId | None
    mandi: MandiId | None
    data_source: str
    is_synthetic: bool


# ---------------------------------------------------------------- alerts (C9, ops only)

class AlertItem(Strict):
    crop: CropId
    mandi: MandiId
    kind: Literal["SELL_SIGNAL", "PRICE_SPIKE"]     # Owner B's alert_check events
    signal: Signal
    current_price: float
    prices_as_of: dt.date
    change_4w_pct: float | None = None


class AlertResult(Strict):
    farmer_id: str                  # never the phone number
    items: list[AlertItem]          # the one alert sent (or due, on a dry run)
    suppressed: int                 # other events held back by the one-a-week limit
    skipped: Literal["weekly_limit", "no_event"] | None
    message: str | None = None
    status: Literal["SENT", "FAILED"] | None = None     # None on a dry run or when nothing was due
    channel: Literal["whatsapp", "sms"] | None = None


class AlertRunResponse(Strict):
    as_of: dt.date
    dry_run: bool
    farmers_checked: int
    sent: int
    results: list[AlertResult]
