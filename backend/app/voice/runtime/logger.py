"""Structured logging for voice runtime with call_id/session_id context."""

import logging
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class CallContext:
    """Context for a voice call."""
    call_id: str
    session_id: str
    stream_sid: Optional[str] = None
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    tenant_id: Optional[str] = None
    agent_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "session_id": self.session_id,
            "stream_sid": self.stream_sid,
            "from_number": self.from_number,
            "to_number": self.to_number,
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "duration_seconds": time.time() - self.start_time,
        }


class VoiceRuntimeLogger:
    """Structured logger for voice runtime with call context."""
    
    def __init__(self, name: str = "voice_runtime"):
        self.logger = logging.getLogger(name)
        self._context: Optional[CallContext] = None
    
    def set_context(self, context: CallContext) -> None:
        """Set the current call context."""
        self._context = context
    
    def clear_context(self) -> None:
        """Clear the current call context."""
        self._context = None
    
    def _log(self, level: int, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log with context."""
        log_extra = {}
        if self._context:
            log_extra.update(self._context.to_dict())
        if extra:
            log_extra.update(extra)
        
        self.logger.log(level, message, extra=log_extra)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with context."""
        self._log(logging.INFO, message, kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context."""
        self._log(logging.DEBUG, message, kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context."""
        self._log(logging.WARNING, message, kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with context."""
        self._log(logging.ERROR, message, kwargs)
    
    def log_event(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log a structured event."""
        event_data = {"event_type": event_type}
        if data:
            event_data.update(data)
        self.info(f"Event: {event_type}", **event_data)
    
    def log_latency(self, component: str, latency_ms: float, **kwargs) -> None:
        """Log latency measurement."""
        self.info(
            f"Latency: {component}",
            component=component,
            latency_ms=latency_ms,
            **kwargs
        )
    
    def log_transcript(self, transcript: str, is_final: bool, **kwargs) -> None:
        """Log transcript."""
        self.info(
            f"Transcript: {'final' if is_final else 'partial'}",
            transcript=transcript,
            is_final=is_final,
            **kwargs
        )
    
    def log_llm_response(self, response: str, **kwargs) -> None:
        """Log LLM response."""
        self.info(
            "LLM Response",
            response=response,
            **kwargs
        )
    
    def log_audio_chunk(self, chunk_size: int, chunk_index: int, **kwargs) -> None:
        """Log audio chunk."""
        self.debug(
            "Audio Chunk",
            chunk_size=chunk_size,
            chunk_index=chunk_index,
            **kwargs
        )
    
    def log_error(self, component: str, error: Exception, **kwargs) -> None:
        """Log error with context."""
        self.error(
            f"Error in {component}: {str(error)}",
            component=component,
            error_type=type(error).__name__,
            error_message=str(error),
            **kwargs
        )


@contextmanager
def call_context(logger: VoiceRuntimeLogger, context: CallContext):
    """Context manager for call-scoped logging."""
    logger.set_context(context)
    try:
        logger.info("Call started")
        yield logger
    finally:
        logger.info("Call ended")
        logger.clear_context()
