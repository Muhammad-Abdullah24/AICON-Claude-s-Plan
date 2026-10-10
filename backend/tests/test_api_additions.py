"""The four additive API changes for the redesigned web app, on the real AMIS data (snapshot of 9 Oct 2026):
GET /api/reference, the own mandi in the offer-check list, reference strength on compare rows, and
GET /api/channels/preview."""

import json

import pytest

from backend.app.channels import conversation as conv
from backend.app.channels import sms_reply, whatsapp

WHEAT_BWP = {"crop": "wheat", "mandi": "bahawalpur"}


# ---------------------------------------------------------------- GET /api/reference

def test_reference_wheat_bahawalpur_is_one_repeated_price(client):
    r = client.get("/api/reference", params=WHEAT_BWP).json()
    assert (r["reference_price"], r["reference_range_low"], r["reference_range_high"]) == (3820, 3820, 3820)
    assert (r["reference_days"], r["window_days"]) == (12, 14) and r["reference_price_as_of"] == "2026-10-09"
    assert r["reference_strength"] == "LIMITED_SAME_PRICE" and r["limitations"] == ["SAME_PRICE_ALL_WINDOW"]
    assert r["is_stale"] is False and r["price_unchanged_since"] is None
    assert (r["unit"], r["data_source"], r["is_synthetic"]) == ("40kg", "amis", False)


@pytest.mark.parametrize("params, strength, code", [
    ({"crop": "cotton", "mandi": "bahawalpur"}, "STRONG", None),
    ({"crop": "wheat", "mandi": "vehari"}, "LIMITED_STALE", "STALE_REFERENCE"),
    ({"crop": "cotton", "mandi": "rahim_yar_khan"}, "LIMITED_FEW_DAYS", "FEW_REFERENCE_DAYS"),
    ({"crop": "irri", "mandi": "bahawalpur", "as_of": "2016-08-01"}, "LIMITED_FROZEN", "FROZEN_REFERENCE"),
])
def test_reference_strength_on_real_series(client, params, strength, code):
    r = client.get("/api/reference", params=params).json()
    assert r["reference_strength"] == strength
    assert (code in r["limitations"]) if code else r["limitations"] == []


def test_reference_replay_uses_only_data_up_to_that_day(client):
    r = client.get("/api/reference", params={**WHEAT_BWP, "as_of": "2025-03-24"}).json()
    assert r["reference_price_as_of"] <= "2025-03-24" and r["reference_strength"] == "STRONG"


def test_reference_missing_and_invalid(client):
    assert client.get("/api/reference", params={"crop": "irri", "mandi": "rahim_yar_khan"}).status_code == 404
    assert client.get("/api/reference", params={"crop": "rice", "mandi": "bahawalpur"}).status_code == 422


def test_reference_matches_the_offer_check(client):
    ref = client.get("/api/reference", params=WHEAT_BWP).json()
    offer = client.post("/api/offer-check", json={**WHEAT_BWP, "offer_price": 3514}).json()
    for key in ("reference_price", "reference_price_as_of", "reference_range_low", "reference_range_high",
                "reference_days", "window_days", "is_stale", "price_unchanged_since", "reference_strength"):
        assert ref[key] == offer[key], key


# ---------------------------------------------------------------- the own mandi in the offer check

def test_own_mandi_is_the_first_row_worked_out_like_the_others(client):
    o = client.post("/api/offer-check", json={**WHEAT_BWP, "offer_price": 3514, "quantity_maund": 100}).json()
    own = o["alternative_mandis"][0]
    assert own["is_own_mandi"] is True and own["mandi"] == "bahawalpur"
    assert own["transport_cost"] == o["estimated_transport_cost"] == 0   # from the table: Rs 0 to its own mandi
    assert own["reference_price"] == own["net_after_transport"] == o["reference_price"]
    assert own["difference_vs_offer_total"] == 30600 == -o["total_difference_vs_reference"]
    assert own["reference_strength"] == o["reference_strength"] == "LIMITED_SAME_PRICE"
    assert own["better_after_transport"] is None          # a weak reference is never "better"
    assert sum(a["is_own_mandi"] for a in o["alternative_mandis"]) == 1


def test_own_mandi_on_a_strong_reference(client):
    o = client.post("/api/offer-check", json={"crop": "cotton", "mandi": "bahawalpur", "offer_price": 8000,
                                              "quantity_maund": 60}).json()
    own = o["alternative_mandis"][0]
    assert own["reference_strength"] == "STRONG" and own["better_after_transport"] is True
    assert own["difference_vs_offer_total"] == round((own["net_after_transport"] - 8000) * 60)


# ---------------------------------------------------------------- compare rows

