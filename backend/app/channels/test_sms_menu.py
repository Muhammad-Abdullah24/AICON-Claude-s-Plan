"""The SMS number menu: 0 menu, 1 buyer offer, 2 compare, 3 why, 4 alerts on, 5 alerts off. All mocked."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.channels import reply, simpapp, sms, sms_menu, whatsapp
from backend.app.channels.test_textbee import Outbox
from backend.app.channels.test_whatsapp import FakeProvider, body_of

PHONE = "923001234567"
OFFER_RESULT = {"fair_low": 3700, "fair_high": 3850, "window_days": 14, "prices_as_of": "2026-10-09"}


class Provider(FakeProvider):
    """The WhatsApp test provider plus the existing offer check."""

    def __init__(self, verdict="below", missing=()):
        super().__init__(missing)
        self.verdict, self.offers = verdict, []

    def offer_check(self, crop_option, mandi, offer, quantity_maund, phone):
        self.offers.append((crop_option, mandi, offer, quantity_maund))
        if (crop_option, mandi) in self.missing:
            raise LookupError
        gap = {"below": offer - 3700, "fair": 0, "above": offer - 3850}[self.verdict]
        return {**OFFER_RESULT, "verdict": self.verdict, "difference_per_maund": gap,
                "difference_total": gap * (quantity_maund or 100)}


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    blank = whatsapp.Memory()   # respond() binds MEMORY as a default argument, so empty that object
    monkeypatch.setattr(whatsapp.MEMORY, "last", blank.last)
    monkeypatch.setattr(whatsapp.MEMORY, "seen", blank.seen)
    monkeypatch.setattr(sms_menu, "PENDING", sms_menu.Pending())


def say(text, provider):
    return body_of(sms_menu.respond({"from": PHONE, "id": "x", "type": "text", "text": {"body": text}}, provider))


def ask_price(crop="گندم", mandi="بہاولپور"):
    return reply.OFFER_ASK_PRICE.format(crop=crop, mandi=mandi)


# ---------------------------------------------------------------- each option

@pytest.mark.parametrize("zero", ["0", " 0 ", "۰"])
def test_0_shows_the_menu(zero):
    assert say(zero, Provider()) == reply.SMS_MENU


def test_1_without_a_query_asks_crop_and_mandi_then_the_price_then_checks():
    p = Provider()
    assert say("1", p) == reply.OFFER_ASK_QUERY
    assert say("گندم بہاولپور 100 من", p) == ask_price()
    out = say("Rs 3,600", p)
    assert p.offers == [("Wheat", "BahawalPur", 3600, 100)]
    result = p.offer_check("Wheat", "BahawalPur", 3600, 100, "")
    assert out == reply.offer_text("Wheat", "BahawalPur", 3600, result, 100)
    assert "Rs 3,600" in out and "Rs 100 فی من کم" in out and "100 من پر: −Rs 10,000" in out
    assert "Rs 3,700 سے Rs 3,850" in out and "2026-10-09" in out


def test_1_after_a_query_asks_only_for_the_price():
    p = Provider(verdict="fair")
    say("gandum vehari 50 mann", p)
    assert say("1", p) == ask_price(mandi="وہاڑی")
    out = say("3800", p)
    assert p.offers == [("Wheat", "Vehari", 3800, 50)] and reply.OFFER_VERDICT["fair"] in out
    assert "من پر" not in out   # a fair offer has no gap to multiply


def test_1_collects_only_what_is_missing():
    p = Provider()
    assert say("١", p) == reply.OFFER_ASK_QUERY            # Arabic-Indic one is 1 too
    assert say("gandum", p) == reply.ASK["mandi"]
    assert say("vehari", p) == ask_price(mandi="وہاڑی")
    assert say("kal ka mausam", p) == reply.OFFER_ASK_PRICE_AGAIN
    say("3900", p)
    assert p.offers == [("Wheat", "Vehari", 3900, None)]


def test_1_asks_which_rice_and_never_guesses():
    p = Provider()
    say("1", p)
    assert say("chawal bahawalpur", p) == reply.ASK["variety"]
    assert say("اری", p) == ask_price(crop="چاول (اری)")


def test_1_without_quantity_gives_only_the_per_maund_gap():
    p = Provider()
    say("1", p)
    say("گندم بہاولپور", p)
    out = say("3600", p)
    assert p.offers == [("Wheat", "BahawalPur", 3600, None)] and "من پر" not in out and "Rs 100 فی من کم" in out


def test_1_with_no_price_data_says_so():
    p = Provider(missing=[("IRRI", "RahimYarKhan")])
    say("1", p)
    say("irri ryk", p)
    assert say("3000", p) == reply.NO_DATA.format(mandi="رحیم یار خان", crop="چاول (اری)")


def test_2_compares_the_last_query():
    p = Provider()
    assert say("2", p) == reply.NEED_QUERY_FIRST
    say("gandum bahawalpur 100 mann", p)
    assert say("2", p) == reply.compare_text("Wheat", p.compare("Wheat", "BahawalPur", 100, PHONE))


def test_3_explains_why():
    p = Provider()
    assert say("3", p) == reply.NEED_QUERY_FIRST
    say("gandum bahawalpur 100 mann", p)
    a = p.advice("Wheat", "BahawalPur", 100, PHONE)
    assert say("3", p) == reply.why_text(a, p.explain("Wheat", "BahawalPur", PHONE))


def test_4_starts_and_5_stops_alerts():
    p = Provider()
    assert say("5", p) == reply.STOPPED and p.alerts == {PHONE: False}
    assert say("4", p) == reply.STARTED and p.alerts == {PHONE: True}


# ---------------------------------------------------------------- what stays as it was

def test_free_text_queries_and_stop_words_are_unchanged():
    p = Provider()
    a = p.advice("Wheat", "BahawalPur", 100, PHONE)
    assert say("گندم بہاولپور 100 من", p) == reply.advice_text(a)
    for word in ("stop", "STOP", "بند"):
        assert say(word, p) == reply.STOPPED
    assert say("شروع", p) == reply.STARTED and say("hi", p) == reply.HELP


def test_a_command_or_menu_number_ends_an_offer_in_progress():
    p = Provider()
    say("1", p)
    assert say("stop", p) == reply.STOPPED and p.alerts == {PHONE: False}
    assert say("3900", p) != ask_price()    # the offer was dropped; 3900 alone is not a query
    say("1", p)
    assert say("0", p) == reply.SMS_MENU
    assert sms_menu.PENDING.get(PHONE) is None and p.offers == []


def test_an_offer_in_progress_expires(monkeypatch):
    p, now = Provider(), [1000.0]
    monkeypatch.setattr(sms_menu.time, "monotonic", lambda: now[0])
    say("1", p)
    now[0] += sms_menu.PENDING_TTL_S + 1
    assert sms_menu.PENDING.get(PHONE) is None


@pytest.mark.parametrize("text, price", [("3900", 3900), ("Rs 3,900", 3900), ("۳۹۰۰ روپے", 3900),
                                         ("3,900.50", 3900.5), ("3900 4000", None), ("سستا", None),
                                         ("2000000", None)])
def test_price_reading(text, price):
    assert sms_menu._price(text) == price


def test_whatsapp_numbers_keep_their_meaning():
    p = Provider()
    msg = {"from": PHONE, "id": "w", "type": "text", "text": {"body": "gandum bahawalpur"}}
    whatsapp.respond(msg, p)
    a = p.advice("Wheat", "BahawalPur", 100, PHONE)
    why = whatsapp.respond({**msg, "text": {"body": "1"}}, p)
    assert body_of(why) == reply.why_text(a, p.explain("Wheat", "BahawalPur", PHONE))
    assert body_of(whatsapp.respond({**msg, "text": {"body": "3"}}, p)) == reply.STOPPED


def test_every_reply_with_buttons_ends_with_the_sms_numbers():
    assert sms.COMMAND_LINE == "2 منڈیاں | 3 کیوں؟ | 5 الرٹ بند | 0 مینو"
    for digit, option in sms.SMS_MENU.items():
        assert digit in reply.SMS_MENU or option == "menu"


# ---------------------------------------------------------------- through the Simpapp webhook

def test_simpapp_sms_0_then_1_then_an_offer():
    db.reset()
    outbox, provider, app = Outbox(), Provider(verdict="above"), FastAPI()
    app.include_router(simpapp.router)
    secret = "webhook-token-for-tests-only-0123456"
    app.dependency_overrides[simpapp.get_simpapp_settings] = lambda: simpapp.SimpappSettings(
        simpapp.DEFAULT_API_URL, "key", secret)
    app.dependency_overrides[simpapp.get_provider] = lambda: provider
    app.dependency_overrides[simpapp.get_simpapp_outbound] = lambda: outbox
    client = TestClient(app)

    def text(message, ts):
        body = {"type": "incoming_sms", "sender": "+923001234567", "message": message, "timestamp": ts}
        r = client.post(f"/api/channels/sms/simpapp/webhook?token={secret}",
                        content=json.dumps(body, ensure_ascii=False).encode(),
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 200 and r.json() == {"status": "accepted"}
        return outbox.sent[-1][1]

    try:
        assert text("0", 1760090000) == reply.SMS_MENU
        assert text("1", 1760090030) == reply.OFFER_ASK_QUERY
        assert text("گندم بہاولپور 100 من", 1760090060) == ask_price()
        out = text("4000", 1760090090)
        assert provider.offers == [("Wheat", "BahawalPur", 4000, 100)]
        assert reply.OFFER_VERDICT["above"].format(diff="Rs 150") in out and out.endswith(sms.COMMAND_LINE)
        assert len(outbox.sent) == 4 and all(to == "+923001234567" for to, _ in outbox.sent)
    finally:
        db.reset()


# ---------------------------------------------------------------- limited evidence: a reference price, not a fair range

FAIR_WORDS = ("مناسب حد", "✅")


def test_frozen_bahawalpur_wheat_is_a_reference_price_not_a_fair_range():
    """Real data: AMIS has reported one wheat price at Bahawalpur for the whole 14-day window."""
    from backend.app.channels.provider import ServicesProvider
    o = ServicesProvider().offer_check("Wheat", "BahawalPur", 3700, 100, PHONE)
    assert o["fair_low"] == o["fair_high"] and "LIMITED" in o["evidence"]
    text = reply.offer_text("Wheat", "BahawalPur", 3700, o, 100)
    ref = reply.rs(o["fair_low"])
    assert f"منڈی کا رپورٹ شدہ ریٹ (صرف حوالہ): {ref} (AMIS، {o['prices_as_of']} تک)" in text
    assert reply.OFFER_EVIDENCE_UR["LIMITED"].format(days=14) in text
    gap = o["fair_low"] - 3700
    assert reply.OFFER_REFERENCE_GAP["below"].format(diff=reply.rs(gap)) in text
    assert f"100 من پر: {reply.signed_rs(-gap * 100)}" in text
    assert text.endswith(reply.OFFER_NOT_ADVICE) and not any(w in text for w in FAIR_WORDS)


def test_an_offer_equal_to_the_frozen_price_is_not_called_fair():
    from backend.app.channels.provider import ServicesProvider
    p = ServicesProvider()
    ref = p.offer_check("Wheat", "BahawalPur", 3700, None, PHONE)["fair_low"]
    o = p.offer_check("Wheat", "BahawalPur", ref, None, PHONE)
    assert o["verdict"] == "fair"   # the engine's verdict is unchanged; only the words are
    text = reply.offer_text("Wheat", "BahawalPur", ref, o, None)
    assert reply.OFFER_REFERENCE_EQUAL in text and not any(w in text for w in FAIR_WORDS) and "من پر" not in text


def test_a_real_range_keeps_the_fair_range_wording():
    from backend.app.channels.provider import ServicesProvider
    o = ServicesProvider().offer_check("Cotton", "BahawalPur", 9000, 50, PHONE)
    assert o["fair_low"] < o["fair_high"] and o["evidence"] == []
    text = reply.offer_text("Cotton", "BahawalPur", 9000, o, 50)
    assert "مناسب حد (اس منڈی میں پچھلے 14 دن)" in text and reply.OFFER_NOT_ADVICE not in text


@pytest.mark.parametrize("flags", [["FROZEN"], ["STALE"], ["LIMITED"], ["FROZEN", "STALE", "LIMITED"]])
@pytest.mark.parametrize("verdict, gap, words", [
    ("below", -150, reply.OFFER_REFERENCE_GAP["below"].format(diff="Rs 150")),
    ("above", 50, reply.OFFER_REFERENCE_GAP["above"].format(diff="Rs 50")),
    ("fair", 0, reply.OFFER_REFERENCE_WITHIN),
])
def test_every_limited_evidence_flag_switches_to_reference_wording(flags, verdict, gap, words):
    o = {**OFFER_RESULT, "verdict": verdict, "difference_per_maund": gap, "difference_total": gap * 100,
         "evidence": flags}
    text = reply.offer_text("Wheat", "Vehari", 3800, o, 100)
    assert "Rs 3,700 سے Rs 3,850" in text and words in text and text.endswith(reply.OFFER_NOT_ADVICE)
    assert all(reply.OFFER_EVIDENCE_UR[f].format(days=14) in text for f in flags)
    assert not any(w in text for w in FAIR_WORDS)
    assert ("100 من پر" in text) == (verdict != "fair")


def test_sms_offer_on_limited_evidence_through_the_menu():
    class Frozen(Provider):
        def offer_check(self, *a):
            return {**super().offer_check(*a), "fair_low": 3820, "fair_high": 3820, "evidence": ["LIMITED"]}

    p = Frozen(verdict="below")
    say("گندم بہاولپور 100 من", p)
    say("1", p)
    out = say("3700", p)
    assert "صرف حوالہ" in out and reply.OFFER_NOT_ADVICE in out and not any(w in out for w in FAIR_WORDS)
