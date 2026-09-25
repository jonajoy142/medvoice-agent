"""Async event persistence service for voice call events."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from app.db.session import check_db_connection, db_session
from app.voice.events.system import RealtimeEvent, EventType


logger = logging.getLogger(__name__)


class VoiceEventPersistence:
    """Async persistence service for voice call events."""
    
    def __init__(self, batch_size: int = 10, flush_interval_seconds: float = 1.0):
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.flush_task: Optional[asyncio.Task] = None
        self.is_running = False
        
    async def start(self) -> None:
        """Start the background persistence task."""
        if self.is_running:
            return
        
        self.is_running = True
        self.flush_task = asyncio.create_task(self._flush_loop())
        logger.info("Voice event persistence started")
    
    async def stop(self) -> None:
        """Stop the background persistence task and flush remaining events."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining events
        await self._flush_queue()
        logger.info("Voice event persistence stopped")
    
    async def persist_event(self, event: RealtimeEvent) -> None:
        """
        Queue an event for persistence.
        
        Args:
            event: RealtimeEvent to persist
        """
        if not self.is_running:
            logger.warning("Event persistence not running, dropping event")
            return
        
        try:
            await self.event_queue.put(event)
        except asyncio.QueueFull:
            logger.warning("Event queue full, dropping event")
    
    async def _flush_loop(self) -> None:
        """Background task to flush events periodically."""
        while self.is_running:
            try:
                await asyncio.sleep(self.flush_interval_seconds)
                await self._flush_queue()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")
    
    async def _flush_queue(self) -> None:
        """Flush queued events to database."""
        if not check_db_connection():
            logger.warning("Database not available, skipping event flush")
            return
        
        events = []
        while not self.event_queue.empty() and len(events) < self.batch_size:
            try:
                event = self.event_queue.get_nowait()
                events.append(event)
            except asyncio.QueueEmpty:
                break
        
        if not events:
            return
        
        try:
            await self._persist_events_batch(events)
            logger.debug(f"Persisted {len(events)} events")
        except Exception as e:
            logger.error(f"Failed to persist events: {e}")
            # Re-queue events on failure
            for event in events:
                try:
                    await self.event_queue.put(event)
                except asyncio.QueueFull:
                    logger.warning("Failed to re-queue event after persistence failure")
    
    async def _persist_events_batch(self, events: list[RealtimeEvent]) -> None:
        """
        Persist a batch of events to database.
        
        Args:
            events: List of RealtimeEvent objects
        """
        if not events:
            return
        
        with db_session() as db:
            for event in events:
                event_dict = event.to_dict()
                
                # Extract fields for database
                hospital_id = event_dict.get("data", {}).get("hospital_id")
                agent_id = event_dict.get("data", {}).get("agent_id")
                call_id = event_dict.get("call_id")
                session_id = event_dict.get("session_id")
                stream_sid = event_dict.get("stream_sid")
                event_type = event_dict.get("event_type")
                metadata = event_dict.get("data", {})
                latency_ms = event_dict.get("latency_ms")
                provider = event_dict.get("data", {}).get("provider")
                
                # Insert event
                db.execute(
                    text("""
                        INSERT INTO voice_call_events 
                        (hospital_id, agent_id, call_id, session_id, stream_sid, event_type, 
                         metadata, latency_ms, provider, status, created_at)
                        VALUES 
                        (:hospital_id, :agent_id, :call_id, :session_id, :stream_sid, :event_type,
                         :metadata, :latency_ms, :provider, :status, :created_at)
                    """),
                    {
                        "hospital_id": hospital_id,
                        "agent_id": agent_id,
                        "call_id": call_id,
                        "session_id": session_id,
                        "stream_sid": stream_sid,
                        "event_type": event_type,
                        "metadata": metadata,
                        "latency_ms": latency_ms,
                        "provider": provider,
                        "status": "completed",
                        "created_at": datetime.utcnow(),
                    },
                )
    
    async def persist_conversation_turn(
        self,
        hospital_id: str,
        call_id: str,
        turn_index: int,
        speaker: str,
        text: str,
        language: str,
        interrupted: bool = False,
        provider: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp_start: Optional[datetime] = None,
        timestamp_end: Optional[datetime] = None,
    ) -> None:
        """
        Persist a conversation turn.
        
        Args:
            hospital_id: Hospital UUID
            call_id: Call UUID
            turn_index: Turn sequence number
            speaker: Speaker identifier (user/ai)
            text: Transcript text
            language: Language code
            interrupted: Whether turn was interrupted
            provider: Provider name
            metadata: Additional metadata
            timestamp_start: Turn start time
            timestamp_end: Turn end time
        """
        if not check_db_connection():
            logger.warning("Database not available, skipping conversation turn persistence")
            return
        
        try:
            with db_session() as db:
                db.execute(
                    text("""
                        INSERT INTO conversation_turns 
                        (hospital_id, call_id, turn_index, speaker, text, redacted_text, 
                         language, interrupted, provider, metadata, timestamp_start, timestamp_end, created_at)
                        VALUES 
                        (:hospital_id, :call_id, :turn_index, :speaker, :text, :text,
                         :language, :interrupted, :provider, :metadata, :timestamp_start, :timestamp_end, :created_at)
                    """),
                    {
                        "hospital_id": hospital_id,
                        "call_id": call_id,
                        "turn_index": turn_index,
                        "speaker": speaker,
                        "text": text,
                        "language": language,
                        "interrupted": interrupted,
                        "provider": provider,
                        "metadata": metadata or {},
                        "timestamp_start": timestamp_start,
                        "timestamp_end": timestamp_end,
                        "created_at": datetime.utcnow(),
                    },
                )
            logger.debug(f"Persisted conversation turn: {speaker} - {text[:50]}...")
        except Exception as e:
            logger.error(f"Failed to persist conversation turn: {e}")


# Global persistence instance
voice_event_persistence = VoiceEventPersistence()
