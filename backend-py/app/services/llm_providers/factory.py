"""
LLM Provider Factory using LangChain abstractions.

Creates the appropriate LLM provider based on configuration.
"""

import logging
from functools import lru_cache
from typing import Literal

from langchain_core.language_models import BaseChatModel

from app.config import settings
from app.utils.logging import sanitize_for_log

logger = logging.getLogger(__name__)

LLMProviderType = Literal["google", "openai"]


def create_llm_provider(provider_type: LLMProviderType | None = None) -> BaseChatModel:
    """
    Create a LangChain chat model based on the specified type or settings.

    Args:
        provider_type: The type of provider to create. If None, uses settings.llm_provider.

    Returns:
        A LangChain BaseChatModel instance.

    Raises:
        ValueError: If the provider type is unknown or required API key is missing.
    """
    if provider_type is None:
        provider_type = settings.llm_provider

    logger.info(f"Creating LLM provider: {sanitize_for_log(provider_type)}")

    if provider_type == "google":
        if not settings.google_api_key:
            raise ValueError("Google API key is required for Google provider")

        from app.services.llm_providers.google_provider import create_google_chat_model

        return create_google_chat_model(
            api_key=settings.google_api_key,
            model=settings.google_model,
            safety_threshold=settings.google_safety_threshold,
        )

    elif provider_type == "openai":
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required for OpenAI provider")

        from app.services.llm_providers.openai_provider import create_openai_chat_model

        return create_openai_chat_model(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    else:
        raise ValueError(f"Unknown LLM provider type: {provider_type}")


@lru_cache(maxsize=1)
def get_llm_provider() -> BaseChatModel:
    """
    Get the configured LangChain chat model (cached).

    Returns:
        The configured LangChain BaseChatModel instance.
    """
    return create_llm_provider()
