import hashlib
import hmac
import json
import urllib.request
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.channels import conversation as conv
from backend.app.channels import provider as advice_provider
from backend.app.channels import reply, whatsapp
from backend.app.channels.parse import parse

SECRET = "test-app-secret"
SETTINGS = whatsapp.WhatsAppSettings(verify_token="verify-me", app_secret=SECRET, access_token="t",
                                     phone_number_id="123")
PHONE = "923001234567"
OPTIONS = conv.default_options()
CROP = {c: str(i) for i, c in enumerate(OPTIONS.crops, 1)}
MANDI = {m: str(i) for i, m in enumerate(OPTIONS.mandis, 1)}
VARIETY = {v: str(i) for i, v in enumerate(OPTIONS.rice_varieties, 1)}


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    db.reset()

    def no_network(*a, **k):
        raise AssertionError("a test tried to reach the network")
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    yield
    db.reset()


class FakeProvider:
    def __init__(self, missing=(), registered=(PHONE,)):
        self.missing, self.calls = set(missing), []
        self.alerts = {p: False for p in registered}   # registered farmers; alerts off until they opt in

    def advice(self, crop_option, mandi, quantity_maund, phone):
        self.calls.append(("advice", crop_option, mandi, quantity_maund))
        if (crop_option, mandi) in self.missing:
            raise LookupError
        return {"crop_option": crop_option, "mandi": mandi, "signal": "WAIT", "current_price": 3820,
                "predicted_price": 4050, "range": {"low": 3700, "high": 4300}, "rupee_impact": 17747,
                "interest_cost": 5253, "quantity_maund": quantity_maund, "confidence": "MEDIUM",
                "prices_as_of": "2026-10-09", "is_synthetic": True}

    def explain(self, crop_option, mandi, phone):
        return [{"text_ur": "پچھلے 4 ہفتوں میں ریٹ بڑھا", "direction": "UP"}]

    def compare(self, crop_option, mandi, quantity_maund, phone):
        self.calls.append(("compare", crop_option, mandi, quantity_maund))
        return [{"mandi": "Vehari", "net_price": 3900, "transport_cost": 165, "gain_vs_preferred": 80,
                 "has_data": True},
                {"mandi": "BahawalPur", "net_price": 3820, "transport_cost": 0, "gain_vs_preferred": 0,
                 "has_data": True}]

    def set_alerts(self, phone, enabled):
        if phone not in self.alerts:
            return False
        self.alerts[phone] = enabled
        return True

    def alerts_enabled(self, phone):
        return self.alerts.get(phone)


class FakeSender:
    def __init__(self):
        self.sent = []

    def send(self, to, message):
        self.sent.append((to, message))
        return True


def body_of(message):
    return message["text"]["body"] if message["type"] == "text" else message["interactive"]["body"]["text"]


def button_ids(message):
    if message["type"] != "interactive":
        return []
    return [b["reply"]["id"] for b in message["interactive"]["action"]["buttons"]]


def text_msg(body, mid="wamid.1", phone=PHONE):
    return {"from": phone, "id": mid, "type": "text", "text": {"body": body}}


def tap(button_id, title=""):
    return {"from": PHONE, "id": "tap", "type": "interactive",
            "interactive": {"type": "button_reply", "button_reply": {"id": button_id, "title": title}}}


def say(provider, *texts, now=None):
    """Send messages one after another, the session kept in the database between them. Returns the last reply."""
    out = None
    for t in texts:
        out = whatsapp.respond(t if isinstance(t, dict) else text_msg(t), provider, now=now)
    return out


def check_limits(message):
    assert len(body_of(message)) <= reply.MAX_BODY
    if message["type"] == "interactive":
        buttons = message["interactive"]["action"]["buttons"]
        assert len(buttons) <= 3 and all(len(b["reply"]["title"]) <= 20 for b in buttons)


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


# ---------------------------------------------------------------- free-text replies (as before)

