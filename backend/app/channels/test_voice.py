"""Voice notes (task A10): off by default, never acted on without the farmer's confirmation. No provider exists,
so these tests use stand-ins; any network call fails the test."""

import urllib.request
from datetime import UTC, datetime, timedelta

import pytest

from backend.app import db
from backend.app.channels import conversation as conv
from backend.app.channels import reply, voice, whatsapp
from backend.app.channels.test_whatsapp import PHONE, FakeProvider, body_of, text_msg

NOW = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)
AUDIO = b"\x00fake-ogg-bytes"


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    db.reset()

    def no_network(*a, **k):
        raise AssertionError("a test tried to reach the network")
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    monkeypatch.delenv("FS_VOICE_NOTES", raising=False)
    yield
    db.reset()


class StubFetcher:
    def __init__(self, audio=AUDIO, mime="audio/ogg", error=None):
        self.audio, self.mime, self.error, self.asked = audio, mime, error, []

    def fetch(self, media_id, max_bytes):
        self.asked.append(media_id)
        if self.error:
            raise self.error
        return self.audio, self.mime


class StubTranscriber:
    def __init__(self, text, confidence=0.95):
        self.result, self.got = voice.Transcript(text, confidence, "ur"), []

    def transcribe(self, audio, mime):
        self.got.append((audio, mime))
        return self.result


def note(media="media-1", mid="v1"):
    return {"from": PHONE, "id": mid, "type": "audio", "audio": {"id": media, "mime_type": "audio/ogg"}}


@pytest.fixture
def voice_on(monkeypatch):
    def install(text, confidence=0.95, fetcher=None):
        monkeypatch.setenv("FS_VOICE_NOTES", "1")
        monkeypatch.setattr(voice, "FETCHER", fetcher or StubFetcher())
        monkeypatch.setattr(voice, "TRANSCRIBER", StubTranscriber(text, confidence))
        return voice.TRANSCRIBER
    return install


# ---------------------------------------------------------------- off by default

def test_off_by_default_says_so_and_points_to_text_or_the_menu():
    assert voice.pipeline() is None and voice.FETCHER is None and voice.TRANSCRIBER is None
    body = body_of(whatsapp.respond(note(), FakeProvider()))
    assert body == reply.VOICE_SOON and "0" in body


def test_the_flag_alone_does_not_turn_it_on(monkeypatch, caplog):
    monkeypatch.setenv("FS_VOICE_NOTES", "1")
    assert voice.pipeline() is None
    assert "no media fetcher or transcriber" in caplog.text
    assert body_of(whatsapp.respond(note(), FakeProvider())) == reply.VOICE_SOON


# ---------------------------------------------------------------- confirm before acting

def test_a_clear_note_is_confirmed_before_any_advice(voice_on):
    voice_on("گندم بہاولپور 100 من")
    provider = FakeProvider()
    body = body_of(whatsapp.respond(note(), provider, now=NOW))
    assert body.startswith("میں نے سنا: گندم، بہاولپور، 100 من")
    assert "1  درست ہے" in body and "2  درست کریں" in body and "0  مینو" in body
    assert provider.calls == []                                   # nothing answered from the transcript yet
    out = whatsapp.respond(text_msg("1", mid="c"), provider, now=NOW)
    assert "Rs 3,820" in body_of(out) and provider.calls == [("advice", "Wheat", "BahawalPur", 100.0)]


def test_2_starts_the_guided_flow_and_keeps_nothing_heard(voice_on):
    voice_on("گندم بہاولپور 100 من")
    provider = FakeProvider()
    whatsapp.respond(note(), provider, now=NOW)
    body = body_of(whatsapp.respond(text_msg("2", mid="c"), provider, now=NOW))
    assert reply.ASK_NUMBERED["ask_crop"] in body and provider.calls == []
    s = conv.load("whatsapp", PHONE)
    assert (s.draft_crop, s.draft_mandi, s.draft_quantity) == (None, None, None)


