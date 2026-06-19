from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any

import requests

from app.core.config import settings
from app.stt.base import STTProvider, STTRequest, STTResult


@dataclass
class SarvamSTTProvider(STTProvider):
    """Sarvam ASR adapter.

    Assumption: endpoint accepts JSON with model, language_code, and audio_base64
    and returns either {"text": ...} or {"transcript": ...}. This is isolated so
    the payload can be corrected once credentials/API docs are verified.
    """

    name: str = "sarvam"

    def transcribe(self, request: STTRequest) -> STTResult:
        if not settings.sarvam_api_key or not settings.sarvam_stt_endpoint:
            raise RuntimeError("SARVAM_API_KEY and SARVAM_STT_ENDPOINT are required for Sarvam STT.")
        started = time.perf_counter()
        payload = {
            "model": settings.sarvam_stt_model or None,
            "language_code": request.language,
            "audio_base64": _read_audio_base64(request.audio_path),
        }
        data = _post_json(settings.sarvam_stt_endpoint, payload)
        text = str(data.get("text") or data.get("transcript") or "").strip()
        confidence = data.get("confidence")
        return STTResult(
            text=text,
            language=str(data.get("language_code") or request.language),
            confidence=float(confidence) if isinstance(confidence, (int, float)) else None,
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
                raise RuntimeError("Unexpected Sarvam STT response format.")
            return data
        except Exception as exc:
            last_exception = exc
    raise RuntimeError(f"Sarvam STT request failed: {last_exception}")


def _read_audio_base64(audio_path: str) -> str:
    with open(audio_path, "rb") as handle:
        return base64.b64encode(handle.read()).decode("utf-8")
