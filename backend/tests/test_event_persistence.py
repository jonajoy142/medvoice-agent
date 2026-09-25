"""Tests for voice event persistence."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.voice.events.persistence import VoiceEventPersistence
from app.voice.events.system import RealtimeEvent, EventType, EventSeverity


class TestVoiceEventPersistence:
    """Tests for VoiceEventPersistence."""
    
    @pytest.fixture
    def persistence(self):
        """Create a persistence instance for testing."""
        return VoiceEventPersistence(batch_size=2, flush_interval_seconds=0.1)
    
    @pytest.mark.asyncio
    async def test_start_stop_persistence(self, persistence):
        """Test starting and stopping persistence."""
        assert not persistence.is_running
        
        await persistence.start()
        assert persistence.is_running
        
        await persistence.stop()
        assert not persistence.is_running
    
    @pytest.mark.asyncio
    async def test_persist_event(self, persistence):
        """Test queuing an event for persistence."""
        await persistence.start()
        
        event = RealtimeEvent(
            event_type=EventType.CALL_STARTED,
            severity=EventSeverity.INFO,
            data={"test": "data"},
            call_id="call-123",
            session_id="session-123",
        )
        
        await persistence.persist_event(event)
        
        # Event should be queued
        assert not persistence.event_queue.empty()
        
        await persistence.stop()
    
    @pytest.mark.asyncio
    @patch('app.voice.events.persistence.check_db_connection')
    @patch('app.voice.events.persistence.db_session')
    async def test_flush_events(self, mock_db_session, mock_check_db, persistence):
        """Test flushing events to database."""
        mock_check_db.return_value = True
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        
        await persistence.start()
        
        # Add events
        for i in range(2):
            event = RealtimeEvent(
                event_type=EventType.CALL_STARTED,
                severity=EventSeverity.INFO,
                data={"index": i},
                call_id="call-123",
                session_id="session-123",
            )
            await persistence.persist_event(event)
        
        # Wait for flush
        await asyncio.sleep(0.2)
        
        # Verify database calls
        assert mock_db.execute.call_count == 2
        
        await persistence.stop()
    
    @pytest.mark.asyncio
    @patch('app.voice.events.persistence.check_db_connection')
    async def test_flush_db_unavailable(self, mock_check_db, persistence):
        """Test flush when database unavailable."""
        mock_check_db.return_value = False
        
        await persistence.start()
        
        event = RealtimeEvent(
            event_type=EventType.CALL_STARTED,
            severity=EventSeverity.INFO,
            data={"test": "data"},
            call_id="call-123",
            session_id="session-123",
        )
        await persistence.persist_event(event)
        
        # Wait for flush
        await asyncio.sleep(0.2)
        
        # Events should remain in queue
        assert not persistence.event_queue.empty()
        
        await persistence.stop()
    
    @pytest.mark.asyncio
    @patch('app.voice.events.persistence.check_db_connection')
    @patch('app.voice.events.persistence.db_session')
    async def test_persist_conversation_turn(self, mock_db_session, mock_check_db):
        """Test persisting conversation turn."""
        mock_check_db.return_value = True
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        
        persistence = VoiceEventPersistence()
        
        # Should not raise error
        await persistence.persist_conversation_turn(
            hospital_id="hospital-1",
            call_id="call-1",
            turn_index=1,
            speaker="user",
            text="Hello",
            language="en-IN",
            interrupted=False,
            provider="openai",
            metadata={"test": "data"},
        )
    
    @pytest.mark.asyncio
    @patch('app.voice.events.persistence.check_db_connection')
    async def test_persist_conversation_turn_db_unavailable(self, mock_check_db):
        """Test persisting conversation turn when database unavailable."""
        mock_check_db.return_value = False
        
        persistence = VoiceEventPersistence()
        
        # Should not raise error
        await persistence.persist_conversation_turn(
            hospital_id="hospital-1",
            call_id="call-1",
            turn_index=1,
            speaker="user",
            text="Hello",
            language="en-IN",
        )
    
    @pytest.mark.asyncio
    @patch('app.voice.events.persistence.check_db_connection')
    @patch('app.voice.events.persistence.db_session')
    async def test_persistence_failure_requeues_events(self, mock_db_session, mock_check_db, persistence):
        """Test that failed persistence re-queues events."""
        mock_check_db.return_value = True
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("DB Error")
        mock_db_session.return_value.__enter__.return_value = mock_db
        
        await persistence.start()
        
        event = RealtimeEvent(
            event_type=EventType.CALL_STARTED,
            severity=EventSeverity.INFO,
            data={"test": "data"},
            call_id="call-123",
            session_id="session-123",
        )
        await persistence.persist_event(event)
        
        # Wait for flush attempt
        await asyncio.sleep(0.2)
        
        # Event should be re-queued (queue not empty)
        assert not persistence.event_queue.empty()
        
        await persistence.stop()
