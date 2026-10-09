"""Write the runtime tables (interface I5) to data/processed/runtime/.

Every value comes from data/processed/economics_inputs.json, the clean price files or the weather file,
and every row carries its source and confidence. Usage (repo root):
    .venv/Scripts/python -m ml.ingest.runtime_tables
"""

import csv
import io
import json
from datetime import date
from pathlib import Path

from ml.features import config as fcfg
from ml.ingest.frozen import FROZEN_MIN_DAYS, frozen_stretches, load_daily

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
OUT_DIR = PROCESSED / "runtime"
ECON_PATH = PROCESSED / "economics_inputs.json"
DAILY_PATH = PROCESSED / "farmsight_prices_clean_daily.csv"
WEEKLY_PATH = PROCESSED / "farmsight_prices_clean_weekly.csv"
WEATHER_PATH = PROCESSED / "weather_daily_2015_2026.csv"

ECON_FILE = "data/processed/economics_inputs.json"
KG_PER_MAUND = 40
STALE_AFTER_WEEKS = 8   # blueprint UC-01 A3: older prices show the date in amber and LOW confidence

DISPLAY_NAME = {"BahawalPur": "Bahawalpur", "Vehari": "Vehari", "RahimYarKhan": "Rahim Yar Khan"}
WEATHER_DISTRICT = {v: k for k, v in fcfg.WEATHER_CITY.items()}

# crop option -> (crop, variety, blueprint CropName, blueprint RiceVariety, season, key in economics_inputs.json)
CROP_OPTIONS = {
    "Wheat": ("Wheat", "none", "WHEAT", "NONE", "RABI", "wheat"),
    "Cotton": ("Cotton", "none", "COTTON", "NONE", "KHARIF", "cotton_seed_cotton"),
    "IRRI": ("Rice", "IRRI", "RICE", "IRRI", "KHARIF", "rice_irri_paddy"),
    "SuperBasmati": ("Rice", "SuperBasmati", "RICE", "SUPER_BASMATI", "KHARIF", "rice_super_basmati_paddy"),
}


def _sources(entry: dict) -> str:
    src = entry.get("source") or []
    src = [src] if isinstance(src, str) else src
    if "formula" in entry:
        src = [*src, f"formula: {entry['formula']}"]
    return " | ".join(src)


def _with_official(entry: dict, official: dict) -> str:
    """A derived value cites the official table it was derived from, then the formula."""
    if entry.get("source"):
        return _sources(entry)
    return " | ".join(s for s in (_sources(official), _sources(entry)) if s)


