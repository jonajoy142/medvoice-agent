from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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


class TTSProvider(Protocol):
    name: str

    def synthesize(self, request: TTSRequest) -> TTSResult:
        ...
