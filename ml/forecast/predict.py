"""Interface I2 (Owner B): `forecast(crop_option, mandi, as_of, weather) -> dict`.

What is deployed (docs/MODEL_CARD.md, artifacts/models/deployed.json):

- Price and range: the persistence-band BASELINE. The XGBoost model did not beat persistence on validation
  (NFR-01), so the forecast is today's AMIS price and the range is today's price moved by the q10 and q90 of
  past 4-week changes for the crop option. The predicted change is 0%, so trend is STABLE.
- Direction: the XGBoost model's call ("UP" / "DOWN"), only for DIRECTION_CROP_OPTIONS, where it showed skill
  on validation (wheat: 72% of moves > 3%). The model's price is never shown. Its SHAP reasons (ml/explain)
  fill `shap`. Other crop options get `direction: None` and `shap: []`.

This is the only runtime module that imports xgboost (CLAUDE.md).
"""

from __future__ import annotations

import csv
import json
import logging
from collections.abc import Iterable, Mapping
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from ml.explain import reasons
from ml.features import runtime_features
from ml.features.build import load_weather, load_weekly
from ml.features.config import CROP_OPTION, HORIZON_WEEKS
from ml.features.core import monday_of

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "data" / "processed" / "runtime"
MODELS_DIR = ROOT / "artifacts" / "models"
DEPLOYED_PATH = MODELS_DIR / "deployed.json"
DIRECTION_MODEL_PATH = MODELS_DIR / "price_point.json"
DIRECTION_META_PATH = MODELS_DIR / "price_meta.json"

# Crop options whose direction call is shown (team proposal in docs/MODEL_CARD.md). Empty tuple = off.
DIRECTION_CROP_OPTIONS = ("Wheat",)

DATA_SOURCE = "amis"
UNIT = "40kg"
# Volatility bands on the half-width of the q10-q90 range, in % of today's price (blueprint glossary).
VOLATILITY_BANDS_PCT = ((5.0, "STABLE"), (15.0, "MODERATE"))

_OPTION_TO_AMIS = {option: amis for amis, option in CROP_OPTION.items()}
log = logging.getLogger(__name__)


# ---------------------------------------------------------------- loading (cached; read once per process)

