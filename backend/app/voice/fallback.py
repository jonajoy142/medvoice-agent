"""Safe fallback responses for provider failures."""

from __future__ import annotations

from typing import Dict, Any


class FallbackResponses:
    """Safe fallback responses for provider failures."""
    
    STT_FAILURE = "Sorry, I didn't catch that. Could you please repeat?"
    LLM_FAILURE = "I'm having trouble connecting right now. Let me try to help you in a moment."
    TTS_FAILURE = None  # No audio fallback, just silence
    
    @staticmethod
    def get_stt_fallback(language: str = "en-IN") -> str:
        """Get fallback text for STT failure."""
        return FallbackResponses.STT_FAILURE
    
    @staticmethod
    def get_llm_fallback(language: str = "en-IN") -> str:
        """Get fallback text for LLM failure."""
        return FallbackResponses.LLM_FAILURE
    
    @staticmethod
    def get_tts_fallback(language: str = "en-IN") -> bytes | None:
        """Get fallback audio for TTS failure."""
        return FallbackResponses.TTS_FAILURE
    
    @staticmethod
    def get_error_message(error_type: str, language: str = "en-IN") -> str:
        """
        Get appropriate error message based on error type.
        
        Args:
            error_type: Type of error (stt, llm, tts, general)
            language: Language code
            
        Returns:
            Error message
        """
        messages = {
            "stt": FallbackResponses.STT_FAILURE,
            "llm": FallbackResponses.LLM_FAILURE,
            "tts": "I apologize, but I'm experiencing technical difficulties.",
            "general": "I'm sorry, something went wrong. Please try again.",
        }
        return messages.get(error_type, messages["general"])


fallback_responses = FallbackResponses()
