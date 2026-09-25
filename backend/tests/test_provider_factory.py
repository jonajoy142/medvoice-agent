"""Tests for streaming provider factory."""

import pytest
from unittest.mock import patch, MagicMock

from app.stt.streaming_factory import get_streaming_stt_provider
from app.llm.streaming_factory import get_streaming_llm_provider
from app.tts.streaming_factory import get_streaming_tts_provider


class TestStreamingSTTFactory:
    """Tests for streaming STT provider factory."""
    
    @patch('app.stt.streaming_factory.OpenAIStreamingSTTProvider')
    def test_get_openai_stt_provider(self, mock_openai_provider):
        """Test getting OpenAI STT provider."""
        mock_instance = MagicMock()
        mock_openai_provider.return_value = mock_instance
        
        agent_config = {"stt_provider": "openai"}
        provider = get_streaming_stt_provider(agent_config)
        
        assert provider == mock_instance
        mock_openai_provider.assert_called_once()
    
    def test_get_unsupported_stt_provider(self):
        """Test getting unsupported STT provider raises error."""
        agent_config = {"stt_provider": "unsupported"}
        
        with pytest.raises(RuntimeError, match="Unsupported streaming STT provider"):
            get_streaming_stt_provider(agent_config)
    
    def test_get_default_stt_provider(self):
        """Test getting default STT provider when not specified."""
        agent_config = {}
        
        with patch('app.stt.streaming_factory.OpenAIStreamingSTTProvider') as mock_provider:
            mock_instance = MagicMock()
            mock_provider.return_value = mock_instance
            
            provider = get_streaming_stt_provider(agent_config)
            
            assert provider == mock_instance
            mock_provider.assert_called_once()


class TestStreamingLLMFactory:
    """Tests for streaming LLM provider factory."""
    
    @patch('app.llm.streaming_factory.OpenAIStreamingLLMProvider')
    def test_get_openai_llm_provider(self, mock_openai_provider):
        """Test getting OpenAI LLM provider."""
        mock_instance = MagicMock()
        mock_openai_provider.return_value = mock_instance
        
        agent_config = {"llm_provider": "openai"}
        provider = get_streaming_llm_provider(agent_config)
        
        assert provider == mock_instance
        mock_openai_provider.assert_called_once()
    
    def test_get_unsupported_llm_provider(self):
        """Test getting unsupported LLM provider raises error."""
        agent_config = {"llm_provider": "unsupported"}
        
        with pytest.raises(RuntimeError, match="Unsupported streaming LLM provider"):
            get_streaming_llm_provider(agent_config)
    
    def test_get_default_llm_provider(self):
        """Test getting default LLM provider when not specified."""
        agent_config = {}
        
        with patch('app.llm.streaming_factory.OpenAIStreamingLLMProvider') as mock_provider:
            mock_instance = MagicMock()
            mock_provider.return_value = mock_instance
            
            provider = get_streaming_llm_provider(agent_config)
            
            assert provider == mock_instance
            mock_provider.assert_called_once()


class TestStreamingTTSFactory:
    """Tests for streaming TTS provider factory."""
    
    @patch('app.tts.streaming_factory.OpenAIStreamingTTSProvider')
    def test_get_openai_tts_provider(self, mock_openai_provider):
        """Test getting OpenAI TTS provider."""
        mock_instance = MagicMock()
        mock_openai_provider.return_value = mock_instance
        
        agent_config = {"tts_provider": "openai"}
        provider = get_streaming_tts_provider(agent_config)
        
        assert provider == mock_instance
        mock_openai_provider.assert_called_once()
    
    def test_get_unsupported_tts_provider(self):
        """Test getting unsupported TTS provider raises error."""
        agent_config = {"tts_provider": "unsupported"}
        
        with pytest.raises(RuntimeError, match="Unsupported streaming TTS provider"):
            get_streaming_tts_provider(agent_config)
    
    def test_get_default_tts_provider(self):
        """Test getting default TTS provider when not specified."""
        agent_config = {}
        
        with patch('app.tts.streaming_factory.OpenAIStreamingTTSProvider') as mock_provider:
            mock_instance = MagicMock()
            mock_provider.return_value = mock_instance
            
            provider = get_streaming_tts_provider(agent_config)
            
            assert provider == mock_instance
            mock_provider.assert_called_once()
