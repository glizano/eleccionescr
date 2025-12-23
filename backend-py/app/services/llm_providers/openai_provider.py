"""
OpenAI LLM Provider using LangChain.
"""

import logging

from langchain_openai import ChatOpenAI

from app.utils.logging import sanitize_for_log

logger = logging.getLogger(__name__)


def create_openai_chat_model(api_key: str, model: str = "gpt-4o-mini") -> ChatOpenAI:
    """
    Create a ChatOpenAI model.

    Args:
        api_key: OpenAI API key.
        model: Model name to use (default: gpt-4o-mini).

    Returns:
        ChatOpenAI instance configured with temperature=0.2 and max_tokens=2048.
    """
    chat_model = ChatOpenAI(
        model=model,
        api_key=api_key,
        temperature=0.2,
        max_tokens=2048,
    )

    logger.info(f"Created OpenAI chat model: {sanitize_for_log(model)}")
    return chat_model
