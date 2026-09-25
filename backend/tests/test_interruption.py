"""Tests for interruption handling and VAD scenarios."""

import pytest
import asyncio
from app.voice.vad.detector import VoiceActivityDetector, VADConfig, SpeechState
from app.voice.state.manager import AIStateManager, AIState, AIStateManagerConfig
from app.voice.metrics.interruption import InterruptionMetricsCollector, InterruptionType
from app.voice.events.system import RealtimeEventBus, VoiceEventEmitter, EventType, EventSeverity


@pytest.fixture
def vad():
    """Create VAD instance."""
    return VoiceActivityDetector(VADConfig())


@pytest.fixture
def ai_state():
    """Create AI state manager."""
    return AIStateManager(AIStateManagerConfig())


def test_vad_initialization(vad):
    """Test VAD initialization."""
    assert vad.state == SpeechState.SILENCE
    assert vad.speech_start_time is None
    assert vad.last_speech_time is None


def test_vad_speech_detection(vad):
    """Test speech detection from audio chunks."""
    # Simulate speech with high energy
    vad.config.speech_threshold = 0.1  # Lower threshold for testing
    vad.config.energy_window_size = 1  # Single sample window for testing
    speech_audio = b"\xff\xff" * 100  # High energy PCM16
    vad.process_audio_chunk(speech_audio)
    
    assert vad.is_speaking() is True
    assert vad.speech_start_time is not None


def test_vad_silence_detection(vad):
    """Test silence detection after speech ends."""
    # Add speech
    speech_audio = b"\xff\xff" * 100
    vad.process_audio_chunk(speech_audio)
    
    # Add silence (low energy)
    silence_audio = b"\x00\x00" * 100
    for _ in range(20):  # Multiple chunks to exceed silence threshold
        vad.process_audio_chunk(silence_audio)
    
    assert vad.is_silence() is True


def test_vad_reset(vad):
    """Test VAD reset."""
    speech_audio = b"\xff\xff" * 100
    vad.process_audio_chunk(speech_audio)
    
    vad.reset()
    
    assert vad.state == SpeechState.SILENCE
    assert vad.speech_start_time is None
    assert vad.last_speech_time is None


def test_vad_metrics(vad):
    """Test VAD metrics tracking."""
    speech_audio = b"\xff\xff" * 100
    vad.process_audio_chunk(speech_audio)
    
    metrics = vad.get_metrics()
    
    assert "state" in metrics
    assert "speech_duration_ms" in metrics
    assert "silence_duration_ms" in metrics
    assert "speech_segments" in metrics


def test_ai_state_initialization(ai_state):
    """Test AI state manager initialization."""
    assert ai_state.current_state == AIState.LISTENING
    assert ai_state.interruption_count == 0


def test_ai_state_transitions(ai_state):
    """Test AI state transitions."""
    ai_state.start_thinking()
    assert ai_state.current_state == AIState.THINKING
    
    ai_state.start_speaking()
    assert ai_state.current_state == AIState.SPEAKING
    
    ai_state.start_listening()
    assert ai_state.current_state == AIState.LISTENING


def test_ai_state_speaking_check(ai_state):
    """Test AI speaking state check."""
    assert ai_state.is_speaking() is False
    
    ai_state.start_speaking()
    assert ai_state.is_speaking() is True


def test_ai_state_listening_check(ai_state):
    """Test AI listening state check."""
    assert ai_state.is_listening() is True
    
    ai_state.start_speaking()
    assert ai_state.is_listening() is False


def test_interruption_when_speaking(ai_state):
    """Test interruption when AI is speaking."""
    ai_state.start_speaking()
    
    result = ai_state.interrupt(reason="test")
    
    assert result is True
    assert ai_state.current_state == AIState.INTERRUPTED
    assert ai_state.interruption_count == 1


def test_interruption_when_not_speaking(ai_state):
    """Test interruption when AI is not speaking."""
    ai_state.start_listening()
    
    result = ai_state.interrupt(reason="test")
    
    assert result is False
    assert ai_state.current_state == AIState.LISTENING
    assert ai_state.interruption_count == 0


def test_interruption_cooldown(ai_state):
    """Test interruption cooldown."""
    ai_state.start_speaking()
    ai_state.interrupt(reason="test1")
    
    # Immediate second interruption should fail due to cooldown
    result = ai_state.interrupt(reason="test2")
    
    assert result is False