def test_a_partial_note_asks_for_the_rest_after_confirming(voice_on):
    voice_on("kapas")
    provider = FakeProvider()
    body = body_of(whatsapp.respond(note(), provider, now=NOW))
    assert "کپاس" in body and "؟" in body
    assert reply.ASK_NUMBERED["ask_mandi"] in body_of(whatsapp.respond(text_msg("1", mid="c"), provider, now=NOW))


def test_rice_without_a_variety_is_asked_not_guessed(voice_on):
    voice_on("chawal vehari 40 man")
    provider = FakeProvider()
    whatsapp.respond(note(), provider, now=NOW)
    body = body_of(whatsapp.respond(text_msg("1", mid="c"), provider, now=NOW))
    assert reply.ASK_NUMBERED["ask_variety"] in body and provider.calls == []


def test_an_invalid_reply_repeats_the_confirmation(voice_on):
    voice_on("gandum vehari 10")
    provider = FakeProvider()
    whatsapp.respond(note(), provider, now=NOW)
    body = body_of(whatsapp.respond(text_msg("5", mid="c"), provider, now=NOW))
    assert body.startswith(reply.INVALID) and "میں نے سنا" in body and provider.calls == []


def test_unscored_transcripts_still_need_confirmation(voice_on):
    voice_on("gandum vehari 10", confidence=None)
    provider = FakeProvider()
    assert "میں نے سنا" in body_of(whatsapp.respond(note(), provider, now=NOW)) and provider.calls == []


def test_confirmation_expires_like_any_session(voice_on):
    voice_on("gandum vehari 10")
    provider = FakeProvider()
    whatsapp.respond(note(), provider, now=NOW)
    late = NOW + timedelta(minutes=conv.SESSION_MINUTES + 1)
    body = body_of(whatsapp.respond(text_msg("1", mid="c"), provider, now=late))
    assert body.startswith(reply.MENU_NOTE["expired"]) and provider.calls == []


# ---------------------------------------------------------------- unclear or failed notes

@pytest.mark.parametrize("text, confidence", [("gandum vehari 10", 0.5), ("کل بارش ہو گی؟", 0.99), ("", 0.99)])
def test_low_confidence_or_unusable_goes_to_the_menu(voice_on, text, confidence):
    voice_on(text, confidence)
    provider = FakeProvider()
    body = body_of(whatsapp.respond(note(), provider, now=NOW))
    assert body.startswith(reply.MENU_NOTE["voice_unclear"]) and "1  خریدار کی آفر چیک کریں" in body
    assert provider.calls == [] and conv.load("whatsapp", PHONE).draft_crop is None


@pytest.mark.parametrize("fetcher", [StubFetcher(error=OSError("down")), StubFetcher(audio=b"x" * 3_000_000),
                                     StubFetcher(mime="image/png")])
def test_fetch_problems_ask_the_farmer_to_type(voice_on, fetcher, caplog):
    voice_on("gandum vehari 10", fetcher=fetcher)
    assert body_of(whatsapp.respond(note(), FakeProvider(), now=NOW)) == reply.VOICE_FAILED
    assert PHONE not in caplog.text


def test_a_note_without_a_media_id(voice_on):
    voice_on("gandum vehari 10")
    msg = {"from": PHONE, "id": "v", "type": "audio", "audio": {}}
    assert body_of(whatsapp.respond(msg, FakeProvider(), now=NOW)) == reply.VOICE_FAILED


# ---------------------------------------------------------------- nothing kept

def test_neither_audio_nor_transcript_is_stored_or_logged(voice_on, caplog):
    caplog.set_level("DEBUG")
    stt = voice_on("gandum vehari 10 secret-words")
    whatsapp.respond(note(), FakeProvider(), now=NOW)
    assert stt.got == [(AUDIO, "audio/ogg")]   # the transcriber did receive the audio
    conn = db.connect()
    for table in [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]:
        for row in conn.execute(f"SELECT * FROM {table}"):  # noqa: S608 (names from sqlite_master)
            assert not any(isinstance(v, (str, bytes)) and ("secret-words" in str(v) or v == AUDIO)
                           for v in tuple(row))
    assert "secret-words" not in caplog.text and PHONE not in caplog.text
