from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, AsyncIterator, Any


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


@dataclass(frozen=True)
class StreamingSTTRequest:
    audio_bytes: bytes
    language: str
    sample_rate_hz: int | None = None


@dataclass(frozen=True)
class PartialTranscript:
    text: str
    is_final: bool
    confidence: float | None
    language: str


class STTProvider(Protocol):
    name: str

    def transcribe(self, request: STTRequest) -> STTResult:
        ...


class StreamingSTTProvider(Protocol):
    name: str

    async def transcribe_stream(
        self, request: StreamingSTTRequest
    ) -> AsyncIterator[PartialTranscript]:
        ...
