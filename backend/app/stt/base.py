from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class STTRequest:
    audio_path: str
    language: str
    sample_rate_hz: int | None = None


@dataclass(frozen=True)
class STTResult:
    text: str
    language: str
    confidence: float | None
    provider: str
    latency_ms: float


class STTProvider(Protocol):
    name: str

    def transcribe(self, request: STTRequest) -> STTResult:
        ...
