"""SMS channel (task A11): provider-neutral sender, inbound adapter boundary, Roman Urdu replies. No real sends:
the only adapter here is a test double, and every network call fails the test."""

import json
import urllib.request

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.channels import conversation as conv
from backend.app.channels import sms, sms_reply, whatsapp
from backend.app.channels.provider import ServicesProvider
from backend.app.chat.llm import RateLimiter

PHONE = "923001234567"
TOKEN = "test-token"
OPTIONS = conv.default_options()
CROP = {c: str(i) for i, c in enumerate(OPTIONS.crops, 1)}
MANDI = {m: str(i) for i, m in enumerate(OPTIONS.mandis, 1)}
VARIETY = {v: str(i) for i, v in enumerate(OPTIONS.rice_varieties, 1)}
ADVICE = {"crop_option": "Wheat", "mandi": "BahawalPur", "signal": "SELL", "current_price": 3820,
          "predicted_price": 3820, "range": {"low": 3606.54, "high": 4071.05}, "rupee_impact": -4848,
          "interest_cost": 4848, "quantity_maund": 100, "confidence": "MEDIUM", "prices_as_of": "2026-10-09",
          "is_stale": False, "price_unchanged_since": None, "is_synthetic": False}


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    db.reset()

    def no_network(*a, **k):
        raise AssertionError("a test tried to reach the network")
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    monkeypatch.delenv("FS_SMS_PROVIDER", raising=False)
    yield
    db.reset()


class FakeProvider:
    def __init__(self, advice=None, registered=(PHONE,)):
        self.a, self.calls = dict(advice or ADVICE), []
        self.alerts = {p: False for p in registered}

    def advice(self, crop_option, mandi, quantity_maund, phone):
        self.calls.append(("advice", crop_option, mandi, quantity_maund))
        return {**self.a, "crop_option": crop_option, "mandi": mandi, "quantity_maund": quantity_maund}

    def explain(self, crop_option, mandi, phone):
        return [{"text_ur": "وجہ", "text_en": "The price rose 3% over the last 4 weeks", "direction": "UP"}]

    def compare(self, crop_option, mandi, quantity_maund, phone):
        return [{"mandi": "Vehari", "net_price": 3900, "transport_cost": 165, "gain_vs_preferred": 8000,
                 "has_data": True, "is_stale": False},
                {"mandi": "BahawalPur", "net_price": 3820, "transport_cost": 0, "gain_vs_preferred": 0,
                 "has_data": True, "is_stale": True},
                {"mandi": "RahimYarKhan", "has_data": False}]

    def set_alerts(self, phone, enabled):
        if phone not in self.alerts:
            return False
        self.alerts[phone] = enabled
        return True

    def alerts_enabled(self, phone):
        return self.alerts.get(phone)


class StubVendorAdapter:
    """Stands in for a real vendor adapter: a shared-token check and a small JSON payload."""

    def __init__(self, sender):
        self._sender = sender

    def verify(self, raw, headers):
        return headers.get("X-Test-Token") == TOKEN

    def parse(self, raw, headers):
        try:
            body = json.loads(raw)
            return [sms.InboundSms(m["from"], m["text"], m.get("id", "")) for m in body["messages"]]
        except (ValueError, KeyError, TypeError) as e:
            raise ValueError("malformed") from e

    def acknowledge(self, queued):
        return JSONResponse({"queued": queued})

    def sender(self):
        return self._sender


def check_sms(text):
    assert sms_reply.is_gsm7(text), text
    assert len(text) <= sms_reply.MAX_CHARS, (len(text), text)
    assert sms_reply.parts(text) <= 2


def say(provider, *texts, phone=PHONE):
    out = None
    for t in texts:
        out = sms.respond(sms.InboundSms(phone, t), provider)
        check_sms(out)
    return out


# ---------------------------------------------------------------- senders and configuration

def test_unconfigured_sms_sends_nothing_and_says_so(caplog):
    assert not sms.configured()
    sender = sms.get_sms_sender()
    assert isinstance(sender, sms.NullSmsSender)
    assert sender.send(PHONE, "x") is False
    assert "no SMS provider" in caplog.text and PHONE not in caplog.text
    assert sms.alert_sender() is None


def test_a_provider_name_without_an_adapter_stays_off(monkeypatch):
    monkeypatch.setenv("FS_SMS_PROVIDER", "somevendor")
    assert sms.ADAPTERS == {}   # no vendor has been integrated
    assert not sms.configured() and isinstance(sms.get_sms_sender(), sms.NullSmsSender)


def test_fake_sender_records():
    s = sms.FakeSmsSender()
    assert s.send(PHONE, "hi") and s.sent == [(PHONE, "hi")]


