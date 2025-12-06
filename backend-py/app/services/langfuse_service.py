"""Langfuse integration for LLM observability and tracing."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# Global Langfuse client instance
_langfuse_client = None


@lru_cache(maxsize=1)
def get_langfuse_client():
    """Get Langfuse client (cached). Returns None if Langfuse is disabled."""
    global _langfuse_client

    if not settings.langfuse_enabled:
        logger.info("Langfuse is disabled")
        return None

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.warning("Langfuse keys not configured, disabling Langfuse")
        return None

    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        logger.info(f"Langfuse client initialized with host: {settings.langfuse_host}")
        return _langfuse_client
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse client: {e}")
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
            metadata=metadata or {},
        )
        yield trace
    except Exception as e:
        logger.error(f"Error creating Langfuse trace: {e}")
        yield None
    finally:
        # Flush to ensure trace is sent
        try:
            if client:
                client.flush()
        except Exception as e:
            logger.warning(f"Error flushing Langfuse client: {e}")


def create_generation(
    trace: Any,
    name: str,
    model: str,
    input_text: str,
    output_text: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Any:
    """
    Create a generation event on a trace for LLM calls.

    Args:
        trace: The parent Langfuse trace
        name: Name of the generation
        model: Model name used
        input_text: Input prompt text
        output_text: Output text from the model
        metadata: Optional additional metadata

    Returns:
        Langfuse generation object if successful, None otherwise
    """
    if trace is None:
        return None

    try:
        generation = trace.generation(
            name=name,
            model=model,
            input=input_text,
            output=output_text,
            metadata=metadata or {},
        )
        return generation
    except Exception as e:
        logger.error(f"Error creating Langfuse generation: {e}")
        return None


def shutdown_langfuse():
    """Shutdown Langfuse client and flush any pending data."""
    client = get_langfuse_client()
    if client:
        try:
            client.flush()
            client.shutdown()
            logger.info("Langfuse client shutdown successfully")
        except Exception as e:
            logger.warning(f"Error shutting down Langfuse client: {e}")
