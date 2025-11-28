import logging
from typing import Literal, TypedDict

from app.services.llm import generate_text

logger = logging.getLogger(__name__)

# Known parties
KNOWN_PARTIES = ["PLN", "PUSC", "PNR", "FA", "PLP", "PPSO", "CAC"]


class IntentClassifierState(TypedDict):
    """State for intent classification"""

    question: str
    intent: Literal["specific_party", "general_comparison", "unclear"]


def classify_intent(question: str) -> str:
    """
    Classify if question is about a specific party or general/comparison

    Returns: "specific_party", "general_comparison", or "unclear"
    """
    prompt = f"""Eres un clasificador de intenciones para preguntas sobre planes de gobierno.

Clasifica la pregunta en una de estas categorías:
- "specific_party": La pregunta es sobre UN partido político específico
- "general_comparison": La pregunta es general o compara múltiples partidos
- "unclear": No está claro

Ejemplos:
- "¿Qué propone el PLN sobre educación?" → specific_party
- "¿Qué dice el PUSC sobre salud?" → specific_party
- "¿Qué proponen los partidos sobre seguridad?" → general_comparison
- "Compara las propuestas de PLN y PUSC" → general_comparison
- "¿Cuál es la mejor propuesta educativa?" → general_comparison

Responde SOLO con: specific_party, general_comparison, o unclear

Pregunta: {question}"""

    try:
        response = generate_text(prompt)
        intent = response.strip().lower()

        # Validate response
        if intent not in ["specific_party", "general_comparison", "unclear"]:
            logger.warning(f"Invalid intent classification: {intent}, defaulting to unclear")
            return "unclear"

        logger.info(f"Intent classified as: {intent}")
        return intent

    except Exception as e:
        logger.error(f"Error classifying intent: {e}")
        return "unclear"


def extract_parties(question: str) -> list[str]:
    """
    Extract party names from question

    Returns: List of party abbreviations (e.g., ["PLN", "PUSC"])
    """
    parties_str = ", ".join(KNOWN_PARTIES)

    prompt = f"""Extrae los nombres de partidos políticos mencionados en la pregunta.

Partidos conocidos: {parties_str}

Reglas:
- Devuelve SOLO las siglas de los partidos mencionados
- Si no se menciona ningún partido, devuelve "NINGUNO"
- Separa múltiples partidos con comas
- Usa las siglas exactas de la lista

Ejemplos:
- "¿Qué propone el PLN?" → PLN
- "Compara PLN y PUSC" → PLN, PUSC
- "¿Qué dicen sobre educación?" → NINGUNO
- "El Partido Liberación Nacional propone..." → PLN

Pregunta: {question}"""

    try:
        response = generate_text(prompt)
        result = response.strip().upper()

        if result == "NINGUNO":
            return []

        # Parse comma-separated parties
        parties = [p.strip() for p in result.split(",")]

        # Filter to only known parties
        valid_parties = [p for p in parties if p in KNOWN_PARTIES]

        logger.info(f"Extracted parties: {valid_parties}")
        return valid_parties

    except Exception as e:
        logger.error(f"Error extracting parties: {e}")
        return []