def test_max_interruptions_limit(ai_state):
    """Test maximum interruptions per call."""
    ai_state.config.max_interruptions_per_call = 2
    ai_state.start_speaking()
    
    # First interruption
    ai_state.interrupt(reason="test1")
    ai_state.start_speaking()
    
    # Second interruption
    ai_state.interrupt(reason="test2")
    ai_state.start_speaking()
    
    # Third interruption should fail
    result = ai_state.interrupt(reason="test3")
    
    assert result is False


def test_cancellation_token_creation(ai_state):
    """Test cancellation token creation."""
    token = ai_state.create_cancellation_token()
    
    assert token is not None
    assert token.is_set() is False


def test_cancellation_token_on_interruption(ai_state):
    """Test cancellation token is set on interruption."""
    token = ai_state.create_cancellation_token()
    ai_state.start_speaking()
    
    ai_state.interrupt(reason="test")
    
    assert token.is_set() is True


def test_state_history_tracking(ai_state):
    """Test state transition history."""
    ai_state.start_thinking()
    ai_state.start_speaking()
    ai_state.start_listening()
    
    history = ai_state.get_state_history(limit=10)
    
    assert len(history) == 3
    assert history[0]["to_state"] == "thinking"
    assert history[1]["to_state"] == "speaking"
    assert history[2]["to_state"] == "listening"


def test_ai_state_reset(ai_state):
    """Test AI state reset."""
    ai_state.start_speaking()
    ai_state.interrupt(reason="test")
    
    ai_state.reset()
    
    assert ai_state.current_state == AIState.LISTENING
    assert ai_state.interruption_count == 0
    assert ai_state.last_interruption_time is None


def test_ai_state_metrics(ai_state):
    """Test AI state metrics."""
    ai_state.start_speaking()
    ai_state.interrupt(reason="test")
    
    metrics = ai_state.get_metrics()
    
    assert metrics["current_state"] == "interrupted"
    assert metrics["interruption_count"] == 1
    assert "can_interrupt" in metrics


def test_state_context_manager(ai_state):
    """Test state context manager."""
    with ai_state.state_context(AIState.THINKING, "test"):
        assert ai_state.current_state == AIState.THINKING
    
    # Should return to previous state
    assert ai_state.current_state == AIState.LISTENING


def test_multiple_rapid_interruptions(ai_state):
    """Test multiple rapid interruptions with cooldown."""
    ai_state.config.max_interruptions_per_call = 5
    ai_state.config.interruption_cooldown_ms = 100  # 100ms cooldown
    
    ai_state.start_speaking()
    ai_state.interrupt(reason="test1")
    
    # Wait for cooldown (using sync sleep in test context)
    import time
    time.sleep(0.15)
    
    ai_state.start_speaking()
    result = ai_state.interrupt(reason="test2")
    
    assert result is True
    assert ai_state.interruption_count == 2


def test_tool_execution_state(ai_state):
    """Test tool execution state."""
    ai_state.start_tool_execution()
    
    assert ai_state.current_state == AIState.TOOL_EXECUTION


def test_waiting_state(ai_state):
    """Test waiting state."""
    ai_state.start_waiting()
    
    assert ai_state.current_state == AIState.WAITING


def test_vad_config_defaults():
    """Test VAD configuration defaults."""
    config = VADConfig()
    
    assert config.speech_threshold == 0.3
    assert config.silence_threshold_ms == 800
    assert config.min_speech_duration_ms == 200
    assert config.max_silence_duration_ms == 2000


def test_ai_state_config_defaults():
    """Test AI state manager configuration defaults."""
    config = AIStateManagerConfig()
    
    assert config.interruption_cooldown_ms == 500
    assert config.max_interruptions_per_call == 10


def test_state_change_callback(ai_state):
    """Test state change callback."""
    callback_called = []
    
    def on_change(from_state, to_state):
        callback_called.append((from_state, to_state))
    
    ai_state.on_state_change = on_change
    ai_state.start_thinking()
    
    assert len(callback_called) == 1
    assert callback_called[0] == (AIState.LISTENING, AIState.THINKING)


def test_interruption_callback(ai_state):
    """Test interruption callback."""
    callback_called = []
    
    def on_interruption():
        callback_called.append(True)
    
    ai_state.on_interruption = on_interruption
    ai_state.start_speaking()
    ai_state.interrupt(reason="test")
    
    assert len(callback_called) == 1


# Phase 4 Enhanced Tests

