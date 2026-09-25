"""Exotel VoiceBot WebSocket handler for real-time bidirectional audio streaming."""

import asyncio
import base64
import json
import logging
import uuid
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect, status

from app.core.config import settings
from app.stt import get_streaming_stt_provider
from app.tts import get_streaming_tts_provider
from app.llm import get_streaming_llm_provider
from app.services.agent_config_service import agent_config_service
from app.voice.runtime.pipeline import VoiceRuntimePipeline
from app.voice.session.lifecycle import voice_session_manager, SessionLifecycleState
from app.voice.events.persistence import voice_event_persistence
from app.voice.runtime.logger import VoiceRuntimeLogger, CallContext
from app.voice.vad.detector import VoiceActivityDetector, VADConfig
from app.voice.state.manager import AIStateManager, AIState
from app.voice.events.system import RealtimeEventBus, VoiceEventEmitter, EventType

logger = logging.getLogger(__name__)


class ExotelVoiceBotHandler:
    """Handles Exotel VoiceBot WebSocket connections for bidirectional audio streaming."""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.account_sid: Optional[str] = None
        self.from_number: Optional[str] = None
        self.to_number: Optional[str] = None
        self.media_format: Dict[str, Any] = {}
        self.custom_parameters: Dict[str, Any] = {}
        self.sequence_number = 0
        self.is_connected = False
        
        # Voice session lifecycle
        self.voice_session = voice_session_manager.create_session(
            hospital_id=self.custom_parameters.get("hospital_id"),
            agent_id=self.custom_parameters.get("agent_id"),
            from_number=self.from_number,
            to_number=self.to_number,
        )
        self.session_id = self.voice_session.session_id
        
        # Voice runtime components
        self.voice_logger: VoiceRuntimeLogger = VoiceRuntimeLogger()
        self.pipeline: Optional[VoiceRuntimePipeline] = None
        
        # VAD and state management
        self.vad: VoiceActivityDetector = VoiceActivityDetector(VADConfig())
        self.ai_state: AIStateManager = AIStateManager()
        
        # Audio buffering for turn detection
        self.audio_buffer: bytearray = bytearray()
        self.audio_buffer_start_time: Optional[float] = None
        self.is_processing_turn: bool = False
        self.silence_threshold_ms: int = 800  # 800ms of silence triggers turn end
        
        # Barge-in detection
        self.barge_in_cooldown_ms: int = 200  # Minimum time between barge-in attempts
        self.last_barge_in_time: Optional[float] = None
        
        # Event system
        self.event_bus: RealtimeEventBus = RealtimeEventBus()
        self.event_emitter: VoiceEventEmitter = VoiceEventEmitter(self.event_bus, session_id=self.session_id)
        
        # Connect event bus to persistence
        self._setup_event_persistence()
    
    def _setup_event_persistence(self) -> None:
        """Subscribe event bus to async persistence."""
        def event_persistence_callback(event):
            asyncio.create_task(voice_event_persistence.persist_event(event))
        
        self.event_bus.subscribe(event_persistence_callback)
    
    async def connect(self) -> None:
        """Accept WebSocket connection and authenticate."""
        await self.websocket.accept()
        self.is_connected = True
        logger.info(f"WebSocket connection accepted")
        
    async def disconnect(self) -> None:
        """Clean disconnect with session cleanup."""
        self.is_connected = False
        if self.stream_sid:
            logger.info(f"Disconnecting stream {self.stream_sid}")
        
        # Cleanup session
        await voice_session_manager.cleanup_session(self.session_id)
        
        try:
            await self.websocket.close()
        except Exception:
            pass
            
    async def send_media(self, audio_payload: str) -> None:
        """Send audio data to caller (base64-encoded PCM)."""
        if not self.is_connected or not self.stream_sid:
            logger.warning("Cannot send media: not connected or no stream_sid")
            return
            
        message = {
            "event": "media",
            "stream_sid": self.stream_sid,
            "media": {
                "payload": audio_payload
            }
        }
        await self.websocket.send_json(message)
        
    async def send_clear(self) -> None:
        """Clear audio buffer (stop current audio)."""
        if not self.is_connected or not self.stream_sid:
            return
            
        message = {
            "event": "clear",
            "stream_sid": self.stream_sid
        }
        await self.websocket.send_json(message)
        
    async def handle_start(self, data: Dict[str, Any]) -> None:
        """Handle start event - initialize session with call metadata."""
        start_data = data.get("start", {})
        self.stream_sid = start_data.get("stream_sid")
        self.call_sid = start_data.get("call_sid")
        self.account_sid = start_data.get("account_sid")
        self.from_number = start_data.get("from")
        self.to_number = start_data.get("to")
        self.custom_parameters = start_data.get("custom_parameters", {})
        self.media_format = start_data.get("media_format", {})
        
        # Update voice session with call metadata
        self.voice_session.call_id = self.call_sid
        self.voice_session.set_stream_sid(self.stream_sid)
        self.voice_session.from_number = self.from_number
        self.voice_session.to_number = self.to_number
        self.voice_session.transition_to(SessionLifecycleState.CONNECTED)
        
        # Initialize voice logger with call context
        call_context = CallContext(
            call_id=self.call_sid or "unknown",
            session_id=self.session_id,
            stream_sid=self.stream_sid,
            from_number=self.from_number,
            to_number=self.to_number,
            tenant_id=self.custom_parameters.get("hospital_id"),
            agent_id=self.custom_parameters.get("agent_id"),
        )
        self.voice_logger.set_context(call_context)
        self.voice_logger.info("Call started via WebSocket")
        
        # Update event emitter context
        self.event_emitter.set_context(call_id=self.call_sid, stream_sid=self.stream_sid)
        self.event_emitter.emit_call_started(from_number=self.from_number, to_number=self.to_number)
        
        # Reset VAD and state manager
        self.vad.reset()
        self.ai_state.reset()
        self.ai_state.start_metrics_collection()
        
        # Set up state change callbacks
        def on_state_change(from_state: AIState, to_state: AIState):
            self.voice_logger.log_event(
                "state_change",
                {"from_state": from_state.value, "to_state": to_state.value}
            )
            
            # Emit structured event
            self.event_emitter.emit_state_change(from_state.value, to_state.value)
            
            # Update VAD with AI speaking state
            if to_state == AIState.SPEAKING:
                self.vad.set_ai_speaking_state(True)
            elif from_state == AIState.SPEAKING:
                self.vad.set_ai_speaking_state(False)
        
        def on_interruption():
            self.voice_logger.log_event("interruption", {"count": self.ai_state.interruption_count})
            
            # Emit structured event
            self.event_emitter.emit_interruption_started(reason="barge_in")
            
            # Send clear event to Exotel to stop audio
            asyncio.create_task(self.send_clear())
            # Complete interruption tracking
            self.ai_state.complete_interruption()
            
            # Emit completion event
            self.event_emitter.emit_interruption_completed(duration_ms=0.0, was_successful=True)
        
        self.ai_state.on_state_change = on_state_change
        self.ai_state.on_interruption = on_interruption
        
        # Load agent configuration
        agent_id = self.custom_parameters.get("agent_id")
        hospital_id = self.custom_parameters.get("hospital_id")
        
        try:
            if agent_id and hospital_id:
                agent_config = agent_config_service.load_agent_config(agent_id, hospital_id)
                self.voice_logger.info(f"Loaded agent configuration: {agent_config['name']}")
            else:
                agent_config = agent_config_service.get_default_config()
                self.voice_logger.info("Using default agent configuration")
        except Exception as e:
            self.voice_logger.log_error("agent_config_load", e)
            # Fall back to default config on error
            agent_config = agent_config_service.get_default_config()
            self.voice_logger.warning("Falling back to default agent configuration")
        
        # Initialize voice runtime pipeline with agent configuration
        try:
            self.pipeline = VoiceRuntimePipeline(
                stt_provider=get_streaming_stt_provider(agent_config),
                llm_provider=get_streaming_llm_provider(agent_config),
                tts_provider=get_streaming_tts_provider(agent_config),
                language=agent_config["language"],
                voice=agent_config.get("voice_name", "alloy"),
                system_prompt=agent_config["system_prompt"],
                audio_format="mulaw" if self.media_format.get("encoding") == "audio/x-mulaw" else "pcm16",
            )
            self.voice_logger.info("Voice runtime pipeline initialized")
        except Exception as e:
            self.voice_logger.log_error("pipeline_init", e)
            raise
        
        logger.info(
            f"Stream started: stream_sid={self.stream_sid}, "
            f"call_sid={self.call_sid}, from={self.from_number}, to={self.to_number}, "
            f"media_format={self.media_format}"
        )
        
    async def handle_media(self, data: Dict[str, Any]) -> Optional[str]:
        """Handle incoming media event - buffer audio and detect turns with barge-in."""
        media_data = data.get("media", {})
        payload = media_data.get("payload")
        chunk = media_data.get("chunk")
        timestamp = media_data.get("timestamp")
        
        if not payload:
            return None
            
        # Decode base64 audio payload
        try:
            audio_bytes = base64.b64decode(payload)
            logger.debug(f"Received media chunk {chunk}, timestamp={timestamp}, size={len(audio_bytes)} bytes")
            
            # Process audio through VAD for speech detection
            self.vad.process_audio_chunk(audio_bytes)
            
            # Check for barge-in (user speaking while AI is speaking)
            if self.vad.detect_barge_in() and self.ai_state.is_speaking():
                current_time = asyncio.get_event_loop().time()
                
                # Check barge-in cooldown
                if self.last_barge_in_time is None or (current_time - self.last_barge_in_time) * 1000 >= self.barge_in_cooldown_ms:
                    # Check if barge-in duration meets threshold
                    barge_in_duration = self.vad.get_barge_in_duration_ms()
                    if barge_in_duration >= self.vad.barge_in_duration_threshold_ms:
                        # Get current energy and VAD state for metrics
                        speech_energy = sum(self.vad.energy_buffer) / len(self.vad.energy_buffer) if self.vad.energy_buffer else 0.0
                        vad_state = self.vad.state.value
                        
                        # User is interrupting
                        if self.ai_state.interrupt(reason="barge_in", speech_energy=speech_energy, vad_state=vad_state):
                            self.voice_logger.info(f"Barge-in detected ({barge_in_duration:.0f}ms), interrupting AI speech")
                            self.event_emitter.emit_barge_in_detected(energy=speech_energy, duration_ms=barge_in_duration)
                            self.last_barge_in_time = current_time
                            # Cancel current pipeline processing
                            if self.pipeline:
                                self.pipeline.cancel_current_turn()
            
            # Buffer audio for turn detection (only if not processing)
            if not self.is_processing_turn:
                self.audio_buffer.extend(audio_bytes)
                if self.audio_buffer_start_time is None:
                    self.audio_buffer_start_time = asyncio.get_event_loop().time()
            
            return audio_bytes
        except Exception as e:
            logger.error(f"Failed to decode audio payload: {e}")
            return None
    
    async def check_silence_timeout(self) -> bool:
        """Check if silence threshold has been reached to trigger turn processing."""
        if not self.audio_buffer_start_time or self.is_processing_turn:
            return False
        
        # Use VAD to determine if turn should end
        if self.vad.should_end_turn():
            return True
        
        # Fallback to time-based silence detection
        elapsed_ms = (asyncio.get_event_loop().time() - self.audio_buffer_start_time) * 1000
        return elapsed_ms >= self.silence_threshold_ms
    
    async def process_audio_turn(self) -> None:
        """Process buffered audio through STT → LLM → TTS pipeline with state management."""
        if not self.audio_buffer or not self.pipeline:
            return
        
        self.is_processing_turn = True
        audio_data = bytes(self.audio_buffer)
        self.audio_buffer.clear()
        self.audio_buffer_start_time = None
        
        self.voice_logger.info("Starting audio turn processing")
        self.event_emitter.emit_event(EventType.STATE_CHANGE, data={"state": "processing_turn"})
        
        # Transition to thinking state
        self.ai_state.start_thinking()
        
        try:
            # Process audio through pipeline
            async for audio_chunk in self.pipeline.process_audio_turn(
                audio_bytes=audio_data,
                call_id=self.call_sid or "unknown",
                session_id=self.session_id,
            ):
                # Check for interruption during audio sending
                if self.ai_state.current_state == AIState.INTERRUPTED:
                    self.voice_logger.info("Audio sending interrupted")
                    self.event_emitter.emit_cancellation_requested(reason="interruption")
                    break
                
                # Transition to speaking state on first chunk
                if self.ai_state.current_state == AIState.THINKING:
                    self.ai_state.start_speaking()
                    self.event_emitter.emit_state_change("thinking", "speaking")
                
                # Send audio chunk to caller
                await self.send_media(audio_chunk.decode("ascii"))
                self.voice_logger.log_audio_chunk(len(audio_chunk), 0)
                self.event_emitter.emit_tts_chunk_sent(chunk_index=0, chunk_size=len(audio_chunk))
            
            # Transition back to listening if not interrupted
            if self.ai_state.current_state != AIState.INTERRUPTED:
                self.ai_state.start_listening()
                self.event_emitter.emit_state_change(self.ai_state.current_state.value, "listening")
            
            self.voice_logger.info("Audio turn processing complete")
            self.event_emitter.emit_event(EventType.STATE_CHANGE, data={"state": "turn_complete"})
            
        except Exception as e:
            self.voice_logger.log_error("audio_turn", e)
            self.event_emitter.emit_error(error=str(e), component="audio_turn")
            # Send error fallback audio
            await self.send_clear()
            self.ai_state.start_listening()
        finally:
            self.is_processing_turn = False
            
    async def handle_dtmf(self, data: Dict[str, Any]) -> Optional[str]:
        """Handle DTMF key press event."""
        dtmf_data = data.get("dtmf", {})
        digit = dtmf_data.get("digit")
        logger.info(f"DTMF digit pressed: {digit}")
        return digit
        
    async def handle_stop(self, data: Dict[str, Any]) -> None:
        """Handle stop event - call ended."""
        logger.info(f"Stream stopped: stream_sid={self.stream_sid}")
        
        # Emit call ended event
        self.event_emitter.emit_call_ended()
        
        await self.disconnect()
        
    async def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process incoming WebSocket message and return structured event."""
        event_type = message.get("event")
        self.sequence_number = message.get("sequence_number", self.sequence_number + 1)
        
        if event_type == "start":
            await self.handle_start(message)
            return {
                "type": "start",
                "stream_sid": self.stream_sid,
                "call_sid": self.call_sid,
                "from": self.from_number,
                "to": self.to_number,
                "media_format": self.media_format,
                "custom_parameters": self.custom_parameters
            }
            
        elif event_type == "media":
            audio_bytes = await self.handle_media(message)
            return {
                "type": "media",
                "stream_sid": self.stream_sid,
                "audio_bytes": audio_bytes,
                "chunk": message.get("media", {}).get("chunk"),
                "timestamp": message.get("media", {}).get("timestamp")
            }
            
        elif event_type == "dtmf":
            digit = await self.handle_dtmf(message)
            return {
                "type": "dtmf",
                "stream_sid": self.stream_sid,
                "digit": digit
            }
            
        elif event_type == "stop":
            await self.handle_stop(message)
            return {
                "type": "stop",
                "stream_sid": self.stream_sid
            }
            
        else:
            logger.warning(f"Unknown event type: {event_type}")
            return None


async def exotel_voicebot_websocket(websocket: WebSocket) -> None:
    """
    Main WebSocket endpoint for Exotel VoiceBot integration.
    
    This endpoint handles:
    - WebSocket connection from Exotel
    - Bidirectional audio streaming
    - Call lifecycle events (start, media, dtmf, stop)
    - STT → LLM → TTS pipeline for real-time conversation
    """
    handler = ExotelVoiceBotHandler(websocket)
    
    try:
        await handler.connect()
        
        # Main message loop with silence detection
        while handler.is_connected:
            try:
                # Receive JSON message from Exotel with timeout for silence detection
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=0.1  # Check for silence every 100ms
                )
                logger.debug(f"Received message: {message.get('event')}")
                
                # Process message
                event = await handler.process_message(message)
                
                if event is None:
                    continue
                    
                # Handle different event types
                if event["type"] == "start":
                    logger.info("Call started - ready for audio streaming")
                    
                elif event["type"] == "media":
                    # Audio is buffered in handle_media
                    # Check if we should process the turn
                    if await handler.check_silence_timeout():
                        await handler.process_audio_turn()
                        
                elif event["type"] == "dtmf":
                    logger.info(f"DTMF: {event['digit']}")
                    
                elif event["type"] == "stop":
                    logger.info("Call ended")
                    break
                    
            except asyncio.TimeoutError:
                # Timeout is expected - check for silence
                if await handler.check_silence_timeout():
                    await handler.process_audio_turn()
                    
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected by client")
                break
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        # Process any remaining buffered audio
        if handler.audio_buffer:
            await handler.process_audio_turn()
        await handler.disconnect()
