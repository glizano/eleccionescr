"""
LLM service module.

Provides a simple interface to use LangChain chat models.
"""

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel

from app.services.llm_providers import get_llm_provider

logger = logging.getLogger(__name__)


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
        # Integrate with Langfuse for observability
        if langfuse_trace:
            generation = langfuse_trace.generation(
                name="llm-generation",
                model=model_name,
                input=prompt[:500],  # Truncate for logging
            )
            response = llm.invoke(prompt)
            generation.end(output=response.content[:500])
        else:
            response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        logger.error(f"Error generating text: {e}", exc_info=True)
        raise RuntimeError(f"Error al generar respuesta: {str(e)}") from e
