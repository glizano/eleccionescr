"""
LLM service module.

Provides a simple interface to use LangChain chat models with retry and timeout support.
"""

import logging
import time
from typing import Any

from langchain_core.language_models import BaseChatModel

from app.config import settings
from app.services.circuit_breaker import CircuitBreakerOpenError, get_llm_circuit_breaker
from app.services.llm_providers import get_llm_provider
from app.services.retry import is_resource_exhausted_error, retry_with_exponential_backoff
from app.utils.logging import sanitize_for_log

logger = logging.getLogger(__name__)


def get_llm() -> BaseChatModel:
    """
    Get the configured LangChain chat model.

    Returns:
        The configured LangChain BaseChatModel instance.
    """
    return get_llm_provider()


def _invoke_llm_with_timeout(llm: BaseChatModel, prompt: str) -> str:
    """
    Invoke LLM with timeout support.

    Args:
        llm: The LLM instance
        prompt: The prompt to send

    Returns:
        Generated text

    Raises:
        TimeoutError: If request exceeds timeout
        Exception: Other LLM errors
    """
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError(f"LLM request exceeded {settings.llm_timeout_seconds}s timeout")

    # Set alarm for timeout (Unix only - for production use asyncio timeout or thread-based timeout)
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(settings.llm_timeout_seconds)

        response = llm.invoke(prompt)

        signal.alarm(0)  # Cancel alarm
        return response.content

    except AttributeError:
        # Windows doesn't support SIGALRM, fall back to direct call
        logger.debug("Signal-based timeout not available, using direct invoke")
        response = llm.invoke(prompt)
        return response.content


def generate_text(prompt: str, langfuse_trace: Any = None) -> str:
    """
    Generate text using the configured LLM with retry, timeout, and circuit breaker.

    Args:
        prompt: The input prompt to generate text from.
        langfuse_trace: Optional Langfuse trace for observability.

    Returns:
        The generated text response.
    """
    llm = get_llm()
    model_name = getattr(llm, "model_name", type(llm).__name__)
    logger.info(f"[LLM] Using model: {sanitize_for_log(model_name)}")

    # Create Langfuse generation for LLM call tracking
    generation = None
    if langfuse_trace:
        from app.services.langfuse_service import create_generation

        generation = create_generation(
            trace=langfuse_trace,
            name="llm_generation",
            model=model_name,
            input_text=prompt,
            metadata={
                "provider": settings.llm_provider,
                "timeout_seconds": settings.llm_timeout_seconds,
                "max_retries": settings.llm_retry_max_attempts,
            },
        )

    start_time = time.time()

    try:
        # Use circuit breaker to prevent cascading failures
        circuit_breaker = get_llm_circuit_breaker()

        # Wrap LLM call with retry logic
        def _make_llm_call():
            return _invoke_llm_with_timeout(llm, prompt)

        # Execute with circuit breaker and retry
        response_text = circuit_breaker.call(retry_with_exponential_backoff, _make_llm_call)

        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[LLM] Generated response ({len(response_text)} chars) in {latency_ms}ms")

        # Update Langfuse generation with output and metrics
        if generation:
            try:
                generation.end(
                    output=response_text,
                    metadata={
                        "latency_ms": latency_ms,
                        "response_length": len(response_text),
                        "prompt_length": len(prompt),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update Langfuse generation: {sanitize_for_log(str(e))}")

        return response_text

    except CircuitBreakerOpenError as e:
        logger.error(f"[LLM] Circuit breaker open: {sanitize_for_log(str(e))}")
        error_msg = (
            "El servicio de IA está temporalmente no disponible. Intenta de nuevo en un minuto."
        )

        if generation:
            try:
                generation.end(
                    output=error_msg,
                    level="ERROR",
                    status_message="Circuit breaker open",
                )
            except Exception:
                pass

        return error_msg

    except TimeoutError as e:
        logger.error(f"[LLM] Request timeout: {sanitize_for_log(str(e))}")
        error_msg = f"La solicitud tomó demasiado tiempo ({settings.llm_timeout_seconds}s). Intenta con una pregunta más corta."

        if generation:
            try:
                generation.end(
                    output=error_msg,
                    level="ERROR",
                    status_message=f"Timeout after {settings.llm_timeout_seconds}s",
                )
            except Exception:
                pass

        return error_msg

    except Exception as e:
        if is_resource_exhausted_error(e):
            logger.warning("[LLM] Rate limited after retries", exc_info=True)
            error_msg = "El servicio de IA está ocupado (429). Intenta de nuevo en unos segundos."
        else:
            logger.error("[LLM] Error generating text", exc_info=True)
            error_msg = f"Error al generar respuesta: {str(e)}"

        if generation:
            try:
                generation.end(
                    output=error_msg,
                    level="ERROR",
                    status_message=str(e),
                )
            except Exception:
                pass

        return error_msg


async def generate_text_stream(prompt: str, langfuse_trace: Any = None):
    """
    Generate text using streaming (yields tokens as they're generated).

    Args:
        prompt: The input prompt
        langfuse_trace: Optional Langfuse trace

    Yields:
        Text tokens as they're generated
    """
    llm = get_llm()
    model_name = getattr(llm, "model_name", type(llm).__name__)
    logger.info(f"[LLM Stream] Using model: {sanitize_for_log(model_name)}")

    # Create Langfuse generation for streaming LLM call
    generation = None
    if langfuse_trace:
        from app.services.langfuse_service import create_generation

        generation = create_generation(
            trace=langfuse_trace,
            name="llm_generation_stream",
            model=model_name,
            input_text=prompt,
            metadata={
                "provider": settings.llm_provider,
                "streaming": True,
            },
        )

    start_time = time.time()
    full_response = ""

    try:
        # Stream tokens from LLM
        async for chunk in llm.astream(prompt):
            if hasattr(chunk, "content") and chunk.content:
                full_response += chunk.content
                yield chunk.content

        latency_ms = int((time.time() - start_time) * 1000)

        # Update generation with final output
        if generation:
            try:
                generation.end(
                    output=full_response,
                    metadata={
                        "latency_ms": latency_ms,
                        "response_length": len(full_response),
                        "prompt_length": len(prompt),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update Langfuse generation: {sanitize_for_log(str(e))}")

    except Exception as e:
        if is_resource_exhausted_error(e):
            logger.warning("[LLM Stream] Rate limited", exc_info=True)
            error_msg = "\\n\\n[El servicio está ocupado, intenta de nuevo en unos segundos]"
        else:
            logger.error("[LLM Stream] Error", exc_info=True)
            error_msg = f"\\n\\n[Error: {str(e)}]"

        if generation:
            try:
                generation.end(
                    output=full_response + error_msg,
                    level="ERROR",
                    status_message=str(e),
                )
            except Exception:
                pass

        yield error_msg
