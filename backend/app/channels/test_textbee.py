"""TextBee SMS gateway: all mocked. No TextBee account, phone or network call is used."""

import hashlib
import hmac
import io
import json
import logging
import urllib.error

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.channels import reply, sms, textbee, whatsapp
from backend.app.channels.test_whatsapp import FakeProvider

API_KEY = "tb-test-key-not-real-0123456789"
SECRET = "webhook-secret-for-tests-only-0123"
DEVICE = "664a9b8cd0e1f2a3b4c5d6e7"
SENDER = "+923001234567"
SETTINGS = textbee.TextBeeSettings(api_key=API_KEY, device_id=DEVICE, base_url=textbee.DEFAULT_BASE_URL,
                                   webhook_secret=SECRET)
URL = "/api/channels/sms/textbee/webhook"


# ---------------------------------------------------------------- fakes

class Outbox:
    """Stands in for the outbound SMS provider."""

    name = "fake"

    def __init__(self, status="ACCEPTED"):
        self.status, self.sent = status, []

    def send(self, to, text):
        self.sent.append((to, text))
        return sms.SendResult(self.status)


class Response(io.BytesIO):
    def __init__(self, body, status=200):
        super().__init__(json.dumps(body).encode())
        self.status = status


class Opener:
    """Stands in for urllib.request.urlopen: records each request, then answers or raises."""

    def __init__(self, answer):
        self.answer, self.requests = answer, []

    def __call__(self, req, timeout=None):
        self.requests.append((req, timeout))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def event(message="گندم بہاولپور 100 من", key="8f7e6d5c-4b3a-4c1d-8e9f-8a7b6c5d4e3f", **extra):
    return {"smsId": "66f7c1e2a4d5e6f7a8b9c0d1", "message": message, "deviceId": DEVICE,
            "webhookSubscriptionId": "664a9b8cd0e1f2a3b4c5d6e8", "webhookEvent": "MESSAGE_RECEIVED",
            "idempotencyKey": key, "sender": SENDER, "receivedAt": "2026-10-10T09:14:03.000Z", **extra}


def signed(payload, secret=SECRET):
    raw = json.dumps(payload, ensure_ascii=False).encode()
    return raw, {"X-Signature": hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest(),
                 "Content-Type": "application/json"}


@pytest.fixture
def gateway(monkeypatch):
    db.reset()
    fresh = whatsapp.Memory()   # respond() binds MEMORY as a default argument, so empty that object
    monkeypatch.setattr(whatsapp.MEMORY, "last", fresh.last)
    monkeypatch.setattr(whatsapp.MEMORY, "seen", fresh.seen)
    outbox, provider, app = Outbox(), FakeProvider(), FastAPI()
    app.include_router(textbee.router)
    app.dependency_overrides[textbee.get_textbee_settings] = lambda: SETTINGS
    app.dependency_overrides[textbee.get_provider] = lambda: provider
    app.dependency_overrides[textbee.get_outbound] = lambda: outbox
    yield TestClient(app), outbox, provider
    db.reset()


def post(client, payload, **kw):
    raw, headers = signed(payload, **kw)
    return client.post(URL, content=raw, headers=headers)


# ---------------------------------------------------------------- outbound

def test_send_request_shape_and_api_key_header():
    opener = Opener(Response({"data": {"success": True, "smsBatchId": "batch-1", "recipientCount": 1}}))
    result = textbee.TextBeeSmsProvider(SETTINGS, opener).send("0300-1234567", "سلام")
    [(req, timeout)] = opener.requests
    assert req.full_url == "https://api.textbee.dev/api/v1/gateway/send-sms" and req.get_method() == "POST"
    assert req.get_header("X-api-key") == API_KEY and req.get_header("Content-type") == "application/json"
    assert json.loads(req.data) == {"recipients": [SENDER], "message": "سلام", "deviceId": DEVICE}
    assert timeout == textbee.TIMEOUT_S
    assert result == sms.SendResult("ACCEPTED", 200, "batch-1") and result.accepted


def test_device_id_is_left_out_when_not_configured():
    opener = Opener(Response({"data": {"successCount": 1}}))
    settings = textbee.TextBeeSettings(API_KEY, "", textbee.DEFAULT_BASE_URL, SECRET)
    assert textbee.TextBeeSmsProvider(settings, opener).send(SENDER, "x").accepted
    assert "deviceId" not in json.loads(opener.requests[0][0].data)


