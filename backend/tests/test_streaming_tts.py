"""Unit tests for streaming TTS providers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.tts.openai_streaming import OpenAIStreamingTTSProvider
from app.tts.base import StreamingTTSRequest, AudioChunk


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch("app.tts.openai_streaming.AsyncOpenAI") as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client


@pytest.fixture
def tts_provider():
    """Create TTS provider instance."""
    with patch("app.tts.openai_streaming.settings"):
        return OpenAIStreamingTTSProvider()


@pytest.mark.asyncio
async def test_tts_provider_init():
    """Test TTS provider initialization."""
    with patch("app.tts.openai_streaming.settings"):
        provider = OpenAIStreamingTTSProvider()
        assert provider.name == "openai_tts_streaming"


@pytest.mark.asyncio
async def test_tts_synthesize_stream(tts_provider, mock_openai_client):
    """Test streaming TTS synthesis."""
    # Mock audio response
    mock_response = MagicMock()
    mock_response.content = b"fake audio data"
    mock_openai_client.audio.speech.create = AsyncMock(return_value=mock_response)
    
    request = StreamingTTSRequest(
        text="Hello world",
        language="en",
        voice="alloy",
    )
    
    results = []
    async for chunk in tts_provider.synthesize_stream(request):
        results.append(chunk)
    
    assert len(results) > 0
    assert results[-1].is_final is True
    assert all(isinstance(chunk.audio_bytes, bytes) for chunk in results)


@pytest.mark.asyncio
async def test_tts_voice_mapping(tts_provider):
    """Test voice name mapping."""
    assert tts_provider._map_voice("female") == "alloy"
    assert tts_provider._map_voice("male") == "echo"
    assert tts_provider._map_voice("unknown") == "alloy"


@pytest.mark.asyncio
async def test_tts_synthesize_stream_error(tts_provider, mock_openai_client):
    """Test TTS error handling."""
    mock_openai_client.audio.speech.create = AsyncMock(
        side_effect=Exception("API error")
    )
    
    request = StreamingTTSRequest(
        text="Hello world",
        language="en",
        voice="alloy",
    )
    
    results = []
    with pytest.raises(Exception):
        async for chunk in tts_provider.synthesize_stream(request):
            results.append(chunk)
