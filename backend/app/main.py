"""FarmSight API (docs/BLUEPRINT.md section 12). Run from the repo root:

    python -m uvicorn backend.app.main:app --reload

Every route is a thin layer over backend/app/services.py (interface I6), which WhatsApp and chat also use, so
every channel gives the same answer. `as_of` on read routes is the time-machine rule: only data on or before
that date is used (for replaying past weeks in the demo).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from backend.app import db, services, weather
from backend.app.auth import current_farmer, make_token, optional_farmer
from backend.app.channels import whatsapp
from backend.app.chat import router as chat_router
from backend.app.config import Settings, get_settings
from backend.app.ids import CROP_FROM_DATA, CROP_NAMES, CROP_TO_DATA, MANDI_FROM_DATA, MANDI_NAMES, MANDI_TO_DATA
from backend.app.schemas import (
    AdviceResponse,
    CompareResponse,
    CropId,
    CropPlanResponse,
    ExplainResponse,
    Farmer,
    FarmerIn,
    FarmerUpdate,
    ForecastResponse,
    Health,
    HistoryResponse,
    LoginRequest,
    MandiId,
    MarginResponse,
    Meta,
    OfferCheckRequest,
    OfferCheckResponse,
    TokenResponse,
    WeatherResponse,
)

AsOf = Annotated[dt.date | None, Query(description="Use only data on or before this date. Omit for the latest.")]
Quantity = Annotated[float | None, Query(gt=0, le=1_000_000, description="Maund. Default: profile, else 100.")]
DEFAULT_QUANTITY = 100.0
DEFAULT_LAND_ACRES = 10.0


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db.connect()
        services._data()  # load and check the data files at start-up, not on the first request
        yield

    app = FastAPI(title="FarmSight API", version="0.2.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.include_router(router)
    app.include_router(whatsapp.router)      # GET/POST /webhooks/whatsapp (Meta Cloud API)
    app.include_router(chat_router.router)   # POST /api/chat

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse("/docs")

    @app.get("/health", response_model=Health, tags=["ops"])
    def health() -> Health:
        return Health(status="ok")

    return app


router = APIRouter(prefix="/api", tags=["api"])
LABEL = {"data_source": "amis", "is_synthetic": False}


def _guard(call, *args, **kwargs):
    """A LookupError from the service layer is a 404 with the reason, never a 500."""
    try:
        return call(*args, **kwargs)
    except LookupError as e:
        raise HTTPException(404, str(e).strip("'")) from e


def _quantity(farmer: dict | None, crop: str, quantity: float | None) -> float:
    if quantity is not None:
        return quantity
    for c in (farmer or {}).get("crops", []):
        if c["crop"] == crop:
            return c["harvest_quantity_maund"]
    return DEFAULT_QUANTITY


def _farmer_out(f: dict) -> Farmer:
    return Farmer(**{**f, "phone": "+" + f["phone"]})


# ---------------------------------------------------------------- meta

@router.get("/meta", response_model=Meta)
def meta() -> Meta:
    m = services.meta()
    return Meta(
        **LABEL, unit="40kg", price_type="wholesale",
        crops=[{"id": CROP_FROM_DATA[c["crop_option"]], "name_ur": CROP_NAMES[CROP_FROM_DATA[c["crop_option"]]][0],
                "name_en": CROP_NAMES[CROP_FROM_DATA[c["crop_option"]]][1], "season": c["season"],
                "sowing_months": c["sowing_months"], "harvest_months": c["harvest_months"]} for c in m["crops"]],
        mandis=[{"id": k, "name_ur": v[0], "name_en": v[1]} for k, v in MANDI_NAMES.items()],
        series=[{"crop": CROP_FROM_DATA[s["crop_option"]], "mandi": MANDI_FROM_DATA[s["mandi"]],
                 "prices_as_of": s["prices_as_of"], "latest_price": s["latest_price"], "is_stale": s["is_stale"]}
                for s in sorted(m["series"], key=lambda s: (s["crop_option"], s["mandi"]))],
        prices_as_of=m["prices_as_of"], horizon_weeks=services.HORIZON_WEEKS,
        wait_threshold_pct=services.WAIT_THRESHOLD_PCT, interest_pct_per_month=m["interest_pct_month"],
        sources=m["sources"],
    )


# ---------------------------------------------------------------- forecast, explain, history, weather

def _weather_features(mandi: str, as_of: dt.date | None) -> dict | None:
    """Live weather only matters to a trained model, and never for a past date (it would be today's weather)."""
    if as_of is not None or not services.model_available():
        return None
    return weather.current(mandi)["features"]


@router.get("/forecast", response_model=ForecastResponse)
def forecast(crop: CropId, mandi: MandiId, as_of: AsOf = None) -> ForecastResponse:
    c, m = CROP_TO_DATA[crop], MANDI_TO_DATA[mandi]
    f = _guard(services.forecast_view, c, m, as_of, _weather_features(m, as_of))
    h = services.history(c, m, as_of)
    return ForecastResponse(
        crop=crop, mandi=mandi, unit="40kg", prices_as_of=f["prices_as_of"],
        current_price=round(f["current_price"], 2), predicted_price=round(f["predicted_price"], 2),
        range={"low": round(f["q10"], 2), "high": round(f["q90"], 2)}, horizon_weeks=services.HORIZON_WEEKS,
        trend=f["trend"], volatility=f["volatility"], confidence=f["confidence"],
        model=f.get("model_version", services.BASELINE_MODEL), is_stale=f["is_stale"],
        price_unchanged_since=f["price_unchanged_since"],
        history=[{"date": d, "price": p} for d, p in h["weekly"]],
        data_source=f.get("data_source", "amis"), is_synthetic=bool(f.get("is_synthetic", False)),
    )


@router.get("/explain", response_model=ExplainResponse)
def explain(crop: CropId, mandi: MandiId, as_of: AsOf = None) -> ExplainResponse:
    c, m = CROP_TO_DATA[crop], MANDI_TO_DATA[mandi]
    f = _guard(services.forecast, c, m, as_of)
    reasons = services.get_explanation(c, m, as_of)
    return ExplainResponse(**LABEL, crop=crop, mandi=mandi, prices_as_of=f["prices_as_of"],
                           source="shap" if f.get("shap") else "facts", reasons=reasons)


@router.get("/history", response_model=HistoryResponse)
def history(crop: CropId, mandi: MandiId, as_of: AsOf = None) -> HistoryResponse:
    h = _guard(services.history, CROP_TO_DATA[crop], MANDI_TO_DATA[mandi], as_of)
    return HistoryResponse(**LABEL, crop=crop, mandi=mandi, unit="40kg", prices_as_of=h["prices_as_of"],
                           weekly=[{"date": d, "price": p} for d, p in h["weekly"]], seasonal=h["seasonal"],
                           sowing_months=h["sowing_months"], harvest_months=h["harvest_months"])


@router.get("/weather", response_model=WeatherResponse)
def current_weather(mandi: MandiId) -> WeatherResponse:
    w = weather.current(MANDI_TO_DATA[mandi])
    return WeatherResponse(mandi=mandi, weather={k: v for k, v in w.items() if k != "features"})


# ---------------------------------------------------------------- advice, compare, offer, margin, crop plan

@router.get("/advice", response_model=AdviceResponse)
def advice(crop: CropId, mandi: MandiId, quantity_maund: Quantity = None, as_of: AsOf = None,
           farmer: dict | None = Depends(optional_farmer)) -> AdviceResponse:  # noqa: B008
    qty = _quantity(farmer, crop, quantity_maund)
    a = _guard(services.get_advice, CROP_TO_DATA[crop], MANDI_TO_DATA[mandi], qty, None, as_of)
    if farmer:
        db.log_recommendation(farmer["id"], crop, mandi, a)
    keep = AdviceResponse.model_fields.keys() - {"crop", "mandi"}
    return AdviceResponse(crop=crop, mandi=mandi, **{k: a[k] for k in keep})


@router.get("/compare-mandis", response_model=CompareResponse)
def compare_mandis(crop: CropId, mandi: MandiId, quantity_maund: Quantity = None, as_of: AsOf = None,
                   farmer: dict | None = Depends(optional_farmer)) -> CompareResponse:  # noqa: B008
    qty = _quantity(farmer, crop, quantity_maund)
    rows = _guard(services.compare_mandis, CROP_TO_DATA[crop], MANDI_TO_DATA[mandi], qty, as_of)
    return CompareResponse(**LABEL, crop=crop, from_mandi=mandi, unit="40kg", quantity_maund=qty,
                           rows=[{**r, "mandi": MANDI_FROM_DATA[r["mandi"]]} for r in rows],
                           transport_is_estimate=True)


@router.post("/offer-check", response_model=OfferCheckResponse)
def offer_check(body: OfferCheckRequest, as_of: AsOf = None) -> OfferCheckResponse:
    r = _guard(services.offer_check, CROP_TO_DATA[body.crop], MANDI_TO_DATA[body.mandi], body.offer_price,
               body.quantity_maund, as_of)
    return OfferCheckResponse(**LABEL, crop=body.crop, mandi=body.mandi, unit="40kg", offer_price=body.offer_price, **r)


@router.get("/margin", response_model=MarginResponse)
def margin(crop: CropId, price: Annotated[float, Query(gt=0, le=1_000_000)],
           arhti_pct: Annotated[float | None, Query(ge=0, le=50)] = None,
           farmer: dict | None = Depends(optional_farmer)) -> MarginResponse:  # noqa: B008
    pct = arhti_pct if arhti_pct is not None else (farmer or {}).get("arhti_commission_pct")
    m = services.margin(CROP_TO_DATA[crop], price, pct)
    return MarginResponse(**LABEL, crop=crop, unit="40kg", price=price, **m)


@router.get("/crop-plan", response_model=CropPlanResponse)
def crop_plan(mandi: MandiId | None = None,
              land_area_acres: Annotated[float | None, Query(gt=0, le=100_000)] = None, as_of: AsOf = None,
              farmer: dict | None = Depends(optional_farmer)) -> CropPlanResponse:  # noqa: B008
    where = mandi or (farmer or {}).get("district") or "bahawalpur"
    acres = land_area_acres or (farmer or {}).get("land_area_acres") or DEFAULT_LAND_ACRES
    p = services.crop_plan(MANDI_TO_DATA[where], acres, as_of)
    items = [{**{k: v for k, v in i.items() if k != "crop_option"}, "crop": CROP_FROM_DATA[i["crop_option"]]}
             for i in p["items"]]
    return CropPlanResponse(**LABEL, mandi=where, land_area_acres=acres, items=items,
                            not_available=[CROP_FROM_DATA[c] for c in p["not_available"]], is_estimate=True)


# ---------------------------------------------------------------- farmers and login

@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login(body: LoginRequest) -> TokenResponse:
    f = db.get_farmer_by_phone(body.phone)
    if f is None:
        raise HTTPException(404, "No farmer with this phone number. Register first.")
    return TokenResponse(token=make_token(f["id"]), farmer=_farmer_out(f))


@router.post("/farmers", response_model=TokenResponse, status_code=201, tags=["auth"])
def register(body: FarmerIn) -> TokenResponse:
    try:
        f = db.create_farmer(body.model_dump())
    except ValueError as e:
        raise HTTPException(409, "This phone number is already registered. Log in instead.") from e
    return TokenResponse(token=make_token(f["id"]), farmer=_farmer_out(f))


@router.get("/farmers/me", response_model=Farmer, tags=["auth"])
def me(farmer: dict = Depends(current_farmer)) -> Farmer:  # noqa: B008
    return _farmer_out(farmer)


@router.put("/farmers/me", response_model=Farmer, tags=["auth"])
def update_me(body: FarmerUpdate, farmer: dict = Depends(current_farmer)) -> Farmer:  # noqa: B008
    changes = body.model_dump(exclude_unset=True)
    if "crops" in changes and changes["crops"] is not None:
        changes["crops"] = [dict(c) for c in changes["crops"]]
    return _farmer_out(db.update_farmer(farmer["id"], changes))


app = create_app()
