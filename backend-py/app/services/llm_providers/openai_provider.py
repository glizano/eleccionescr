"""
OpenAI LLM Provider.
"""

import logging

from openai import OpenAI

from app.services.llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key.
            model: Model name to use (default: gpt-4o-mini).
        """
        self._api_key = api_key
        self._model = model
        self._client = OpenAI(api_key=api_key)

    @property
    def model_name(self) -> str:
        """Return the name of the model being used."""
        return self._model

    def generate_text(self, prompt: str) -> str:
        """Generate text using OpenAI."""
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2048,
            )

            if response.choices and len(response.choices) > 0:
                text = response.choices[0].message.content
                if text:
                    logger.info(f"Generated text length: {len(text)}")
                    return text

            return "No se pudo generar una respuesta válida."

        except Exception as e:
            logger.error(f"Error generating text with OpenAI: {e}", exc_info=True)
            return f"Error al generar respuesta: {str(e)}"
