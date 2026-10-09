"""FarmSight API (PLAN.md section 14.1).

Reads only from artifacts/ and runs the decision engine. Never imports model
code. Run from the repo root:

    python -m uvicorn backend.app.main:app --reload
"""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated
from xml.sax.saxutils import escape

from fastapi import APIRouter, FastAPI, Form, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response

from backend.app import phrasing
from backend.app.artifacts import ArtifactStore, load_store
from backend.app.config import HISTORY_WEEKS, Settings, get_settings
from backend.app.schemas import (
    AdviceRequest,
    AdviceResponse,
    AlertsResponse,
    AlternativeMandi,
    AssumptionUsed,
    BacktestArtifact,
    EventRef,
    ForecastResponse,
    Health,
    Lang,
    Meta,
    ReplayResponse,
)
from ml.decision.engine import BandPoint, Costs, DecisionInput, OtherMandi, decide

AsOf = Annotated[dt.date | None, Query(description="Latest data on or before this date. Omit for latest.")]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Fails loudly on invalid artifacts: the server does not start.
        app.state.store = load_store(settings.artifacts_dir)
        yield

    app = FastAPI(title="FarmSight API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        # Anyone opening the backend's address lands on the interactive API docs, not a bare 404.
        return RedirectResponse("/docs")

    @app.get("/health", response_model=Health, tags=["ops"])
    def health() -> Health:
        return Health(status="ok")

    @app.post("/whatsapp", tags=["channels"], response_class=Response)
    def whatsapp(Body: Annotated[str, Form()] = "") -> Response:  # noqa: N803 (Twilio's field name)
        # Walking skeleton: fixed Urdu reply. Twilio expects TwiML (XML), not JSON.
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f"<Response><Message>{escape(phrasing.WHATSAPP_PLACEHOLDER_REPLY)}</Message></Response>"
        )
        return Response(content=twiml, media_type="application/xml")

    return app


router = APIRouter(prefix="/api", tags=["api"])


def _store(request: Request) -> ArtifactStore:
    return request.app.state.store


def _require_series(store: ArtifactStore, crop: str, mandi: str) -> None:
    if not store.has_series(crop, mandi):
        raise HTTPException(404, f"No series for crop '{crop}' at mandi '{mandi}'")


@router.get("/meta", response_model=Meta)
def meta(request: Request) -> Meta:
    return _store(request).meta


@router.get("/forecast", response_model=ForecastResponse)
def forecast(request: Request, crop: str, mandi: str, as_of: AsOf = None) -> ForecastResponse:
    store = _store(request)
    _require_series(store, crop, mandi)
    f = store.forecast_at(crop, mandi, as_of)
    if f is None:
        raise HTTPException(404, f"No forecast on or before {as_of}")
    return ForecastResponse(
        crop=crop,
        mandi=mandi,
        as_of=f.as_of,
        unit=store.meta.unit,
        price_now=f.price_now,
        history=store.history_until(crop, mandi, f.as_of, HISTORY_WEEKS),
        forecast=f.forecast,
        naive=f.naive,
        model=f.model,
        mase_vs_naive=f.mase_vs_naive,
        price_type=store.meta.price_type,
        data_source=store.forecasts.data_source,
        is_synthetic=store.forecasts.is_synthetic,
    )


