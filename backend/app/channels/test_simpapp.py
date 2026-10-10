"""SMS Gateway API (Simpapp) gateway: all mocked. No account, phone or network call is used."""

import json
import logging
import urllib.error

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.channels import reply, simpapp, sms, whatsapp
from backend.app.channels.test_textbee import Opener, Outbox, Response
from backend.app.channels.test_whatsapp import FakeProvider

API_KEY = "sk_live_test_key_not_real_0123456789"
SECRET = "webhook-token-for-tests-only-0123456"
SENDER = "+923001234567"
V1 = simpapp.DEFAULT_API_URL
V2 = "https://europe-west1-sms-gateway-api-simpapp.cloudfunctions.net/api_v2_sms_send"
SETTINGS = simpapp.SimpappSettings(api_url=V1, api_key=API_KEY, webhook_secret=SECRET)
URL = f"/api/channels/sms/simpapp/webhook?token={SECRET}"


def incoming(message="گندم بہاولپور 100 من", timestamp=1760090000, **extra):
    return {"type": "incoming_sms", "sender": SENDER, "message": message, "timestamp": timestamp, **extra}


@pytest.fixture
def gateway(monkeypatch):
    db.reset()
    fresh = whatsapp.Memory()   # respond() binds MEMORY as a default argument, so empty that object
    monkeypatch.setattr(whatsapp.MEMORY, "last", fresh.last)
    monkeypatch.setattr(whatsapp.MEMORY, "seen", fresh.seen)
    outbox, provider, app = Outbox(), FakeProvider(), FastAPI()
    app.include_router(simpapp.router)
    app.dependency_overrides[simpapp.get_simpapp_settings] = lambda: SETTINGS
    app.dependency_overrides[simpapp.get_provider] = lambda: provider
    app.dependency_overrides[simpapp.get_simpapp_outbound] = lambda: outbox
    yield TestClient(app), outbox, provider
    db.reset()


def post(client, payload, url=URL):
    return client.post(url, content=json.dumps(payload, ensure_ascii=False).encode(),
                       headers={"Content-Type": "application/json"})


# ---------------------------------------------------------------- outbound

def test_v1_request_shape_and_x_api_key():
    opener = Opener(Response({"success": True, "messageId": "sms_abc123xyz", "status": "queued"}))
    result = simpapp.SimpappSmsProvider(SETTINGS, opener).send("03001234567", "سلام")
    [(req, timeout)] = opener.requests
    assert req.full_url == V1 and req.get_method() == "POST" and timeout == simpapp.TIMEOUT_S
    assert req.get_header("X-api-key") == API_KEY and req.get_header("Authorization") is None
    assert req.get_header("Content-type") == "application/json"
    assert json.loads(req.data) == {"phoneNumber": SENDER, "message": "سلام"}
    assert result == sms.SendResult("ACCEPTED", 200, "sms_abc123xyz")


def test_v2_uses_a_bearer_token():
    opener = Opener(Response({"success": True, "messageId": "m1", "status": "queued"}))
    settings = simpapp.SimpappSettings(V2, API_KEY, SECRET)
    assert simpapp.SimpappSmsProvider(settings, opener).send(SENDER, "x").accepted
    req = opener.requests[0][0]
    assert req.get_header("Authorization") == f"Bearer {API_KEY}" and req.get_header("X-api-key") is None


def test_missing_configuration_fails_closed(monkeypatch):
    with pytest.raises(sms.SmsConfigError, match="SIMPAPP_SMS_API_KEY"):
        simpapp.SimpappSmsProvider(simpapp.SimpappSettings(V1, "", SECRET))
    with pytest.raises(sms.SmsConfigError, match="https"):
        simpapp.SimpappSmsProvider(simpapp.SimpappSettings("http://example.test/api_sms_send", API_KEY, SECRET))
    monkeypatch.setenv("SMS_PROVIDER", "simpapp")
    monkeypatch.delenv("SIMPAPP_SMS_API_KEY", raising=False)
    assert simpapp.get_simpapp_outbound() is None
    monkeypatch.setenv("SIMPAPP_SMS_API_KEY", API_KEY)
    monkeypatch.delenv("SIMPAPP_SMS_API_URL", raising=False)
    p = simpapp.get_simpapp_outbound()
    assert isinstance(p, simpapp.SimpappSmsProvider) and p.s.api_url == V1
    monkeypatch.setenv("SMS_PROVIDER", "textbee")   # another provider chosen: this webhook does not reply
    assert simpapp.get_simpapp_outbound() is None


@pytest.mark.parametrize("answer, status", [
    (urllib.error.HTTPError(V1, 400, "Bad Request", {}, None), "FAILED"),
    (urllib.error.HTTPError(V1, 401, "Unauthorized", {}, None), "FAILED"),
    (urllib.error.HTTPError(V1, 403, "Subscription required", {}, None), "FAILED"),
    (urllib.error.HTTPError(V1, 429, "Too Many Requests", {}, None), "FAILED"),
    (urllib.error.HTTPError(V1, 503, "Device offline", {}, None), "FAILED"),
    (urllib.error.HTTPError(V1, 500, "Internal error", {}, None), "UNKNOWN"),
    (urllib.error.URLError(TimeoutError()), "UNKNOWN"),
    (urllib.error.URLError(ConnectionRefusedError()), "FAILED"),
    (TimeoutError(), "UNKNOWN"),
    (Response({"success": False, "error": "Invalid API key", "code": 401}), "FAILED"),
    (Response({"messageId": "m"}), "FAILED"),
])
def test_send_failures_are_safe_never_retried_and_leak_nothing(answer, status, caplog):
    opener = Opener(answer)
    with caplog.at_level(logging.DEBUG):
        result = simpapp.SimpappSmsProvider(SETTINGS, opener).send(SENDER, "گندم کا ریٹ")
    assert result.status == status and not result.accepted and len(opener.requests) == 1
    for secret in (API_KEY, SECRET, SENDER, "923001234567", "گندم کا ریٹ"):
        assert secret not in caplog.text


