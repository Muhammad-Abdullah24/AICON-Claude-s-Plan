"""Live weather for the forecast (task C5, blueprint UC-13). Standard library only.

Fetches the last 92 days of daily weather from Open-Meteo, so the model gets exactly the weekly and 4- and
12-week aggregates it was trained on (ml.features.weather_features). Cached per mandi for an hour. If the API
is down, the newest offline history (data/processed/weather_daily_2015_2026.csv) is used and marked cached.
Open-Meteo data is CC BY 4.0: show WEATHER_ATTRIBUTION with a link wherever weather appears.
"""

from __future__ import annotations

import csv
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from ml.features import config as fcfg
from ml.features.core import monday_of, weather_features

ROOT = Path(__file__).resolve().parents[2]
OFFLINE = ROOT / "data" / "processed" / "weather_daily_2015_2026.csv"
API = "https://api.open-meteo.com/v1/forecast"
DAILY = "temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_mean,et0_fao_evapotranspiration"
CACHE_SECONDS = 3600
WEATHER_ATTRIBUTION = "Weather data by Open-Meteo.com"
WEATHER_URL = "https://open-meteo.com/"

log = logging.getLogger("farmsight.weather")
_cache: dict[str, tuple[float, dict]] = {}

COORDS = {  # the coordinates used for the offline weather download (runtime/mandis.csv)
    "BahawalPur": (29.3956, 71.6722), "Vehari": (30.0445, 72.3484), "RahimYarKhan": (28.4212, 70.2989),
}


def fetch_open_meteo(lat: float, lon: float, timeout: float = 8.0) -> list[dict]:
    q = urllib.parse.urlencode({"latitude": lat, "longitude": lon, "daily": DAILY, "past_days": 92,
                                "forecast_days": 1, "timezone": "Asia/Karachi"})
    with urllib.request.urlopen(f"{API}?{q}", timeout=timeout) as resp:
        d = json.loads(resp.read())["daily"]
    rows = []
    for i, day in enumerate(d["time"]):
        values = [d[k][i] for k in DAILY.split(",")]
        if None in values:
            continue
        tmax, tmin, rain, rh, et0 = values
        rows.append({"date": day, "tmax": tmax, "tmin": tmin, "precip_mm": rain, "rh_mean": rh, "et0": et0})
    return rows


@lru_cache(maxsize=1)
def _offline() -> dict[str, list[dict]]:
    by_city: dict[str, list[dict]] = {}
    with OFFLINE.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            city = fcfg.WEATHER_CITY.get(r["district"])
            if city:
                by_city.setdefault(city, []).append(r)
    return by_city


def _summary(daily: list[dict], cached: bool, source: str, fetched: datetime) -> dict:
    last = max(d["date"] for d in daily)
    last = last if isinstance(last, date) else date.fromisoformat(last)
    # The week the model needs is the latest one with most of its days observed.
    week = monday_of(last) if last.weekday() >= 4 else monday_of(last) - timedelta(days=7)
    feats = weather_features(daily, week)
    return {"week_start": week, **{k: feats[k] for k in ("tmax_c", "tmin_c", "precip_mm_wk", "rh_pct",
                                                        "precip_mm_4w", "hot_days_wk")},
            "features": feats, "cached": cached, "source": source, "fetched_at": fetched,
            "attribution": WEATHER_ATTRIBUTION}


def current(mandi: str, fetch=None, clock=time.time) -> dict:
    """Weather features for a mandi (data name, e.g. "BahawalPur"): live, cached, or offline."""
    hit = _cache.get(mandi)
    if hit and clock() - hit[0] < CACHE_SECONDS:
        return hit[1]   # a fresh reading from the last hour; "cached" is kept for "live API failed"
    lat, lon = COORDS[mandi]
    try:
        daily = (fetch or fetch_open_meteo)(lat, lon)
        if not daily:
            raise ValueError("no days")
        out = _summary(daily, False, "open-meteo", datetime.now(UTC))
        _cache[mandi] = (clock(), out)
        return out
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e:
        log.warning("weather: Open-Meteo unavailable for %s (%s); using the latest offline history", mandi,
                    type(e).__name__)
        if hit:
            return {**hit[1], "cached": True}
        rows = _offline()[mandi][-92:]
        return _summary(rows, True, "offline file", datetime.now(UTC))
