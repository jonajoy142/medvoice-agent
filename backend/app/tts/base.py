from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, AsyncIterator, Optional, Any


@dataclass(frozen=True)
class TTSRequest:
    text: str
    language: str
    voice: str
    speed: float = 1.0


@dataclass(frozen=True)
class TTSResult:
    audio_content: bytes | None
    audio_url: str | None
    provider: str
    latency_ms: float


@dataclass(frozen=True)
class StreamingTTSRequest:
    text: str
    language: str
    voice: str
    speed: float = 1.0
    cancellation_token: Optional[Any] = None  # asyncio.Event for cancellation


@dataclass(frozen=True)
class AudioChunk:
    audio_bytes: bytes
    is_final: bool
    chunk_index: int


class TTSProvider(Protocol):
    name: str

    def synthesize(self, request: TTSRequest) -> TTSResult:
        ...


class StreamingTTSProvider(Protocol):
    name: str

    async def synthesize_stream(
        self, request: StreamingTTSRequest
    ) -> AsyncIterator[AudioChunk]:
        ...
