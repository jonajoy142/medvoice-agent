"""Tests for retry logic with exponential backoff."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from app.core.retry import (
    retry_with_backoff,
    RetryConfig,
    with_retry,
    _is_non_retryable_error,
)


class TestRetryConfig:
    """Tests for RetryConfig."""
    
    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.base_delay_seconds == 0.5
        assert config.max_delay_seconds == 10.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
    
    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay_seconds=1.0,
            max_delay_seconds=30.0,
            exponential_base=3.0,
            jitter=False,
        )
        
        assert config.max_retries == 5
        assert config.base_delay_seconds == 1.0
        assert config.max_delay_seconds == 30.0
        assert config.exponential_base == 3.0
        assert config.jitter is False


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""
    
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test function succeeds on first attempt."""
        async def success_func():
            return "success"
        
        result = await retry_with_backoff(success_func)
        
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test function retries on failure and succeeds."""
        attempt_count = 0
        
        async def flaky_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise RuntimeError("Temporary failure")
            return "success"
        
        result = await retry_with_backoff(
            flaky_func,
            config=RetryConfig(max_retries=3, base_delay_seconds=0.01),
        )
        
        assert result == "success"
        assert attempt_count == 2
    
    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self):
        """Test function fails after max retries."""
        async def failing_func():
            raise RuntimeError("Persistent failure")
        
        with pytest.raises(RuntimeError, match="Persistent failure"):
            await retry_with_backoff(
                failing_func,
                config=RetryConfig(max_retries=2, base_delay_seconds=0.01),
            )
    
    @pytest.mark.asyncio
    async def test_cancellation_before_attempt(self):
        """Test cancellation before first attempt."""
        cancellation_token = asyncio.Event()
        cancellation_token.set()
        
        async def slow_func():
            await asyncio.sleep(10)
            return "success"
        
        with pytest.raises(asyncio.CancelledError):
            await retry_with_backoff(
                slow_func,
                cancellation_token=cancellation_token,
            )
    
    @pytest.mark.asyncio
    async def test_non_retryable_error(self):
        """Test non-retryable errors are not retried."""
        async def auth_error_func():
            raise RuntimeError("401 Unauthorized")
        
        with pytest.raises(RuntimeError, match="401 Unauthorized"):
            await retry_with_backoff(
                auth_error_func,
                config=RetryConfig(max_retries=3),
            )
    
    @pytest.mark.asyncio
    async def test_retry_callback(self):
        """Test retry callback is called."""
        callback_calls = []
        
        def on_retry(attempt, error):
            callback_calls.append((attempt, type(error).__name__))
        
        attempt_count = 0
        
        async def flaky_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise RuntimeError("Temporary failure")
            return "success"
        
        await retry_with_backoff(
            flaky_func,
            config=RetryConfig(max_retries=3, base_delay_seconds=0.01),
            on_retry=on_retry,
        )
        
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 1
        assert callback_calls[0][1] == "RuntimeError"


class TestIsNonRetryableError:
    """Tests for _is_non_retryable_error function."""
    
    def test_401_error_non_retryable(self):
        """Test 401 errors are non-retryable."""
        error = RuntimeError("401 Unauthorized")
        assert _is_non_retryable_error(error) is True
    
    def test_403_error_non_retryable(self):
        """Test 403 errors are non-retryable."""
        error = RuntimeError("403 Forbidden")
        assert _is_non_retryable_error(error) is True
    
    def test_404_error_non_retryable(self):
        """Test 404 errors are non-retryable."""
        error = RuntimeError("404 Not Found")
        assert _is_non_retryable_error(error) is True
    
    def test_validation_error_non_retryable(self):
        """Test validation errors are non-retryable."""
        error = RuntimeError("Validation failed")
        assert _is_non_retryable_error(error) is True
    
    def test_timeout_error_retryable(self):
        """Test timeout errors are retryable."""
        error = RuntimeError("Timeout")
        assert _is_non_retryable_error(error) is False
    
    def test_500_error_retryable(self):
        """Test 500 errors are retryable."""
        error = RuntimeError("500 Internal Server Error")
        assert _is_non_retryable_error(error) is False


class TestWithRetryDecorator:
    """Tests for with_retry decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Test decorator with successful function."""
        @with_retry(config=RetryConfig(max_retries=2, base_delay_seconds=0.01))
        async def success_func():
            return "success"
        
        result = await success_func()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_decorator_retry(self):
        """Test decorator retries on failure."""
        attempt_count = 0
        
        @with_retry(config=RetryConfig(max_retries=2, base_delay_seconds=0.01))
        async def flaky_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise RuntimeError("Temporary failure")
            return "success"
        
        result = await flaky_func()
        assert result == "success"
        assert attempt_count == 2
    
    @pytest.mark.asyncio
    async def test_decorator_with_cancellation_token(self):
        """Test decorator with cancellation token."""
        cancellation_token = asyncio.Event()
        cancellation_token.set()
        
        @with_retry(config=RetryConfig(max_retries=2))
        async def slow_func():
            await asyncio.sleep(10)
            return "success"
        
        with pytest.raises(asyncio.CancelledError):
            await slow_func(cancellation_token=cancellation_token)