# ---------------------------------------------------------------- Roman Urdu replies

def test_menu_fits_one_sms_and_lists_every_number():
    text = say(FakeProvider(), "0")
    assert sms_reply.parts(text) == 1
    for n, label in (("1", "Rate/mashwara"), ("2", "Mandiyan"), ("3", "Kyun"), ("4", "Alert on"),
                     ("5", "Alert band"), ("0", "Menu")):
        assert f"{n} {label}" in text


def test_numeric_flow_ends_in_the_same_advice_numbers():
    provider = FakeProvider()
    assert say(provider, "0", "1").startswith("Fasal? 1 Gandum 2 Kapas 3 Chawal 0 Menu")
    assert say(provider, CROP["Wheat"]).startswith("Mandi? 1 Bahawalpur")
    assert say(provider, MANDI["BahawalPur"]).startswith(sms_reply.ASK["ask_quantity"])
    text = say(provider, "100")
    assert provider.calls == [("advice", "Wheat", "BahawalPur", 100.0)]
    for part in ("FarmSight Gandum Bahawalpur: bech dein.", "Aaj Rs3820/man (AMIS 2026-10-09).",
                 "4 hafte baad Rs3820 (Rs3607-Rs4071).", sms_reply.GUESS, "100 man rukne ka farq -Rs4848",
                 "1 Kyun 2 Mandiyan 3 Alert on 0 Menu"):
        assert part in text, part


def test_rice_variety_branch():
    provider = FakeProvider()
    assert say(provider, "0", "1", CROP[conv.RICE]).startswith("Kon se chawal? 1 Chawal Super Basmati 2 Chawal IRRI")
    say(provider, VARIETY["IRRI"], MANDI["Vehari"], "40")
    assert provider.calls == [("advice", "IRRI", "Vehari", 40.0)]


def test_free_text_and_after_advice_numbers():
    provider = FakeProvider()
    say(provider, "gandum bahawalpur 100 man")
    assert provider.calls == [("advice", "Wheat", "BahawalPur", 100.0)]
    why = say(provider, "1")
    assert "wajah:" in why and "The price rose 3%" in why
    compare = say(provider, "2")
    assert "Vehari Rs3900 +Rs8000;" in compare and "Bahawalpur Rs3820 (purana);" in compare
    assert "Rahim Yar Khan rate nahi;" in compare


def test_invalid_and_no_session_numbers():
    provider = FakeProvider()
    assert say(provider, "4").startswith(sms_reply.MENU_NOTE["no_session"]) and provider.alerts[PHONE] is False
    assert say(provider, "0", "1", "9").startswith(sms_reply.INVALID)


def test_stale_frozen_and_synthetic_warnings_are_never_dropped():
    old = {**ADVICE, "is_stale": True, "prices_as_of": "2026-07-01", "price_unchanged_since": "2026-06-01",
           "is_synthetic": True, "quantity_maund": 123456.75}
    text = sms_reply.advice_sms(old, quantity_assumed=True, choices=conv.post_choices(True))
    check_sms(text)
    assert "DHYAN: AMIS rate 2026-06-01 se nahi badla." in text and "MASNOI DATA" in text
    stale = sms_reply.advice_sms({**ADVICE, "is_stale": True, "prices_as_of": "2026-07-01"}, False)
    assert "DHYAN: purana rate (2026-07-01)." in stale


def test_too_long_drops_optional_detail_says_where_it_is_and_keeps_the_choices():
    reasons = [{"text_en": "A long reason " * 20}] * 3
    text = sms_reply.why_sms({**ADVICE, "is_stale": True}, reasons, conv.post_choices(False))
    check_sms(text)
    assert "DHYAN: purana rate" in text and sms_reply.MORE_IN_APP in text and text.endswith("0 Menu")


def test_every_reply_kind_fits():
    provider = FakeProvider(registered=())
    for texts in (("0",), ("hello there friend",), ("0", "1"), ("0", "1", CROP[conv.RICE]), ("0", "4"),
                  ("gandum bwp", "3"), ("gandum bwp", "baarish kab hogi"), ("0", "1", "1", "1", "abc")):
        db.reset()
        say(provider, *texts)


def test_whatsapp_and_sms_give_the_same_numbers_from_the_real_service_layer():
    from backend.app import services

    price, as_of = services.latest_price("Wheat", "BahawalPur")
    a = services.get_advice("Wheat", "BahawalPur", 100)
    text = say(ServicesProvider(), "gandum bahawalpur 100 man", phone="920000000009")
    wa = whatsapp.respond({"from": "920000000009", "id": "x", "type": "text",
                           "text": {"body": "gandum bahawalpur 100 man"}}, ServicesProvider())
    wa_body = wa["interactive"]["body"]["text"]
    assert sms_reply.rs(price) in text and as_of in text and as_of in wa_body
    assert sms_reply.rs(a["range"]["low"]) in text and f"{round(a['range']['low']):,}" in wa_body


