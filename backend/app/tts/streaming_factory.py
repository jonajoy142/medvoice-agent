"""Streaming TTS provider factory for voice runtime."""

from __future__ import annotations

from typing import Dict, Any, Optional
from app.tts.base import StreamingTTSProvider
from app.tts.openai_streaming import OpenAIStreamingTTSProvider


def get_streaming_tts_provider(agent_config: Dict[str, Any]) -> StreamingTTSProvider:
    """
    Get streaming TTS provider based on agent configuration.
    
    Args:
        agent_config: Agent configuration dictionary with provider settings
        
    Returns:
        StreamingTTSProvider instance
        
    Raises:
        RuntimeError: If provider is not supported or credentials are missing
    """
    provider_name = agent_config.get("tts_provider", "openai").lower()
    
    if provider_name == "openai":
        return OpenAIStreamingTTSProvider()
    
    # Future providers can be added here:
    # elif provider_name == "sarvam":
    #     return SarvamStreamingTTSProvider(agent_config)
    
    raise RuntimeError(f"Unsupported streaming TTS provider: {provider_name}")


def get_streaming_tts_provider_with_fallback(
    agent_config: Dict[str, Any],
    fallback_provider: Optional[StreamingTTSProvider] = None
) -> StreamingTTSProvider:
    """
    Get streaming TTS provider with fallback on error.
    
    Args:
        agent_config: Agent configuration dictionary
        fallback_provider: Optional fallback provider if primary fails
        
    Returns:
        StreamingTTSProvider instance
    """
    try:
        return get_streaming_tts_provider(agent_config)
    except RuntimeError as e:
        if fallback_provider:
            return fallback_provider
        raise
