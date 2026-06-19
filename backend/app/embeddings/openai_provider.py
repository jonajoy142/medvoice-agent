from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.embeddings.base import EmbeddingProvider


@dataclass
class OpenAIEmbeddingProvider(EmbeddingProvider):
    name: str = "openai"

    def embed(self, text: str) -> list[float]:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for embeddings.")
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        result = client.embeddings.create(model=settings.openai_embedding_model, input=text)
        return list(result.data[0].embedding)