def test_compare_rows_carry_strength_days_and_frozen(client):
    rows = client.get("/api/compare-mandis", params={**WHEAT_BWP, "quantity_maund": 100}).json()["rows"]
    by = {r["mandi"]: r for r in rows}
    assert by["bahawalpur"]["reference_strength"] == "LIMITED_SAME_PRICE" and by["bahawalpur"]["reference_days"] == 12
    assert by["vehari"]["reference_strength"] == "LIMITED_STALE"
    assert all("price_unchanged_since" in r for r in rows if r["has_data"])


def test_no_weak_mandi_is_called_best(client):
    wheat = client.get("/api/compare-mandis", params={**WHEAT_BWP, "quantity_maund": 100}).json()["rows"]
    assert not any(r["is_best"] for r in wheat)      # every wheat reference is weak today
    cotton = client.get("/api/compare-mandis", params={"crop": "cotton", "mandi": "bahawalpur"}).json()["rows"]
    assert [r["is_best"] for r in cotton] == [True, False, False]
    assert cotton[0]["reference_strength"] == "STRONG"
    for r in cotton:
        if r["is_best"]:
            assert r["reference_strength"] == "STRONG"


def test_compare_frozen_replay(client):
    rows = client.get("/api/compare-mandis", params={"crop": "irri", "mandi": "bahawalpur",
                                                     "as_of": "2016-08-01"}).json()["rows"]
    bwp = next(r for r in rows if r["mandi"] == "bahawalpur")
    assert bwp["price_unchanged_since"] == "2016-06-10" and bwp["reference_strength"] == "LIMITED_FROZEN"
    assert bwp["is_best"] is False


# ---------------------------------------------------------------- GET /api/channels/preview

def test_preview_menu_is_what_the_channels_send(client):
    p = client.get("/api/channels/preview", params=WHEAT_BWP).json()
    menu = conv.Reply("menu", {}, conv.MAIN_CHOICES)
    assert p["whatsapp_menu"] == whatsapp.render(menu, None, "")["text"]["body"]
    assert p["sms_menu"] == sms_reply.render(menu)
    assert p["menu_choices"] == ["offer", "compare", "why", "alerts_on", "alerts_off", "menu"]
    assert "1  خریدار کی آفر چیک کریں" in p["whatsapp_menu"] and "1 Offer check" in p["sms_menu"]
    assert p["whatsapp_offer"] is None and p["sms_offer"] is None and p["whatsapp_offer_buttons"] == []


def test_preview_offer_uses_the_real_offer_check(client):
    p = client.get("/api/channels/preview", params={**WHEAT_BWP, "quantity_maund": 100, "offer_price": 3514}).json()
    assert "−Rs 30,600" in p["whatsapp_offer"] and "حوالہ ڈیٹا محدود ہے" in p["whatsapp_offer"]
    assert "-Rs30600" in p["sms_offer"] and "Reference data mehdood" in p["sms_offer"]
    assert p["sms_offer_parts"] == sms_reply.parts(p["sms_offer"]) <= 2
    assert p["whatsapp_offer_buttons"] == ["کیوں؟", "منڈیاں", "الرٹ چالو"]
    assert p["prices_as_of"] == "2026-10-09"


def test_preview_replay_and_errors(client):
    p = client.get("/api/channels/preview", params={**WHEAT_BWP, "offer_price": 2700, "as_of": "2025-03-24"}).json()
    assert p["prices_as_of"] <= "2025-03-24" and "حالیہ حوالہ حد سے کم" in p["whatsapp_offer"]
    missing = {"crop": "irri", "mandi": "rahim_yar_khan", "offer_price": 4000}
    assert client.get("/api/channels/preview", params=missing).status_code == 404
    assert client.get("/api/channels/preview", params={**WHEAT_BWP, "offer_price": 0}).status_code == 422


def test_preview_status_flags_only(client, monkeypatch):
    for k in ("FS_WA_APP_SECRET", "FS_WA_ACCESS_TOKEN", "FS_WA_PHONE_NUMBER_ID", "FS_SMS_PROVIDER", "FS_VOICE_NOTES"):
        monkeypatch.delenv(k, raising=False)
    s = client.get("/api/channels/preview", params=WHEAT_BWP).json()["status"]
    assert s == {"whatsapp_configured": False, "sms_provider_configured": False, "voice_notes_enabled": False}
    secrets = {"FS_WA_APP_SECRET": "secret-xyz", "FS_WA_ACCESS_TOKEN": "token-abc", "FS_WA_PHONE_NUMBER_ID": "998877"}
    for k, v in secrets.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("FS_SMS_PROVIDER", "notavendor")   # a name with no adapter is still "not configured"
    monkeypatch.setenv("FS_VOICE_NOTES", "1")             # the flag alone does not enable voice
    body = client.get("/api/channels/preview", params=WHEAT_BWP)
    assert body.json()["status"] == {"whatsapp_configured": True, "sms_provider_configured": False,
                                     "voice_notes_enabled": False}
    raw = json.dumps(body.json())
    assert not any(v in raw for v in secrets.values())   # flags only: no setting value is returned