def test_query_reply_uses_only_the_advice_numbers():
    out = say(FakeProvider(), "گندم بہاولپور 100 من")
    body = body_of(out)
    assert out["type"] == "interactive"
    for expected in ("رکیں", "Rs 3,820", "Rs 4,050", "Rs 3,700", "Rs 4,300", "+Rs 17,747", "Rs 5,253",
                     "2026-10-09", reply.SYNTHETIC, reply.DISCLAIMER):
        assert expected in body
    check_limits(out)


def test_answer_offers_numbered_next_steps_and_matching_buttons():
    out = say(FakeProvider(), "گندم بہاولپور 100 من")
    assert body_of(out).endswith("1 کیوں؟ · 2 منڈیاں · 3 الرٹ چالو · 0 مینو")
    assert button_ids(out) == ["why", "compare", "start"]
    provider = FakeProvider()
    provider.alerts[PHONE] = True
    out = say(provider, "گندم بہاولپور 100 من")
    assert "3 الرٹ بند" in body_of(out) and button_ids(out) == ["why", "compare", "stop"]


def test_missing_quantity_assumes_100_and_says_so():
    assert "100 من مان کر" in body_of(say(FakeProvider(), "gandum bahawalpur"))


def test_why_and_compare_follow_the_last_query():
    provider = FakeProvider()
    say(provider, "گندم بہاولپور 100 من")
    assert "پچھلے 4 ہفتوں میں ریٹ بڑھا" in body_of(say(provider, tap("why", "کیوں؟")))
    compare = body_of(say(provider, "2"))
    assert compare.index("وہاڑی") < compare.index("بہاولپور") and "+Rs 80" in compare
    assert "پچھلے 4 ہفتوں" in body_of(say(provider, "کیوں"))


def test_why_without_a_query_asks_for_the_crop_instead_of_failing():
    body = body_of(say(FakeProvider(), "کیوں"))
    assert reply.ASK_NUMBERED["ask_crop"] in body and "1  گندم" in body


def test_no_price_data_is_said_plainly_and_other_mandis_are_offered():
    provider = FakeProvider(missing={("IRRI", "RahimYarKhan")})
    body = body_of(say(provider, "chawal irri ryk 40"))
    assert "رحیم یار خان" in body and "موجود نہیں" in body and "1  بہاولپور" in body
    out = say(provider, MANDI["Vehari"])
    assert "Rs 3,820" in body_of(out) and provider.calls[-1] == ("advice", "IRRI", "Vehari", 40)


def test_if_services_are_missing_the_reply_is_honest(monkeypatch):
    import backend.app

    monkeypatch.setitem(__import__("sys").modules, "backend.app.services", None)   # import now fails
    monkeypatch.delattr(backend.app, "services", raising=False)                    # even if loaded earlier
    provider = advice_provider.ServicesProvider()
    assert body_of(say(provider, "gandum bahawalpur 100")) == reply.NOT_READY


def test_end_to_end_with_the_real_service_layer():
    from backend.app import services

    price, as_of = services.latest_price("Wheat", "BahawalPur")
    body = body_of(say(advice_provider.ServicesProvider(), "گندم بہاولپور 100 من"))
    assert reply.rs(price) in body and as_of in body
    assert "موجود نہیں" in body_of(say(advice_provider.ServicesProvider(), "chawal irri ryk"))


def test_voice_is_deferred():
    voice = {"from": PHONE, "id": "v", "type": "audio", "audio": {"id": "media"}}
    assert body_of(whatsapp.respond(voice, FakeProvider())) == reply.VOICE_SOON


# ---------------------------------------------------------------- numbered menu

def test_zero_opens_the_menu_with_every_number():
    body = body_of(say(FakeProvider(), "0"))
    assert body.startswith(reply.MENU_HEAD)
    for n, label in (("1", "ریٹ اور مشورہ"), ("2", "منڈیوں کا موازنہ"), ("3", "مشورے کی وجہ"),
                     ("4", "الرٹ چالو"), ("5", "الرٹ بند"), ("0", "مینو")):
        assert f"{n}  {label}" in body


