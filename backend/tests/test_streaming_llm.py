"""Unit tests for streaming LLM providers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.llm.openai_streaming import OpenAIStreamingLLMProvider
from app.llm.base import StreamingLLMRequest, TokenChunk


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch("app.llm.openai_streaming.AsyncOpenAI") as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client


@pytest.fixture
def llm_provider():
    """Create LLM provider instance."""
    with patch("app.llm.openai_streaming.settings"):
        return OpenAIStreamingLLMProvider()


@pytest.mark.asyncio
async def test_llm_provider_init():
    """Test LLM provider initialization."""
    with patch("app.llm.openai_streaming.settings"):
        provider = OpenAIStreamingLLMProvider()
        assert provider.name == "openai_streaming"


@pytest.mark.asyncio
async def test_llm_generate_stream(llm_provider, mock_openai_client):
    """Test streaming LLM generation."""
    # Mock streaming response
    mock_chunk1 = MagicMock()
    mock_chunk1.choices = [MagicMock()]
    mock_chunk1.choices[0].delta.content = "Hello"
    
    mock_chunk2 = MagicMock()
    mock_chunk2.choices = [MagicMock()]
    mock_chunk2.choices[0].delta.content = " world"
    
    mock_chunk3 = MagicMock()
    mock_chunk3.choices = [MagicMock()]
    mock_chunk3.choices[0].delta.content = ""
    
    async def mock_stream():
        yield mock_chunk1
        yield mock_chunk2
        yield mock_chunk3
    
    mock_response = AsyncMock()
    mock_response.__aiter__ = lambda self: mock_stream()
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    request = StreamingLLMRequest(
        user_text="Hi there",
        system_prompt="You are helpful",
        conversation_history=[],
    )
    
    results = []
    async for chunk in llm_provider.generate_stream(request):
        results.append(chunk)
    
    assert len(results) > 0
    assert results[-1].is_final is True
    combined_text = "".join(c.text for c in results)
    assert "Hello world" in combined_text


@pytest.mark.asyncio
async def test_llm_is_available(llm_provider):
    """Test provider availability check."""
    with patch("app.llm.openai_streaming.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"
        assert llm_provider.is_available() is True
        
        mock_settings.openai_api_key = None
        assert llm_provider.is_available() is False


@pytest.mark.asyncio
async def test_llm_generate_stream_error(llm_provider, mock_openai_client):
    """Test LLM error handling."""
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=Exception("API error")
    )
    
    request = StreamingLLMRequest(
        user_text="Hi there",
        system_prompt="You are helpful",
        conversation_history=[],
    )
    
    results = []
    with pytest.raises(Exception):
        async for chunk in llm_provider.generate_stream(request):
            results.append(chunk)
