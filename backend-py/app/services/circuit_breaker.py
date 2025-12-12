"""
Circuit breaker pattern for LLM service resilience.
"""

import logging
import time
from enum import Enum
from threading import Lock

from app.config import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    When too many failures occur, opens the circuit and stops
    calling the service for a recovery period.
    """

    def __init__(
        self,
        failure_threshold: int | None = None,
        recovery_timeout: int | None = None,
    ):
        self.failure_threshold = failure_threshold or settings.circuit_breaker_failure_threshold
        self.recovery_timeout = recovery_timeout or settings.circuit_breaker_recovery_timeout

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self._lock = Lock()

    def call(self, func, *args, **kwargs):
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to func

        Returns:
            Result from func

        Raises:
            Exception: From func or CircuitBreakerOpen
        """
        with self._lock:
            if self.state == CircuitState.OPEN:
                # Check if recovery timeout passed
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    logger.info("Circuit breaker: Transitioning to HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                else:
                    remaining = self.recovery_timeout - (time.time() - self.last_failure_time)
                    logger.warning(
                        f"Circuit breaker OPEN. Service unavailable for {remaining:.1f}s more"
                    )
                    raise CircuitBreakerOpenError(
                        f"Service temporarily unavailable. Try again in {remaining:.1f}s"
                    )

        # Try to execute
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                logger.info("Circuit breaker: Service recovered, transitioning to CLOSED")
                self.state = CircuitState.CLOSED

            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                logger.warning("Circuit breaker: Recovery test failed, transitioning to OPEN")
                self.state = CircuitState.OPEN
            elif self.failure_count >= self.failure_threshold:
                logger.error(
                    f"Circuit breaker: Failure threshold ({self.failure_threshold}) "
                    f"reached, transitioning to OPEN"
                )
                self.state = CircuitState.OPEN

    def reset(self):
        """Reset circuit breaker to closed state"""
        with self._lock:
            self.failure_count = 0
            self.last_failure_time = None
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker manually reset to CLOSED")


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""

    pass


# Global circuit breaker instance for LLM calls
_llm_circuit_breaker = None
_circuit_breaker_lock = Lock()


def get_llm_circuit_breaker() -> CircuitBreaker:
    """Get or create global LLM circuit breaker"""
    global _llm_circuit_breaker

    if not settings.circuit_breaker_enabled:
        # Return a no-op circuit breaker
        class NoOpCircuitBreaker:
            def call(self, func, *args, **kwargs):
                return func(*args, **kwargs)

        return NoOpCircuitBreaker()

    with _circuit_breaker_lock:
        if _llm_circuit_breaker is None:
            _llm_circuit_breaker = CircuitBreaker()
            logger.info("Initialized LLM circuit breaker")

        return _llm_circuit_breaker
