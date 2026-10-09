import hashlib
import hmac
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.channels import reply, whatsapp
from backend.app.channels.parse import parse

SECRET = "test-app-secret"
SETTINGS = whatsapp.WhatsAppSettings(verify_token="verify-me", app_secret=SECRET, access_token="t",
                                     phone_number_id="123")
PHONE = "923001234567"


class FakeProvider:
    def __init__(self, missing=()):
        self.missing, self.alerts = set(missing), {}

    def advice(self, crop_option, mandi, quantity_maund, phone):
        if (crop_option, mandi) in self.missing:
            raise LookupError
        return {"crop_option": crop_option, "mandi": mandi, "signal": "WAIT", "current_price": 3820,
                "predicted_price": 4050, "range": {"low": 3700, "high": 4300}, "rupee_impact": 17747,
                "interest_cost": 5253, "quantity_maund": quantity_maund, "confidence": "MEDIUM",
                "prices_as_of": "2026-10-09", "is_synthetic": True}

    def explain(self, crop_option, mandi, phone):
        return [{"text_ur": "پچھلے 4 ہفتوں میں ریٹ بڑھا", "direction": "UP"}]

    def compare(self, crop_option, mandi, quantity_maund, phone):
        return [{"mandi": "Vehari", "net_price": 3900, "transport_cost": 165, "gain_vs_preferred": 80,
                 "has_data": True},
                {"mandi": "BahawalPur", "net_price": 3820, "transport_cost": 0, "gain_vs_preferred": 0,
                 "has_data": True}]

    def set_alerts(self, phone, enabled):
        self.alerts[phone] = enabled


class FakeSender:
    def __init__(self):
        self.sent = []

    def send(self, to, message):
        self.sent.append((to, message))


def body_of(message):
    return message["text"]["body"] if message["type"] == "text" else message["interactive"]["body"]["text"]


def text_msg(body, mid="wamid.1"):
    return {"from": PHONE, "id": mid, "type": "text", "text": {"body": body}}


# ---------------------------------------------------------------- parsing

@pytest.mark.parametrize("text, crop, mandi, qty", [
    ("گندم بہاولپور 100 من", "Wheat", "BahawalPur", 100),
    ("gandum vehari 50 mann", "Wheat", "Vehari", 50),
    ("گندم بہاولپور ۱۰۰ من", "Wheat", "BahawalPur", 100),          # Urdu digits
    ("Super Basmati Rahim Yar Khan 2000 kg", "SuperBasmati", "RahimYarKhan", 50),
    ("kapas RYK", "Cotton", "RahimYarKhan", None),
    ("چاول اری وہاڑی 30", "IRRI", "Vehari", 30),
])
def test_parse_queries(text, crop, mandi, qty):
    p = parse(text)
    assert (p.kind, p.crop_option, p.mandi, p.quantity_maund, p.missing) == ("query", crop, mandi, qty, [])


def test_parse_asks_instead_of_guessing():
    assert parse("chawal bahawalpur").missing == ["variety"]
    assert parse("gandum 100 mann").missing == ["mandi"]
    assert parse("vehari").missing == ["crop"]


@pytest.mark.parametrize("text, kind", [("کیوں", "why"), ("why?", "why"), ("2", "compare"), ("بند", "stop"),
                                        ("hi", "help"), ("", "help"), ("kal ka mausam", "unknown")])
def test_parse_commands(text, kind):
    assert parse(text).kind == kind


# ---------------------------------------------------------------- replies

def test_query_reply_uses_only_the_advice_numbers():
    out = whatsapp.respond(text_msg("گندم بہاولپور 100 من"), FakeProvider(), whatsapp.Memory())
    body = body_of(out)
    assert out["type"] == "interactive"
    for expected in ("رکیں", "Rs 3,820", "Rs 4,050", "Rs 3,700", "Rs 4,300", "+Rs 17,747", "Rs 5,253",
                     "2026-10-09", reply.SYNTHETIC, reply.DISCLAIMER):
        assert expected in body
    buttons = out["interactive"]["action"]["buttons"]
    assert len(buttons) <= 3 and all(len(b["reply"]["title"]) <= 20 for b in buttons)
    assert len(body) <= reply.MAX_BODY


def test_missing_quantity_assumes_100_and_says_so():
    body = body_of(whatsapp.respond(text_msg("gandum bahawalpur"), FakeProvider(), whatsapp.Memory()))
    assert "100 من مان کر" in body


