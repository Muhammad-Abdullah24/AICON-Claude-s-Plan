"""Schemas of the files in artifacts/ written by ml/precompute.py (Owner B).

These belong to the superseded plan (docs/archive/PLAN_v2_superseded.md). The API no longer serves them;
`python -m backend.app.check_artifacts` still validates the files in CI until Owner B retires or replaces
them (hand-off H-B12). The API contract is now backend/app/schemas.py.

`extra="forbid"` everywhere: a misspelt field in an artifact or a request is
an error, not something silently ignored.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

Id = str  # lowercase ids such as "wheat" or "rahim_yar_khan"; checked by ID_PATTERN
ID_PATTERN = r"^[a-z][a-z0-9_]*$"

Tier = Literal["normal", "stress", "alert", "crisis"]
Verdict = Literal["sell_now", "sell_elsewhere", "store", "split"]
Storage = Literal["none", "home", "cold_store", "warehouse"]
StoringOption = Literal["home", "cold_store", "warehouse"]
Lang = Literal["ur", "en"]
Unit = Literal["40kg"]
PriceType = Literal["wholesale", "retail"]
EventType = Literal[
    "border_closure", "export_ban", "import_permission", "procurement_policy",
    "flood", "drought", "bumper_crop", "transport_disruption", "other",
]
AlarmFlag = Literal["below_3yr_harvest_avg", "yoy_drop_over_50pct"]
ModelRole = Literal["primary", "challenger", "baseline", "placeholder"]

Price = Annotated[float, Field(gt=0)]  # Rs per 40 kg


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Labelled(Strict):
    """Every artifact and data-bearing response says where its numbers came from (PLAN.md 6.4)."""

    data_source: str
    is_synthetic: bool


# ---------------------------------------------------------------- meta.json


class NamedItem(Strict):
    id: Id = Field(pattern=ID_PATTERN)
    name_ur: str = Field(min_length=1)
    name_en: str = Field(min_length=1)


class SeriesKey(Strict):
    crop: Id
    mandi: Id


class ReplayCaseRef(Strict):
    case_id: Id = Field(pattern=ID_PATTERN)
    crop: Id
    mandi: Id
    title_ur: str
    title_en: str


class DateRange(Strict):
    start: dt.date
    end: dt.date

    @model_validator(mode="after")
    def _ordered(self) -> DateRange:
        if self.start > self.end:
            raise ValueError("date_range.start is after date_range.end")
        return self


class ModelInfo(Strict):
    name: str
    version: str
    role: ModelRole


class AssumptionValue(Strict):
    value: float = Field(ge=0)
    source: str


class StorageDefault(Strict):
    crop: Id
    storage: StoringOption
    storage_cost_per_maund_week: float = Field(ge=0)
    spoilage_pct_week: float = Field(ge=0, le=100)
    source: str


class TransportCost(Strict):
    from_mandi: Id
    to_mandi: Id
    cost_per_maund: float = Field(ge=0)
    source: str


class Assumptions(Strict):
    finance_cost_pct_month: AssumptionValue
    storage_defaults: list[StorageDefault]
    transport: list[TransportCost]


class Meta(Labelled):
    schema_version: Literal[1]
    generated_at: dt.date
    crops: list[NamedItem] = Field(min_length=1)
    mandis: list[NamedItem] = Field(min_length=1)
    series: list[SeriesKey] = Field(min_length=1)
    replay_cases: list[ReplayCaseRef]
    date_range: DateRange
    latest_as_of: dt.date
    unit: Unit
    price_type: PriceType
    models: list[ModelInfo] = Field(min_length=1)
    assumptions: Assumptions


# ----------------------------------------------------------- forecasts.json


class PricePoint(Strict):
    date: dt.date
    price: Price


class BandPoint(Strict):
    weeks_ahead: int = Field(ge=1, le=12)
    q10: Price
    q50: Price
    q90: Price

    @model_validator(mode="after")
    def _ordered(self) -> BandPoint:
        if not self.q10 <= self.q50 <= self.q90:
            raise ValueError(f"quantiles out of order at weeks_ahead={self.weeks_ahead}")
        return self


class NaivePoint(Strict):
    weeks_ahead: int = Field(ge=1, le=12)
    price: Price


class ForecastEntry(Strict):
    as_of: dt.date
    price_now: Price
    forecast: list[BandPoint] = Field(min_length=1)
    naive: list[NaivePoint]
    model: str
    mase_vs_naive: float | None = Field(default=None, ge=0)  # null = not measured


class SeriesForecasts(Strict):
    crop: Id
    mandi: Id
    history: list[PricePoint] = Field(min_length=1)
    forecasts: list[ForecastEntry] = Field(min_length=1)


class ForecastsArtifact(Labelled):
    schema_version: Literal[1]
    series: list[SeriesForecasts]


# -------------------------------------------------------------- alarms.json


class Alarm(Strict):
    crop: Id
    mandi: Id
    date: dt.date
    indicator: float  # signed: above zero means above the seasonal normal
    tier: Tier
    flags: list[AlarmFlag]


class Event(Strict):
    date: dt.date
    active_until: dt.date
    event_type: EventType
    crops: list[Id] = Field(min_length=1)
    direction: Literal["up", "down", "unclear"]
    region: str
    headline: str = Field(min_length=1)
    source_url: HttpUrl | None
    confidence: Literal["high", "medium", "low"]
    is_synthetic: bool

    @model_validator(mode="after")
    def _ordered(self) -> Event:
        if self.active_until < self.date:
            raise ValueError("event active_until is before its date")
        return self


class AlarmsArtifact(Labelled):
    schema_version: Literal[1]
    alarms: list[Alarm]
    events: list[Event]


# -------------------------------------------------------------- replay.json


class EventRef(Strict):
    event_type: EventType
    headline: str
    source_url: HttpUrl | None


class ReplayStep(Strict):
    as_of: dt.date
    price_now: Price
    forecast_q10: Price
    forecast_q50: Price
    forecast_q90: Price
    verdict: Verdict
    alarm_tier: Tier
    events_active: list[EventRef]
    actual_price_4w_later: float | None = Field(default=None, gt=0)


class ReplayCase(Strict):
    case_id: Id = Field(pattern=ID_PATTERN)
    crop: Id
    mandi: Id
    title_ur: str
    title_en: str
    summary_ur: str
    summary_en: str
    steps: list[ReplayStep] = Field(min_length=1)


class ReplayArtifact(Labelled):
    schema_version: Literal[1]
    cases: list[ReplayCase]


# ------------------------------------------------------------ backtest.json


class MetricRow(Strict):
    crop: Id
    mandi: Id
    model: str
    mase: float | None = Field(ge=0)
    quantile_loss: float | None = Field(ge=0)
    coverage_80: float | None = Field(ge=0, le=1)
    n_forecasts: int = Field(ge=0)


class NamedAssumption(Strict):
    name: str
    value: float
    source: str


class RupeeBacktest(Strict):
    quantity_maund: float = Field(gt=0)
    n_cases: int = Field(ge=0)
    avg_gain_vs_harvest_pkr: float
    share_better: float = Field(ge=0, le=1)
    worst_case_pkr: float
    hindsight_avg_gain_pkr: float
    assumptions: list[NamedAssumption]


class BacktestArtifact(Labelled):
    schema_version: Literal[1]
    horizon_weeks: int = Field(ge=1)
    cutoffs: list[dt.date]
    metrics: list[MetricRow]
    rupee_backtest: RupeeBacktest | None
    limitations: list[str]
