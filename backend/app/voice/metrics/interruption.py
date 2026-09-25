"""Comprehensive interruption metrics collection and reporting."""

import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class InterruptionType(Enum):
    """Types of interruptions."""
    BARGE_IN = "barge_in"
    TIMEOUT = "timeout"
    ERROR = "error"
    MANUAL = "manual"
    FORCE = "force"


@dataclass
class InterruptionEvent:
    """Single interruption event."""
    event_type: InterruptionType
    timestamp: float
    duration_ms: float
    reason: str
    was_successful: bool
    ai_state_before: str
    ai_state_after: str
    speech_energy: float = 0.0
    vad_state: str = "unknown"


@dataclass
class InterruptionMetrics:
    """Comprehensive interruption metrics."""
    total_interruptions: int = 0
    successful_interruptions: int = 0
    failed_interruptions: int = 0
    average_interruption_latency_ms: float = 0.0
    average_interruption_duration_ms: float = 0.0
    min_interruption_latency_ms: float = float('inf')
    max_interruption_latency_ms: float = 0.0
    interruption_events: List[InterruptionEvent] = field(default_factory=list)
    
    # Barge-in specific metrics
    barge_in_count: int = 0
    barge_in_success_rate: float = 0.0
    average_barge_in_energy: float = 0.0
    
    # Timing metrics
    first_interruption_time: Optional[float] = None
    last_interruption_time: Optional[float] = None
    average_time_between_interruptions_ms: float = 0.0
    
    # State transition metrics
    state_transitions: int = 0
    unexpected_state_changes: int = 0
    
    # Cancellation metrics
    cancellation_count: int = 0
    successful_cancellations: int = 0
    failed_cancellations: int = 0


