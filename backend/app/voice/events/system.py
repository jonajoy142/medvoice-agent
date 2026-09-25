"""Structured realtime events system for voice operations."""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime


class EventType(Enum):
    """Types of realtime events."""
    # Lifecycle events
    CALL_STARTED = "call_started"
    CALL_ENDED = "call_ended"
    STREAM_CONNECTED = "stream_connected"
    STREAM_DISCONNECTED = "stream_disconnected"
    
    # State events
    STATE_CHANGE = "state_change"
    AI_STATE_CHANGE = "ai_state_change"
    
    # Speech events
    SPEECH_DETECTED = "speech_detected"
    SPEECH_ENDED = "speech_ended"
    SILENCE_DETECTED = "silence_detected"
    
    # Interruption events
    INTERRUPTION_STARTED = "interruption_started"
    INTERRUPTION_COMPLETED = "interruption_completed"
    INTERRUPTION_FAILED = "interruption_failed"
    BARGE_IN_DETECTED = "barge_in_detected"
    
    # Pipeline events
    STT_STARTED = "stt_started"
    STT_COMPLETED = "stt_completed"
    STT_FAILED = "stt_failed"
    LLM_STARTED = "llm_started"
    LLM_COMPLETED = "llm_completed"
    LLM_FAILED = "llm_failed"
    TTS_STARTED = "tts_started"
    TTS_COMPLETED = "tts_completed"
    TTS_FAILED = "tts_failed"
    TTS_CHUNK_SENT = "tts_chunk_sent"
    
    # Cancellation events
    CANCELLATION_REQUESTED = "cancellation_requested"
    CANCELLATION_COMPLETED = "cancellation_completed"
    CANCELLATION_FAILED = "cancellation_failed"
    
    # Error events
    ERROR_OCCURRED = "error_occurred"
    WARNING_ISSUED = "warning_issued"
    
    # Metrics events
    METRICS_UPDATED = "metrics_updated"
    PERFORMANCE_DATA = "performance_data"


class EventSeverity(Enum):
    """Severity levels for events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class RealtimeEvent:
    """Structured realtime event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.CALL_STARTED
    timestamp: float = field(default_factory=time.perf_counter)
    severity: EventSeverity = EventSeverity.INFO
    
    # Context
    call_id: Optional[str] = None
    session_id: Optional[str] = None
    stream_sid: Optional[str] = None
    
    # Event data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Timing
    duration_ms: Optional[float] = None
    latency_ms: Optional[float] = None
    
    # Metadata
    source: str = "voice_system"
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "severity": self.severity.value,
            "call_id": self.call_id,
            "session_id": self.session_id,
            "stream_sid": self.stream_sid,
            "data": self.data,
            "duration_ms": self.duration_ms,
            "latency_ms": self.latency_ms,
            "source": self.source,
            "correlation_id": self.correlation_id,
        }


class EventSubscriber:
    """Subscriber for realtime events."""
    
    def __init__(self, callback: Callable[[RealtimeEvent], None], event_types: Optional[List[EventType]] = None):
        self.callback = callback
        self.event_types = event_types  # None means subscribe to all events
        self.subscriber_id: str = str(uuid.uuid4())
    
    def should_receive(self, event: RealtimeEvent) -> bool:
        """Check if subscriber should receive this event."""
        if self.event_types is None:
            return True
        return event.event_type in self.event_types