def test_whatsapp_and_sms_sessions_are_separate():
    provider = FakeProvider()
    whatsapp.respond({"from": PHONE, "id": "w", "type": "text", "text": {"body": "0"}}, provider)
    whatsapp.respond({"from": PHONE, "id": "w2", "type": "text", "text": {"body": "1"}}, provider)
    assert say(provider, CROP["Wheat"]).startswith(sms_reply.MENU_NOTE["no_session"])


# ---------------------------------------------------------------- inbound webhook

@pytest.fixture
def webhook(monkeypatch):
    sender, provider = sms.FakeSmsSender(), FakeProvider()
    monkeypatch.setitem(sms.ADAPTERS, "testvendor", lambda settings: StubVendorAdapter(sender))
    monkeypatch.setenv("FS_SMS_PROVIDER", "testvendor")
    monkeypatch.setattr(sms, "_limiters", {})
    app = FastAPI()
    app.include_router(sms.router)
    app.dependency_overrides[sms.get_provider] = lambda: provider
    return TestClient(app), sender, provider


def post(client, *messages, token=TOKEN):
    return client.post("/webhooks/sms", content=json.dumps({"messages": list(messages)}),
                       headers={"X-Test-Token": token})


def msg(text, mid, phone=PHONE):
    return {"from": phone, "text": text, "id": mid}


def test_route_is_off_without_an_adapter():
    app = FastAPI()
    app.include_router(sms.router)
    assert TestClient(app).post("/webhooks/sms", content=b"{}").status_code == 503


def test_two_way_numeric_flow_through_the_webhook(webhook):
    client, sender, provider = webhook
    for i, t in enumerate(["0", "1", CROP["Wheat"], MANDI["Vehari"], "50"]):
        assert post(client, msg(t, f"s{i}")).json() == {"queued": 1}
    assert [to for to, _ in sender.sent] == [PHONE] * 5
    assert "bech dein" in sender.sent[-1][1] and provider.calls == [("advice", "Wheat", "Vehari", 50.0)]


def test_bad_token_and_malformed_payloads(webhook):
    client, sender, _ = webhook
    assert post(client, msg("0", "a"), token="wrong").status_code == 403
    assert client.post("/webhooks/sms", content=b"not json", headers={"X-Test-Token": TOKEN}).status_code == 400
    assert client.post("/webhooks/sms", content=b'{"messages": [{"text": "0"}]}',
                       headers={"X-Test-Token": TOKEN}).status_code == 400
    assert post(client, msg("0", "b", phone="unknown")).json() == {"queued": 0}   # no digits: ignored
    assert sender.sent == []


def test_retried_delivery_is_answered_once(webhook):
    client, sender, _ = webhook
    assert post(client, msg("0", "same")).json() == {"queued": 1}
    assert post(client, msg("0", "same")).json() == {"queued": 0}
    assert len(sender.sent) == 1


def test_rate_limit_per_number(webhook, monkeypatch):
    client, sender, _ = webhook
    monkeypatch.setenv("FS_SMS_REPLIES_PER_MIN", "2")
    for i in range(3):
        post(client, msg("0", f"r{i}"))
    post(client, msg("0", "other", phone="923007654321"))
    assert [to for to, _ in sender.sent] == [PHONE, PHONE, "923007654321"]


def test_handle_respects_the_limiter_directly():
    sender, limiter = sms.FakeSmsSender(), RateLimiter(1)
    assert sms.handle(sms.InboundSms(PHONE, "0"), FakeProvider(), sender, limiter)
    assert not sms.handle(sms.InboundSms(PHONE, "0"), FakeProvider(), sender, limiter)
    assert len(sender.sent) == 1


def test_alert_opt_in_and_out_by_sms(webhook):
    client, sender, provider = webhook
    post(client, msg("0", "a1"))
    post(client, msg("4", "a2"))
    assert provider.alerts[PHONE] is True and sender.sent[-1][1].startswith(sms_reply.STARTED)
    post(client, msg("band", "a3"))
    assert provider.alerts[PHONE] is False and sender.sent[-1][1].startswith("Alerts band.")


def test_phone_numbers_and_text_are_not_logged(webhook, caplog):
    client, _, _ = webhook
    caplog.set_level("DEBUG")
    post(client, msg("gandum vehari 77 man", "log"))
    assert PHONE not in caplog.text and "vehari" not in caplog.text.lower()
