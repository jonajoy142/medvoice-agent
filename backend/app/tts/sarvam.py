from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any

import requests

from app.core.config import settings
from app.tts.base import TTSProvider, TTSRequest, TTSResult


@dataclass
class SarvamTTSProvider(TTSProvider):
    """Sarvam TTS adapter.

    Assumption: endpoint accepts JSON with text, language_code, speaker/voice,
    pace, and optional model; response contains audio_base64 or audio_url.
    """

    name: str = "sarvam"

    def synthesize(self, request: TTSRequest) -> TTSResult:
        if not settings.sarvam_api_key or not settings.sarvam_tts_endpoint:
            raise RuntimeError("SARVAM_API_KEY and SARVAM_TTS_ENDPOINT are required for Sarvam TTS.")
        started = time.perf_counter()
        payload = {
            "model": settings.sarvam_tts_model or None,
            "text": request.text,
            "language_code": request.language,
            "speaker": request.voice,
            "voice": request.voice,
            "pace": request.speed,
        }
        data = _post_json(settings.sarvam_tts_endpoint, payload)
        audio_base64 = data.get("audio_base64") or data.get("audio")
        audio_content = base64.b64decode(audio_base64) if isinstance(audio_base64, str) else None
        return TTSResult(
            audio_content=audio_content,
            audio_url=data.get("audio_url") if isinstance(data.get("audio_url"), str) else None,
            provider=self.name,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    last_exception: Exception | None = None
    for _ in range(max(1, settings.provider_retry_count + 1)):
        try:
            response = requests.post(
                url,
                headers={"api-subscription-key": settings.sarvam_api_key, "Content-Type": "application/json"},
                json={key: value for key, value in payload.items() if value is not None},
                timeout=settings.sarvam_timeout_seconds,
            )
            if response.status_code in {401, 403}:
                response = requests.post(
                    url,
                    headers={"Authorization": f"Bearer {settings.sarvam_api_key}", "Content-Type": "application/json"},
                    json={key: value for key, value in payload.items() if value is not None},
                    timeout=settings.sarvam_timeout_seconds,
                )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise RuntimeError("Unexpected Sarvam TTS response format.")
            return data
        except Exception as exc:
            last_exception = exc
    raise RuntimeError(f"Sarvam TTS request failed: {last_exception}")
