import io
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.channels import reply, whatsapp
from backend.app.channels.provider import NotReady, ServicesProvider, get_provider
from backend.app.chat import guard, llm, prompt, router, service
from backend.app.chat.llm import LLMUnavailable, RateLimiter

ROOT = Path(__file__).resolve().parents[3]
ADVICE = {"crop_option": "Wheat", "mandi": "BahawalPur", "signal": "WAIT", "current_price": 3820,
          "predicted_price": 4050, "range": {"low": 3700, "high": 4300}, "rupee_impact": 17747,
          "interest_cost": 5253, "quantity_maund": 100, "confidence": "MEDIUM", "prices_as_of": "2026-10-09",
          "is_synthetic": False, "data_source": "amis"}


class FakeProvider:
    def __init__(self, advice=ADVICE, error=None):
        self.a, self.error = advice, error

    def advice(self, crop_option, mandi, quantity_maund, phone):
        if self.error:
            raise self.error
        return dict(self.a, crop_option=crop_option, mandi=mandi, quantity_maund=quantity_maund)

    def explain(self, crop_option, mandi, phone):
        return [{"text_ur": "کٹائی کے بعد رسد کم ہو رہی ہے", "direction": "UP"}]

    def compare(self, *a):
        return []

    def set_alerts(self, *a):
        pass


class FakeLLM:
    def __init__(self, text="", error=None):
        self.text, self.error, self.calls = text, error, []

    def generate(self, system, user):
        self.calls.append((system, user))
        if self.error:
            raise self.error
        return self.text


def ask(question, llm_, provider=None, limiter=None, **kw):
    return service.answer(question, kw.get("crop"), kw.get("mandi"), kw.get("qty"), provider or FakeProvider(),
                          llm_, limiter or RateLimiter(100))


# ---------------------------------------------------------------- the number guard

def test_numbers_are_canonical_across_scripts_and_formats():
    assert guard.numbers("Rs 3,820 اور ۴۰۵۰، 6.0% on 2026-10-09") == {"3820", "4050", "6", "2026", "10", "9"}


def test_unexpected_numbers():
    assert guard.unexpected_numbers("Rs 4,050 in 4 weeks", "Rs 4,050 in 4 weeks") == set()
    assert guard.unexpected_numbers("Rs 5,000", "Rs 4,050") == {"5000"}


# ---------------------------------------------------------------- answers

def test_grounded_answer_is_kept():
    text = "Gandum ka rate 4 hafte baad takreeban Rs 4,050 ho sakta hai (Rs 3,700 se Rs 4,300). Ye andaza hai."
    a = ask("gandum bahawalpur agle mahine kitna?", FakeLLM(text))
    assert (a.used_fallback, a.answer, a.crop_option, a.mandi) == (False, text, "Wheat", "BahawalPur")


def test_invented_number_falls_back_to_the_template():
    a = ask("gandum bahawalpur kitna?", FakeLLM("Rate Rs 5,000 tak jayega"))
    assert a.used_fallback and a.fallback_reason == "unverified_numbers"
    assert a.answer == reply.advice_text(dict(ADVICE, quantity_maund=100))


def test_llm_down_or_over_quota_falls_back():
    down = ask("gandum bahawalpur?", FakeLLM(error=LLMUnavailable("timeout")))
    assert down.used_fallback and down.fallback_reason == "llm_unavailable"
    limiter = RateLimiter(1)
    ask("gandum bahawalpur?", FakeLLM("ok"), limiter=limiter)
    limited = ask("gandum bahawalpur?", FakeLLM("ok"), limiter=limiter)
    assert limited.fallback_reason == "rate_limited"


def test_needs_crop_and_mandi_before_calling_the_llm():
    model = FakeLLM("x")
    assert ask("rate kya hai?", model).answer == reply.ASK["crop"]
    assert ask("chawal ka rate?", model).answer == reply.ASK["variety"]
    assert ask("gandum ka rate?", model).answer == reply.ASK["mandi"]
    assert model.calls == []


def test_no_data_and_service_not_ready():
    assert ask("irri ryk", FakeLLM("x"), FakeProvider(error=LookupError())).fallback_reason == "no_data"
    assert ask("gandum vehari", FakeLLM("x"), FakeProvider(error=NotReady("x"))).answer == reply.NOT_READY
    assert ask("gandum vehari", FakeLLM("x"), ServicesProvider()).fallback_reason == "service_not_ready"