@router.post("/advice", response_model=AdviceResponse)
def advice(request: Request, req: AdviceRequest) -> AdviceResponse:
    store = _store(request)
    _require_series(store, req.crop, req.mandi)
    f = store.forecast_at(req.crop, req.mandi, req.as_of)
    if f is None:
        raise HTTPException(404, f"No forecast on or before {req.as_of}")

    can_store = req.storage != "none"
    assumptions: list[AssumptionUsed] = []

    def pick(name: str, farmer_value: float | None, default: float) -> float:
        value = default if farmer_value is None else farmer_value
        source = "default" if farmer_value is None else "farmer"
        assumptions.append(AssumptionUsed(name=name, value=value, source=source))
        return value

    if can_store:
        d = store.storage_default(req.crop, req.storage)
        costs = Costs(
            storage_cost_per_maund_week=pick(
                "storage_cost_per_maund_week", req.storage_cost_per_maund_week, d.storage_cost_per_maund_week
            ),
            spoilage_pct_week=pick("spoilage_pct_week", req.spoilage_pct_week, d.spoilage_pct_week),
            finance_cost_pct_month=pick(
                "finance_cost_pct_month",
                req.finance_cost_pct_month,
                store.meta.assumptions.finance_cost_pct_month.value,
            ),
        )
    else:
        costs = Costs(0.0, 0.0, 0.0)  # unused: the engine never stores when can_store is False

    others = []
    for m in store.mandis_for(req.crop):
        if m == req.mandi:
            continue
        other = store.forecast_at(req.crop, m, f.as_of)
        transport = store.transport_cost(req.mandi, m)
        if other is not None and transport is not None:
            others.append(OtherMandi(mandi=m, price_now=other.price_now, transport_cost_per_maund=transport))
            assumptions.append(
                AssumptionUsed(name=f"transport_to_{m}_per_maund", value=transport, source="default")
            )

    events = store.events_active(req.crop, f.as_of)
    alarm = store.alarm_at(req.crop, req.mandi, f.as_of)

    decision = decide(DecisionInput(
        price_now=f.price_now,
        band=[BandPoint(b.weeks_ahead, b.q10, b.q50, b.q90) for b in f.forecast],
        can_store=can_store,
        costs=costs,
        other_mandis=others,
        alert_active=bool(events),
    ))

    lang = req.lang
    mandi_names = {m.id: getattr(m, f"name_{lang}") for m in store.meta.mandis}
    best = decision.best_other
    return AdviceResponse(
        as_of=f.as_of,
        verdict=decision.verdict,
        verdict_text=phrasing.verdict_text(decision.verdict, lang),
        rupee_difference=round(decision.gain_per_maund * req.quantity_maund),
        best_week=decision.best_week,
        reasons=phrasing.reasons_text(decision.reasons, lang, mandi_names),
        risk_line=phrasing.risk_line(decision.lowest_price, decision.lowest_price_week, lang),
        alternative_mandi=AlternativeMandi(mandi=best.mandi, net_price=round(best.net_price)) if best else None,
        alerts=[EventRef(event_type=e.event_type, headline=e.headline, source_url=e.source_url) for e in events],
        alarm_tier=alarm.tier if alarm else None,
        assumptions=assumptions,
        data_source=store.forecasts.data_source,
        is_synthetic=store.forecasts.is_synthetic,
    )


@router.get("/alerts", response_model=AlertsResponse)
def alerts(request: Request, crop: str, mandi: str | None = None, as_of: AsOf = None) -> AlertsResponse:
    store = _store(request)
    if crop not in {c.id for c in store.meta.crops}:
        raise HTTPException(404, f"Unknown crop '{crop}'")
    if mandi is not None:
        _require_series(store, crop, mandi)
    on = as_of or store.meta.latest_as_of
    mandis = [mandi] if mandi else store.mandis_for(crop)
    found = [store.alarm_at(crop, m, on) for m in mandis]
    return AlertsResponse(
        crop=crop,
        as_of=on,
        alarms=[a for a in found if a is not None],
        events=store.events_active(crop, on),
        data_source=store.alarms.data_source,
        is_synthetic=store.alarms.is_synthetic,
    )


@router.get("/replay/{case_id}", response_model=ReplayResponse)
def replay(request: Request, case_id: str, lang: Lang = "ur") -> ReplayResponse:
    store = _store(request)
    case = store.case(case_id)
    if case is None:
        raise HTTPException(404, f"Unknown replay case '{case_id}'")
    return ReplayResponse(
        case_id=case.case_id,
        crop=case.crop,
        mandi=case.mandi,
        title=getattr(case, f"title_{lang}"),
        summary=getattr(case, f"summary_{lang}"),
        steps=case.steps,
        data_source=store.replay.data_source,
        is_synthetic=store.replay.is_synthetic,
    )


@router.get("/backtest", response_model=BacktestArtifact)
def backtest(request: Request) -> BacktestArtifact:
    return _store(request).backtest


app = create_app()
