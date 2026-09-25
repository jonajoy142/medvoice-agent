"""AI speaking state management for interruption handling."""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable
from contextlib import contextmanager


class AIState(Enum):
    """Safe operational states for AI (no chain-of-thought exposure)."""
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    TOOL_EXECUTION = "tool_execution"
    WAITING = "waiting"


@dataclass
class StateTransition:
    """Record of a state transition."""
    from_state: Optional[AIState]
    to_state: AIState
    timestamp: float
    reason: str


@dataclass
class AIStateManagerConfig:
    """Configuration for AI state manager."""
    interruption_cooldown_ms: int = 500  # Minimum time between interruptions
    max_interruptions_per_call: int = 10  # Maximum interruptions before fallback
    barge_in_sensitivity: float = 0.5  # Sensitivity for barge-in detection (0.0-1.0)
    interruption_timeout_ms: int = 30000  # Maximum time to wait for interruption to complete
    fallback_on_max_interruptions: bool = True  # Whether to fallback to non-interruptible mode


class AIStateManager:
    """Manages AI speaking state with interruption support."""
    
    def __init__(self, config: Optional[AIStateManagerConfig] = None):
        self.config = config or AIStateManagerConfig()
        self.current_state = AIState.LISTENING
        self.state_history: list[StateTransition] = []
        self.interruption_count = 0
        self.last_interruption_time: Optional[float] = None
        self.cancellation_token: Optional[asyncio.Event] = None
        
        # Callbacks for state changes
        self.on_state_change: Optional[Callable[[AIState, AIState], None]] = None
        self.on_interruption: Optional[Callable[[], None]] = None
        
        # Interruption tracking
        self.interruption_reasons: list[str] = []
        self.interruption_durations_ms: list[float] = []
        self.fallback_mode: bool = False
        self.interruption_start_time: Optional[float] = None
        
        # Metrics collection (late import to avoid circular dependency)
        self.metrics_collector = None  # Will be initialized when needed
    
    def set_state(self, new_state: AIState, reason: str = "") -> None:
        """Transition to a new state with logging."""
        if self.current_state == new_state:
            return
        
        from_state = self.current_state
        self.current_state = new_state
        
        # Record transition
        transition = StateTransition(
            from_state=from_state,
            to_state=new_state,
            timestamp=time.perf_counter(),
            reason=reason,
        )
        self.state_history.append(transition)
        
        # Trigger callback
        if self.on_state_change:
            self.on_state_change(from_state, new_state)
    
    def get_state(self) -> AIState:
        """Get current AI state."""
        return self.current_state
    
    def is_speaking(self) -> bool:
        """Check if AI is currently speaking."""
        return self.current_state == AIState.SPEAKING
    
    def is_listening(self) -> bool:
        """Check if AI is currently listening."""
        return self.current_state == AIState.LISTENING
    
    def can_interrupt(self) -> bool:
        """Check if interruption is allowed (AI must be speaking)."""
        if not self.is_speaking():
            return False
        
        # Check fallback mode
        if self.fallback_mode:
            return False
        
        # Check cooldown
        if self.last_interruption_time:
            elapsed_ms = (time.perf_counter() - self.last_interruption_time) * 1000
            if elapsed_ms < self.config.interruption_cooldown_ms:
                return False
        
        # Check max interruptions
        if self.interruption_count >= self.config.max_interruptions_per_call:
            return False
        
        return True
    
    def interrupt(self, reason: str = "user_speech", speech_energy: float = 0.0, vad_state: str = "unknown") -> bool:
        """Attempt to interrupt current AI speech."""
        if not self.can_interrupt():
            # Record failed interruption if metrics collector is available
            if self.metrics_collector:
                try:
                    from app.voice.metrics.interruption import InterruptionType
                    event_type = InterruptionType.BARGE_IN if "barge" in reason.lower() else InterruptionType.MANUAL
                    self.metrics_collector.record_interruption(
                        event_type=event_type,
                        duration_ms=0.0,
                        reason=reason,
                        was_successful=False,
                        ai_state_before=self.current_state.value,
                        ai_state_after=self.current_state.value,
                        speech_energy=speech_energy,
                        vad_state=vad_state,
                    )
                except Exception:
                    pass  # Silently fail if metrics collection isn't available
            return False
        
        # Record interruption
        self.interruption_count += 1
        self.last_interruption_time = time.perf_counter()
        self.interruption_start_time = time.perf_counter()
        self.interruption_reasons.append(reason)
        
        previous_state = self.current_state
        
        # Transition to interrupted state
        self.set_state(AIState.INTERRUPTED, reason)
        
        # Cancel current operation
        if self.cancellation_token:
            self.cancellation_token.set()
            if self.metrics_collector:
                try:
                    self.metrics_collector.record_cancellation(was_successful=True)
                except Exception:
                    pass
        
        # Trigger callback
        if self.on_interruption:
            self.on_interruption()
        
        # Record successful interruption if metrics collector is available
        if self.metrics_collector:
            try:
                from app.voice.metrics.interruption import InterruptionType
                event_type = InterruptionType.BARGE_IN if "barge" in reason.lower() else InterruptionType.MANUAL
                self.metrics_collector.record_interruption(
                    event_type=event_type,
                    duration_ms=0.0,  # Will be updated when complete_interruption is called
                    reason=reason,
                    was_successful=True,
                    ai_state_before=previous_state.value,
                    ai_state_after=self.current_state.value,
                    speech_energy=speech_energy,
                    vad_state=vad_state,
                )
            except Exception:
                pass  # Silently fail if metrics collection isn't available
        
        # Check if we should enter fallback mode
        if (self.config.fallback_on_max_interruptions and 
            self.interruption_count >= self.config.max_interruptions_per_call):
            self.fallback_mode = True
        
        return True
    
    def start_listening(self) -> None:
        """Transition to listening state."""
        self.set_state(AIState.LISTENING, "start_listening")
    
    def start_thinking(self) -> None:
        """Transition to thinking state."""
        self.set_state(AIState.THINKING, "start_thinking")
    
    def start_speaking(self) -> None:
        """Transition to speaking state."""
        self.set_state(AIState.SPEAKING, "start_speaking")
    
    def start_tool_execution(self) -> None:
        """Transition to tool execution state."""
        self.set_state(AIState.TOOL_EXECUTION, "start_tool_execution")
    
    def start_waiting(self) -> None:
        """Transition to waiting state."""
        self.set_state(AIState.WAITING, "start_waiting")
    
    def complete_interruption(self) -> None:
        """Mark interruption as complete and record duration."""
        if self.interruption_start_time:
            duration_ms = (time.perf_counter() - self.interruption_start_time) * 1000
            self.interruption_durations_ms.append(duration_ms)
            
            # Update the last interruption event with the actual duration
            if self.metrics_collector and self.metrics_collector.metrics.interruption_events:
                last_event = self.metrics_collector.metrics.interruption_events[-1]
                # Update duration in the event (this is a bit of a hack, but works for now)
                last_event.duration_ms = duration_ms
            
            self.interruption_start_time = None
    
    def force_interruption(self, reason: str = "force", speech_energy: float = 0.0, vad_state: str = "unknown") -> bool:
        """Force interruption even if conditions aren't met (for emergencies)."""
        if not self.is_speaking():
            return False
        
        # Record interruption
        self.interruption_count += 1
        self.last_interruption_time = time.perf_counter()
        self.interruption_start_time = time.perf_counter()
        self.interruption_reasons.append(f"force:{reason}")
        
        previous_state = self.current_state
        
        # Transition to interrupted state
        self.set_state(AIState.INTERRUPTED, f"force:{reason}")
        
        # Cancel current operation
        if self.cancellation_token:
            self.cancellation_token.set()
            if self.metrics_collector:
                try:
                    self.metrics_collector.record_cancellation(was_successful=True)
                except Exception:
                    pass
        
        # Trigger callback
        if self.on_interruption:
            self.on_interruption()
        
        # Record force interruption if metrics collector is available
        if self.metrics_collector:
            try:
                from app.voice.metrics.interruption import InterruptionType
                self.metrics_collector.record_interruption(
                    event_type=InterruptionType.FORCE,
                    duration_ms=0.0,
                    reason=f"force:{reason}",
                    was_successful=True,
                    ai_state_before=previous_state.value,
                    ai_state_after=self.current_state.value,
                    speech_energy=speech_energy,
                    vad_state=vad_state,
                )
            except Exception:
                pass  # Silently fail if metrics collection isn't available
        
        return True
    
    @contextmanager
    def state_context(self, state: AIState, reason: str = ""):
        """Context manager for temporary state changes."""
        old_state = self.current_state
        self.set_state(state, reason)
        try:
            yield
        finally:
            self.set_state(old_state, f"exit_{state}")
    
    def create_cancellation_token(self) -> asyncio.Event:
        """Create a new cancellation token for current operation."""
        self.cancellation_token = asyncio.Event()
        return self.cancellation_token
    
    def start_metrics_collection(self) -> None:
        """Start metrics collection for a new call."""
        try:
            from app.voice.metrics.interruption import InterruptionMetricsCollector
            self.metrics_collector = InterruptionMetricsCollector()
            self.metrics_collector.start_collection()
        except Exception:
            self.metrics_collector = None  # Silently fail if metrics aren't available
    
    def reset(self) -> None:
        """Reset state manager for new call."""
        self.current_state = AIState.LISTENING
        self.state_history.clear()
        self.interruption_count = 0
        self.last_interruption_time = None
        self.cancellation_token = None
        self.interruption_reasons.clear()
        self.interruption_durations_ms.clear()
        self.fallback_mode = False
        self.interruption_start_time = None
        if self.metrics_collector:
            try:
                self.metrics_collector.reset()
            except Exception:
                pass
    
    def get_comprehensive_metrics(self) -> dict:
        """Get comprehensive metrics including state and interruption metrics."""
        state_metrics = self.get_metrics()
        
        if self.metrics_collector:
            try:
                interruption_metrics = self.metrics_collector.get_metrics()
                recent_events = self.metrics_collector.get_recent_events(limit=5)
            except Exception:
                interruption_metrics = {}
                recent_events = []
        else:
            interruption_metrics = {}
            recent_events = []
        
        return {
            **state_metrics,
            "interruption_metrics": interruption_metrics,
            "recent_interruption_events": recent_events,
        }
    
    def get_metrics(self) -> dict:
        """Get current state metrics."""
        avg_interruption_duration = (
            sum(self.interruption_durations_ms) / len(self.interruption_durations_ms)
            if self.interruption_durations_ms else 0.0
        )
        
        return {
            "current_state": self.current_state.value,
            "interruption_count": self.interruption_count,
            "last_interruption_ms": (
                (time.perf_counter() - self.last_interruption_time) * 1000
                if self.last_interruption_time else None
            ),
            "state_transitions": len(self.state_history),
            "can_interrupt": self.can_interrupt(),
            "fallback_mode": self.fallback_mode,
            "interruption_reasons": self.interruption_reasons,
            "average_interruption_duration_ms": avg_interruption_duration,
            "interruption_durations_ms": self.interruption_durations_ms,
            "max_interruptions_per_call": self.config.max_interruptions_per_call,
            "interruption_cooldown_ms": self.config.interruption_cooldown_ms,
        }
    
    def get_state_history(self, limit: int = 10) -> list[dict]:
        """Get recent state transitions."""
        recent = self.state_history[-limit:] if self.state_history else []
        return [
            {
                "from_state": t.from_state.value if t.from_state else None,
                "to_state": t.to_state.value,
                "timestamp": t.timestamp,
                "reason": t.reason,
            }
            for t in recent
        ]
