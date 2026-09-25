"""Streaming LLM provider factory for voice runtime."""

from __future__ import annotations

from typing import Dict, Any, Optional
from app.llm.base import StreamingLLMProvider
from app.llm.openai_streaming import OpenAIStreamingLLMProvider


def get_streaming_llm_provider(agent_config: Dict[str, Any]) -> StreamingLLMProvider:
    """
    Get streaming LLM provider based on agent configuration.
    
    Args:
        agent_config: Agent configuration dictionary with provider settings
        
    Returns:
        StreamingLLMProvider instance
        
    Raises:
        RuntimeError: If provider is not supported or credentials are missing
    """
    provider_name = agent_config.get("llm_provider", "openai").lower()
    
    if provider_name == "openai":
        return OpenAIStreamingLLMProvider()
    
    # Future providers can be added here:
    # elif provider_name == "anthropic":
    #     return AnthropicStreamingLLMProvider(agent_config)
    # elif provider_name == "groq":
    #     return GroqStreamingLLMProvider(agent_config)
    
    raise RuntimeError(f"Unsupported streaming LLM provider: {provider_name}")


def get_streaming_llm_provider_with_fallback(
    agent_config: Dict[str, Any],
    fallback_provider: Optional[StreamingLLMProvider] = None
) -> StreamingLLMProvider:
    """
    Get streaming LLM provider with fallback on error.
    
    Args:
        agent_config: Agent configuration dictionary
        fallback_provider: Optional fallback provider if primary fails
        
    Returns:
        StreamingLLMProvider instance
    """
    try:
        return get_streaming_llm_provider(agent_config)
    except RuntimeError as e:
        if fallback_provider:
            return fallback_provider
        raise
