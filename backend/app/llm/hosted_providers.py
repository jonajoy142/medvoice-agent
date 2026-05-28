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
                    {"role": "system", "content": "You are a concise hospital receptionist. Never invent medical facts."},
                    {"role": "user", "content": request.prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 80,
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