def test_why_and_compare_follow_the_last_query():
    memory, provider = whatsapp.Memory(), FakeProvider()
    assert body_of(whatsapp.respond(text_msg("کیوں"), provider, memory)) == reply.NEED_QUERY_FIRST
    whatsapp.respond(text_msg("گندم بہاولپور 100 من"), provider, memory)
    tap = {"from": PHONE, "id": "x", "type": "interactive",
           "interactive": {"type": "button_reply", "button_reply": {"id": "why", "title": "کیوں؟"}}}
    assert "پچھلے 4 ہفتوں میں ریٹ بڑھا" in body_of(whatsapp.respond(tap, provider, memory))
    compare = body_of(whatsapp.respond(text_msg("2"), provider, memory))
    assert compare.index("وہاڑی") < compare.index("بہاولپور") and "+Rs 80" in compare


def test_no_price_data_is_said_plainly():
    provider = FakeProvider(missing={("IRRI", "RahimYarKhan")})
    body = body_of(whatsapp.respond(text_msg("chawal irri ryk 40"), provider, whatsapp.Memory()))
    assert "رحیم یار خان" in body and "موجود نہیں" in body


def test_until_services_exist_the_reply_is_honest():
    provider = whatsapp.ServicesProvider()
    body = body_of(whatsapp.respond(text_msg("gandum bahawalpur 100"), provider, whatsapp.Memory()))
    assert body == reply.NOT_READY


def test_stop_turns_alerts_off_and_voice_is_deferred():
    provider = FakeProvider()
    assert body_of(whatsapp.respond(text_msg("بند"), provider, whatsapp.Memory())) == reply.STOPPED
    assert provider.alerts[PHONE] is False
    voice = {"from": PHONE, "id": "v", "type": "audio", "audio": {"id": "media"}}
    assert body_of(whatsapp.respond(voice, provider, whatsapp.Memory())) == reply.VOICE_SOON


# ---------------------------------------------------------------- webhook

@pytest.fixture
def app_and_sender(monkeypatch):
    monkeypatch.setattr(whatsapp, "MEMORY", whatsapp.Memory())
    sender, app = FakeSender(), FastAPI()
    app.include_router(whatsapp.router)
    app.dependency_overrides[whatsapp.get_wa_settings] = lambda: SETTINGS
    app.dependency_overrides[whatsapp.get_provider] = FakeProvider
    app.dependency_overrides[whatsapp.get_sender] = lambda: sender
    return TestClient(app), sender


def signed(payload):
    raw = json.dumps(payload).encode()
    signature = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return raw, {"X-Hub-Signature-256": "sha256=" + signature, "Content-Type": "application/json"}


def meta_payload(*messages):
    return {"object": "whatsapp_business_account",
            "entry": [{"changes": [{"value": {"messaging_product": "whatsapp", "messages": list(messages)}}]}]}


def test_verification_handshake(app_and_sender):
    client, _ = app_and_sender
    ok = client.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "verify-me",
                                                  "hub.challenge": "1158201444"})
    assert ok.status_code == 200 and ok.text == "1158201444"
    bad = client.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "nope",
                                                   "hub.challenge": "x"})
    assert bad.status_code == 403


def test_signed_message_gets_one_reply_even_if_meta_retries(app_and_sender):
    client, sender = app_and_sender
    raw, headers = signed(meta_payload(text_msg("گندم بہاولپور 100 من", mid="wamid.A")))
    assert client.post("/webhooks/whatsapp", content=raw, headers=headers).json()["queued"] == 1
    assert client.post("/webhooks/whatsapp", content=raw, headers=headers).json()["queued"] == 0
    assert len(sender.sent) == 1 and sender.sent[0][0] == PHONE


def test_unsigned_or_tampered_requests_are_rejected(app_and_sender):
    client, sender = app_and_sender
    raw, headers = signed(meta_payload(text_msg("gandum bahawalpur")))
    assert client.post("/webhooks/whatsapp", content=raw).status_code == 403
    assert client.post("/webhooks/whatsapp", content=raw + b" ", headers=headers).status_code == 403
    assert sender.sent == []


def test_unconfigured_webhook_refuses(app_and_sender):
    client, _ = app_and_sender
    client.app.dependency_overrides[whatsapp.get_wa_settings] = lambda: whatsapp.WhatsAppSettings("", "", "", "")
    assert client.post("/webhooks/whatsapp", content=b"{}").status_code == 503


def test_signature_check():
    raw = b'{"a":1}'
    good = "sha256=" + hmac.new(b"s", raw, hashlib.sha256).hexdigest()
    assert whatsapp.signature_ok(raw, good, "s")
    assert not whatsapp.signature_ok(raw, good, "other") and not whatsapp.signature_ok(raw, None, "s")
