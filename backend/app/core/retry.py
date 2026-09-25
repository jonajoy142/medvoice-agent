"""Retry logic with exponential backoff for provider calls."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, TypeVar, Optional, Any
from functools import wraps


T = TypeVar('T')

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay_seconds: float = 0.5,
        max_delay_seconds: float = 10.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.exponential_base = exponential_base
        self.jitter = jitter


async def retry_with_backoff(
    func: Callable[..., T],
    config: Optional[RetryConfig] = None,
    cancellation_token: Optional[asyncio.Event] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> T:
    """
    Execute function with exponential backoff retry.
    
    Args:
        func: Async function to retry
        config: Retry configuration
        cancellation_token: Optional cancellation token
        on_retry: Callback called on each retry attempt
        
    Returns:
        Function result
        
    Raises:
        Last exception if all retries exhausted
    """
    if config is None:
        config = RetryConfig()
    
    last_exception: Optional[Exception] = None
    
    for attempt in range(config.max_retries + 1):
        # Check cancellation before attempt
        if cancellation_token and cancellation_token.is_set():
            logger.info("Operation cancelled before attempt")
            raise asyncio.CancelledError("Operation cancelled")
        
        try:
            return await func()
        except Exception as e:
            last_exception = e
            
            # Don't retry non-retryable errors
            if _is_non_retryable_error(e):
                logger.warning(f"Non-retryable error: {type(e).__name__}: {e}")
                raise
            
            # Don't retry if this was the last attempt
            if attempt == config.max_retries:
                logger.error(f"All {config.max_retries} retries exhausted for {func.__name__}")
                raise
            
            # Calculate delay with exponential backoff
            delay = min(
                config.base_delay_seconds * (config.exponential_base ** attempt),
                config.max_delay_seconds
            )
            
            # Add jitter if enabled
            if config.jitter:
                import random
                delay = delay * (0.5 + random.random() * 0.5)
            
            logger.warning(
                f"Attempt {attempt + 1}/{config.max_retries + 1} failed for {func.__name__}: "
                f"{type(e).__name__}: {e}. Retrying in {delay:.2f}s"
            )
            
            # Call retry callback
            if on_retry:
                on_retry(attempt + 1, e)
            
            # Wait before retry
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                logger.info("Retry cancelled during backoff")
                raise
    
    # This should never be reached, but type checker needs it
    raise last_exception or RuntimeError("Retry logic failed")


def _is_non_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is non-retryable.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error should not be retried
    """
    # Authentication errors
    if "401" in str(error) or "403" in str(error):
        return True
    
    # Not found errors
    if "404" in str(error):
        return True
    
    # Validation errors
    if "validation" in str(error).lower() or "invalid" in str(error).lower():
        return True
    
    # Rate limit errors (429) are retryable
    # Timeout errors are retryable
    # Server errors (5xx) are retryable
    
    return False


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        config: Retry configuration
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            cancellation_token = kwargs.pop('cancellation_token', None)
            return await retry_with_backoff(
                lambda: func(*args, **kwargs),
                config=config,
                cancellation_token=cancellation_token,
            )
        return wrapper
    return decorator
