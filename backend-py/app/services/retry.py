"""
Retry logic with exponential backoff for LLM calls.
"""

import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from app.config import settings
from app.utils.logging import sanitize_for_log

logger = logging.getLogger(__name__)

T = TypeVar("T")


def is_resource_exhausted_error(error: Exception) -> bool:
    """Return True when the exception corresponds to a 429/RESOURCE_EXHAUSTED."""

    # Direct status code check on the exception
    if getattr(error, "status_code", None) == 429:
        return True

    # Some SDKs nest the status code inside a response attribute
    response = getattr(error, "response", None)
    if getattr(response, "status_code", None) == 429:
        return True

    # OpenAI specific rate limit error
    try:  # pragma: no cover - defensive import
        from openai import RateLimitError  # type: ignore

        if isinstance(error, RateLimitError):
            return True
    except Exception:
        pass

    # Google Generative AI specific error
    try:  # pragma: no cover - defensive import
        from google.api_core.exceptions import ResourceExhausted  # type: ignore

        if isinstance(error, ResourceExhausted):
            return True
    except Exception:
        pass

    # Fallback to message inspection
    message = str(error).lower()
    return "resource_exhausted" in message or "429" in message


def extract_retry_delay(error: Exception) -> float | None:
    """
    Extract retry delay from error message if available.

    Google API often includes retry delay in the error response.
    """
    error_str = str(error)

    # Try to extract from "Please retry in X.Xs" pattern
    try:
        if "retry in" in error_str.lower():
            # Extract number before 's' or 'seconds'
            import re

            match = re.search(r"retry in (\d+\.?\d*)s", error_str, re.IGNORECASE)
            if match:
                return float(match.group(1))
    except Exception:
        pass

    # Try to extract from RetryInfo if available
    try:
        if hasattr(error, "__dict__") and "details" in str(error.__dict__):
            # Google API returns retry delay in metadata
            details = getattr(error, "details", [])
            for detail in details:
                if (
                    isinstance(detail, dict)
                    and detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo"
                ):
                    retry_delay = detail.get("retryDelay", "")
                    if retry_delay:
                        # Parse delay like "52s"
                        match = re.search(r"(\d+)", retry_delay)
                        if match:
                            return float(match.group(1))
    except Exception:
        pass

    return None


def retry_with_exponential_backoff(
    func: Callable[..., T],
    *args: Any,
    max_attempts: int | None = None,
    initial_delay: float | None = None,
    max_delay: float | None = None,
    exponential_base: float | None = None,
    **kwargs: Any,
) -> T:
    """
    Retry a function with exponential backoff on rate limit errors.

    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts (default from config)
        initial_delay: Initial delay in seconds (default from config)
        max_delay: Maximum delay in seconds (default from config)
        exponential_base: Base for exponential backoff (default from config)
        *args, **kwargs: Arguments to pass to func

    Returns:
        Result from func

    Raises:
        Exception: If all retries are exhausted or non-retryable error occurs
    """
    max_attempts = max_attempts or settings.llm_retry_max_attempts
    initial_delay = initial_delay or settings.llm_retry_initial_delay
    max_delay = max_delay or settings.llm_retry_max_delay
    exponential_base = exponential_base or settings.llm_retry_exponential_base

    last_exception = None

    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            # Only retry on rate limit errors
            if not is_resource_exhausted_error(e):
                logger.debug(f"Non-retryable error on attempt {attempt + 1}: {sanitize_for_log(str(e))}")
                raise

            # Don't sleep on last attempt
            if attempt == max_attempts - 1:
                logger.warning(
                    f"Rate limit retry exhausted after {max_attempts} attempts",
                    extra={"attempt": attempt + 1, "max_attempts": max_attempts},
                )
                raise

            # Check if error contains suggested retry delay
            suggested_delay = extract_retry_delay(e)

            if suggested_delay:
                # Use suggested delay but cap it at max_delay
                delay = min(suggested_delay, max_delay)
                logger.info(
                    f"Rate limited. Using API-suggested delay: {delay:.1f}s",
                    extra={"attempt": attempt + 1, "delay": delay, "suggested": True},
                )
            else:
                # Use exponential backoff
                delay = min(initial_delay * (exponential_base**attempt), max_delay)
                logger.info(
                    f"Rate limited. Retrying in {delay:.1f}s",
                    extra={"attempt": attempt + 1, "delay": delay, "suggested": False},
                )

            time.sleep(delay)

    # Should never reach here, but just in case
    raise last_exception or Exception("Retry logic error")
