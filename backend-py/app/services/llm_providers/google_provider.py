"""
Google Gemini LLM Provider using LangChain.
"""

import logging

from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory

from app.services.llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)

# Map config string to LangChain enum
SAFETY_THRESHOLD_MAP = {
    "BLOCK_NONE": HarmBlockThreshold.BLOCK_NONE,
    "BLOCK_ONLY_HIGH": HarmBlockThreshold.BLOCK_ONLY_HIGH,
    "BLOCK_MEDIUM_AND_ABOVE": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    "BLOCK_LOW_AND_ABOVE": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
}


def create_google_provider(
    api_key: str,
    model: str = "gemini-2.5-flash",
    safety_threshold: str = "BLOCK_MEDIUM_AND_ABOVE",
) -> LLMProvider:
    """
    Create a Google Gemini provider using LangChain.

    Args:
        api_key: Google API key.
        model: Model name to use (default: gemini-2.5-flash).
        safety_threshold: Safety filter threshold (default: BLOCK_MEDIUM_AND_ABOVE).

    Returns:
        LLMProvider instance wrapping ChatGoogleGenerativeAI.
    """
    threshold = SAFETY_THRESHOLD_MAP.get(
        safety_threshold, HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    )

    # Configure safety settings for all harm categories
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: threshold,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: threshold,
        HarmCategory.HARM_CATEGORY_HARASSMENT: threshold,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: threshold,
    }

    chat_model = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0.2,
        max_output_tokens=2048,
        safety_settings=safety_settings,
    )

    logger.info(f"Created Google Gemini provider with model: {model}, safety: {safety_threshold}")
    return LLMProvider(chat_model)
