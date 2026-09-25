"""Streaming STT provider factory for voice runtime."""

from __future__ import annotations

from typing import Dict, Any, Optional
from app.stt.base import StreamingSTTProvider
from app.stt.openai_streaming import OpenAIStreamingSTTProvider


def get_streaming_stt_provider(agent_config: Dict[str, Any]) -> StreamingSTTProvider:
    """
    Get streaming STT provider based on agent configuration.
    
    Args:
        agent_config: Agent configuration dictionary with provider settings
        
    Returns:
        StreamingSTTProvider instance
        
    Raises:
        RuntimeError: If provider is not supported or credentials are missing
    """
    provider_name = agent_config.get("stt_provider", "openai").lower()
    
    if provider_name == "openai":
        return OpenAIStreamingSTTProvider()
    
    # Future providers can be added here:
    # elif provider_name == "sarvam":
    #     return SarvamStreamingSTTProvider(agent_config)
    
    raise RuntimeError(f"Unsupported streaming STT provider: {provider_name}")


def get_streaming_stt_provider_with_fallback(
    agent_config: Dict[str, Any],
    fallback_provider: Optional[StreamingSTTProvider] = None
) -> StreamingSTTProvider:
    """
    Get streaming STT provider with fallback on error.
    
    Args:
        agent_config: Agent configuration dictionary
        fallback_provider: Optional fallback provider if primary fails
        
    Returns:
        StreamingSTTProvider instance
    """
    try:
        return get_streaming_stt_provider(agent_config)
    except RuntimeError as e:
        if fallback_provider:
            return fallback_provider
        raise