def test_vad_barge_in_detection(vad):
    """Test VAD barge-in detection when AI is speaking."""
    vad.set_ai_speaking_state(True)
    vad.config.speech_threshold = 0.1  # Lower threshold for testing
    vad.barge_in_energy_threshold = 0.2  # Lower barge-in threshold for testing
    vad.config.energy_window_size = 1  # Single sample window for testing
    
    # Simulate high energy speech while AI is speaking
    high_energy_audio = b"\xff\xff" * 100
    vad.process_audio_chunk(high_energy_audio)
    
    assert vad.detect_barge_in() is True
    assert vad.get_barge_in_duration_ms() > 0


def test_vad_barge_in_cooldown(vad):
    """Test barge-in detection respects cooldown."""
    vad.set_ai_speaking_state(True)
    vad.config.speech_threshold = 0.1  # Lower threshold for testing
    vad.barge_in_energy_threshold = 0.2  # Lower barge-in threshold for testing
    vad.config.energy_window_size = 1  # Single sample window for testing
    
    # First barge-in
    high_energy_audio = b"\xff\xff" * 100
    vad.process_audio_chunk(high_energy_audio)
    assert vad.detect_barge_in() is True
    
    # Reset and try immediate second barge-in
    vad.barge_in_start_time = None
    vad.process_audio_chunk(high_energy_audio)
    # Should still detect barge-in, but duration might be short


def test_vad_silence_leakage(vad):
    """Test VAD silence leakage allows brief pauses in speech."""
    vad.config.speech_threshold = 0.1  # Lower threshold for testing
    vad.config.energy_window_size = 1  # Single sample window for testing
    speech_audio = b"\xff\xff" * 100
    silence_audio = b"\x00\x00" * 50
    
    # Start speech
    vad.process_audio_chunk(speech_audio)
    assert vad.is_speaking() is True
    
    # Brief silence (within leakage threshold)
    for _ in range(5):  # Less than silence threshold
        vad.process_audio_chunk(silence_audio)
    
    # Should still be in speech state due to leakage
    assert vad.is_speaking() is True


def test_vad_no_speech_timeout(vad):
    """Test VAD no-speech timeout."""
    vad.config.no_speech_timeout_ms = 1000  # 1 second timeout
    
    # Process some speech to set activity time
    speech_audio = b"\xff\xff" * 100
    vad.process_audio_chunk(speech_audio)
    
    # Should not timeout immediately
    assert vad.check_no_speech_timeout() is False


def test_vad_turn_end_decision(vad):
    """Test VAD turn end decision logic."""
    vad.config.speech_threshold = 0.1  # Lower threshold for testing
    vad.config.silence_threshold_ms = 500
    vad.config.energy_window_size = 1  # Single sample window for testing
    
    # Start with speech
    speech_audio = b"\xff\xff" * 100
    vad.process_audio_chunk(speech_audio)
    
    # Add enough silence to trigger turn end
    silence_audio = b"\x00\x00" * 100
    for _ in range(20):  # Exceed silence threshold
        vad.process_audio_chunk(silence_audio)
    
    # Should indicate turn should end
    assert vad.should_end_turn() is True


def test_interruption_metrics_collector():
    """Test interruption metrics collector."""
    collector = InterruptionMetricsCollector()
    collector.start_collection()
    
    # Record some interruptions
    collector.record_interruption(
        event_type=InterruptionType.BARGE_IN,
        duration_ms=150.0,
        reason="user_speech",
        was_successful=True,
        ai_state_before="speaking",
        ai_state_after="interrupted",
        speech_energy=0.6,
        vad_state="speaking",
    )
    
    collector.record_interruption(
        event_type=InterruptionType.MANUAL,
        duration_ms=0.0,
        reason="timeout",
        was_successful=False,
        ai_state_before="speaking",
        ai_state_after="speaking",
        speech_energy=0.0,
        vad_state="silence",
    )
    
    metrics = collector.get_metrics()
    
    assert metrics["total_interruptions"] == 2
    assert metrics["successful_interruptions"] == 1
    assert metrics["failed_interruptions"] == 1
    assert metrics["barge_in_count"] == 1


def test_interruption_metrics_cancellation():
    """Test cancellation metrics."""
    collector = InterruptionMetricsCollector()
    collector.start_collection()
    
    # Record cancellations
    collector.record_cancellation(was_successful=True)
    collector.record_cancellation(was_successful=False)
    
    metrics = collector.get_metrics()
    
    assert metrics["cancellation_count"] == 2
    assert metrics["successful_cancellations"] == 1
    assert metrics["failed_cancellations"] == 1