def test_missing_configuration_fails_closed(monkeypatch):
    with pytest.raises(sms.SmsConfigError, match="TEXTBEE_API_KEY"):
        textbee.TextBeeSmsProvider(textbee.TextBeeSettings("", DEVICE, textbee.DEFAULT_BASE_URL, SECRET))
    with pytest.raises(sms.SmsConfigError, match="https"):
        textbee.TextBeeSmsProvider(textbee.TextBeeSettings(API_KEY, "", "http://api.textbee.dev/api/v1", SECRET))
    monkeypatch.delenv("SMS_PROVIDER", raising=False)
    with pytest.raises(sms.SmsConfigError, match="SMS_PROVIDER"):
        sms.get_sms_provider()
    monkeypatch.setenv("SMS_PROVIDER", "textbee")
    monkeypatch.delenv("TEXTBEE_API_KEY", raising=False)
    with pytest.raises(sms.SmsConfigError) as e:
        sms.get_sms_provider()
    assert "TEXTBEE_API_KEY" in str(e.value)
    monkeypatch.setenv("TEXTBEE_API_KEY", API_KEY)
    assert isinstance(sms.get_sms_provider(), textbee.TextBeeSmsProvider)
    monkeypatch.setenv("SMS_PROVIDER", "twilio")
    with pytest.raises(sms.SmsConfigError):
        sms.get_sms_provider()


@pytest.mark.parametrize("answer, status", [
    (urllib.error.HTTPError(textbee.DEFAULT_BASE_URL, 401, "Unauthorized", {}, None), "FAILED"),
    (urllib.error.HTTPError(textbee.DEFAULT_BASE_URL, 429, "Too Many Requests", {}, None), "FAILED"),
    (urllib.error.HTTPError(textbee.DEFAULT_BASE_URL, 502, "Bad Gateway", {}, None), "UNKNOWN"),
    (urllib.error.URLError(ConnectionRefusedError()), "FAILED"),
    (urllib.error.URLError(TimeoutError()), "UNKNOWN"),
    (TimeoutError(), "UNKNOWN"),
    (Response({"data": {"success": False}}), "FAILED"),
    (Response({"error": "no device"}), "FAILED"),
])
def test_send_failures_are_never_reported_as_sent_and_never_retried(answer, status, caplog):
    opener = Opener(answer)
    with caplog.at_level(logging.DEBUG):
        result = textbee.TextBeeSmsProvider(SETTINGS, opener).send(SENDER, "گندم کا ریٹ")
    assert result.status == status and not result.accepted
    assert len(opener.requests) == 1   # one attempt: a retry after a timeout could send it twice
    for secret in (API_KEY, SECRET, SENDER, "923001234567", "گندم کا ریٹ"):
        assert secret not in caplog.text


def test_send_refuses_a_number_that_is_not_a_pakistani_mobile():
    opener = Opener(Response({"data": {"success": True}}))
    assert textbee.TextBeeSmsProvider(SETTINGS, opener).send("8558", "x").status == "FAILED"
    assert opener.requests == []


# ---------------------------------------------------------------- phone numbers and rendering

@pytest.mark.parametrize("raw, e164", [
    ("+923001234567", SENDER), ("923001234567", SENDER), ("00923001234567", SENDER), ("03001234567", SENDER),
    ("3001234567", SENDER), ("+92 300 1234567", SENDER), ("0300-1234567", SENDER),
    ("8558", None), ("+12015550123", None), ("0622881234", None), ("+9230012345678", None), ("", None),
    ("+92300123456a", None), ("+924212345678", None),
])
def test_pakistani_numbers_are_normalised(raw, e164):
    assert sms.normalize_pk_phone(raw) == e164


def test_render_turns_buttons_into_the_sms_menu_numbers():
    assert sms.COMMAND_LINE == "2 منڈیاں | 3 کیوں؟ | 5 الرٹ بند | 0 مینو"
    assert sms.render(whatsapp.text_message("سلام")) == "سلام"
    assert sms.render(whatsapp.buttons_message("مشورہ")) == "مشورہ\n" + sms.COMMAND_LINE
    long = sms.render(whatsapp.buttons_message("ا" * 2000))
    assert len(long) <= sms.SMS_MAX_CHARS and long.endswith(sms.COMMAND_LINE)


# ---------------------------------------------------------------- inbound webhook

def test_signed_message_goes_through_the_shared_conversation(gateway):
    client, outbox, _ = gateway
    r = post(client, event())
    assert r.status_code == 200 and r.json() == {"status": "accepted"}
    [(to, text)] = outbox.sent
    advice = FakeProvider().advice("Wheat", "BahawalPur", 100, "")
    assert to == SENDER and text == reply.advice_text(advice) + "\n" + sms.COMMAND_LINE
    assert db.sms_event_status(event()["idempotencyKey"]) == "ACCEPTED"
    # SMS menu "3" is the existing "why" command, and the conversation remembers the query, as on WhatsApp.
    post(client, event("3", key="key-for-the-why-question"))
    assert outbox.sent[1][1].startswith(reply.why_text(advice, FakeProvider().explain("Wheat", "BahawalPur", "")))


def test_stop_reaches_the_existing_alerts_consent(gateway):
    client, outbox, provider = gateway
    post(client, event("5"))   # SMS menu 5: alerts off
    assert provider.alerts == {"923001234567": False} and outbox.sent[0][1] == reply.STOPPED


