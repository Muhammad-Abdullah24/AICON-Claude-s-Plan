"""WhatsApp voice notes (task A10): ready to plug in, off by default, and not a dependency of the demo.

No speech-to-text provider has been chosen, so nothing here transcribes anything yet. What exists:

    MediaFetcher   gets a voice note's audio from WhatsApp, given its media id
    Transcriber    turns Urdu audio into text, with a confidence score if the provider gives one
    pipeline()     the configured pair, or None: then the farmer is told to type or use the numbered menu

Voice is used only when FS_VOICE_NOTES=1 AND both a fetcher and a transcriber are registered (FETCHER,
TRANSCRIBER below; both None). With either missing it stays off, whatever the flag says.

What a fetcher must do (WhatsApp Cloud API): ask the Graph API for the media URL with the app's access token, then
download it with the same token over HTTPS; refuse anything over FS_VOICE_MAX_BYTES or not audio/*; never log the
URL, the token, the phone number or the transcript. Audio is held in memory for one call and never written to disk
or the database (blueprint NFR-09: voice files deleted after transcription).

What happens with a transcript (conversation.heard): FarmSight replies "I heard: Gandum, Bahawalpur, 100 maund.
1 right, 2 correct it" and gives advice only after the farmer replies 1. A score below FS_VOICE_MIN_CONFIDENCE, or a
transcript naming no crop and no mandi, goes to the numbered menu. The transcript itself is not stored.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Protocol

log = logging.getLogger("farmsight.voice")


@dataclass(frozen=True)
class Transcript:
    text: str
    confidence: float | None = None   # 0..1; None when the provider gives no score
    language: str | None = None


class MediaFetcher(Protocol):
    def fetch(self, media_id: str, max_bytes: int) -> tuple[bytes, str]: ...   # (audio, mime type)


class Transcriber(Protocol):
    def transcribe(self, audio: bytes, mime: str) -> Transcript: ...


class VoiceFailed(Exception):
    """The note could not be fetched or transcribed (too big, wrong type, provider error)."""


@dataclass(frozen=True)
class VoiceSettings:
    enabled: bool = False
    min_confidence: float = 0.8
    max_bytes: int = 2_000_000


def get_voice_settings() -> VoiceSettings:
    return VoiceSettings(
        enabled=os.environ.get("FS_VOICE_NOTES", "").strip().lower() in ("1", "true", "yes", "on"),
        min_confidence=float(os.environ.get("FS_VOICE_MIN_CONFIDENCE", "0.8")),
        max_bytes=int(os.environ.get("FS_VOICE_MAX_BYTES", "2000000")),
    )


# Registered once a provider is chosen and written. None on purpose: voice notes are not built.
FETCHER: MediaFetcher | None = None
TRANSCRIBER: Transcriber | None = None


def pipeline(settings: VoiceSettings | None = None) -> tuple[MediaFetcher, Transcriber] | None:
    settings = settings or get_voice_settings()
    if not settings.enabled:
        return None
    if FETCHER is None or TRANSCRIBER is None:
        log.warning("Voice notes off: FS_VOICE_NOTES is set but no media fetcher or transcriber is registered")
        return None
    return FETCHER, TRANSCRIBER


def media_id(msg: dict) -> str | None:
    """The media id of a WhatsApp audio or voice message."""
    part = msg.get("audio") or msg.get("voice") or {}
    return part.get("id") or None


def transcribe_note(media: str, fetcher: MediaFetcher, transcriber: Transcriber, settings: VoiceSettings) -> Transcript:
    """Fetch and transcribe one note. The audio is dropped as soon as this returns."""
    try:
        audio, mime = fetcher.fetch(media, settings.max_bytes)
    except VoiceFailed:
        raise
    except Exception as e:  # noqa: BLE001 (any provider error means: ask the farmer to type)
        raise VoiceFailed(type(e).__name__) from e
    if len(audio) > settings.max_bytes or not mime.startswith("audio/"):
        raise VoiceFailed("not an acceptable audio file")
    try:
        return transcriber.transcribe(audio, mime)
    except Exception as e:  # noqa: BLE001
        raise VoiceFailed(type(e).__name__) from e
    finally:
        del audio
