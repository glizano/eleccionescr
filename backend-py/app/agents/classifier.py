import logging
from typing import Literal, TypedDict

from pydantic import BaseModel, Field

from app.services.llm import get_llm

logger = logging.getLogger(__name__)

# Known parties - Complete list of all parties with government plans
KNOWN_PARTIES = [
    "ACRM",  # Aquí Costa Rica Manda
    "CAC",  # Coalición Agenda Ciudadana
    "CDS",  # Centro Democrático y Social
    "CR1",  # Alianza Costa Rica Primero
    "FA",  # Frente Amplio
    "PA",  # Avanza
    "PDLCT",  # De la Clase Trabajadora
    "PEL",  # Esperanza y Libertad
    "PEN",  # Esperanza Nacional
    "PIN",  # Integración Nacional
    "PJSC",  # Justicia Social Costarricense
    "PLN",  # Liberación Nacional
    "PLP",  # Liberal Progresista
    "PNG",  # Nueva Generación
    "PNR",  # Nueva República
    "PPSO",  # Pueblo Soberano
    "PSD",  # Progreso Social Democrático
    "PUCD",  # Unión Costarricense Democrática
    "PUSC",  # Unidad Social Cristiana
    "UP",  # Unidos Podemos
]


class IntentClassifierState(TypedDict):
    """State for intent classification"""

    question: str
    intent: Literal["specific_party", "party_general_plan", "general_comparison", "unclear"]


class IntentClassification(BaseModel):
    """Structured output for intent classification"""

    intent: Literal["specific_party", "party_general_plan", "general_comparison", "unclear"] = (
        Field(description="The classified intent of the question")
    )


class PartyExtraction(BaseModel):
    """Structured output for party extraction"""

    parties: list[str] = Field(
        description="List of party abbreviations mentioned in the question (e.g., PLN, PUSC)"
    )


def classify_intent(question: str, conversation_history: str | None = None) -> str:
    """
    Classify if question is about a specific party or general/comparison

    Args:
        question: The current question
        conversation_history: Optional conversation context for follow-up questions

    Returns: "specific_party", "party_general_plan", "general_comparison", or "unclear"
    """
    context_note = ""
    if conversation_history:
        context_note = f"\n\nCONTEXTO DE LA CONVERSACIÓN PREVIA:\n{conversation_history}\n"
    
    prompt = f"""Eres un clasificador de intenciones para preguntas sobre planes de gobierno.{context_note}

Clasifica la pregunta en una de estas categorías:
- "specific_party": La pregunta es sobre UN TEMA O ASPECTO ESPECÍFICO de un partido (ej: educación, salud, seguridad)
- "party_general_plan": La pregunta pide un RESUMEN COMPLETO o GENERAL del plan de un partido específico
- "general_comparison": La pregunta es general o compara múltiples partidos
- "unclear": No está claro

Ejemplos:
- "¿Qué propone el PLN sobre educación?" → specific_party (tema específico: educación)
- "¿Qué dice el PUSC sobre salud?" → specific_party (tema específico: salud)
- "¿Cuál es la propuesta del FA para seguridad?" → specific_party (tema específico: seguridad)
- "¿Qué plantea el PEN sobre empleo?" → specific_party (tema específico: empleo)
- "¿Qué plantea el plan del PLN?" → party_general_plan (pregunta general sobre todo el plan)
- "¿Cuál es el plan del PUSC?" → party_general_plan (pregunta general sobre todo el plan)
- "Resume el plan de gobierno del PNR" → party_general_plan (resumen completo)
- "Cuéntame sobre el plan del PJSC" → party_general_plan (resumen completo)
- "¿Qué proponen los partidos sobre seguridad?" → general_comparison (múltiples partidos)
- "Compara las propuestas de PLN y PUSC" → general_comparison (comparación)
- "¿Cuál es la mejor propuesta educativa?" → general_comparison (comparación implícita)

IMPORTANTE: Si hay contexto de conversación previa y la pregunta es de seguimiento (ej: "Y el PIN?", "¿Y qué dice el PUSC?"):
- Si el contexto menciona un tema específico → specific_party
- Si el contexto no menciona tema específico → party_general_plan

Pregunta actual: {question}"""

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(IntentClassification)
        result = structured_llm.invoke(prompt)

        logger.info(f"Intent classified as: {result.intent}")
        return result.intent

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
- Devuelve las siglas de los partidos mencionados como lista
- Si no se menciona ningún partido, devuelve lista vacía
- Usa las siglas exactas de la lista
- Solo incluye partidos que estén en la lista de partidos conocidos

Ejemplos:
- "¿Qué propone el PLN?" → ["PLN"]
- "Compara PLN y PUSC" → ["PLN", "PUSC"]
- "¿Qué dicen sobre educación?" → []
- "El Partido Liberación Nacional propone..." → ["PLN"]
- "¿Cuál es el plan del FA?" → ["FA"]
- "Compara PEN, PEL y PJSC" → ["PEN", "PEL", "PJSC"]
- "¿Qué dice Esperanza Nacional sobre salud?" → ["PEN"]

Pregunta: {question}"""

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(PartyExtraction)
        result = structured_llm.invoke(prompt)

        # Filter to only known parties (extra safety)
        valid_parties = [p for p in result.parties if p in KNOWN_PARTIES]

        logger.info(f"Extracted parties: {valid_parties}")
        return valid_parties

    except Exception as e:
        logger.error(f"Error extracting parties: {e}")
        return []
