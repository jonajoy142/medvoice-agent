"""Real-time voice runtime pipeline for STT → LLM → TTS."""

import asyncio
import base64
import logging
import time
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Dict, Any
from enum import Enum

from app.stt.base import StreamingSTTProvider, StreamingSTTRequest, PartialTranscript
from app.tts.base import StreamingTTSProvider, StreamingTTSRequest, AudioChunk
from app.llm.base import StreamingLLMProvider, StreamingLLMRequest, TokenChunk
from app.voice.audio.converter import AudioConverter

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    """States of the voice runtime pipeline."""
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    GENERATING = "generating"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class PipelineMetrics:
    """Metrics for pipeline performance tracking."""
    stt_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    tts_latency_ms: float = 0.0
    total_turn_latency_ms: float = 0.0
    stt_provider: str = ""
    llm_provider: str = ""
    tts_provider: str = ""


@dataclass
class VoiceRuntimePipeline:
    """Real-time voice runtime pipeline for STT → LLM → TTS."""
    
    stt_provider: StreamingSTTProvider
    llm_provider: StreamingLLMProvider
    tts_provider: StreamingTTSProvider
    
    # Configuration
    language: str = "en-IN"
    voice: str = "alloy"
    system_prompt: str = "You are a helpful AI assistant. Be concise and friendly."
    audio_format: str = "mulaw"  # "mulaw" or "pcm16"
    
    # State
    state: PipelineState = PipelineState.IDLE
    conversation_history: list[Dict[str, str]] = field(default_factory=list)
    current_transcript: str = ""
    cancellation_token: Optional[asyncio.Event] = field(default_factory=asyncio.Event)
    
    # Race condition protection
    processing_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    state_lock: asyncio.Lock = field(default_factory=asyncio.Lock)  # Protect state transitions
    cancellation_lock: asyncio.Lock = field(default_factory=asyncio.Lock)  # Protect cancellation operations
    
    # Metrics
    metrics: PipelineMetrics = field(default_factory=PipelineMetrics)
    
    def __post_init__(self):
        """Initialize pipeline after creation."""
        self.metrics.stt_provider = self.stt_provider.name
        self.metrics.llm_provider = self.llm_provider.name
        self.metrics.tts_provider = self.tts_provider.name
    
    async def process_audio_turn(
        self,
        audio_bytes: bytes,
        call_id: str,
        session_id: str,
    ) -> AsyncIterator[bytes]:
        """
        Process a complete audio turn: STT → LLM → TTS.
        
        Yields audio chunks ready to send to Exotel.
        Uses lock to prevent race conditions between concurrent turns.
        """
        # Acquire lock to prevent concurrent processing
        async with self.processing_lock:
            # Acquire state lock for state transition
            async with self.state_lock:
                turn_start = time.perf_counter()
                self.state = PipelineState.TRANSCRIBING
                self.cancellation_token.clear()
            
            logger.info(f"[{call_id}] Starting audio turn")
            
            try:
                # Step 1: STT - Transcribe audio
                async with self.state_lock:
                    self.state = PipelineState.TRANSCRIBING
                stt_start = time.perf_counter()
                
                transcript = ""
                try:
                    async for partial in self.stt_provider.transcribe_stream(
                        StreamingSTTRequest(
                            audio_bytes=audio_bytes,
                            language=self.language,
                        )
                    ):
                        if self.cancellation_token.is_set():
                            logger.warning(f"[{call_id}] STT cancelled")
                            break
                        transcript = partial.text
                        if partial.is_final:
                            break
                except Exception as e:
                    logger.error(f"[{call_id}] STT failed: {e}")
                    transcript = ""  # Fallback to empty transcript
                
                self.metrics.stt_latency_ms = round((time.perf_counter() - stt_start) * 1000, 2)
                logger.info(f"[{call_id}] STT complete: '{transcript}' ({self.metrics.stt_latency_ms}ms)")
                
                if not transcript:
                    logger.warning(f"[{call_id}] Empty transcript, skipping turn")
                    return
                
                # Step 2: LLM - Generate response with cancellation token
                async with self.state_lock:
                    self.state = PipelineState.GENERATING
                llm_start = time.perf_counter()
                
                llm_response = ""
                try:
                    async for chunk in self.llm_provider.generate_stream(
                        StreamingLLMRequest(
                            user_text=transcript,
                            system_prompt=self.system_prompt,
                            conversation_history=self.conversation_history,
                            cancellation_token=self.cancellation_token,
                        )
                    ):
                        if self.cancellation_token.is_set():
                            logger.warning(f"[{call_id}] LLM cancelled")
                            break
                        llm_response += chunk.text
                        if chunk.is_final:
                            break
                except Exception as e:
                    logger.error(f"[{call_id}] LLM failed: {e}")
                    llm_response = "I'm sorry, I couldn't process that. Could you please repeat?"  # Fallback response
                
                self.metrics.llm_latency_ms = round((time.perf_counter() - llm_start) * 1000, 2)
                logger.info(f"[{call_id}] LLM complete: '{llm_response}' ({self.metrics.llm_latency_ms}ms)")
                
                # Update conversation history
                self.conversation_history.append({"role": "user", "content": transcript})
                self.conversation_history.append({"role": "assistant", "content": llm_response})
                
                # Keep history manageable
                if len(self.conversation_history) > 10:
                    self.conversation_history = self.conversation_history[-10:]
                
                # Step 3: TTS - Synthesize audio with cancellation token
                async with self.state_lock:
                    self.state = PipelineState.SPEAKING
                tts_start = time.perf_counter()
                
                try:
                    async for audio_chunk in self.tts_provider.synthesize_stream(
                        StreamingTTSRequest(
                            text=llm_response,
                            language=self.language,
                            voice=self.voice,
                            cancellation_token=self.cancellation_token,
                        )
                    ):
                        if self.cancellation_token.is_set():
                            logger.warning(f"[{call_id}] TTS cancelled")
                            break
                        
                        # Convert audio format if needed
                        try:
                            converted_audio = AudioConverter.ensure_exotel_format(
                                audio_chunk.audio_bytes,
                                source_format="pcm16",  # OpenAI returns PCM
                                target_format=self.audio_format,
                            )
                        except Exception as e:
                            logger.error(f"[{call_id}] Audio conversion failed: {e}")
                            converted_audio = audio_chunk.audio_bytes  # Use original if conversion fails
                        
                        # Encode to base64 for Exotel
                        encoded_audio = base64.b64encode(converted_audio).decode("ascii")
                        
                        yield encoded_audio.encode("utf-8")
                except Exception as e:
                    logger.error(f"[{call_id}] TTS failed: {e}")
                    # Fallback: send nothing, caller will hear silence
                    return
                
                self.metrics.tts_latency_ms = round((time.perf_counter() - tts_start) * 1000, 2)
                self.metrics.total_turn_latency_ms = round((time.perf_counter() - turn_start) * 1000, 2)
                
                logger.info(
                    f"[{call_id}] Turn complete - STT: {self.metrics.stt_latency_ms}ms, "
                    f"LLM: {self.metrics.llm_latency_ms}ms, TTS: {self.metrics.tts_latency_ms}ms, "
                    f"Total: {self.metrics.total_turn_latency_ms}ms"
                )
                
                async with self.state_lock:
                    self.state = PipelineState.IDLE
                
            except Exception as e:
                logger.error(f"[{call_id}] Pipeline error: {e}", exc_info=True)
                async with self.state_lock:
                    self.state = PipelineState.ERROR
                raise
    
    def cancel_current_turn(self) -> None:
        """Cancel the current audio turn (for interruption)."""
        # Use cancellation lock to prevent race conditions
        # This is a synchronous method, so we can't use async lock here
        # Instead, we rely on the atomic nature of Event.set()
        if self.cancellation_token and not self.cancellation_token.is_set():
            self.cancellation_token.set()
            logger.info("Pipeline turn cancelled")
        else:
            logger.warning("Pipeline turn already cancelled or no cancellation token")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current pipeline metrics."""
        return {
            "stt_latency_ms": self.metrics.stt_latency_ms,
            "llm_latency_ms": self.metrics.llm_latency_ms,
            "tts_latency_ms": self.metrics.tts_latency_ms,
            "total_turn_latency_ms": self.metrics.total_turn_latency_ms,
            "stt_provider": self.metrics.stt_provider,
            "llm_provider": self.metrics.llm_provider,
            "tts_provider": self.metrics.tts_provider,
            "state": self.state.value,
            "conversation_turns": len(self.conversation_history) // 2,
        }
    
    def reset(self) -> None:
        """Reset pipeline state for new call."""
        self.state = PipelineState.IDLE
        self.conversation_history = []
        self.current_transcript = ""
        self.cancellation_token = asyncio.Event()
        self.metrics = PipelineMetrics(
            stt_provider=self.stt_provider.name,
            llm_provider=self.llm_provider.name,
            tts_provider=self.tts_provider.name,
        )