# ---------------------------------------------------------------- inbound webhook

def test_incoming_sms_goes_through_the_shared_conversation(gateway):
    client, outbox, _ = gateway
    r = post(client, incoming())
    assert r.status_code == 200 and r.json() == {"status": "accepted"} and "sms_text" not in r.text
    advice = FakeProvider().advice("Wheat", "BahawalPur", 100, "")
    assert outbox.sent == [(SENDER, reply.advice_text(advice) + "\n" + sms.COMMAND_LINE)]
    post(client, incoming("1", timestamp=1760090060))     # the existing "why" command
    assert outbox.sent[1][1].startswith(reply.why_text(advice, FakeProvider().explain("Wheat", "BahawalPur", "")))


def test_first_message_without_a_query_gets_the_help_text(gateway):
    client, outbox, _ = gateway
    post(client, incoming("0"))
    assert outbox.sent[0][1] == reply.NOT_UNDERSTOOD   # "0" is no command today: the help text, unchanged


def test_repeated_delivery_gets_no_second_reply(gateway):
    client, outbox, _ = gateway
    assert post(client, incoming()).json()["status"] == "accepted"
    assert post(client, incoming()).json() == {"status": "duplicate"}
    assert post(client, incoming(timestamp=1760090001)).json()["status"] == "accepted"   # a new message
    assert len(outbox.sent) == 2


@pytest.mark.parametrize("url", ["/api/channels/sms/simpapp/webhook",
                                 "/api/channels/sms/simpapp/webhook?token=wrong-token-of-enough-length",
                                 f"/api/channels/sms/simpapp/webhook?token={SECRET}x"])
def test_missing_or_wrong_token_is_rejected(gateway, url):
    client, outbox, _ = gateway
    assert post(client, incoming(), url=url).status_code == 401 and outbox.sent == []


def test_delivery_reports_are_acknowledged_without_a_reply(gateway):
    client, outbox, _ = gateway
    r = post(client, {"type": "delivery_status", "id": "sms_abc123xyz", "phoneNumber": SENDER,
                      "status": "delivered", "timestamp": 1714000000})
    assert r.status_code == 200 and r.json() == {"status": "ignored"} and outbox.sent == []


@pytest.mark.parametrize("change", [{"sender": None}, {"message": 5}, {"message": "x" * 2001},
                                    {"timestamp": "1760090000"}, {"timestamp": 12}, {"timestamp": None}])
def test_malformed_events_are_rejected(gateway, change):
    client, outbox, _ = gateway
    assert post(client, {**incoming(), **change}).status_code == 422 and outbox.sent == []


def test_short_codes_and_non_json_get_no_reply(gateway):
    client, outbox, _ = gateway
    assert post(client, incoming(sender="8558")).json() == {"status": "ignored"}
    assert post(client, [1]).status_code == 400
    assert client.post(URL, content=b"not json").status_code == 400
    assert outbox.sent == []


def test_unconfigured_webhook_refuses_and_claims_nothing(gateway):
    client, outbox, _ = gateway
    client.app.dependency_overrides[simpapp.get_simpapp_settings] = lambda: simpapp.SimpappSettings(V1, API_KEY, "")
    assert post(client, incoming()).status_code == 503
    client.app.dependency_overrides[simpapp.get_simpapp_settings] = lambda: SETTINGS
    client.app.dependency_overrides[simpapp.get_simpapp_outbound] = lambda: None
    assert post(client, incoming()).status_code == 503
    client.app.dependency_overrides[simpapp.get_simpapp_outbound] = lambda: outbox
    assert post(client, incoming()).json()["status"] == "accepted" and len(outbox.sent) == 1


def test_provider_failure_is_recorded_safely(gateway, caplog):
    client, _, _ = gateway
    failing = Outbox(status="FAILED")
    client.app.dependency_overrides[simpapp.get_simpapp_outbound] = lambda: failing
    with caplog.at_level(logging.DEBUG):
        r = post(client, incoming())
        again = post(client, incoming())
    assert r.json() == {"status": "accepted"} and again.json() == {"status": "duplicate"} and len(failing.sent) == 1
    key = simpapp.event_key(simpapp.IncomingSms.model_validate(incoming()), SENDER)
    assert db.sms_event_status(key) == "FAILED"
    for secret in (API_KEY, SECRET, SENDER, "923001234567", "گندم بہاولپور"):
        assert secret not in caplog.text and secret not in r.text


def test_access_log_lines_never_show_the_token(caplog):
    # uvicorn's access log: '%s - "%s %s HTTP/%s" %d' with the full path, query string included.
    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        logging.getLogger("uvicorn.access").info('%s - "%s %s HTTP/%s" %d', "1.2.3.4:5", "POST",
                                                 f"/api/channels/sms/simpapp/webhook?token={SECRET}&x=1", "1.1", 200)
    assert SECRET not in caplog.text and "token=***&x=1" in caplog.text


def test_engine_error_sends_nothing_and_shows_no_trace(gateway, monkeypatch):
    client, outbox, _ = gateway

    def broken(*a, **k):
        raise RuntimeError("internal detail")

    monkeypatch.setattr(whatsapp, "respond", broken)
    r = post(client, incoming())
    assert r.status_code == 200 and "internal" not in r.text and outbox.sent == []
