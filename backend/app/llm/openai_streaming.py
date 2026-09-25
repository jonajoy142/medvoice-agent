"""OpenAI streaming LLM provider for real-time text generation."""

from dataclasses import dataclass
from typing import AsyncIterator

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.retry import retry_with_backoff, RetryConfig
from app.llm.base import StreamingLLMProvider, StreamingLLMRequest, TokenChunk


@dataclass
class OpenAIStreamingLLMProvider(StreamingLLMProvider):
    """OpenAI streaming LLM provider for real-time text generation."""
    
    name: str = "openai_streaming"
    
    def __init__(self):
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI streaming LLM.")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def generate_stream(
        self, request: StreamingLLMRequest
    ) -> AsyncIterator[TokenChunk]:
        """
        Stream LLM response using OpenAI's streaming API with retry logic.
        """
        async def _generate():
            # Check for cancellation before starting
            if request.cancellation_token and request.cancellation_token.is_set():
                return iter([TokenChunk(text="", is_final=True, chunk_index=0)])
            
            # Build messages from conversation history
            messages = [
                {"role": "system", "content": request.system_prompt},
            ]
            
            # Add conversation history
            for msg in request.conversation_history:
                messages.append(msg)
            
            # Add current user message
            messages.append({"role": "user", "content": request.user_text})
            
            # Stream response
            stream = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                temperature=0.7,
                max_tokens=300,
                stream=True,
            )
            return stream
        
        try:
            # Use retry with exponential backoff for the initial call
            stream = await retry_with_backoff(
                _generate,
                config=RetryConfig(max_retries=2, base_delay_seconds=0.5),
                cancellation_token=request.cancellation_token,
            )
            
            chunk_index = 0
            async for chunk in stream:
                # Check for cancellation during streaming
                if request.cancellation_token and request.cancellation_token.is_set():
                    # Stop streaming and yield final empty chunk
                    yield TokenChunk(
                        text="",
                        is_final=True,
                        chunk_index=chunk_index,
                    )
                    return
                
                if chunk.choices[0].delta.content:
                    yield TokenChunk(
                        text=chunk.choices[0].delta.content,
                        is_final=False,
                        chunk_index=chunk_index,
                    )
                    chunk_index += 1
            
            # Final chunk
            yield TokenChunk(
                text="",
                is_final=True,
                chunk_index=chunk_index,
            )
            
        except Exception as e:
            # Yield error chunk
            yield TokenChunk(
                text="",
                is_final=True,
                chunk_index=0,
            )
            raise
    
    def is_available(self) -> bool:
        return bool(settings.openai_api_key)
