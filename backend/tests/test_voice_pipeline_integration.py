"""Integration tests for voice runtime pipeline."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.voice.runtime.pipeline import VoiceRuntimePipeline, PipelineState
from app.stt.openai_streaming import OpenAIStreamingSTTProvider
from app.tts.openai_streaming import OpenAIStreamingTTSProvider
from app.llm.openai_streaming import OpenAIStreamingLLMProvider


@pytest.fixture
def mock_providers():
    """Create mock providers for testing."""
    with patch("app.stt.openai_streaming.settings"), \
         patch("app.tts.openai_streaming.settings"), \
         patch("app.llm.openai_streaming.settings"):
        stt = OpenAIStreamingSTTProvider()
        tts = OpenAIStreamingTTSProvider()
        llm = OpenAIStreamingLLMProvider()
        return stt, tts, llm


@pytest.fixture
def voice_pipeline(mock_providers):
    """Create voice pipeline instance."""
    stt, tts, llm = mock_providers
    return VoiceRuntimePipeline(
        stt_provider=stt,
        llm_provider=llm,
        tts_provider=tts,
        language="en-IN",
        voice="alloy",
        system_prompt="You are helpful",
    )


@pytest.mark.asyncio
async def test_pipeline_initialization(voice_pipeline):
    """Test pipeline initialization."""
    assert voice_pipeline.state == PipelineState.IDLE
    assert voice_pipeline.language == "en-IN"
    assert voice_pipeline.voice == "alloy"
    assert len(voice_pipeline.conversation_history) == 0


@pytest.mark.asyncio
async def test_pipeline_cancellation(voice_pipeline):
    """Test pipeline cancellation."""
    voice_pipeline.cancel_current_turn()
    assert voice_pipeline.cancellation_token.is_set()


@pytest.mark.asyncio
async def test_pipeline_reset(voice_pipeline):
    """Test pipeline reset."""
    voice_pipeline.conversation_history.append({"role": "user", "content": "test"})
    voice_pipeline.state = PipelineState.SPEAKING
    
    voice_pipeline.reset()
    
    assert voice_pipeline.state == PipelineState.IDLE
    assert len(voice_pipeline.conversation_history) == 0


@pytest.mark.asyncio
async def test_pipeline_metrics(voice_pipeline):
    """Test pipeline metrics tracking."""
    metrics = voice_pipeline.get_metrics()
    
    assert "stt_latency_ms" in metrics
    assert "llm_latency_ms" in metrics
    assert "tts_latency_ms" in metrics
    assert "total_turn_latency_ms" in metrics
    assert "state" in metrics


@pytest.mark.asyncio
async def test_pipeline_state_transitions(voice_pipeline):
    """Test pipeline state transitions."""
    assert voice_pipeline.state == PipelineState.IDLE
    
    # State would transition during actual processing
    # This is a basic state check
    voice_pipeline.state = PipelineState.LISTENING
    assert voice_pipeline.state == PipelineState.LISTENING


@pytest.mark.asyncio
async def test_conversation_history_management(voice_pipeline):
    """Test conversation history management."""
    # Add messages
    voice_pipeline.conversation_history.append({"role": "user", "content": "Hello"})
    voice_pipeline.conversation_history.append({"role": "assistant", "content": "Hi"})
    
    assert len(voice_pipeline.conversation_history) == 2
    
    # Add more than limit
    for i in range(15):
        voice_pipeline.conversation_history.append({"role": "user", "content": f"Message {i}"})
        voice_pipeline.conversation_history.append({"role": "assistant", "content": f"Response {i}"})
    
    # Should be trimmed to last 10 messages
    assert len(voice_pipeline.conversation_history) <= 10
