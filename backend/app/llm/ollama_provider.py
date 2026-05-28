from __future__ import annotations

import requests

from app.core.config import settings
from app.llm.base import LLMRequest


class OllamaLLMProvider:
    name = "ollama"

    def __init__(
        self,
        base_url: str = settings.ollama_base_url,
        model: str = settings.ollama_model,
        timeout_seconds: int = settings.llm_timeout_seconds,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate(self, request: LLMRequest) -> str:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": request.prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "max_tokens": 60,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1,
                },
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=min(self.timeout_seconds, 5))
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