def test_complete_wheat_flow_by_numbers():
    provider = FakeProvider()
    assert reply.ASK_NUMBERED["ask_crop"] in body_of(say(provider, "0", "1"))
    assert reply.ASK_NUMBERED["ask_mandi"] in body_of(say(provider, CROP["Wheat"]))
    assert reply.ASK_QUANTITY in body_of(say(provider, MANDI["BahawalPur"]))
    out = say(provider, "100")
    assert "Rs 3,820" in body_of(out) and provider.calls == [("advice", "Wheat", "BahawalPur", 100.0)]
    check_limits(out)
    assert "+Rs 80" in body_of(say(provider, "2"))   # after the answer, 2 compares the same query


def test_rice_asks_the_variety():
    provider = FakeProvider()
    body = body_of(say(provider, "0", "1", CROP[conv.RICE]))
    assert reply.ASK_NUMBERED["ask_variety"] in body and "سپر باسمتی" in body and "اری" in body
    say(provider, VARIETY["SuperBasmati"], MANDI["Vehari"], "30")
    assert provider.calls == [("advice", "SuperBasmati", "Vehari", 30.0)]


def test_invalid_option_repeats_the_choices():
    provider = FakeProvider()
    body = body_of(say(provider, "0", "1", "7"))
    assert body.startswith(reply.INVALID) and reply.ASK_NUMBERED["ask_crop"] in body and "0  مینو" in body
    assert provider.calls == []
    assert reply.ASK_NUMBERED["ask_mandi"] in body_of(say(provider, CROP["Wheat"]))   # the step was kept


def test_bare_number_without_a_session_shows_the_menu_and_changes_nothing():
    provider = FakeProvider()
    provider.alerts[PHONE] = True
    body = body_of(say(provider, "4"))
    assert body.startswith(reply.MENU_NOTE["no_session"]) and provider.alerts[PHONE] is True


def test_legacy_3_without_a_session_still_stops_alerts():
    provider = FakeProvider()
    provider.alerts[PHONE] = True
    assert body_of(say(provider, "3")).startswith(reply.STOPPED) and provider.alerts[PHONE] is False


def test_3_inside_the_main_menu_means_why_not_stop():
    provider = FakeProvider()
    provider.alerts[PHONE] = True
    body = body_of(say(provider, "0", "3"))
    assert reply.ASK_NUMBERED["ask_crop"] in body and provider.alerts[PHONE] is True


def test_expired_session_returns_to_the_menu():
    provider = FakeProvider()
    t0 = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)
    say(provider, "0", "1", CROP["Wheat"], now=t0)
    late = t0 + timedelta(minutes=conv.SESSION_MINUTES + 1)
    body = body_of(say(provider, MANDI["Vehari"], now=late))
    assert body.startswith(reply.MENU_NOTE["expired"]) and provider.calls == []


def test_session_survives_a_restart(tmp_path):
    path = str(tmp_path / "wa.sqlite")
    provider = FakeProvider()
    db.reset(path)
    say(provider, "0", "1", CROP["Cotton"])
    db.reset(path)   # the server restarts
    say(provider, MANDI["Vehari"], "60")
    assert provider.calls == [("advice", "Cotton", "Vehari", 60.0)]


def test_free_text_query_works_in_the_middle_of_a_menu():
    provider = FakeProvider()
    say(provider, "0", "2", CROP["Cotton"])
    out = say(provider, "gandum vehari 50 mann")
    assert "Rs 3,820" in body_of(out) and provider.calls == [("advice", "Wheat", "Vehari", 50.0)]


# ---------------------------------------------------------------- alerts

def test_alerts_on_and_off_from_the_menu_and_after_an_answer():
    provider = FakeProvider()
    assert body_of(say(provider, "0", "4")).startswith(reply.STARTED) and provider.alerts[PHONE] is True
    assert body_of(say(provider, "0", "5")).startswith(reply.STOPPED) and provider.alerts[PHONE] is False
    say(provider, "gandum bwp 10")
    out = say(provider, "3")
    assert provider.alerts[PHONE] is True and "3 الرٹ بند" in body_of(out)
    say(provider, tap("stop"))
    assert provider.alerts[PHONE] is False


