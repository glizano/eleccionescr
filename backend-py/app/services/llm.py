"""
LLM service module.

Provides a simple interface to generate text using the configured LLM provider.
"""

import logging

from app.services.llm_providers import get_llm_provider

logger = logging.getLogger(__name__)


def generate_text(prompt: str) -> str:
    """
    Generate text using the configured LLM provider.

    Args:
        prompt: The input prompt to generate text from.

    Returns:
        The generated text response.
    """
    provider = get_llm_provider()
    logger.info(f"Using LLM provider: {provider.model_name}")
    return provider.generate_text(prompt)
