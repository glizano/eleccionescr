"""
OpenAI LLM Provider using LangChain.
"""

import logging

from langchain_openai import ChatOpenAI

from app.services.llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)


def create_openai_provider(api_key: str, model: str = "gpt-4o-mini") -> LLMProvider:
    """
    Create an OpenAI provider using LangChain.

    Args:
        api_key: OpenAI API key.
        model: Model name to use (default: gpt-4o-mini).

    Returns:
        LLMProvider instance wrapping ChatOpenAI.
    """
    chat_model = ChatOpenAI(
        model=model,
        api_key=api_key,
        temperature=0.2,
        max_tokens=2048,
    )

    logger.info(f"Created OpenAI provider with model: {model}")
    return LLMProvider(chat_model)