def test_interruption_metrics_recent_events():
    """Test getting recent interruption events."""
    collector = InterruptionMetricsCollector()
    collector.start_collection()
    
    # Record multiple events
    for i in range(5):
        collector.record_interruption(
            event_type=InterruptionType.BARGE_IN,
            duration_ms=100.0 + i * 10,
            reason=f"test_{i}",
            was_successful=True,
            ai_state_before="speaking",
            ai_state_after="interrupted",
            speech_energy=0.5,
            vad_state="speaking",
        )
    
    recent_events = collector.get_recent_events(limit=3)
    
    assert len(recent_events) == 3
    assert recent_events[0]["reason"] == "test_2"  # Last 3 events


def test_ai_state_with_metrics():
    """Test AI state manager with metrics collection."""
    ai_state = AIStateManager()
    ai_state.start_metrics_collection()
    
    ai_state.start_speaking()
    ai_state.interrupt(reason="test", speech_energy=0.6, vad_state="speaking")
    ai_state.complete_interruption()
    
    metrics = ai_state.get_comprehensive_metrics()
    
    assert metrics["interruption_count"] == 1
    assert "interruption_metrics" in metrics
    assert metrics["interruption_metrics"]["total_interruptions"] == 1


def test_ai_state_force_interruption():
    """Test force interruption bypassing normal checks."""
    ai_state = AIStateManager()
    ai_state.start_listening()  # Not speaking
    
    # Normal interruption should fail
    result = ai_state.interrupt(reason="test")
    assert result is False
    
    # Start speaking
    ai_state.start_speaking()
    
    # Force interruption should work
    result = ai_state.force_interruption(reason="emergency", speech_energy=0.8, vad_state="speaking")
    assert result is True
    assert ai_state.current_state == AIState.INTERRUPTED


def test_ai_state_fallback_mode():
    """Test fallback mode after max interruptions."""
    ai_state = AIStateManager()
    ai_state.config.max_interruptions_per_call = 2
    ai_state.config.fallback_on_max_interruptions = True
    ai_state.config.interruption_cooldown_ms = 0  # Disable cooldown for testing
    
    # Test that fallback mode logic is present
    ai_state.start_speaking()
    result1 = ai_state.interrupt(reason="test1")
    assert result1 is True
    assert ai_state.interruption_count == 1
    
    # Reset to speaking state (interruption sets state to INTERRUPTED)
    ai_state.start_speaking()
    result2 = ai_state.interrupt(reason="test2")
    assert result2 is True
    assert ai_state.interruption_count == 2
    
    # Check if fallback mode is triggered (it checks if count >= max)
    # Since we have exactly 2 interruptions and max is 2, it should trigger
    assert ai_state.fallback_mode is True


def test_realtime_event_bus():
    """Test realtime event bus."""
    bus = RealtimeEventBus()
    
    events_received = []
    
    def event_callback(event):
        events_received.append(event)
    
    subscriber = bus.subscribe(event_callback)
    
    # Publish some events
    from app.voice.events.system import RealtimeEvent
    event1 = RealtimeEvent(event_type=EventType.CALL_STARTED)
    event2 = RealtimeEvent(event_type=EventType.SPEECH_DETECTED)
    
    bus.publish(event1)
    bus.publish(event2)
    
    assert len(events_received) == 2
    assert events_received[0].event_type == EventType.CALL_STARTED
    assert events_received[1].event_type == EventType.SPEECH_DETECTED


def test_realtime_event_bus_filtering():
    """Test event bus filtering by event type."""
    bus = RealtimeEventBus()
    
    speech_events = []
    all_events = []
    
    def speech_callback(event):
        speech_events.append(event)
    
    def all_callback(event):
        all_events.append(event)
    
    # Subscribe to specific events
    bus.subscribe(speech_callback, [EventType.SPEECH_DETECTED, EventType.SPEECH_ENDED])
    bus.subscribe(all_callback)  # Subscribe to all
    
    from app.voice.events.system import RealtimeEvent
    bus.publish(RealtimeEvent(event_type=EventType.CALL_STARTED))
    bus.publish(RealtimeEvent(event_type=EventType.SPEECH_DETECTED))
    bus.publish(RealtimeEvent(event_type=EventType.SPEECH_ENDED))
    
    assert len(all_events) == 3
    assert len(speech_events) == 2


