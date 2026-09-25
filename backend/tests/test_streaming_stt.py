"""Unit tests for streaming STT providers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.stt.openai_streaming import OpenAIStreamingSTTProvider
from app.stt.base import StreamingSTTRequest, PartialTranscript


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch("app.stt.openai_streaming.AsyncOpenAI") as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client


@pytest.fixture
def stt_provider():
    """Create STT provider instance."""
    with patch("app.stt.openai_streaming.settings"):
        return OpenAIStreamingSTTProvider()


@pytest.mark.asyncio
async def test_stt_provider_init():
    """Test STT provider initialization."""
    with patch("app.stt.openai_streaming.settings"):
        provider = OpenAIStreamingSTTProvider()
        assert provider.name == "openai_whisper_streaming"


@pytest.mark.asyncio
async def test_stt_transcribe_stream(stt_provider, mock_openai_client):
    """Test streaming transcription."""
    # Mock audio response
    mock_response = MagicMock()
    mock_response.text = "Hello world"
    mock_openai_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
    
    request = StreamingSTTRequest(
        audio_bytes=b"fake audio data",
        language="en",
    )
    
    results = []
    async for partial in stt_provider.transcribe_stream(request):
        results.append(partial)
    
    assert len(results) == 1
    assert results[0].text == "Hello world"
    assert results[0].is_final is True
    assert results[0].language == "en"


@pytest.mark.asyncio
async def test_stt_transcribe_stream_error(stt_provider, mock_openai_client):
    """Test STT error handling."""
    mock_openai_client.audio.transcriptions.create = AsyncMock(
        side_effect=Exception("API error")
    )
    
    request = StreamingSTTRequest(
        audio_bytes=b"fake audio data",
        language="en",
    )
    
    results = []
    with pytest.raises(Exception):
        async for partial in stt_provider.transcribe_stream(request):
            results.append(partial)