def test_synthetic_data_is_always_labelled():
    a = ask("gandum bahawalpur?", FakeLLM("Rs 4,050 ka andaza hai."), FakeProvider(dict(ADVICE, is_synthetic=True)))
    assert not a.used_fallback and a.answer.endswith(reply.SYNTHETIC) and a.is_synthetic


def test_the_llm_sees_the_context_and_never_the_phone():
    model = FakeLLM("Rs 4,050")
    service.answer("gandum bahawalpur?", None, None, None, FakeProvider(), model, RateLimiter(5),
                   phone="923001234567")
    system, user = model.calls[0]
    assert system == prompt.SYSTEM_PROMPT
    assert "Rs 3,820" in user and "2026-10-09" in user and "923001234567" not in user


def test_prompts_md_holds_the_prompt_word_for_word():
    doc = (ROOT / "docs" / "PROMPTS.md").read_text(encoding="utf-8")
    assert prompt.SYSTEM_PROMPT in doc and prompt.USER_TEMPLATE in doc


# ---------------------------------------------------------------- Gemini client

def test_gemini_without_a_key_is_unavailable():
    with pytest.raises(LLMUnavailable):
        llm.GeminiClient(llm.LLMSettings(api_key="")).generate("s", "u")


def test_gemini_request_and_response(monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout):
        seen["url"], seen["body"] = req.full_url, json.loads(req.data)
        seen["key"] = req.get_header("X-goog-api-key")
        payload = {"candidates": [{"content": {"parts": [{"text": "Rs 4,050"}]}}]}
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    out = llm.GeminiClient(llm.LLMSettings(api_key="k", model="gemini-test")).generate("SYS", "USER")
    assert out == "Rs 4,050"
    assert seen["url"].endswith("/models/gemini-test:generateContent") and seen["key"] == "k"
    assert seen["body"]["system_instruction"]["parts"][0]["text"] == "SYS"


def test_gemini_blocked_answer_is_unavailable(monkeypatch):
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda req, timeout: io.BytesIO(b'{"candidates": []}'))
    with pytest.raises(LLMUnavailable):
        llm.GeminiClient(llm.LLMSettings(api_key="k")).generate("s", "u")


def test_rate_limiter_window():
    t = [0.0]
    limiter = RateLimiter(2, clock=lambda: t[0])
    assert limiter.allow("a") and limiter.allow("a") and not limiter.allow("a")
    t[0] = 61
    assert limiter.allow("a")


# ---------------------------------------------------------------- route

@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router.router)
    app.dependency_overrides[get_provider] = FakeProvider
    app.dependency_overrides[llm.get_llm] = lambda: FakeLLM("Rs 4,050 ka andaza hai.")
    limiter = RateLimiter(2)
    app.dependency_overrides[router.get_client_limiter] = lambda: limiter
    return TestClient(app)


def test_chat_route(client):
    r = client.post("/api/chat", json={"question": "kitna rate hoga?", "crop_option": "Wheat", "mandi": "Vehari"})
    assert r.status_code == 200
    body = r.json()
    assert body["used_fallback"] is False and body["mandi"] == "Vehari" and body["data_source"] == "amis"


def test_chat_route_validates_and_rate_limits(client):
    assert client.post("/api/chat", json={"question": ""}).status_code == 422
    assert client.post("/api/chat", json={"question": "x", "mandi": "Lahore"}).status_code == 422
    q = {"question": "gandum vehari?"}
    assert [client.post("/api/chat", json=q).status_code for _ in range(3)] == [200, 200, 429]


# ---------------------------------------------------------------- WhatsApp hand-off

def test_whatsapp_free_question_after_a_query_goes_to_chat():
    memory, provider = whatsapp.Memory(), FakeProvider()
    msg = {"from": "92300", "id": "1", "type": "text", "text": {"body": "gandum bahawalpur 100"}}
    whatsapp.respond(msg, provider, memory)
    asked = {"from": "92300", "id": "2", "type": "text", "text": {"body": "kal ka mausam kaisa hoga"}}
    out = whatsapp.respond(asked, provider, memory, chat=lambda text, q, phone: f"chat:{q.crop_option}:{q.mandi}")
    assert out["interactive"]["body"]["text"] == "chat:Wheat:BahawalPur"
