from __future__ import annotations

from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.deterministic_provider import DeterministicLLMProvider
from app.llm.hosted_providers import OpenAICompatibleProvider
from app.llm.ollama_provider import OllamaLLMProvider


def get_llm_provider(provider_name: str | None = None) -> LLMProvider:
    name = (provider_name or settings.llm_provider or "deterministic").strip().lower()
    if name == "ollama":
        return OllamaLLMProvider()
    if name == "openai":
        if not settings.openai_api_key:
            return DeterministicLLMProvider()
        return OpenAICompatibleProvider(
            name="openai",
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            api_url="https://api.openai.com/v1/chat/completions",
            timeout_seconds=settings.llm_timeout_seconds,
        )
    if name == "groq":
        if not settings.groq_api_key:
            return DeterministicLLMProvider()
        return OpenAICompatibleProvider(
            name="groq",
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            api_url="https://api.groq.com/openai/v1/chat/completions",
            timeout_seconds=settings.llm_timeout_seconds,
        )
    if name == "openrouter":
        if not settings.openrouter_api_key:
            return DeterministicLLMProvider()
        return OpenAICompatibleProvider(
            name="openrouter",
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            api_url="https://openrouter.ai/api/v1/chat/completions",
            timeout_seconds=settings.llm_timeout_seconds,
        )
    return DeterministicLLMProvider()
