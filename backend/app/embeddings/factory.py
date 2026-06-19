from __future__ import annotations

from app.embeddings.base import EmbeddingProvider
from app.embeddings.openai_provider import OpenAIEmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    return OpenAIEmbeddingProvider()
