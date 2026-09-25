from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, AsyncIterator


@dataclass(frozen=True)
class LLMRequest:
    user_text: str
    prompt: str
    context: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    fallback_used: bool = False


@dataclass(frozen=True)
class StreamingLLMRequest:
    user_text: str
    system_prompt: str
    conversation_history: list[Dict[str, str]]
    context: Optional[Dict[str, Any]] = None
    cancellation_token: Optional[Any] = None  # asyncio.Event for cancellation


@dataclass(frozen=True)
class TokenChunk:
    text: str
    is_final: bool
    chunk_index: int


class LLMProvider(Protocol):
    name: str

    def generate(self, request: LLMRequest) -> str:
        ...

    def is_available(self) -> bool:
        ...


class StreamingLLMProvider(Protocol):
    name: str

    async def generate_stream(
        self, request: StreamingLLMRequest
    ) -> AsyncIterator[TokenChunk]:
        ...

    def is_available(self) -> bool:
        ...