def test_voice_event_emitter():
    """Test voice event emitter."""
    bus = RealtimeEventBus()
    emitter = VoiceEventEmitter(bus, call_id="test_call", session_id="test_session")
    
    events_received = []
    
    def event_callback(event):
        events_received.append(event)
    
    bus.subscribe(event_callback)
    
    # Emit various events
    emitter.emit_call_started(from_number="+1234567890", to_number="+0987654321")
    emitter.emit_speech_detected(energy=0.7)
    emitter.emit_interruption_started(reason="barge_in")
    
    assert len(events_received) == 3
    assert events_received[0].event_type == EventType.CALL_STARTED
    assert events_received[0].call_id == "test_call"
    assert events_received[1].event_type == EventType.SPEECH_DETECTED
    assert events_received[1].data["energy"] == 0.7
    assert events_received[2].event_type == EventType.INTERRUPTION_STARTED


def test_event_history():
    """Test event bus history."""
    bus = RealtimeEventBus()
    bus.max_history_size = 5
    
    from app.voice.events.system import RealtimeEvent
    for i in range(10):
        bus.publish(RealtimeEvent(event_type=EventType.SPEECH_DETECTED))
    
    history = bus.get_history()
    assert len(history) == 5  # Should be limited to max_history_size
    
    # Test filtering
    bus.publish(RealtimeEvent(event_type=EventType.CALL_STARTED))
    call_events = bus.get_history(event_type=EventType.CALL_STARTED)
    assert len(call_events) == 1


def test_event_severity():
    """Test event severity levels."""
    bus = RealtimeEventBus()
    
    error_events = []
    
    def error_callback(event):
        if event.severity == EventSeverity.ERROR:
            error_events.append(event)
    
    bus.subscribe(error_callback)
    
    from app.voice.events.system import RealtimeEvent
    bus.publish(RealtimeEvent(event_type=EventType.CALL_STARTED, severity=EventSeverity.INFO))
    bus.publish(RealtimeEvent(event_type=EventType.ERROR_OCCURRED, severity=EventSeverity.ERROR))
    
    assert len(error_events) == 1
    assert error_events[0].severity == EventSeverity.ERROR


def test_concurrent_interruption_protection():
    """Test race condition protection in concurrent interruptions."""
    ai_state = AIStateManager()
    ai_state.start_speaking()
    ai_state.start_metrics_collection()
    
    async def attempt_interruptions():
        tasks = []
        for i in range(5):
            task = asyncio.create_task(
                asyncio.to_thread(ai_state.interrupt, reason=f"concurrent_{i}")
            )
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    # Run concurrent interruptions
    results = asyncio.run(attempt_interruptions())
    
    # Only one should succeed due to race condition protection
    successful = sum(1 for r in results if r is True)
    assert successful == 1


def test_pipeline_cancellation_token_integration():
    """Test pipeline cancellation token integration."""
    from app.voice.runtime.pipeline import VoiceRuntimePipeline
    from app.core.config import settings
    
    # Skip test if OpenAI API key is not available
    if not settings.openai_api_key:
        pytest.skip("OPENAI_API_KEY not available for integration test")
    
    from app.stt.openai_streaming import OpenAIStreamingSTTProvider
    from app.llm.openai_streaming import OpenAIStreamingLLMProvider
    from app.tts.openai_streaming import OpenAIStreamingTTSProvider
    
    pipeline = VoiceRuntimePipeline(
        stt_provider=OpenAIStreamingSTTProvider(),
        llm_provider=OpenAIStreamingLLMProvider(),
        tts_provider=OpenAIStreamingTTSProvider(),
    )
    
    # Test cancellation token creation
    token = pipeline.create_cancellation_token()
    assert token is not None
    assert token.is_set() is False
    
    # Test cancellation
    pipeline.cancel_current_turn()
    assert token.is_set() is True


def test_vad_metrics_comprehensive():
    """Test comprehensive VAD metrics."""
    vad = VoiceActivityDetector(VADConfig())
    vad.config.speech_threshold = 0.1  # Lower threshold for testing
    
    # Process some audio
    speech_audio = b"\xff\xff" * 100
    silence_audio = b"\x00\x00" * 100
    
    vad.process_audio_chunk(speech_audio)
    vad.process_audio_chunk(speech_audio)
    vad.process_audio_chunk(silence_audio)
    
    metrics = vad.get_metrics()
    
    # Check new metrics
    assert "barge_in_count" in metrics
    assert "average_speech_energy" in metrics
    assert "peak_speech_energy" in metrics
    assert "valid_speech_count" in metrics
    assert "false_positive_count" in metrics
    assert "silence_accumulator_ms" in metrics
    assert "no_speech_timeout_reached" in metrics
    assert "should_end_turn" in metrics