def render(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def crops_table(econ: dict) -> list[dict]:
    cop = econ["cost_of_production_punjab"]
    milling = cop["rice_irri_paddy"]["paddy_to_milled_rice_yield"]
    rows = []
    for option_id, (option, (crop, variety, name, rice_variety, season, key)) in enumerate(CROP_OPTIONS.items()):
        e = cop[key]
        if option == "Wheat":
            cost40, cost40_entry = e["estimate_2026"]["market_level_incl_rent"], e["estimate_2026"]
            acre_entry = e["estimate_2026_per_acre"]
            official = e["official_2023_24"]
            yield_kg, yield_unit = official["yield_kg_per_acre"], "grain"
        elif option == "Cotton":
            cost40, cost40_entry = e["estimate_2026"]["market_ginnery_level_rs_per_40kg"], e["estimate_2026"]
            acre_entry = e["estimate_2026"]
            official = e["official_2022_23"]
            yield_kg, yield_unit = official["yield_kg_per_acre"], "seed cotton"
        else:
            cost40, cost40_entry = e["milled_equivalent_rs_per_40kg"]["value"], e["milled_equivalent_rs_per_40kg"]
            acre_entry = e["estimate_2026"]
            official = e["official_2022_23"]
            yield_kg, yield_unit = official["yield_kg_paddy_per_acre"], "paddy"
        is_rice = crop == "Rice"
        rows.append({
            "id": option_id,
            "crop_option": option,
            "amis_crop": crop,
            "amis_variety": variety,
            "name": name,
            "variety": rice_variety,
            "season": season,
            "production_cost_per_40kg": cost40,
            "cost_unit": "Rs per 40 kg, milled-rice equivalent" if is_rice else "Rs per 40 kg",
            "cost_source": _with_official(cost40_entry, official),
            "cost_confidence": cost40_entry["confidence"],
            "production_cost_per_acre": acre_entry["net_cost_rs_per_acre"],
            "cost_per_acre_source": _with_official(acre_entry, official),
            "cost_per_acre_confidence": acre_entry["confidence"],
            "yield_maund_per_acre": yield_kg / KG_PER_MAUND,
            "yield_unit": yield_unit,
            "yield_source": _sources(official),
            "yield_confidence": official["confidence"],
            "milling_yield": milling["value"] if is_rice else "",
            "milling_yield_confidence": milling["confidence"] if is_rice else "",
        })
    return rows


def mandis_table() -> list[dict]:
    coords: dict[str, tuple[str, str]] = {}
    with WEATHER_PATH.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            coords.setdefault(r["district"], (r["lat"], r["lon"]))
    rows = []
    for mandi_id, amis_name in enumerate(fcfg.CITY_ID):
        lat, lon = coords[WEATHER_DISTRICT[amis_name]]
        rows.append({
            "id": mandi_id,
            "name": DISPLAY_NAME[amis_name],
            "amis_name": amis_name,
            "weather_district": WEATHER_DISTRICT[amis_name],
            "latitude": lat,
            "longitude": lon,
            "source": "coordinates used for the Open-Meteo weather download (weather_daily_2015_2026.csv)",
            "confidence": "high",
        })
    return rows


def calendar_table() -> list[dict]:
    rows = []
    for option, (crop, *_rest) in CROP_OPTIONS.items():
        cal = fcfg.CROP_CALENDAR[crop]
        rows.append({
            "crop_option": option,
            "sowing_start_month": cal["sow"][0],
            "sowing_end_month": cal["sow"][1],
            "harvest_start_month": cal["harvest"][0],
            "harvest_end_month": cal["harvest"][1],
            "source": "general Punjab crop calendar used by the feature pipeline (ml/features/config.py); "
                      "not yet checked against an official calendar",
            "confidence": "assumption",
        })
    return rows


def support_prices_table(econ: dict) -> list[dict]:
    rows = []
    by_year = econ["support_and_government_prices_rs_per_40kg"]["wheat"]["by_crop_year"]
    for label, e in by_year.items():
        price = e["value"] if e.get("value") is not None else e.get("announced_notional")
        if price is None or e.get("status") not in ("PROCURED", "ANNOUNCED_NOT_PROCURED"):
            continue  # unknown, not announced or not yet announced: left out on purpose
        rows.append({
            "crop_option": "Wheat",
            "crop_year": label,
            "year": int(label[:4]),
            "harvest": e["harvest"],
            "price_per_40kg": price,
            "status": e["status"],
            "source": _sources(e) or f"{ECON_FILE} (no link recorded)",
            "confidence": e.get("confidence", "medium"),
            "note": e.get("note", ""),
        })
    return rows


def transport_table(econ: dict) -> list[dict]:
    t = econ["transport"]
    rate = t["rate_rs_per_40kg_per_km"]
    dist = t["distance_km"]
    rows = []
    for a in fcfg.CITY_ID:
        for b, to_id in fcfg.CITY_ID.items():
            km = 0 if a == b else (dist.get(f"{a}_{b}") or dist.get(f"{b}_{a}"))["road_est"]
            rows.append({
                "from_district": DISPLAY_NAME[a],
                "to_mandi_id": to_id,
                "to_mandi": b,
                "distance_km": km,
                "cost_per_40kg": round(km * rate["value"], 2),
                "distance_source": f"{ECON_FILE}: {dist['formula']}",
                "distance_confidence": dist["confidence"],
                "rate_rs_per_40kg_per_km": rate["value"],
                "rate_confidence": rate["confidence"],
            })
    return rows


def series_coverage_table() -> tuple[list[dict], date]:
    stats: dict[tuple[str, str, str], dict] = {}
    with DAILY_PATH.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            key = (r["city"], r["crop"], r["variety"])
            s = stats.setdefault(key, {"first": r["date"], "last": r["date"], "n": 0, "last_price": None})
            s["first"] = min(s["first"], r["date"])
            if r["date"] >= s["last"]:
                s["last"], s["last_price"] = r["date"], r["price_rs_per_40kg"]
            s["n"] += 1
    snapshot = max(date.fromisoformat(s["last"]) for s in stats.values())
    weekly_obs: dict[tuple[str, str, str], int] = {}
    with WEEKLY_PATH.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["filled"] == "0":
                key = (r["city"], r["crop"], r["variety"])
                weekly_obs[key] = weekly_obs.get(key, 0) + 1
    rows = []
    for (city, crop, variety), s in sorted(stats.items()):
        option = fcfg.CROP_OPTION[(crop, variety)]
        age_weeks = (snapshot - date.fromisoformat(s["last"])).days // 7
        rows.append({
            "series": f"{city}|{crop}|{variety}",
            "mandi": city,
            "crop_option": option,
            "first_price_date": s["first"],
            "prices_as_of": s["last"],
            "latest_price_per_40kg": s["last_price"],
            "daily_observations": s["n"],
            "observed_weeks": weekly_obs.get((city, crop, variety), 0),
            "weeks_old_at_snapshot": age_weeks,
            "is_stale": int(age_weeks > STALE_AFTER_WEEKS),
            "source": "AMIS Punjab daily mandi prices (amis.pk), cleaned: data/processed/cleaning_report.txt",
            "unit_stored": "100kg",
            "is_synthetic": 0,
        })
    return rows, snapshot


def data_sources_table(econ: dict, snapshot: date) -> list[dict]:
    return [
        {"id": 1, "name": "AMIS.pk", "type": "OFFLINE", "last_refreshed": snapshot.isoformat(),
         "url": "http://www.amis.pk", "covers": "daily wholesale mandi prices 2015 to Oct 2026"},
        {"id": 2, "name": "Open-Meteo", "type": "LIVE", "last_refreshed": "",
         "url": "https://open-meteo.com", "covers": "historical weather (offline file to 2026-10-01) and live weather"},
        {"id": 3, "name": "Agriculture Policy Institute cost tables", "type": "OFFLINE",
         "last_refreshed": "2022-23 rice and cotton; 2023-24 wheat", "url": "https://api.gov.pk/Policies",
         "covers": "cost of production and yields, Punjab"},
        {"id": 4, "name": "economics_inputs.json", "type": "OFFLINE", "last_refreshed": econ["_meta"]["compiled"],
         "url": ECON_FILE, "covers": "support prices, interest, transport, macro values, each with its own source"},
    ]


def frozen_table() -> list[dict]:
    rows = []
    for series, daily in load_daily().items():
        city, crop, variety = series.split("|")
        for s in frozen_stretches(daily):
            rows.append({
                "series": series,
                "mandi": city,
                "crop_option": fcfg.CROP_OPTION[(crop, variety)],
                "from_date": s["from"],
                "to_date": s["to"],
                "reported_days": s["days"],
                "price_per_40kg": s["price"],
                "source": f"derived from AMIS daily prices: the same price on at least {FROZEN_MIN_DAYS} "
                          "reported days in a row (ml/ingest/frozen.py); likely stale reporting",
            })
    return rows


def build_all() -> dict[str, list[dict]]:
    econ = json.loads(ECON_PATH.read_text(encoding="utf-8"))
    coverage, snapshot = series_coverage_table()
    return {
        "crops.csv": crops_table(econ),
        "mandis.csv": mandis_table(),
        "crop_calendar.csv": calendar_table(),
        "support_prices.csv": support_prices_table(econ),
        "transport_costs.csv": transport_table(econ),
        "series_coverage.csv": coverage,
        "frozen_stretches.csv": frozen_table(),
        "data_sources.csv": data_sources_table(econ, snapshot),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, rows in build_all().items():
        path = OUT_DIR / name
        path.write_text(render(rows), encoding="utf-8", newline="")
        print(f"{path.relative_to(ROOT)}: {len(rows)} rows")


if __name__ == "__main__":
    main()
