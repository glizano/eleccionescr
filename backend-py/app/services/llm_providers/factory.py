"""
LLM Provider Factory.

Creates the appropriate LLM provider based on configuration.
"""

import logging
from functools import lru_cache
from typing import Literal

from app.config import settings
from app.services.llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)

LLMProviderType = Literal["google", "openai"]


def create_llm_provider(provider_type: LLMProviderType | None = None) -> LLMProvider:
    """
    Create an LLM provider based on the specified type or settings.

    Args:
        provider_type: The type of provider to create. If None, uses settings.llm_provider.

    Returns:
        An instance of the appropriate LLM provider.

    Raises:
        ValueError: If the provider type is unknown or required API key is missing.
    """
    if provider_type is None:
        provider_type = settings.llm_provider

    logger.info(f"Creating LLM provider: {provider_type}")

    if provider_type == "google":
        if not settings.google_api_key:
            raise ValueError("Google API key is required for Google provider")

        from app.services.llm_providers.google_provider import GoogleProvider

        return GoogleProvider(
            api_key=settings.google_api_key,
            model=settings.google_model,
            safety_threshold=settings.google_safety_threshold,
        )

    elif provider_type == "openai":
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required for OpenAI provider")

        from app.services.llm_providers.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    else:
        raise ValueError(f"Unknown LLM provider type: {provider_type}")


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """
    Get the configured LLM provider (cached).

    Returns:
        The configured LLM provider instance.
    """
    return create_llm_provider()
