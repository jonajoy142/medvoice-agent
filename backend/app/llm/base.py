from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol


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


class LLMProvider(Protocol):
    name: str

    def generate(self, request: LLMRequest) -> str:
        ...

    def is_available(self) -> bool:
        ...
