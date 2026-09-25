"""Voice session lifecycle management."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from sqlalchemy import text

from app.db.session import check_db_connection, db_session


class SessionLifecycleState(Enum):
    """Voice session lifecycle states."""
    CREATED = "created"
    CONNECTED = "connected"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    TOOL_EXECUTION = "tool_execution"
    WAITING = "waiting"
    ENDING = "ending"
    ENDED = "ended"
    FAILED = "failed"


class VoiceSession:
    """Voice session with lifecycle management."""
    
    def __init__(
        self,
        hospital_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        call_id: Optional[str] = None,
        from_number: Optional[str] = None,
        to_number: Optional[str] = None,
    ):
        self.session_id = str(uuid.uuid4())
        self.hospital_id = hospital_id
        self.agent_id = agent_id
        self.call_id = call_id
        self.stream_sid: Optional[str] = None
        self.from_number = from_number
        self.to_number = to_number
        
        self.lifecycle_state = SessionLifecycleState.CREATED
        self.started_at = datetime.utcnow()
        self.connected_at: Optional[datetime] = None
        self.ended_at: Optional[datetime] = None
        self.metadata: Dict[str, Any] = {}
        
        # Background tasks tracking
        self.background_tasks: set[asyncio.Task] = set()
        
        logger = logging.getLogger(__name__)
        logger.info(f"Voice session created: {self.session_id}")
    
    def transition_to(self, new_state: SessionLifecycleState) -> None:
        """
        Transition to a new lifecycle state.
        
        Args:
            new_state: New lifecycle state
        """
        old_state = self.lifecycle_state
        self.lifecycle_state = new_state
        
        logger = logging.getLogger(__name__)
        logger.info(f"Session {self.session_id} transition: {old_state.value} -> {new_state.value}")
        
        # Update timestamps
        if new_state == SessionLifecycleState.CONNECTED and self.connected_at is None:
            self.connected_at = datetime.utcnow()
        elif new_state in (SessionLifecycleState.ENDED, SessionLifecycleState.FAILED):
            self.ended_at = datetime.utcnow()
    
    def set_stream_sid(self, stream_sid: str) -> None:
        """Set the stream SID from Exotel."""
        self.stream_sid = stream_sid
    
    def add_background_task(self, task: asyncio.Task) -> None:
        """
        Track a background task for cleanup.
        
        Args:
            task: Async task to track
        """
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
    
    async def cleanup(self) -> None:
        """Cancel all background tasks and cleanup resources."""
        logger = logging.getLogger(__name__)
        
        # Cancel all background tasks
        for task in list(self.background_tasks):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.background_tasks.clear()
        logger.info(f"Voice session cleaned up: {self.session_id}")
    
    def get_duration_seconds(self) -> Optional[float]:
        """Get session duration in seconds."""
        if self.ended_at and self.started_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "hospital_id": self.hospital_id,
            "agent_id": self.agent_id,
            "call_id": self.call_id,
            "stream_sid": self.stream_sid,
            "from_number": self.from_number,
            "to_number": self.to_number,
            "lifecycle_state": self.lifecycle_state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_seconds": self.get_duration_seconds(),
            "metadata": self.metadata,
        }


class VoiceSessionManager:
    """Manager for voice session lifecycle and persistence."""
    
    def __init__(self):
        self.active_sessions: Dict[str, VoiceSession] = {}
        logger = logging.getLogger(__name__)
        logger.info("Voice session manager initialized")
    
    def create_session(
        self,
        hospital_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        call_id: Optional[str] = None,
        from_number: Optional[str] = None,
        to_number: Optional[str] = None,
    ) -> VoiceSession:
        """
        Create a new voice session.
        
        Args:
            hospital_id: Hospital UUID
            agent_id: Agent UUID
            call_id: Call UUID
            from_number: Caller phone number
            to_number: Called phone number
            
        Returns:
            VoiceSession instance
        """
        session = VoiceSession(
            hospital_id=hospital_id,
            agent_id=agent_id,
            call_id=call_id,
            from_number=from_number,
            to_number=to_number,
        )
        self.active_sessions[session.session_id] = session
        
        # Persist session to database
        self._persist_session(session)
        
        return session
    
    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """
        Get an active session by ID.
        
        Args:
            session_id: Session UUID
            
        Returns:
            VoiceSession instance or None
        """
        return self.active_sessions.get(session_id)
    
    def remove_session(self, session_id: str) -> None:
        """
        Remove a session from active sessions.
        
        Args:
            session_id: Session UUID
        """
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.transition_to(SessionLifecycleState.ENDED)
            self._update_session_in_db(session)
            del self.active_sessions[session_id]
    
    async def cleanup_session(self, session_id: str) -> None:
        """
        Cleanup a session and remove it.
        
        Args:
            session_id: Session UUID
        """
        session = self.get_session(session_id)
        if session:
            await session.cleanup()
            self.remove_session(session_id)
    
    def _persist_session(self, session: VoiceSession) -> None:
        """Persist session to database."""
        if not check_db_connection():
            return
        
        try:
            with db_session() as db:
                db.execute(
                    text("""
                        INSERT INTO voice_call_sessions 
                        (hospital_id, agent_id, call_id, session_id, stream_sid, from_number, to_number,
                         lifecycle_state, started_at, metadata, created_at)
                        VALUES 
                        (:hospital_id, :agent_id, :call_id, :session_id, :stream_sid, :from_number, :to_number,
                         :lifecycle_state, :started_at, :metadata, :created_at)
                    """),
                    {
                        "hospital_id": session.hospital_id,
                        "agent_id": session.agent_id,
                        "call_id": session.call_id,
                        "session_id": session.session_id,
                        "stream_sid": session.stream_sid,
                        "from_number": session.from_number,
                        "to_number": session.to_number,
                        "lifecycle_state": session.lifecycle_state.value,
                        "started_at": session.started_at,
                        "metadata": session.metadata,
                        "created_at": datetime.utcnow(),
                    },
                )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to persist session: {e}")
    
    def _update_session_in_db(self, session: VoiceSession) -> None:
        """Update session in database."""
        if not check_db_connection():
            return
        
        try:
            with db_session() as db:
                db.execute(
                    text("""
                        UPDATE voice_call_sessions
                        SET lifecycle_state = :lifecycle_state,
                            connected_at = COALESCE(:connected_at, connected_at),
                            ended_at = COALESCE(:ended_at, ended_at),
                            duration_seconds = :duration_seconds,
                            stream_sid = COALESCE(:stream_sid, stream_sid),
                            metadata = :metadata
                        WHERE session_id = :session_id
                    """),
                    {
                        "lifecycle_state": session.lifecycle_state.value,
                        "connected_at": session.connected_at,
                        "ended_at": session.ended_at,
                        "duration_seconds": session.get_duration_seconds(),
                        "stream_sid": session.stream_sid,
                        "metadata": session.metadata,
                        "session_id": session.session_id,
                    },
                )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to update session in database: {e}")
    
    def mark_session_failed(self, session_id: str, error: Optional[str] = None) -> None:
        """
        Mark a session as failed.
        
        Args:
            session_id: Session UUID
            error: Optional error message
        """
        session = self.get_session(session_id)
        if session:
            session.transition_to(SessionLifecycleState.FAILED)
            if error:
                session.metadata["error"] = error
            self._update_session_in_db(session)


# Global session manager instance
voice_session_manager = VoiceSessionManager()
