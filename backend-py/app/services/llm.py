"""
LLM service module.

Provides a simple interface to use LangChain chat models.
"""

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel

from app.services.llm_providers import get_llm_provider

logger = logging.getLogger(__name__)


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


def get_llm() -> BaseChatModel:
    """
    Get the configured LangChain chat model.

    Returns:
        The configured LangChain BaseChatModel instance.
    """
    return get_llm_provider()


def generate_text(prompt: str, langfuse_trace: Any = None) -> str:
    """
    Generate text using the configured LLM.

    Args:
        prompt: The input prompt to generate text from.
        langfuse_trace: Optional Langfuse trace for observability.

    Returns:
        The generated text response.
    """
    llm = get_llm()
    model_name = getattr(llm, "model_name", type(llm).__name__)
    logger.info(f"Using LLM: {model_name}")

    try:
        # TODO: Integrate langfuse_trace for observability when invoking
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        if is_resource_exhausted_error(e):
            logger.warning("LLM rate limited or resource exhausted", exc_info=True)
            return "El servicio de IA está ocupado (429). Intenta de nuevo en unos segundos."

        logger.error("Error generating text", exc_info=True)
        return f"Error al generar respuesta: {str(e)}"
