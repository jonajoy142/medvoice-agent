from __future__ import annotations

from dataclasses import dataclass
import time

from app.core.config import settings
from app.stt.base import STTProvider, STTRequest, STTResult
from app.stt.sarvam import SarvamSTTProvider


@dataclass
class LocalSTTProvider(STTProvider):
    name: str = "local"

    def transcribe(self, request: STTRequest) -> STTResult:
        if not settings.enable_local_stt:
            raise RuntimeError("Local STT is disabled. Configure Sarvam or enable local STT explicitly.")
        from app.core.voice_pipeline import transcribe_audio

        started = time.perf_counter()
        return STTResult(
            text=transcribe_audio(request.audio_path),
            language=request.language,
            confidence=None,
            provider=self.name,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )


def get_stt_provider(preferred: str | None = None) -> STTProvider:
    provider = (preferred or settings.voice_provider or "sarvam").lower()
    if provider == "sarvam":
        return SarvamSTTProvider()
    if provider == "local":
        return LocalSTTProvider()
    raise RuntimeError(f"Unsupported STT provider: {provider}")