@lru_cache(maxsize=1)
def _mandi_names() -> dict[str, str]:
    """Display name or AMIS name -> AMIS name, from the runtime table (never hardcoded)."""
    with open(RUNTIME / "mandis.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return {**{r["amis_name"]: r["amis_name"] for r in rows}, **{r["name"]: r["amis_name"] for r in rows}}


@lru_cache(maxsize=1)
def _crop_options() -> frozenset[str]:
    with open(RUNTIME / "crops.csv", encoding="utf-8", newline="") as f:
        return frozenset(row["crop_option"] for row in csv.DictReader(f))


@lru_cache(maxsize=1)
def _weekly() -> dict[tuple[str, str, str], list[dict]]:
    return load_weekly()


@lru_cache(maxsize=1)
def _weather_by_week() -> dict:
    return load_weather()


@lru_cache(maxsize=1)
def _deployed() -> dict:
    return json.loads(DEPLOYED_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _direction_model():
    """(booster, feature names, meta), or None when no model is saved or xgboost is not installed."""
    if not DIRECTION_MODEL_PATH.exists():
        return None
    try:
        import xgboost as xgb
    except ImportError:
        log.warning("xgboost is not installed, so the direction call is off: "
                    "pip install -r ml/forecast/requirements.txt")
        return None

    booster = xgb.Booster()
    booster.load_model(DIRECTION_MODEL_PATH)
    meta = json.loads(DIRECTION_META_PATH.read_text(encoding="utf-8"))
    return booster, meta["features"], meta


# ---------------------------------------------------------------- pieces

def _volatility(half_width_pct: float) -> str:
    for limit, label in VOLATILITY_BANDS_PCT:
        if half_width_pct < limit:
            return label
    return "VOLATILE"


def _daily_weather_for(city: str, weather: Iterable[Mapping] | None) -> list[Mapping]:
    """Live daily records from the weather service, or the stored daily history for this mandi."""
    if weather is not None:
        return list(weather)
    return [rec for days in _weather_by_week().get(city, {}).values() for rec in days]


def _direction(crop_option: str, city: str, history: list[dict], daily: list[Mapping],
               week_start: date, current_price: float) -> tuple[dict | None, list[dict]]:
    """The model's UP / DOWN call and its SHAP reasons, or (None, []) without a model or features."""
    loaded = _direction_model()
    if loaded is None:
        return None, []
    booster, features, meta = loaded
    crop, variety = _OPTION_TO_AMIS[crop_option]
    row = runtime_features(
        city, crop, variety, [(h["week_start"], h["price"], h["filled"]) for h in history], daily, week_start,
    )
    if row is None:
        return None, []

    import xgboost as xgb

    values = [[float("nan") if row[f] is None else float(row[f]) for f in features]]
    data = xgb.DMatrix(values, feature_names=features)
    change = float(booster.predict(data)[0])
    contribs = booster.predict(data, pred_contribs=True)[0]
    shap = reasons(dict(zip([*features, "bias"], map(float, contribs), strict=True)), current_price)
    call = {
        "call": "UP" if change > 0 else "DOWN",
        "model_version": meta.get("version"),
        "validation_accuracy_pct": meta.get("direction_accuracy_pct", {}).get(crop_option),
    }
    return call, shap


# ---------------------------------------------------------------- interface I2

def forecast(
    crop_option: str,
    mandi: str,
    as_of: date | None = None,
    weather: Iterable[Mapping] | None = None,
) -> dict | None:
    """4-week forecast for one crop option at one mandi, using only data from weeks on or before `as_of`.

    `crop_option` is Wheat, Cotton, IRRI or SuperBasmati. `mandi` is the display name ("Rahim Yar Khan") or
    the AMIS name ("RahimYarKhan"). `as_of` defaults to the latest data. `weather` is a list of daily records
    ({date, tmax, tmin, precip_mm, rh_mean, et0}) from the live weather service; None uses the stored history.

    Returns None when the series has no observed price on or before `as_of` (e.g. IRRI at Rahim Yar Khan).
    Raises ValueError for an unknown crop option or mandi.
    """
    if crop_option not in _crop_options() or crop_option not in _OPTION_TO_AMIS:
        raise ValueError(f"unknown crop option: {crop_option!r}")
    city = _mandi_names().get(mandi)
    if city is None:
        raise ValueError(f"unknown mandi: {mandi!r}")
    crop, variety = _OPTION_TO_AMIS[crop_option]

    cutoff = monday_of(as_of) if as_of is not None else None
    history = [h for h in _weekly().get((city, crop, variety), []) if cutoff is None or h["week_start"] <= cutoff]
    observed = [h for h in history if h["filled"] == 0]
    if not observed:
        return None
    latest = observed[-1]
    prices_as_of, current = latest["week_start"], latest["price"]

    deployed = _deployed()
    band = deployed["band_change_pct"][crop_option]
    q10, q90 = current * (1 + band["q10"] / 100), current * (1 + band["q90"] / 100)

    direction, shap = None, []
    if crop_option in DIRECTION_CROP_OPTIONS:
        daily = _daily_weather_for(city, weather)
        direction, shap = _direction(crop_option, city, history, daily, prices_as_of, current)

    return {
        "crop_option": crop_option,
        "mandi": city,
        "unit": UNIT,
        "current_price": round(current, 2),
        "predicted_price": round(current, 2),
        "q10": round(q10, 2),
        "q90": round(q90, 2),
        "trend": "STABLE",
        "volatility": _volatility((q90 - q10) / 2 / current * 100),
        "prices_as_of": prices_as_of.isoformat(),
        "target_date": (prices_as_of + timedelta(weeks=HORIZON_WEEKS)).isoformat(),
        "forecast_type": "baseline",
        "model_version": f"{deployed['deployed']}@{deployed['written_at'][:10]}",
        "direction": direction,
        "shap": shap,
        "data_source": DATA_SOURCE,
        "is_synthetic": False,
    }
