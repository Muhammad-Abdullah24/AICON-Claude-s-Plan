"""Tests for What to Grow, made cautious (F4). Pure: crop_plan rows and policy events are passed in."""

import datetime as dt

import pytest

from ml.decision import grow, inputs
from ml.decision.advisory import crop_plan


def _row(option, season, profit, stale=False, frozen=False, enough=True):
    return {"crop_option": option, "season": season, "expected_profit": profit, "is_stale": stale,
            "is_frozen": frozen, "enough_years": enough}


def _by_crop(result):
    return {r["crop_option"]: r for r in result["items"]}


def _season(result, name):
    return next(s for s in result["seasons"] if s["season"] == name)


# ---------------------------------------------------------------- 1. a stale candidate never ranks first

def test_stale_candidate_is_excluded_from_the_ranking_even_with_the_highest_profit():
    r = grow.rank_within_seasons([_row("Cotton", "KHARIF", 100), _row("IRRI", "KHARIF", 80),
                                  _row("SuperBasmati", "KHARIF", 999, stale=True)])
    rows = _by_crop(r)
    assert rows["Cotton"]["rank"] == 1 and rows["IRRI"]["rank"] == 2
    assert rows["SuperBasmati"]["rank"] is None and rows["SuperBasmati"]["evidence_issues"] == ["STALE_PRICE"]
    assert [x["crop_option"] for x in r["items"]] == ["Cotton", "IRRI", "SuperBasmati"]   # evidence kept, last
    assert _season(r, "KHARIF")["status"] == "RANKED"


@pytest.mark.parametrize("flags, issue", [(dict(frozen=True), "FROZEN_PRICE"), (dict(enough=False), "FEW_YEARS")])
def test_frozen_or_thin_evidence_is_not_ranked_either(flags, issue):
    r = grow.rank_within_seasons([_row("Cotton", "KHARIF", 100), _row("IRRI", "KHARIF", 80),
                                  _row("SuperBasmati", "KHARIF", 999, **flags)])
    assert _by_crop(r)["SuperBasmati"]["rank"] is None and _by_crop(r)["SuperBasmati"]["evidence_issues"] == [issue]


# ---------------------------------------------------------------- 2. all stale: no recommendation

def test_all_candidates_stale_means_no_ranking():
    r = grow.rank_within_seasons([_row("Cotton", "KHARIF", 100, stale=True), _row("IRRI", "KHARIF", 80, stale=True)])
    assert all(x["rank"] is None for x in r["items"])
    assert _season(r, "KHARIF") == {"season": "KHARIF", "status": "NOT_ENOUGH_CURRENT_EVIDENCE", "n_crops": 2,
                                    "n_comparable": 0}


# ---------------------------------------------------------------- 3. no comparison across seasons

def test_wheat_is_never_ranked_against_kharif_crops():
    r = grow.rank_within_seasons([_row("Wheat", "RABI", 10_000), _row("Cotton", "KHARIF", 100),
                                  _row("IRRI", "KHARIF", 80)])
    rows = _by_crop(r)
    assert rows["Wheat"]["rank"] is None                       # highest profit, but nothing to compare it with
    assert rows["Cotton"]["rank"] == 1 and rows["IRRI"]["rank"] == 2
    assert _season(r, "RABI")["status"] == "TOO_FEW_CROPS" and _season(r, "KHARIF")["status"] == "RANKED"
    assert [s["season"] for s in r["seasons"]] == ["RABI", "KHARIF"]


def test_unknown_season_is_an_error_not_a_guess():
    with pytest.raises(ValueError):
        grow.rank_within_seasons([_row("Wheat", None, 1)])


# ---------------------------------------------------------------- 4. too few same-season candidates

def test_one_reliable_crop_in_a_season_is_not_a_winner():
    r = grow.rank_within_seasons([_row("Cotton", "KHARIF", 100), _row("SuperBasmati", "KHARIF", 50, stale=True)])
    assert all(x["rank"] is None for x in r["items"])
    assert _season(r, "KHARIF")["status"] == "NOT_ENOUGH_CURRENT_EVIDENCE"
    assert _season(r, "KHARIF")["n_comparable"] == 1


def test_the_minimum_is_configurable_and_at_least_two():
    rows = [_row("Cotton", "KHARIF", 100), _row("IRRI", "KHARIF", 80)]
    assert _season(grow.rank_within_seasons(rows, min_comparable=3), "KHARIF")["status"] == "TOO_FEW_CROPS"
    with pytest.raises(ValueError):
        grow.rank_within_seasons(rows, min_comparable=1)


# ---------------------------------------------------------------- 5. the rice water note is scoped

def test_rice_water_note_only_for_rice_at_bahawalpur():
    for rice in ("IRRI", "SuperBasmati"):
        notes = grow.context_notes(rice, "BahawalPur")
        assert [n["id"] for n in notes] == ["RICE_WATER_BAHAWALPUR"]
        assert notes[0]["url"].startswith("https://") and notes[0]["source"] and notes[0]["source_date"]
    for crop, mandi in [("IRRI", "Vehari"), ("SuperBasmati", "RahimYarKhan"), ("Cotton", "BahawalPur"),
                        ("Wheat", "BahawalPur")]:
        assert grow.context_notes(crop, mandi) == []


# ---------------------------------------------------------------- 6. wheat support-price context

EVENTS = [  # newest first, as get_policy_events returns them
    {"date": "2026-10-06", "tag": "SUPPORT_PRICE", "text_en": "undecided", "text_ur": "…", "source": "B", "url": "u"},
    {"date": "2026-07-24", "tag": "IMPORT", "text_en": "import", "text_ur": "…", "source": "P", "url": "u"},
    {"date": "2026-01-21", "tag": "SUPPORT_PRICE", "text_en": "Rs 3,500", "text_ur": "…", "source": "D", "url": "u"},
]


def test_support_price_context_is_current_outdated_or_unavailable():
    now = grow.support_price_context(EVENTS, dt.date(2026, 10, 9))
    assert now["state"] == "CURRENT" and now["event"]["date"] == "2026-10-06" and now["age_days"] == 3
    # A replay on 10 May sees only the January item, 109 days old: shown as out of date, not as current.
    may = grow.support_price_context([e for e in EVENTS if e["date"] <= "2026-05-10"], dt.date(2026, 5, 10))
    assert may["state"] == "OUTDATED" and may["event"]["date"] == "2026-01-21" and may["age_days"] == 109
    assert grow.support_price_context([EVENTS[1]], dt.date(2026, 10, 9))["state"] == "UNAVAILABLE"
    assert grow.support_price_context([], dt.date(2026, 10, 9))["event"] is None


def test_support_price_context_never_reads_past_as_of():
    assert grow.support_price_context(EVENTS, dt.date(2026, 10, 5))["event"]["date"] == "2026-01-21"


# ---------------------------------------------------------------- on the real tables

def test_real_tables_carry_season_and_evidence_flags():
    rows = crop_plan(inputs.crop_plan_inputs("Bahawalpur"), land_area_acres=1)["crops"]
    with_data = [r for r in rows if r["has_data"]]
    assert {r["crop_option"]: r["season"] for r in with_data}["Wheat"] == "RABI"
    assert all(r["season"] in ("RABI", "KHARIF") and isinstance(r["is_frozen"], bool) for r in with_data)
    result = grow.rank_within_seasons(with_data)
    assert _season(result, "RABI")["status"] == "TOO_FEW_CROPS"     # wheat is the only Rabi crop we track
    assert all(r["rank"] is None for r in result["items"] if r["evidence_issues"])
