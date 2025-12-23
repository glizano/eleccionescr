"""Langfuse integration for LLM observability and tracing."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from app.config import settings
from app.utils.logging import sanitize_for_log

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_langfuse_client():
    """Get Langfuse client (cached). Returns None if Langfuse is disabled."""
    if not settings.langfuse_enabled:
        logger.info("Langfuse is disabled")
        return None

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.warning("Langfuse keys not configured, disabling Langfuse")
        return None

    try:
        from langfuse import Langfuse

        client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        logger.info(f"Langfuse client initialized with host: {settings.langfuse_host}")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse client: {sanitize_for_log(str(e))}")
        return None


@contextmanager
def langfuse_trace(
    name: str,
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Generator[Any, None, None]:
    """
    Context manager for creating a Langfuse trace.

    Usage:
        with langfuse_trace("my-operation", user_id="user123") as trace:
            # Your code here
            if trace:
                span = trace.span(name="sub-operation")
                # ...
                span.end()

    Args:
        name: Name of the trace
        user_id: Optional user identifier
        session_id: Optional session identifier
        metadata: Optional additional metadata

    Yields:
        Langfuse trace object if enabled, None otherwise
    """
    client = get_langfuse_client()

    if client is None:
        yield None
        return

    try:
        trace = client.trace(
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata if metadata is not None else {},
        )
        yield trace
    except Exception as e:
        logger.error(f"Error creating Langfuse trace: {sanitize_for_log(str(e))}")
        yield None


def create_generation(
    trace: Any,
    name: str,
    model: str,
    input_text: str,
    output_text: str | None = None,
    metadata: dict[str, Any] | None = None,
    usage: dict[str, int] | None = None,
) -> Any:
    """
    Create a generation event on a trace for LLM calls.

    Args:
        trace: The parent Langfuse trace
        name: Name of the generation
        model: Model name used
        input_text: Input prompt text
        output_text: Optional output text from the model. This can be provided during
            creation or later via the generation's `.end(output=output_text)` method.
        metadata: Optional additional metadata
        usage: Optional token usage dict with 'prompt_tokens', 'completion_tokens', 'total_tokens'

    Returns:
        Langfuse generation object if successful, None otherwise
    """
    if trace is None:
        return None

    try:
        generation_kwargs = {
            "name": name,
            "model": model,
            "input": input_text,
            "output": output_text,
            "metadata": metadata if metadata is not None else {},
        }

        # Add usage information if provided
        if usage:
            generation_kwargs["usage"] = usage

        generation = trace.generation(**generation_kwargs)
        return generation
    except Exception as e:
        logger.error(f"Error creating Langfuse generation: {sanitize_for_log(str(e))}")
        return None


@contextmanager
def langfuse_span(
    trace: Any,
    name: str,
    metadata: dict[str, Any] | None = None,
    input_data: Any | None = None,
    level: str = "DEFAULT",
) -> Generator[Any, None, None]:
    """
    Context manager for creating a Langfuse span.

    Usage:
        with langfuse_span(trace, "my-operation", metadata={"key": "value"}) as span:
            # Your code here
            pass

    Args:
        trace: The parent Langfuse trace
        name: Name of the span
        metadata: Optional additional metadata
        input_data: Optional input data for the span
        level: Observation level (DEFAULT, DEBUG, WARNING, ERROR)

    Yields:
        Langfuse span object if trace is valid, None otherwise
    """
    if trace is None:
        yield None
        return

    try:
        span = trace.span(
            name=name,
            metadata=metadata if metadata is not None else {},
            input=input_data,
            level=level,
        )
        yield span
        if span:
            span.end()
    except Exception as e:
        logger.error(f"Error creating Langfuse span: {sanitize_for_log(str(e))}")
        yield None


def create_event(
    trace: Any,
    name: str,
    metadata: dict[str, Any] | None = None,
    input_data: Any | None = None,
    output_data: Any | None = None,
    level: str = "DEFAULT",
) -> Any:
    """
    Create an event on a trace for tracking discrete operations.

    Args:
        trace: The parent Langfuse trace
        name: Name of the event
        metadata: Optional additional metadata
        input_data: Optional input data
        output_data: Optional output data
        level: Observation level (DEFAULT, DEBUG, WARNING, ERROR)

    Returns:
        Langfuse event object if successful, None otherwise
    """
    if trace is None:
        return None

    try:
        event = trace.event(
            name=name,
            metadata=metadata if metadata is not None else {},
            input=input_data,
            output=output_data,
            level=level,
        )
        return event
    except Exception as e:
        logger.error(f"Error creating Langfuse event: {sanitize_for_log(str(e))}")
        return None


def score_trace(
    trace_id: str,
    name: str,
    value: float,
    comment: str | None = None,
) -> bool:
    """
    Score a trace for user feedback tracking.

    Args:
        trace_id: The trace ID to score
        name: Name of the score (e.g., "user_feedback", "quality")
        value: Score value (typically 0-1 or 1-5 depending on scale)
        comment: Optional comment about the score

    Returns:
        True if successful, False otherwise
    """
    client = get_langfuse_client()
    if client is None:
        return False

    try:
        client.score(
            trace_id=trace_id,
            name=name,
            value=value,
            comment=comment,
        )
        logger.info(f"Scored trace in Langfuse with score_name={name}, value={value}")
        return True
    except Exception as e:
        logger.error(f"Error scoring trace: {sanitize_for_log(str(e))}")
        return False


def shutdown_langfuse():
    """Shutdown Langfuse client and flush any pending data."""
    client = get_langfuse_client()
    if client:
        try:
            client.flush()
            client.shutdown()
            logger.info("Langfuse client shutdown successfully")
        except Exception as e:
            logger.warning(f"Error shutting down Langfuse client: {sanitize_for_log(str(e))}")
