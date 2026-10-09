import csv
import io
import json

import pytest

from ml.ingest.runtime_tables import ECON_PATH, OUT_DIR, build_all, render


@pytest.fixture(scope="module")
def tables():
    return build_all()


def read(name):
    return list(csv.DictReader(io.StringIO((OUT_DIR / name).read_text(encoding="utf-8"))))


def test_committed_tables_match_a_fresh_build(tables):
    for name, rows in tables.items():
        assert (OUT_DIR / name).read_text(encoding="utf-8") == render(rows), name


def test_every_value_has_a_source_and_confidence(tables):
    for name, rows in tables.items():
        if name == "data_sources.csv":
            continue
        for row in rows:
            for col, value in row.items():
                if col.endswith(("source", "confidence")):
                    paired_value = col.replace("_source", "").replace("_confidence", "")
                    if paired_value in row and row[paired_value] in ("", None):
                        continue  # no value, so nothing to source (e.g. milling yield for wheat)
                    assert value not in ("", None), (name, col, row)


def test_costs_come_from_economics_inputs(tables):
    cop = json.loads(ECON_PATH.read_text(encoding="utf-8"))["cost_of_production_punjab"]
    cost = {r["crop_option"]: r["production_cost_per_40kg"] for r in tables["crops.csv"]}
    assert cost["Wheat"] == cop["wheat"]["estimate_2026"]["market_level_incl_rent"]
    assert cost["Cotton"] == cop["cotton_seed_cotton"]["estimate_2026"]["market_ginnery_level_rs_per_40kg"]
    assert cost["IRRI"] == cop["rice_irri_paddy"]["milled_equivalent_rs_per_40kg"]["value"]
    assert cost["SuperBasmati"] == cop["rice_super_basmati_paddy"]["milled_equivalent_rs_per_40kg"]["value"]


def test_series_coverage_matches_the_scope(tables):
    series = {r["series"] for r in tables["series_coverage.csv"]}
    assert len(series) == 11
    assert "RahimYarKhan|Rice|IRRI" not in series
    stale = {r["series"] for r in tables["series_coverage.csv"] if r["is_stale"]}
    assert {s for s in series if s.endswith("SuperBasmati")} <= stale
    assert "BahawalPur|Wheat|none" not in stale


def test_transport_is_symmetric_and_zero_at_home(tables):
    cost = {(r["from_district"], r["to_mandi"]): r["cost_per_40kg"] for r in tables["transport_costs.csv"]}
    assert cost[("Bahawalpur", "BahawalPur")] == 0
    assert cost[("Bahawalpur", "Vehari")] == cost[("Vehari", "BahawalPur")] > 0


def test_support_prices_only_list_known_years(tables):
    rows = {r["crop_year"]: r for r in tables["support_prices.csv"]}
    assert rows["2023-24"]["status"] == "ANNOUNCED_NOT_PROCURED"
    assert rows["2023-24"]["harvest"] == "spring 2024"
    assert rows["2025-26"]["price_per_40kg"] == 3500
    assert rows["2022-23"]["price_per_40kg"] == 3900          # AMIS official table
    assert "2024-25" not in rows and "2026-27" not in rows    # no support price / not announced


def test_csv_files_read_back(tables):
    assert len(read("mandis.csv")) == 3