def test_duplicate_idempotency_key_gets_no_second_reply(gateway):
    client, outbox, _ = gateway
    assert post(client, event()).json()["status"] == "accepted"
    assert post(client, event()).json() == {"status": "duplicate"}
    assert post(client, event("1")).json() == {"status": "duplicate"}   # same key, whatever the body says
    assert len(outbox.sent) == 1


@pytest.mark.parametrize("headers", [{}, {"X-Signature": "0" * 64}, {"X-Signature": "not-hex"}])
def test_missing_or_bad_signature_is_rejected(gateway, headers):
    client, outbox, _ = gateway
    raw = json.dumps(event()).encode()
    assert client.post(URL, content=raw, headers=headers).status_code == 401
    assert outbox.sent == [] and db.sms_event_status(event()["idempotencyKey"]) is None


def test_tampered_body_or_other_secret_is_rejected(gateway):
    client, outbox, _ = gateway
    raw, headers = signed(event())
    assert client.post(URL, content=raw + b" ", headers=headers).status_code == 401
    assert post(client, event(), secret="another-secret-of-20-chars").status_code == 401
    assert outbox.sent == []


@pytest.mark.parametrize("kind", ["MESSAGE_SENT", "MESSAGE_DELIVERED", "MESSAGE_FAILED", "UNKNOWN_STATE"])
def test_status_events_are_acknowledged_without_a_reply(gateway, kind):
    client, outbox, _ = gateway
    r = post(client, {"webhookEvent": kind, "smsId": "1", "idempotencyKey": "k-status-0001"})
    assert r.status_code == 200 and r.json() == {"status": "ignored"} and outbox.sent == []


@pytest.mark.parametrize("change", [{"sender": None}, {"idempotencyKey": ""}, {"deviceId": ""},
                                    {"message": 5}, {"message": "x" * 2001}])
def test_malformed_events_are_rejected(gateway, change):
    client, outbox, _ = gateway
    assert post(client, {**event(), **change}).status_code == 422 and outbox.sent == []


def test_other_device_and_non_mobile_senders_get_no_reply(gateway):
    client, outbox, _ = gateway
    assert post(client, event(deviceId="someone-elses-phone")).status_code == 403
    assert post(client, event(sender="8558", key="key-from-a-short-code")).json() == {"status": "ignored"}
    assert post(client, [1]).status_code == 400
    assert outbox.sent == []


def test_unconfigured_webhook_refuses_and_claims_nothing(gateway):
    client, outbox, _ = gateway
    client.app.dependency_overrides[textbee.get_textbee_settings] = lambda: textbee.TextBeeSettings(
        API_KEY, DEVICE, textbee.DEFAULT_BASE_URL, "")
    assert post(client, event()).status_code == 503
    client.app.dependency_overrides[textbee.get_textbee_settings] = lambda: SETTINGS
    client.app.dependency_overrides[textbee.get_outbound] = lambda: None
    assert post(client, event()).status_code == 503   # TextBee retries it once SMS sending is configured
    assert db.sms_event_status(event()["idempotencyKey"]) is None and outbox.sent == []


def test_failed_send_is_recorded_not_retried_and_leaks_nothing(gateway, caplog):
    client, _, _ = gateway
    failing = Outbox(status="UNKNOWN")
    client.app.dependency_overrides[textbee.get_outbound] = lambda: failing
    with caplog.at_level(logging.DEBUG):
        r = post(client, event())
        again = post(client, event())
    assert r.json() == {"status": "accepted"} and again.json() == {"status": "duplicate"}
    assert len(failing.sent) == 1 and db.sms_event_status(event()["idempotencyKey"]) == "UNKNOWN"
    for secret in (API_KEY, SECRET, SENDER, "923001234567", "گندم بہاولپور"):
        assert secret not in caplog.text and secret not in r.text


def test_engine_error_sends_nothing_and_shows_no_trace(gateway, monkeypatch):
    client, outbox, _ = gateway

    def broken(*a, **k):
        raise RuntimeError("internal detail")

    monkeypatch.setattr(whatsapp, "respond", broken)
    r = post(client, event())
    assert r.status_code == 200 and "internal" not in r.text and outbox.sent == []
    assert db.sms_event_status(event()["idempotencyKey"]) == "ERROR"


def test_signature_check():
    raw = b'{"a":1}'
    good = hmac.new(b"s" * 20, raw, hashlib.sha256).hexdigest()
    assert textbee.signature_ok(raw, good, "s" * 20) and textbee.signature_ok(raw, good.upper(), "s" * 20)
    assert not textbee.signature_ok(raw, good, "t" * 20) and not textbee.signature_ok(raw, None, "s" * 20)
    assert not textbee.signature_ok(raw, good, "")