class RealtimeEventBus:
    """Central event bus for structured realtime events."""
    
    def __init__(self):
        self.subscribers: List[EventSubscriber] = []
        self.event_history: List[RealtimeEvent] = []
        self.max_history_size: int = 1000
        self.enabled: bool = True
    
    def subscribe(self, callback: Callable[[RealtimeEvent], None], event_types: Optional[List[EventType]] = None) -> EventSubscriber:
        """Subscribe to events."""
        subscriber = EventSubscriber(callback, event_types)
        self.subscribers.append(subscriber)
        return subscriber
    
    def unsubscribe(self, subscriber: EventSubscriber) -> None:
        """Unsubscribe from events."""
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)
    
    def publish(self, event: RealtimeEvent) -> None:
        """Publish an event to all subscribers."""
        if not self.enabled:
            return
        
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)
        
        # Notify subscribers
        for subscriber in self.subscribers:
            if subscriber.should_receive(event):
                try:
                    subscriber.callback(event)
                except Exception as e:
                    # Log error but don't break the event bus
                    print(f"Error in event subscriber: {e}")
    
    def enable(self) -> None:
        """Enable event publishing."""
        self.enabled = True
    
    def disable(self) -> None:
        """Disable event publishing."""
        self.enabled = False
    
    def clear_history(self) -> None:
        """Clear event history."""
        self.event_history.clear()
    
    def get_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[RealtimeEvent]:
        """Get event history, optionally filtered by type."""
        if event_type:
            filtered = [e for e in self.event_history if e.event_type == event_type]
            return filtered[-limit:] if len(filtered) > limit else filtered
        return self.event_history[-limit:] if len(self.event_history) > limit else self.event_history
    
    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent events as dictionaries."""
        recent = self.event_history[-limit:] if self.event_history else []
        return [event.to_dict() for event in recent]


class VoiceEventEmitter:
    """Helper class for emitting voice-related events."""
    
    def __init__(self, event_bus: RealtimeEventBus, call_id: Optional[str] = None, session_id: Optional[str] = None):
        self.event_bus = event_bus
        self.call_id = call_id
        self.session_id = session_id
        self.stream_sid: Optional[str] = None
    
    def set_context(self, call_id: Optional[str] = None, session_id: Optional[str] = None, stream_sid: Optional[str] = None) -> None:
        """Update event context."""
        if call_id is not None:
            self.call_id = call_id
        if session_id is not None:
            self.session_id = session_id
        if stream_sid is not None:
            self.stream_sid = stream_sid
    
    def emit_event(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        severity: EventSeverity = EventSeverity.INFO,
        duration_ms: Optional[float] = None,
        latency_ms: Optional[float] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Emit a realtime event."""
        event = RealtimeEvent(
            event_type=event_type,
            severity=severity,
            call_id=self.call_id,
            session_id=self.session_id,
            stream_sid=self.stream_sid,
            data=data or {},
            duration_ms=duration_ms,
            latency_ms=latency_ms,
            correlation_id=correlation_id,
        )
        self.event_bus.publish(event)
    
    # Convenience methods for common events
    def emit_call_started(self, from_number: Optional[str] = None, to_number: Optional[str] = None) -> None:
        """Emit call started event."""
        self.emit_event(
            EventType.CALL_STARTED,
            data={"from_number": from_number, "to_number": to_number},
        )
    
    def emit_call_ended(self, duration_seconds: Optional[float] = None) -> None:
        """Emit call ended event."""
        self.emit_event(
            EventType.CALL_ENDED,
            data={"duration_seconds": duration_seconds},
        )
    
    def emit_state_change(self, from_state: str, to_state: str, reason: str = "") -> None:
        """Emit state change event."""
        self.emit_event(
            EventType.STATE_CHANGE,
            data={"from_state": from_state, "to_state": to_state, "reason": reason},
        )
    
    def emit_speech_detected(self, energy: float = 0.0) -> None:
        """Emit speech detected event."""
        self.emit_event(
            EventType.SPEECH_DETECTED,
            data={"energy": energy},
        )
    
    def emit_speech_ended(self, duration_ms: float) -> None:
        """Emit speech ended event."""
        self.emit_event(
            EventType.SPEECH_ENDED,
            data={"duration_ms": duration_ms},
            duration_ms=duration_ms,
        )
    
    def emit_interruption_started(self, reason: str = "user_speech") -> None:
        """Emit interruption started event."""
        self.emit_event(
            EventType.INTERRUPTION_STARTED,
            data={"reason": reason},
        )
    
    def emit_interruption_completed(self, duration_ms: float, was_successful: bool = True) -> None:
        """Emit interruption completed event."""
        self.emit_event(
            EventType.INTERRUPTION_COMPLETED,
            data={"duration_ms": duration_ms, "was_successful": was_successful},
            duration_ms=duration_ms,
        )
    
    def emit_barge_in_detected(self, energy: float, duration_ms: float) -> None:
        """Emit barge-in detected event."""
        self.emit_event(
            EventType.BARGE_IN_DETECTED,
            data={"energy": energy, "duration_ms": duration_ms},
        )
    
    def emit_stt_started(self) -> None:
        """Emit STT started event."""
        self.emit_event(EventType.STT_STARTED)
    
    def emit_stt_completed(self, transcript: str, latency_ms: float) -> None:
        """Emit STT completed event."""
        self.emit_event(
            EventType.STT_COMPLETED,
            data={"transcript": transcript},
            latency_ms=latency_ms,
        )
    
    def emit_llm_started(self) -> None:
        """Emit LLM started event."""
        self.emit_event(EventType.LLM_STARTED)
    
    def emit_llm_completed(self, response: str, latency_ms: float) -> None:
        """Emit LLM completed event."""
        self.emit_event(
            EventType.LLM_COMPLETED,
            data={"response": response},
            latency_ms=latency_ms,
        )
    
    def emit_tts_started(self, text: str) -> None:
        """Emit TTS started event."""
        self.emit_event(
            EventType.TTS_STARTED,
            data={"text": text},
        )
    
    def emit_tts_completed(self, duration_ms: float) -> None:
        """Emit TTS completed event."""
        self.emit_event(
            EventType.TTS_COMPLETED,
            duration_ms=duration_ms,
        )
    
    def emit_tts_chunk_sent(self, chunk_index: int, chunk_size: int) -> None:
        """Emit TTS chunk sent event."""
        self.emit_event(
            EventType.TTS_CHUNK_SENT,
            data={"chunk_index": chunk_index, "chunk_size": chunk_size},
        )
    
    def emit_cancellation_requested(self, reason: str = "") -> None:
        """Emit cancellation requested event."""
        self.emit_event(
            EventType.CANCELLATION_REQUESTED,
            data={"reason": reason},
        )
    
    def emit_error(self, error: str, component: str = "unknown") -> None:
        """Emit error event."""
        self.emit_event(
            EventType.ERROR_OCCURRED,
            data={"error": error, "component": component},
            severity=EventSeverity.ERROR,
        )
    
    def emit_warning(self, warning: str, component: str = "unknown") -> None:
        """Emit warning event."""
        self.emit_event(
            EventType.WARNING_ISSUED,
            data={"warning": warning, "component": component},
            severity=EventSeverity.WARNING,
        )