import logging
from functools import lru_cache

from google import genai
from google.genai import types

from app.config import settings


@lru_cache(maxsize=1)
def get_client():
    """Get Google GenAI client (cached)"""
    return genai.Client(api_key=settings.google_api_key)


def generate_text(prompt: str) -> str:
    """Generate text using Gemini"""
    client = get_client()

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2048,  # Increased for longer responses
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

        logging.info(
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
                    logging.info(f"Generated text length: {len(text)}")
                    return text

        # Fallback: try response.text
        if hasattr(response, "text") and response.text:
            return response.text

        return "No se pudo generar una respuesta válida."

    except Exception as e:
        logging.error(f"Error generating text: {e}", exc_info=True)
        return f"Error al generar respuesta: {str(e)}"
