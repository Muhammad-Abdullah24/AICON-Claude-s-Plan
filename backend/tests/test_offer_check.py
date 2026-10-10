"""Offer check through the service layer and the API, on the real AMIS data (snapshot of 9 Oct 2026)."""

import datetime as dt

import pytest

from backend.app import services

WHEAT_BWP = {"crop": "wheat", "mandi": "bahawalpur"}


def post(client, **body):
    return client.post("/api/offer-check", json={**WHEAT_BWP, **body})


def test_wheat_bahawalpur_repeated_price_is_data_limited_but_shows_the_total(client):
    r = post(client, offer_price=3514, quantity_maund=100)
    assert r.status_code == 200
    out = r.json()
    assert (out["reference_price"], out["reference_range_low"], out["reference_range_high"]) == (3820, 3820, 3820)
    assert (out["reference_days"], out["window_days"]) == (12, 14)
    assert out["reference_strength"] == "LIMITED_SAME_PRICE"
    assert out["result_status"] == "REFERENCE_DATA_LIMITED"
    assert out["range_position"] == "BELOW_REFERENCE_RANGE"
    assert out["difference_vs_reference_per_maund"] == -306 and out["total_difference_vs_reference"] == -30600
    assert out["buyer_offer_price"] == 3514 and out["offer_price_basis"] == "GROSS_QUOTED"
    assert out["reference_price_as_of"] == "2026-10-09" and out["data_source"] == "amis"
    assert "SAME_PRICE_ALL_WINDOW" in out["limitations"]


def test_deprecated_aliases_still_answer_older_clients(client):
    out = post(client, offer_price=1).json()
    assert out["verdict"] == "below" and out["difference_total"] < 0 and out["offer_price"] == 1
    assert out["fair_low"] == out["reference_range_low"] and out["prices_as_of"] == out["reference_price_as_of"]


def test_strong_reference_classifies(client):
    body = {"crop": "cotton", "mandi": "bahawalpur", "quantity_maund": 60}
    low = post(client, **body, offer_price=8000).json()
    assert low["reference_strength"] == "STRONG" and low["result_status"] == "BELOW_REFERENCE_RANGE"
    assert low["total_difference_vs_range"] == round((8000 - low["reference_range_low"]) * 60)
    mid = (low["reference_range_low"] + low["reference_range_high"]) / 2
    assert post(client, **body, offer_price=mid).json()["result_status"] == "WITHIN_REFERENCE_RANGE"
    assert post(client, **body, offer_price=99_999).json()["result_status"] == "ABOVE_REFERENCE_RANGE"


def test_replayed_week_uses_only_data_up_to_that_day(client):
    out = client.post("/api/offer-check", params={"as_of": "2025-03-24"},
                      json={**WHEAT_BWP, "offer_price": 2700}).json()
    assert out["reference_price_as_of"] <= "2025-03-24" and out["reference_strength"] == "STRONG"
    assert out["result_status"] == "BELOW_REFERENCE_RANGE"


def test_stale_reference_is_limited(client):
    out = client.post("/api/offer-check", json={"crop": "wheat", "mandi": "vehari", "offer_price": 3000}).json()
    assert out["is_stale"] is True and out["reference_strength"] == "LIMITED_STALE"
    assert out["result_status"] == "REFERENCE_DATA_LIMITED" and "STALE_REFERENCE" in out["limitations"]


def test_frozen_reference_is_limited():
    out = services.offer_check("IRRI", "BahawalPur", 1400, 10, as_of=dt.date(2016, 8, 1))
    assert out["price_unchanged_since"] == "2016-06-10"
    assert out["reference_strength"] == "LIMITED_FROZEN" and out["result_status"] == "REFERENCE_DATA_LIMITED"


def test_missing_price_is_404(client):
    r = client.post("/api/offer-check", json={"crop": "irri", "mandi": "rahim_yar_khan", "offer_price": 4000})
    assert r.status_code == 404


def test_quantity_scales_every_total(client):
    a = post(client, offer_price=3514, quantity_maund=100).json()
    b = post(client, offer_price=3514, quantity_maund=50).json()
    assert b["total_difference_vs_reference"] * 2 == a["total_difference_vs_reference"]
    for x, y in zip(a["alternative_mandis"], b["alternative_mandis"], strict=True):
        if x["has_data"]:
            assert abs(y["difference_vs_offer_total"] * 2 - x["difference_vs_offer_total"]) <= 1


def test_alternatives_use_the_same_transport_and_prices_as_compare_mandis(client):
    offer = post(client, offer_price=3514, quantity_maund=100).json()
    compare = client.get("/api/compare-mandis", params={**WHEAT_BWP, "quantity_maund": 100}).json()
    rows = {r["mandi"]: r for r in compare["rows"]}
    own, *others = offer["alternative_mandis"]
    assert own["is_own_mandi"] is True and own["mandi"] == "bahawalpur"
    assert not any(a["is_own_mandi"] for a in others)
    assert {a["mandi"] for a in offer["alternative_mandis"]} == set(rows)   # every mandi, the farmer's own first
    for a in offer["alternative_mandis"]:
        r = rows[a["mandi"]]
        assert a["reference_price"] == r["price"] and a["transport_cost"] == r["transport_cost"]
        assert a["net_after_transport"] == pytest.approx(r["net_price"])
        assert a["is_stale"] == r["is_stale"]
    assert offer["estimated_transport_cost"] == rows["bahawalpur"]["transport_cost"] == 0
    assert "TRANSPORT_IS_ESTIMATE" in offer["limitations"]


def test_weak_alternatives_are_never_called_better(client):
    for a in post(client, offer_price=1000).json()["alternative_mandis"]:
        if a["has_data"] and a["reference_strength"] != "STRONG":
            assert a["better_after_transport"] is None


def test_commission_from_the_request_or_the_profile_only(client):
    plain = post(client, offer_price=3514).json()
    assert plain["estimated_commission"] is None and "COMMISSION_NOT_INCLUDED" in plain["limitations"]
    given = post(client, offer_price=3514, quantity_maund=100, arhti_pct=2).json()
    assert given["estimated_commission"] == {"pct": 2, "per_maund": 70.28, "total": 7028, "source": "farmer"}
    assert given["result_status"] == plain["result_status"]
    assert given["total_difference_vs_reference"] == plain["total_difference_vs_reference"]
    assert post(client, offer_price=3514, arhti_pct=60).status_code == 422


def test_assumption_codes_are_from_the_published_list(client):
    from typing import get_args

    from backend.app.schemas import OfferLimitation

    allowed = set(get_args(OfferLimitation))
    for body in ({}, {"arhti_pct": 1.5}):
        assert set(post(client, offer_price=3514, **body).json()["limitations"]) <= allowed
