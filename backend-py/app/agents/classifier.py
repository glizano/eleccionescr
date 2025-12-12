import logging
from typing import Literal, TypedDict

from pydantic import BaseModel, Field

from app.party_metadata import (
    PARTIES_METADATA,
)
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
    Extract party names from question using LLM with complete metadata.

    The LLM receives full party information (abbreviations, full names, and candidates)
    to accurately identify parties mentioned by any reference method.

    Returns: List of party abbreviations (e.g., ["PLN", "PUSC"])
    """
    # Build complete metadata for LLM context
    parties_info = "\n".join(
        [
            f"- {p['abbreviation']}: {p['name']} (Candidato: {p['candidate']})"
            for p in PARTIES_METADATA
        ]
    )

    prompt = f"""Extrae los partidos políticos mencionados en la pregunta.

PARTIDOS DE COSTA RICA 2026:
{parties_info}

REGLAS:
- Devuelve las siglas de los partidos mencionados como lista
- Si no se menciona ningún partido, devuelve lista vacía []
- Identifica partidos mencionados por:
  • Siglas (PLN, PUSC, FA, etc.)
  • Nombre completo ("Liberación Nacional", "Frente Amplio")
  • Nombre del candidato ("Fabricio Alvarado", "Claudia Dobles")
  • Apellido del candidato ("Alvarado", "Feinzaig")
- Usa SIEMPRE las siglas exactas de la lista
- Solo incluye partidos que estén en la lista de arriba

EJEMPLOS:
- "¿Qué propone el PLN?" → ["PLN"]
- "¿Fabricio Alvarado qué dice?" → ["PNR"]
- "Compara Liberación Nacional con el PUSC" → ["PLN", "PUSC"]
- "¿Claudia Dobles tiene propuestas?" → ["CAC"]
- "¿Qué dice Feinzaig sobre economía?" → ["PLP"]
- "Compara todos los partidos" → []
- "¿Propuestas sobre educación?" → []

PREGUNTA: {question}"""

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(PartyExtraction)
        result = structured_llm.invoke(prompt)

        # Filter to only known parties (safety check)
        valid_parties = [p for p in result.parties if p in KNOWN_PARTIES]

        if valid_parties:
            logger.info(f"Extracted parties: {valid_parties}")
        else:
            logger.info("No parties detected in question")

        return valid_parties

    except Exception as e:
        logger.error(f"Error extracting parties: {e}")
        return []