def test_stop_word_turns_alerts_off():
    provider = FakeProvider()
    provider.alerts[PHONE] = True
    assert body_of(say(provider, "بند")).startswith(reply.STOPPED) and provider.alerts[PHONE] is False


def test_unregistered_number_is_told_nothing_changed():
    provider = FakeProvider(registered=())
    body = body_of(say(provider, "0", "4"))
    assert body.startswith(reply.NOT_REGISTERED) and reply.STARTED not in body
    say(provider, "gandum bwp 10")
    assert "3 الرٹ چالو" in body_of(say(provider, "3"))   # the label did not flip


def test_real_services_report_unregistered_numbers():
    from backend.app import services

    assert services.alerts_status("923339999999") is None
    assert services.set_alerts("923339999999", True) is False
    assert services.alerts_status(db.DEMO_FARMER["phone"]) in (True, False)


# ---------------------------------------------------------------- message limits

def test_long_answers_keep_their_numbered_choices():
    class Wordy(FakeProvider):
        def explain(self, crop_option, mandi, phone):
            return [{"text_ur": "وجہ " * 400, "direction": "UP"}] * 3
    out = say(Wordy(), "gandum bwp 10", "1")
    check_limits(out)
    assert body_of(out).endswith("0 مینو")


# ---------------------------------------------------------------- webhook

@pytest.fixture
def app_and_sender():
    sender, provider, app = FakeSender(), FakeProvider(), FastAPI()
    app.include_router(whatsapp.router)
    app.dependency_overrides[whatsapp.get_wa_settings] = lambda: SETTINGS
    app.dependency_overrides[whatsapp.get_provider] = lambda: provider
    app.dependency_overrides[whatsapp.get_sender] = lambda: sender
    return TestClient(app), sender


def signed(payload):
    raw = json.dumps(payload).encode()
    signature = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return raw, {"X-Hub-Signature-256": "sha256=" + signature, "Content-Type": "application/json"}


def meta_payload(*messages):
    return {"object": "whatsapp_business_account",
            "entry": [{"changes": [{"value": {"messaging_product": "whatsapp", "messages": list(messages)}}]}]}


def post(client, *messages):
    raw, headers = signed(meta_payload(*messages))
    return client.post("/webhooks/whatsapp", content=raw, headers=headers)


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


def test_menu_flow_through_the_webhook(app_and_sender):
    client, sender = app_and_sender
    for i, text in enumerate(["0", "1", CROP["Wheat"], MANDI["Vehari"], "100", "1", "0", "4"]):
        assert post(client, text_msg(text, mid=f"wamid.{i}")).json()["queued"] == 1
    bodies = [body_of(m) for _, m in sender.sent]
    assert bodies[0].startswith(reply.MENU_HEAD)
    assert reply.ASK_NUMBERED["ask_crop"] in bodies[1] and reply.ASK_NUMBERED["ask_mandi"] in bodies[2]
    assert reply.ASK_QUANTITY in bodies[3] and "Rs 3,820" in bodies[4]
    assert "پچھلے 4 ہفتوں" in bodies[5] and bodies[7].startswith(reply.STARTED)


def test_button_reply_through_the_webhook(app_and_sender):
    client, sender = app_and_sender
    post(client, text_msg("gandum bwp 20", mid="a"))
    post(client, {**tap("compare", "منڈیاں"), "id": "b"})
    assert "+Rs 80" in body_of(sender.sent[-1][1])


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


def test_phone_numbers_and_text_are_not_logged(app_and_sender, caplog):
    client, _ = app_and_sender
    caplog.set_level("DEBUG")
    post(client, text_msg("gandum vehari 77 mann", mid="log1"))
    assert PHONE not in caplog.text and "vehari" not in caplog.text.lower()
