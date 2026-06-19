from __future__ import annotations

from dataclasses import dataclass
import time

from app.core.config import settings
from app.tts.base import TTSProvider, TTSRequest, TTSResult
from app.tts.sarvam import SarvamTTSProvider


@dataclass
class LocalTTSProvider(TTSProvider):
    name: str = "local"

    def synthesize(self, request: TTSRequest) -> TTSResult:
        if not settings.enable_local_tts:
            raise RuntimeError("Local TTS is disabled. Configure Sarvam or enable local TTS explicitly.")
        from app.core.voice_pipeline import speak

        started = time.perf_counter()
        speak(request.text, request.voice)
        return TTSResult(None, None, self.name, round((time.perf_counter() - started) * 1000, 2))


def get_tts_provider(preferred: str | None = None) -> TTSProvider:
    provider = (preferred or settings.voice_provider or "sarvam").lower()
    if provider == "sarvam":
        return SarvamTTSProvider()
    if provider == "local":
        return LocalTTSProvider()
    raise RuntimeError(f"Unsupported TTS provider: {provider}")
