from __future__ import annotations

from dataclasses import dataclass
import base64
from typing import Optional, Protocol

import requests
from app.core.config import settings


class VoiceProvider(Protocol):
    name: str

    def transcribe(self, audio_path: str, language: str) -> str:
        ...

    def synthesize(self, text: str, voice: str, language: str, speed: float) -> None:
        ...


@dataclass
class LocalVoiceProvider:
    name: str = "local"

    def transcribe(self, audio_path: str, language: str) -> str:
        from app.core.voice_pipeline import transcribe_audio
        return transcribe_audio(audio_path)

    def synthesize(self, text: str, voice: str, language: str, speed: float) -> None:
        from app.core.voice_pipeline import speak
        _ = language, speed  # Kept for provider interface compatibility
        speak(text, voice)


@dataclass
class SarvamVoiceProvider:
    name: str = "sarvam"

    def transcribe(self, audio_path: str, language: str) -> str:
        if not settings.sarvam_api_key or not settings.sarvam_stt_url:
            raise RuntimeError("Sarvam STT config missing.")
        headers = {"Authorization": f"Bearer {settings.sarvam_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": settings.sarvam_stt_model,
            "language": language,
            # TODO(SARVAM): Confirm final STT payload contract and transport format.
            "audio_base64": _read_audio_base64(audio_path),
        }
        return _post_with_retry(settings.sarvam_stt_url, headers, payload).get("text", "").strip()

    def synthesize(self, text: str, voice: str, language: str, speed: float) -> None:
        if not settings.sarvam_api_key or not settings.sarvam_tts_url:
            raise RuntimeError("Sarvam TTS config missing.")
        headers = {"Authorization": f"Bearer {settings.sarvam_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": settings.sarvam_tts_model,
            "text": text,
            "language": language,
            "voice": voice,
            "speed": speed,
            # TODO(SARVAM): Confirm final response format and playback integration.
        }
        _post_with_retry(settings.sarvam_tts_url, headers, payload)


def get_voice_provider(preferred: Optional[str] = None) -> VoiceProvider:
    provider_name = (preferred or settings.voice_provider or "local").lower()
    if provider_name == "sarvam" and settings.sarvam_api_key:
        return SarvamVoiceProvider()
    return LocalVoiceProvider()


def _post_with_retry(url: str, headers: dict, payload: dict) -> dict:
    last_exception: Optional[Exception] = None
    attempts = max(1, settings.provider_retry_count + 1)
    for _ in range(attempts):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=settings.sarvam_timeout_seconds)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise RuntimeError("Unexpected provider response format.")
            return data
        except Exception as exc:
            last_exception = exc
    raise RuntimeError(f"Sarvam provider request failed: {last_exception}")


def _read_audio_base64(audio_path: str) -> str:
    with open(audio_path, "rb") as handle:
        return base64.b64encode(handle.read()).decode("utf-8")
