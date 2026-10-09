import pytest

from ml.decision import config, offer_reference, reference_strength
from ml.decision import offer as o

FRESH = [3700, 3720, 3760, 3800, 3820, 3800, 3790]   # 7 reported days, varied
FRESH_REF = 3790


def check(offer, qty=100, window=FRESH, ref=FRESH_REF, **kw):
    return offer_reference(offer, qty, window, ref, is_stale=kw.pop("is_stale", False), **kw)


# ---------------------------------------------------------------- classification on a strong reference

@pytest.mark.parametrize("offer, status, gap", [(3600, o.BELOW, -100), (3750, o.WITHIN, 0), (3820, o.WITHIN, 0),
                                                (3900, o.ABOVE, 80)])
def test_below_within_above_on_a_strong_reference(offer, status, gap):
    out = check(offer)
    assert out["reference_strength"] == o.STRONG
    assert out["result_status"] == out["range_position"] == status
    assert out["difference_vs_range_per_maund"] == gap and out["total_difference_vs_range"] == gap * 100
    assert out["difference_vs_reference_per_maund"] == offer - FRESH_REF
    assert (out["reference_range_low"], out["reference_range_high"], out["reference_days"]) == (3700, 3820, 7)


@pytest.mark.parametrize("qty", [1, 37.5, 100, 2500])
def test_totals_scale_with_the_farmers_quantity(qty):
    out = check(3600, qty=qty)
    assert out["total_difference_vs_reference"] == round((3600 - FRESH_REF) * qty)
    assert out["total_difference_vs_range"] == round(-100 * qty)
    assert out["quantity_maund"] == qty


# ---------------------------------------------------------------- weak references never give a strong verdict

def test_wheat_bahawalpur_repeated_price_case():
    """10 Oct 2026: AMIS reported Rs 3,820 on all 12 days of the window. Offer Rs 3,514 on 100 maund."""
    out = offer_reference(3514, 100, [3820.0] * 12, 3820.0, is_stale=False)
    assert out["reference_strength"] == o.LIMITED_SAME_PRICE
    assert out["result_status"] == o.DATA_LIMITED                   # no "below the range" verdict
    assert out["range_position"] == o.BELOW                         # but the fact is kept
    assert out["reference_days"] == 12
    assert out["difference_vs_reference_per_maund"] == -306
    assert out["total_difference_vs_reference"] == -30600           # the total is still shown
    assert "SAME_PRICE_ALL_WINDOW" in out["limitations"]


@pytest.mark.parametrize("kw, strength, code", [
    ({"is_stale": True}, o.LIMITED_STALE, "STALE_REFERENCE"),
    ({"price_unchanged_since": "2026-08-01"}, o.LIMITED_FROZEN, "FROZEN_REFERENCE"),
    ({"window": FRESH[:4]}, o.LIMITED_FEW_DAYS, "FEW_REFERENCE_DAYS"),
])
def test_stale_frozen_and_thin_references_are_data_limited(kw, strength, code):
    out = check(3600, **kw)
    assert out["reference_strength"] == strength and out["result_status"] == o.DATA_LIMITED
    assert code in out["limitations"]
    assert out["total_difference_vs_reference"] == round((3600 - FRESH_REF) * 100)   # numbers still there


def test_the_minimum_is_five_reported_days():
    assert config.OFFER_MIN_REFERENCE_DAYS == 5
    assert reference_strength(FRESH[:5], False, None)[0] == o.STRONG
    assert reference_strength(FRESH[:4], False, None)[0] == o.LIMITED_FEW_DAYS


def test_every_weakness_is_listed_and_the_first_one_names_the_strength():
    strength, weak = reference_strength([3000.0], True, "2026-01-01")
    assert strength == o.LIMITED_STALE
    assert weak == [o.LIMITED_STALE, o.LIMITED_FROZEN, o.LIMITED_FEW_DAYS, o.LIMITED_SAME_PRICE]


# ---------------------------------------------------------------- alternatives after transport

def alt(mandi, price, transport, **kw):
    return {"mandi": mandi, "reference_price": price, "transport_cost": transport, "prices_as_of": "2026-10-09",
            "is_stale": False, "window_prices": [price - 10, price, price + 5, price, price - 5], **kw}


def test_alternative_better_after_transport():
    [a] = check(3600, alternatives=[alt("Vehari", 3900, 165)])["alternative_mandis"]
    assert a["net_after_transport"] == 3735 and a["difference_vs_offer_per_maund"] == 135
    assert a["difference_vs_offer_total"] == 13500 and a["better_after_transport"] is True
    assert a["higher_quote_not_better"] is False and a["transport_cost"] == 165


def test_higher_quote_that_transport_eats_is_not_better():
    [a] = check(3700, alternatives=[alt("RahimYarKhan", 3900, 291)])["alternative_mandis"]
    assert a["higher_quote_not_better"] is True and a["better_after_transport"] is False
    assert a["difference_vs_offer_total"] == round((3900 - 291 - 3700) * 100)


@pytest.mark.parametrize("kw, strength", [({"is_stale": True}, o.LIMITED_STALE),
                                          ({"price_unchanged_since": "2026-07-01"}, o.LIMITED_FROZEN),
                                          ({"window_prices": [4000.0] * 9}, o.LIMITED_SAME_PRICE)])
def test_a_weak_alternative_is_never_called_better(kw, strength):
    [a] = check(3000, alternatives=[alt("Vehari", 4000, 165, **kw)])["alternative_mandis"]
    assert a["reference_strength"] == strength and a["better_after_transport"] is None
    assert a["net_after_transport"] == 3835   # the numbers are still shown


def test_mandi_without_a_price():
    [a] = check(3600, alternatives=[{"mandi": "RahimYarKhan", "reference_price": None}])["alternative_mandis"]
    assert a == {"mandi": "RahimYarKhan", "has_data": False}


# ---------------------------------------------------------------- commission and assumptions

def test_commission_only_when_the_farmer_gave_one_and_never_changes_the_result():
    plain = check(3600)
    assert plain["estimated_commission"] is None and "COMMISSION_NOT_INCLUDED" in plain["limitations"]
    with_arhti = check(3600, arhti_pct=2.5)
    assert with_arhti["estimated_commission"] == {"pct": 2.5, "per_maund": 90.0, "total": 9000, "source": "farmer"}
    assert "COMMISSION_FARMER_ESTIMATE" in with_arhti["limitations"]
    for key in ("result_status", "total_difference_vs_reference", "total_difference_vs_range"):
        assert with_arhti[key] == plain[key]


def test_offer_is_a_gross_quote_and_the_standing_limits_are_always_listed():
    out = check(3600, alternatives=[alt("Vehari", 3900, 165)], is_synthetic=True)
    assert out["offer_price_basis"] == "GROSS_QUOTED"
    for code in ("QUALITY_GRADE_NOT_INCLUDED", "BUYER_TERMS_NOT_INCLUDED", "TRANSPORT_IS_ESTIMATE",
                 "SYNTHETIC_DATA"):
        assert code in out["limitations"]
    assert "TRANSPORT_IS_ESTIMATE" not in check(3600)["limitations"]   # no alternatives, no transport shown


@pytest.mark.parametrize("kw", [{"offer": 0}, {"offer": -5}, {"qty": 0}, {"window": []}, {"ref": 0}])
def test_bad_inputs_raise(kw):
    with pytest.raises(ValueError):
        check(kw.pop("offer", 3600), **kw)
