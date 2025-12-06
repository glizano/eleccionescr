"""
Google Gemini LLM Provider.
"""

import logging

from google import genai
from google.genai import types

from app.services.llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)


class GoogleProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """
        Initialize the Google Gemini provider.

        Args:
            api_key: Google API key.
            model: Model name to use (default: gemini-2.5-flash).
        """
        self._api_key = api_key
        self._model = model
        self._client = genai.Client(api_key=api_key)

    @property
    def model_name(self) -> str:
        """Return the name of the model being used."""
        return self._model

    def generate_text(self, prompt: str) -> str:
        """Generate text using Google Gemini."""
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=2048,
                    safety_settings=[
                        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                        types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
                        ),
                        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
                        types.SafetySetting(
                            category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
                        ),
                    ],
                ),
            )

            logger.info(
                f"LLM finish_reason: {response.candidates[0].finish_reason if response.candidates else 'NO_CANDIDATES'}"
            )

            # Get the text from response
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    text = "".join(
                        part.text for part in candidate.content.parts if hasattr(part, "text")
                    )
                    if text:
                        logger.info(f"Generated text length: {len(text)}")
                        return text

            # Fallback: try response.text
            if hasattr(response, "text") and response.text:
                return response.text

            return "No se pudo generar una respuesta válida."

        except Exception as e:
            logger.error(f"Error generating text with Google Gemini: {e}", exc_info=True)
            return f"Error al generar respuesta: {str(e)}"