class InterruptionMetricsCollector:
    """Collects and aggregates interruption metrics from multiple sources."""
    
    def __init__(self):
        self.metrics = InterruptionMetrics()
        self.start_time: Optional[float] = None
        self.cancellation_times: List[float] = []
    
    def start_collection(self) -> None:
        """Start metrics collection for a new call."""
        self.start_time = time.perf_counter()
        self.metrics = InterruptionMetrics()
        self.cancellation_times.clear()
    
    def record_interruption(
        self,
        event_type: InterruptionType,
        duration_ms: float,
        reason: str,
        was_successful: bool,
        ai_state_before: str,
        ai_state_after: str,
        speech_energy: float = 0.0,
        vad_state: str = "unknown",
    ) -> None:
        """Record an interruption event."""
        current_time = time.perf_counter()
        
        event = InterruptionEvent(
            event_type=event_type,
            timestamp=current_time,
            duration_ms=duration_ms,
            reason=reason,
            was_successful=was_successful,
            ai_state_before=ai_state_before,
            ai_state_after=ai_state_after,
            speech_energy=speech_energy,
            vad_state=vad_state,
        )
        
        self.metrics.interruption_events.append(event)
        self.metrics.total_interruptions += 1
        
        if was_successful:
            self.metrics.successful_interruptions += 1
        else:
            self.metrics.failed_interruptions += 1
        
        # Update timing metrics
        if self.metrics.first_interruption_time is None:
            self.metrics.first_interruption_time = current_time
        self.metrics.last_interruption_time = current_time
        
        # Update latency metrics
        if self.start_time:
            latency_ms = (current_time - self.start_time) * 1000
            self.metrics.average_interruption_latency_ms = (
                (self.metrics.average_interruption_latency_ms * (self.metrics.total_interruptions - 1) + latency_ms) /
                self.metrics.total_interruptions
            )
            self.metrics.min_interruption_latency_ms = min(self.metrics.min_interruption_latency_ms, latency_ms)
            self.metrics.max_interruption_latency_ms = max(self.metrics.max_interruption_latency_ms, latency_ms)
        
        # Update duration metrics
        self.metrics.average_interruption_duration_ms = (
            (self.metrics.average_interruption_duration_ms * (self.metrics.total_interruptions - 1) + duration_ms) /
            self.metrics.total_interruptions
        )
        
        # Update barge-in specific metrics
        if event_type == InterruptionType.BARGE_IN:
            self.metrics.barge_in_count += 1
            self.metrics.average_barge_in_energy = (
                (self.metrics.average_barge_in_energy * (self.metrics.barge_in_count - 1) + speech_energy) /
                self.metrics.barge_in_count
            )
            self.metrics.barge_in_success_rate = self.metrics.successful_interruptions / self.metrics.total_interruptions
    
    def record_cancellation(self, was_successful: bool) -> None:
        """Record a cancellation event."""
        self.metrics.cancellation_count += 1
        if was_successful:
            self.metrics.successful_cancellations += 1
        else:
            self.metrics.failed_cancellations += 1
        
        current_time = time.perf_counter()
        if self.start_time:
            self.cancellation_times.append((current_time - self.start_time) * 1000)
    
    def record_state_transition(self, was_expected: bool = True) -> None:
        """Record a state transition."""
        self.metrics.state_transitions += 1
        if not was_expected:
            self.metrics.unexpected_state_changes += 1
    
    def calculate_time_between_interruptions(self) -> None:
        """Calculate average time between interruptions."""
        if len(self.metrics.interruption_events) < 2:
            return
        
        total_time = 0.0
        for i in range(1, len(self.metrics.interruption_events)):
            time_diff = self.metrics.interruption_events[i].timestamp - self.metrics.interruption_events[i-1].timestamp
            total_time += time_diff
        
        self.metrics.average_time_between_interruptions_ms = (total_time / (len(self.metrics.interruption_events) - 1)) * 1000
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive interruption metrics."""
        self.calculate_time_between_interruptions()
        
        return {
            "total_interruptions": self.metrics.total_interruptions,
            "successful_interruptions": self.metrics.successful_interruptions,
            "failed_interruptions": self.metrics.failed_interruptions,
            "success_rate": self.metrics.successful_interruptions / self.metrics.total_interruptions if self.metrics.total_interruptions > 0 else 0.0,
            "average_interruption_latency_ms": self.metrics.average_interruption_latency_ms,
            "average_interruption_duration_ms": self.metrics.average_interruption_duration_ms,
            "min_interruption_latency_ms": self.metrics.min_interruption_latency_ms if self.metrics.min_interruption_latency_ms != float('inf') else 0.0,
            "max_interruption_latency_ms": self.metrics.max_interruption_latency_ms,
            "barge_in_count": self.metrics.barge_in_count,
            "barge_in_success_rate": self.metrics.barge_in_success_rate,
            "average_barge_in_energy": self.metrics.average_barge_in_energy,
            "average_time_between_interruptions_ms": self.metrics.average_time_between_interruptions_ms,
            "state_transitions": self.metrics.state_transitions,
            "unexpected_state_changes": self.metrics.unexpected_state_changes,
            "cancellation_count": self.metrics.cancellation_count,
            "successful_cancellations": self.metrics.successful_cancellations,
            "failed_cancellations": self.metrics.failed_cancellations,
            "call_duration_ms": (time.perf_counter() - self.start_time) * 1000 if self.start_time else 0.0,
            "interruptions_per_minute": self._calculate_interruptions_per_minute(),
        }
    
    def _calculate_interruptions_per_minute(self) -> float:
        """Calculate interruptions per minute."""
        if not self.start_time:
            return 0.0
        
        duration_minutes = (time.perf_counter() - self.start_time) / 60.0
        if duration_minutes == 0:
            return 0.0
        
        return self.metrics.total_interruptions / duration_minutes
    
    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent interruption events."""
        recent = self.metrics.interruption_events[-limit:] if self.metrics.interruption_events else []
        return [
            {
                "event_type": event.event_type.value,
                "timestamp": event.timestamp,
                "duration_ms": event.duration_ms,
                "reason": event.reason,
                "was_successful": event.was_successful,
                "ai_state_before": event.ai_state_before,
                "ai_state_after": event.ai_state_after,
                "speech_energy": event.speech_energy,
                "vad_state": event.vad_state,
            }
            for event in recent
        ]
    
    def reset(self) -> None:
        """Reset metrics collector."""
        self.metrics = InterruptionMetrics()
        self.start_time = None
        self.cancellation_times.clear()