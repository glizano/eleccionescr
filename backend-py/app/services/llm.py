import logging
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import types

from app.config import settings


@lru_cache(maxsize=1)
def get_client():
    """Get Google GenAI client (cached)"""
    return genai.Client(api_key=settings.google_api_key)


def generate_text(prompt: str, langfuse_trace: Any = None) -> str:
    """Generate text using Gemini

    Args:
        prompt: The input prompt for the LLM
        langfuse_trace: Optional Langfuse trace for observability

    Returns:
        Generated text response
    """
    client = get_client()
    model_name = "gemini-2.5-flash"

    # Start Langfuse generation tracking if trace is provided
    generation = None
    if langfuse_trace:
        try:
            from app.services.langfuse_service import create_generation

            generation = create_generation(
                trace=langfuse_trace,
                name="llm-generation",
                model=model_name,
                input_text=prompt,
            )
        except Exception as e:
            logging.warning(f"Failed to create Langfuse generation: {e}")

    try:
        response = client.models.generate_content(
            model=model_name,
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
        output_text = None
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                text = "".join(
                    part.text for part in candidate.content.parts if hasattr(part, "text")
                )
                if text:
                    logging.info(f"Generated text length: {len(text)}")
                    output_text = text

        # Fallback: try response.text
        if not output_text and hasattr(response, "text") and response.text:
            output_text = response.text

        if not output_text:
            output_text = "No se pudo generar una respuesta válida."

        # Update Langfuse generation with output
        if generation:
            try:
                generation.end(output=output_text)
            except Exception as e:
                logging.warning(f"Failed to end Langfuse generation: {e}")

        return output_text

    except Exception as e:
        logging.error(f"Error generating text: {e}", exc_info=True)
        error_msg = f"Error al generar respuesta: {str(e)}"

        # Update Langfuse generation with error
        if generation:
            try:
                generation.end(output=error_msg, level="ERROR", status_message=str(e))
            except Exception as gen_e:
                logging.warning(f"Failed to end Langfuse generation with error: {gen_e}")

        return error_msg
