import pytest

from ml.ingest.runtime_tables import OUT_DIR, render
from ml.seasonal import tables


@pytest.fixture(scope="module")
def built():
    return tables.build_all()


def test_committed_tables_match_a_fresh_build(built):
    for name, rows in built.items():
        assert (OUT_DIR / name).read_text(encoding="utf-8") == render(rows), name


def test_add_months_wraps_the_year():
    assert tables.add_months((2025, 11), 3) == (2026, 2)
    assert tables.add_months((2026, 2), -5) == (2025, 9)


def test_next_harvest_is_the_upcoming_one():
    assert tables._next_harvest_start((2025, 10), "Wheat") == (2026, 4)
    assert tables._next_harvest_start((2026, 2), "Wheat") == (2026, 4)
    assert tables._next_harvest_start((2026, 4), "Wheat") == (2027, 4)   # in harvest: the next one


def _flat_daily(series=("Vehari", "Wheat", "none"), years=range(2018, 2024), price=3000.0):
    city, crop, variety = series
    return [{"city": city, "crop": crop, "variety": variety, "date": f"{y}-{m:02d}-{d:02d}",
             "price_rs_per_40kg": str(price)} for y in years for m in range(1, 13) for d in (1, 10, 20)]


def test_flat_prices_give_index_100_and_ratio_1():
    monthly = tables.monthly_means(_flat_daily())
    assert {r["index_median"] for r in tables.seasonal_index(monthly) if r["n_years"]} == {100.0}
    assert {r["ratio_median"] for r in tables.harvest_ratios(monthly) if r["n_years"]} == {1.0}
    assert {r["ratio_median"] for r in tables.post_harvest_ratios(monthly) if r["n_years"]} == {1.0}


def test_thin_months_are_not_trusted():
    daily = [r for r in _flat_daily() if not (r["date"].endswith("-20") or r["date"].endswith("-10"))]
    assert tables.monthly_means(daily) == {}   # one price a month is below MIN_OBS_PER_MONTH


def test_scope_and_flags(built):
    series = {r["series"] for r in built["harvest_ratios.csv"]}
    assert len(series) == 11 and "RahimYarKhan|Rice|IRRI" not in series
    for rows in built.values():
        for r in rows:
            assert r["enough_years"] == int(r["n_years"] >= tables.ENOUGH_YEARS)


def test_cotton_has_no_spring_mandi_price(built):
    spring = [r for r in built["harvest_ratios.csv"]
              if r["series"] == "Vehari|Cotton|none" and r["ref_month"] in (4, 5)]
    assert spring and all(r["n_years"] == 0 for r in spring)


def test_wheat_peaks_before_harvest_and_dips_at_harvest(built):
    idx = {r["month"]: r["index_median"] for r in built["seasonal_index.csv"] if r["series"] == "BahawalPur|Wheat|none"}
    assert min(idx[2], idx[3]) > max(idx[5], idx[6])
