"""Tests for voice session lifecycle management."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from app.voice.session.lifecycle import (
    VoiceSession,
    SessionLifecycleState,
    VoiceSessionManager,
)


class TestVoiceSession:
    """Tests for VoiceSession lifecycle."""
    
    def test_session_creation(self):
        """Test session creation with initial state."""
        session = VoiceSession(
            hospital_id="hospital-1",
            agent_id="agent-1",
            from_number="+1234567890",
            to_number="+0987654321",
        )
        
        assert session.session_id is not None
        assert session.hospital_id == "hospital-1"
        assert session.agent_id == "agent-1"
        assert session.from_number == "+1234567890"
        assert session.to_number == "+0987654321"
        assert session.lifecycle_state == SessionLifecycleState.CREATED
        assert session.started_at is not None
        assert session.connected_at is None
        assert session.ended_at is None
    
    def test_session_transition(self):
        """Test session state transitions."""
        session = VoiceSession()
        
        session.transition_to(SessionLifecycleState.CONNECTED)
        assert session.lifecycle_state == SessionLifecycleState.CONNECTED
        assert session.connected_at is not None
        
        session.transition_to(SessionLifecycleState.ENDED)
        assert session.lifecycle_state == SessionLifecycleState.ENDED
        assert session.ended_at is not None
    
    def test_session_set_stream_sid(self):
        """Test setting stream SID."""
        session = VoiceSession()
        session.set_stream_sid("stream-sid-123")
        
        assert session.stream_sid == "stream-sid-123"
    
    @pytest.mark.asyncio
    async def test_session_background_task_tracking(self):
        """Test background task tracking."""
        session = VoiceSession()
        
        async def dummy_task():
            await asyncio.sleep(0.1)
        
        task = asyncio.create_task(dummy_task())
        session.add_background_task(task)
        
        assert task in session.background_tasks
    
    @pytest.mark.asyncio
    async def test_session_cleanup(self):
        """Test session cleanup cancels background tasks."""
        session = VoiceSession()
        
        async def dummy_task():
            await asyncio.sleep(10)
        
        task = asyncio.create_task(dummy_task())
        session.add_background_task(task)
        
        await session.cleanup()
        
        assert task.cancelled()
        assert len(session.background_tasks) == 0
    
    def test_session_duration(self):
        """Test session duration calculation."""
        from datetime import datetime, timedelta
        
        session = VoiceSession()
        session.started_at = datetime.utcnow() - timedelta(seconds=10)
        session.ended_at = datetime.utcnow()
        
        duration = session.get_duration_seconds()
        assert duration is not None
        assert 9 <= duration <= 11  # Allow some tolerance
    
    def test_session_to_dict(self):
        """Test session serialization to dictionary."""
        session = VoiceSession(hospital_id="hospital-1")
        session.set_stream_sid("stream-123")
        
        session_dict = session.to_dict()
        
        assert session_dict["session_id"] == session.session_id
        assert session_dict["hospital_id"] == "hospital-1"
        assert session_dict["stream_sid"] == "stream-123"
        assert session_dict["lifecycle_state"] == SessionLifecycleState.CREATED.value


class TestVoiceSessionManager:
    """Tests for VoiceSessionManager."""
    
    @patch('app.voice.session.lifecycle.check_db_connection')
    @patch('app.voice.session.lifecycle.db_session')
    def test_create_session(self, mock_db_session, mock_check_db):
        """Test creating a new session."""
        mock_check_db.return_value = True
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        
        manager = VoiceSessionManager()
        session = manager.create_session(
            hospital_id="hospital-1",
            agent_id="agent-1",
        )
        
        assert session.session_id is not None
        assert session.hospital_id == "hospital-1"
        assert session.agent_id == "agent-1"
        assert session.session_id in manager.active_sessions
    
    def test_get_session(self):
        """Test retrieving an existing session."""
        manager = VoiceSessionManager()
        session = manager.create_session(hospital_id="hospital-1")
        
        retrieved = manager.get_session(session.session_id)
        
        assert retrieved is session
    
    def test_get_nonexistent_session(self):
        """Test retrieving non-existent session returns None."""
        manager = VoiceSessionManager()
        
        retrieved = manager.get_session("non-existent")
        
        assert retrieved is None
    
    @patch('app.voice.session.lifecycle.check_db_connection')
    @patch('app.voice.session.lifecycle.db_session')
    def test_remove_session(self, mock_db_session, mock_check_db):
        """Test removing a session."""
        mock_check_db.return_value = True
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        
        manager = VoiceSessionManager()
        session = manager.create_session(hospital_id="hospital-1")
        
        manager.remove_session(session.session_id)
        
        assert session.session_id not in manager.active_sessions
        assert session.lifecycle_state == SessionLifecycleState.ENDED
    
    @pytest.mark.asyncio
    @patch('app.voice.session.lifecycle.check_db_connection')
    @patch('app.voice.session.lifecycle.db_session')
    async def test_cleanup_session(self, mock_db_session, mock_check_db):
        """Test cleaning up a session."""
        mock_check_db.return_value = True
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        
        manager = VoiceSessionManager()
        session = manager.create_session(hospital_id="hospital-1")
        
        await manager.cleanup_session(session.session_id)
        
        assert session.session_id not in manager.active_sessions
    
    @patch('app.voice.session.lifecycle.check_db_connection')
    @patch('app.voice.session.lifecycle.db_session')
    def test_mark_session_failed(self, mock_db_session, mock_check_db):
        """Test marking a session as failed."""
        mock_check_db.return_value = True
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        
        manager = VoiceSessionManager()
        session = manager.create_session(hospital_id="hospital-1")
        
        manager.mark_session_failed(session.session_id, "Test error")
        
        assert session.lifecycle_state == SessionLifecycleState.FAILED
        assert session.metadata["error"] == "Test error"
