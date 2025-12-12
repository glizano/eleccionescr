"""
LLM service module.

Provides a simple interface to use LangChain chat models with retry and timeout support.
"""

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel

from app.config import settings
from app.services.circuit_breaker import CircuitBreakerOpenError, get_llm_circuit_breaker
from app.services.llm_providers import get_llm_provider
from app.services.retry import is_resource_exhausted_error, retry_with_exponential_backoff

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
    logger.info(f"[LLM] Using model: {model_name}")

    try:
        # Use circuit breaker to prevent cascading failures
        circuit_breaker = get_llm_circuit_breaker()

        # Wrap LLM call with retry logic
        def _make_llm_call():
            return _invoke_llm_with_timeout(llm, prompt)

        # Execute with circuit breaker and retry
        response_text = circuit_breaker.call(retry_with_exponential_backoff, _make_llm_call)

        logger.info(f"[LLM] Generated response ({len(response_text)} chars)")
        # TODO: Integrate langfuse_trace for observability
        return response_text

    except CircuitBreakerOpenError as e:
        logger.error(f"[LLM] Circuit breaker open: {e}")
        return "El servicio de IA está temporalmente no disponible. Intenta de nuevo en un minuto."

    except TimeoutError as e:
        logger.error(f"[LLM] Request timeout: {e}")
        return f"La solicitud tomó demasiado tiempo ({settings.llm_timeout_seconds}s). Intenta con una pregunta más corta."

    except Exception as e:
        if is_resource_exhausted_error(e):
            logger.warning("[LLM] Rate limited after retries", exc_info=True)
            return "El servicio de IA está ocupado (429). Intenta de nuevo en unos segundos."

        logger.error("[LLM] Error generating text", exc_info=True)
        return f"Error al generar respuesta: {str(e)}"
