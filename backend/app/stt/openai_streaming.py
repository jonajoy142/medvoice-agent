"""OpenAI streaming STT provider for real-time transcription."""

import base64
import time
from dataclasses import dataclass
from typing import AsyncIterator

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.retry import retry_with_backoff, RetryConfig
from app.stt.base import StreamingSTTProvider, StreamingSTTRequest, PartialTranscript


@dataclass
class OpenAIStreamingSTTProvider(StreamingSTTProvider):
    """OpenAI Whisper streaming STT provider for real-time transcription."""
    
    name: str = "openai_whisper_streaming"
    
    def __init__(self):
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI streaming STT.")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def transcribe_stream(
        self, request: StreamingSTTRequest
    ) -> AsyncIterator[PartialTranscript]:
        """
        Stream transcription using OpenAI Whisper with retry logic.
        
        Note: OpenAI Whisper doesn't support true streaming, so we'll use
        the standard API with fast turnaround. For true streaming, consider
        using a provider like Deepgram or AssemblyAI.
        """
        started = time.perf_counter()
        
        async def _transcribe():
            # Convert audio bytes to base64 for OpenAI API
            audio_base64 = base64.b64encode(request.audio_bytes).decode("utf-8")
            
            # Create a temporary file-like object from base64
            import io
            audio_file = io.BytesIO(base64.b64decode(audio_base64))
            audio_file.name = "audio.webm"
            
            # Transcribe using OpenAI Whisper
            response = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=request.language.split("-")[0] if "-" in request.language else request.language,
                response_format="text",
                temperature=0.0,
            )
            return response
        
        try:
            # Use retry with exponential backoff
            response = await retry_with_backoff(
                _transcribe,
                config=RetryConfig(max_retries=2, base_delay_seconds=0.5),
                cancellation_token=getattr(request, 'cancellation_token', None),
            )
            
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            
            # Yield as final result (no partial results with current Whisper API)
            yield PartialTranscript(
                text=response,
                is_final=True,
                confidence=None,  # Whisper doesn't provide confidence
                language=request.language,
            )
            
        except Exception as e:
            # Yield error as partial transcript
            yield PartialTranscript(
                text="",
                is_final=True,
                confidence=0.0,
                language=request.language,
            )
            raise
