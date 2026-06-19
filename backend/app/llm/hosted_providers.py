from __future__ import annotations

from dataclasses import dataclass

import requests

from app.llm.base import LLMRequest


@dataclass
class OpenAICompatibleProvider:
    name: str
    api_key: str
    model: str
    api_url: str
    timeout_seconds: int

    def generate(self, request: LLMRequest) -> str:
        if not self.api_key:
            raise RuntimeError(f"{self.name} API key is not configured.")
        response = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a concise hospital operations assistant. Never diagnose, prescribe, "
                            "change doctor instructions, or invent facts. Use only supplied context."
                        ),
                    },
                    {"role": "user", "content": request.prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 220,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        choices = response.json().get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        return str(message.get("content", "")).strip()

    def is_available(self) -> bool:
        return bool(self.api_key)


@dataclass
class AnthropicProvider:
    name: str
    api_key: str
    model: str
    timeout_seconds: int

    def generate(self, request: LLMRequest) -> str:
        if not self.api_key:
            raise RuntimeError("Anthropic API key is not configured.")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 220,
                "temperature": 0.2,
                "system": (
                    "You are a concise hospital operations assistant. Never diagnose, prescribe, "
                    "change doctor instructions, or invent facts. Use only supplied context."
                ),
                "messages": [{"role": "user", "content": request.prompt}],
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        content = response.json().get("content", [])
        if not content:
            return ""
        return "".join(str(block.get("text", "")) for block in content if isinstance(block, dict)).strip()

    def is_available(self) -> bool:
        return bool(self.api_key)
