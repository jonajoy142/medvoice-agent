"""OpenAI streaming TTS provider for real-time audio synthesis."""

import asyncio
import time
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.retry import retry_with_backoff, RetryConfig
from app.tts.base import StreamingTTSProvider, StreamingTTSRequest, AudioChunk


@dataclass
class OpenAIStreamingTTSProvider(StreamingTTSProvider):
    """OpenAI TTS streaming provider for real-time audio synthesis."""
    
    name: str = "openai_tts_streaming"
    
    def __init__(self):
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI streaming TTS.")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def synthesize_stream(
        self, request: StreamingTTSRequest
    ) -> AsyncIterator[AudioChunk]:
        """
        Stream TTS audio using OpenAI TTS API with retry logic.
        
        Note: OpenAI TTS doesn't support true streaming, so we'll chunk
        the response for incremental playback.
        """
        started = time.perf_counter()
        
        async def _synthesize():
            # Check for cancellation before starting
            if request.cancellation_token and request.cancellation_token.is_set():
                return None
            
            # Generate audio using OpenAI TTS
            response = await self.client.audio.speech.create(
                model="tts-1",
                voice=self._map_voice(request.voice),
                input=request.text,
                response_format="mp3",
                speed=request.speed,
            )
            return response.content
        
        try:
            # Use retry with exponential backoff
            audio_content = await retry_with_backoff(
                _synthesize,
                config=RetryConfig(max_retries=2, base_delay_seconds=0.5),
                cancellation_token=request.cancellation_token,
            )
            
            # Check for cancellation after generation
            if audio_content is None or (request.cancellation_token and request.cancellation_token.is_set()):
                yield AudioChunk(
                    audio_bytes=b"",
                    is_final=True,
                    chunk_index=0,
                )
                return
            
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            
            # Chunk the audio for streaming (e.g., 100ms chunks at 8kHz)
            chunk_size = 3200  # ~100ms at 8kHz PCM (adjust based on actual format)
            total_chunks = (len(audio_content) + chunk_size - 1) // chunk_size
            
            for i in range(total_chunks):
                # Check for cancellation before each chunk
                if request.cancellation_token and request.cancellation_token.is_set():
                    # Stop streaming and yield final empty chunk
                    yield AudioChunk(
                        audio_bytes=b"",
                        is_final=True,
                        chunk_index=i,
                    )
                    return
                
                start = i * chunk_size
                end = min(start + chunk_size, len(audio_content))
                chunk_bytes = audio_content[start:end]
                
                yield AudioChunk(
                    audio_bytes=chunk_bytes,
                    is_final=(i == total_chunks - 1),
                    chunk_index=i,
                )
                
                # Small delay to simulate streaming
                await asyncio.sleep(0.01)
            
        except Exception as e:
            # Yield empty chunk on error
            yield AudioChunk(
                audio_bytes=b"",
                is_final=True,
                chunk_index=0,
            )
            raise
    
    def _map_voice(self, voice: str) -> str:
        """Map custom voice names to OpenAI voices."""
        voice_mapping = {
            "female": "alloy",
            "male": "echo",
            "female_warm": "nova",
            "male_warm": "onyx",
            "female_calm": "shimmer",
        }
        return voice_mapping.get(voice.lower(), "alloy")
