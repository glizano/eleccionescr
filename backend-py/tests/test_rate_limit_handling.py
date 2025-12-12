"""
Tests for 429/rate limit handling.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState
from app.services.llm import generate_text
from app.services.retry import (
    extract_retry_delay,
    is_resource_exhausted_error,
    retry_with_exponential_backoff,
)


class TestRateLimitDetection:
    """Test rate limit error detection"""

    def test_detect_429_status_code(self):
        """Test detection via status_code attribute"""
        error = Exception("Rate limited")
        error.status_code = 429
        assert is_resource_exhausted_error(error)

    def test_detect_429_in_response(self):
        """Test detection via response.status_code"""
        error = Exception("Rate limited")
        error.response = MagicMock(status_code=429)
        assert is_resource_exhausted_error(error)

    def test_detect_resource_exhausted_message(self):
        """Test detection via message content"""
        error = Exception("RESOURCE_EXHAUSTED: quota exceeded")
        assert is_resource_exhausted_error(error)

    def test_detect_429_in_message(self):
        """Test detection via 429 in message"""
        error = Exception("Error 429: too many requests")
        assert is_resource_exhausted_error(error)

    def test_non_rate_limit_error(self):
        """Test that other errors are not detected as rate limits"""
        error = Exception("Some other error")
        assert not is_resource_exhausted_error(error)


class TestRetryDelayExtraction:
    """Test retry delay extraction from error messages"""

    def test_extract_delay_from_retry_message(self):
        """Test extracting delay from 'retry in Xs' message"""
        error = Exception("Please retry in 52.120115668s")
        delay = extract_retry_delay(error)
        assert delay == pytest.approx(52.120115668)

    def test_extract_delay_integer_seconds(self):
        """Test extracting integer seconds"""
        error = Exception("Please retry in 30s")
        delay = extract_retry_delay(error)
        assert delay == 30.0

    def test_no_delay_in_message(self):
        """Test when no delay is present"""
        error = Exception("Rate limit exceeded")
        delay = extract_retry_delay(error)
        assert delay is None


class TestRetryLogic:
    """Test retry with exponential backoff"""

    def test_success_on_first_attempt(self):
        """Test that successful calls don't retry"""
        mock_func = MagicMock(return_value="success")

        result = retry_with_exponential_backoff(mock_func, max_attempts=3, initial_delay=0.1)

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_on_rate_limit(self):
        """Test retry on rate limit error"""
        mock_func = MagicMock()
        # Fail twice, then succeed
        mock_func.side_effect = [Exception("RESOURCE_EXHAUSTED"), Exception("429"), "success"]

        with patch("time.sleep"):  # Mock sleep to speed up test
            result = retry_with_exponential_backoff(mock_func, max_attempts=3, initial_delay=0.1)

        assert result == "success"
        assert mock_func.call_count == 3

    def test_exhaust_retries(self):
        """Test that retries are exhausted"""
        mock_func = MagicMock(side_effect=Exception("RESOURCE_EXHAUSTED"))

        with patch("time.sleep"), pytest.raises(Exception, match="RESOURCE_EXHAUSTED"):
            retry_with_exponential_backoff(mock_func, max_attempts=3, initial_delay=0.1)

        assert mock_func.call_count == 3

    def test_non_retryable_error_raises_immediately(self):
        """Test that non-rate-limit errors don't retry"""
        mock_func = MagicMock(side_effect=ValueError("Invalid input"))

        with pytest.raises(ValueError, match="Invalid input"):
            retry_with_exponential_backoff(mock_func, max_attempts=3, initial_delay=0.1)

        # Should only call once, not retry
        assert mock_func.call_count == 1


class TestCircuitBreaker:
    """Test circuit breaker pattern"""

    def test_circuit_closed_initially(self):
        """Test circuit starts in closed state"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10)
        assert cb.state == CircuitState.CLOSED

    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10)

        def failing_func():
            raise RuntimeError("Service error")

        # Trigger failures up to threshold
        for _ in range(3):
            with pytest.raises(RuntimeError):
                cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

    def test_circuit_blocks_when_open(self):
        """Test that open circuit blocks calls"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10)

        def failing_func():
            raise RuntimeError("Service error")

        # Trigger failures to open circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

        # Next call should be blocked
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(failing_func)

    def test_successful_call_resets_counter(self):
        """Test that success resets failure counter"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10)

        def sometimes_failing():
            if cb.failure_count < 2:
                raise RuntimeError("Temporary error")
            return "success"

        # Two failures
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("err")))

        assert cb.failure_count == 2

        # Success should reset
        result = cb.call(lambda: "success")
        assert result == "success"
        assert cb.failure_count == 0


class TestLLMServiceIntegration:
    """Integration tests for LLM service with 429 handling"""

    @patch("app.services.llm.get_llm")
    def test_generate_text_handles_rate_limit(self, mock_get_llm):
        """Test that generate_text handles rate limits gracefully"""
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("RESOURCE_EXHAUSTED: quota exceeded")
        mock_get_llm.return_value = mock_llm

        with patch("time.sleep"):  # Speed up retries
            result = generate_text("Test prompt")

        assert "ocupado" in result.lower() or "429" in result

    @patch("app.services.llm.get_llm")
    def test_generate_text_with_timeout(self, mock_get_llm):
        """Test timeout handling (skipped on Windows)"""
        import platform

        if platform.system() == "Windows":
            pytest.skip("Timeout test not supported on Windows")

        mock_llm = MagicMock()

        def slow_invoke(*args, **kwargs):
            import time

            time.sleep(100)  # Very slow

        mock_llm.invoke.side_effect = slow_invoke
        mock_get_llm.return_value = mock_llm

        # Should timeout
        with patch("app.config.settings.llm_timeout_seconds", 1):
            result = generate_text("Test prompt")

        assert "tiempo" in result.lower() or "timeout" in result.lower()
