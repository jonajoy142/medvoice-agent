from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol

from app.core.config import settings
from app.stt.base import STTRequest
from app.stt.factory import get_stt_provider
from app.tts.base import TTSRequest
from app.tts.factory import get_tts_provider


class VoiceProvider(Protocol):
    name: str

    def transcribe(self, audio_path: str, language: str) -> str:
        ...

    def synthesize(self, text: str, voice: str, language: str, speed: float) -> Any:
        ...


@dataclass
class SplitVoiceProvider:
    """Compatibility adapter around the production STT/TTS interfaces."""

    name: str
    stt_provider_name: str
    tts_provider_name: str

    def transcribe(self, audio_path: str, language: str) -> str:
        result = get_stt_provider(self.stt_provider_name).transcribe(STTRequest(audio_path=audio_path, language=language))
        return result.text

    def synthesize(self, text: str, voice: str, language: str, speed: float) -> Any:
        return get_tts_provider(self.tts_provider_name).synthesize(TTSRequest(text=text, voice=voice, language=language, speed=speed))


@dataclass
class OpenAIVoiceProvider:
    name: str = "openai"

    def transcribe(self, audio_path: str, language: str) -> str:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI STT.")
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=settings.openai_stt_model,
                file=audio_file,
                language=_openai_language(language),
            )
        return str(getattr(transcript, "text", "") or "").strip()

    def synthesize(self, text: str, voice: str, language: str, speed: float) -> Any:
        if not settings.enable_local_tts:
            return None
        from app.core.voice_pipeline import speak

        _ = language, speed
        return speak(text, voice)


def get_voice_provider(preferred: Optional[str] = None) -> VoiceProvider:
    provider_name = (preferred or settings.voice_provider or "sarvam").lower()
    if provider_name == "openai" and settings.openai_api_key:
        return OpenAIVoiceProvider()
    if provider_name in {"sarvam", "local"}:
        return SplitVoiceProvider(provider_name, provider_name, provider_name)
    if provider_name == "openai":
        raise RuntimeError("OPENAI_API_KEY is required for OpenAI voice provider.")
    raise RuntimeError(f"Unsupported voice provider: {provider_name}")


def _openai_language(language: str) -> str:
    normalized = (language or "").split("-")[0].strip().lower()
    return normalized or "en"
