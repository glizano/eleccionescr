import logging
from typing import Literal, TypedDict

from pydantic import BaseModel, Field

from app.agents.prompts import (
    build_intent_classification_prompt,
    build_party_extraction_prompt,
)
from app.party_metadata import (
    PARTIES_METADATA,
)
from app.services.llm import get_llm
from app.services.retry import is_resource_exhausted_error
from app.utils.logging import sanitize_for_log

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
    intent: Literal[
        "specific_party",
        "party_general_plan",
        "general_comparison",
        "metadata_query",
        "unclear",
        "rate_limited",
    ]


class IntentClassification(BaseModel):
    """Structured output for intent classification"""

    intent: Literal[
        "specific_party",
        "party_general_plan",
        "general_comparison",
        "metadata_query",
        "unclear",
    ] = Field(description="The classified intent of the question")


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

    Returns: "specific_party", "party_general_plan", "general_comparison", "metadata_query", or "unclear"
    """
    prompt = build_intent_classification_prompt(question, conversation_history)

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(IntentClassification)
        result = structured_llm.invoke(prompt)

        logger.info(f"Intent classified as: {sanitize_for_log(result.intent)}")
        return result.intent

    except Exception as e:
        if is_resource_exhausted_error(e):
            logger.warning(
                "Intent classification rate limited or resource exhausted; stopping workflow"
            )
            return "rate_limited"

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

    prompt = build_party_extraction_prompt(question, parties_info)

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(PartyExtraction)
        result = structured_llm.invoke(prompt)

        # Filter to only known parties (safety check)
        valid_parties = [p for p in result.parties if p in KNOWN_PARTIES]

        if valid_parties:
            # No sanitization needed - parties come from controlled KNOWN_PARTIES set
            logger.info(f"Extracted parties: {valid_parties}")
        else:
            logger.info("No parties detected in question")

        return valid_parties

    except Exception as e:
        if is_resource_exhausted_error(e):
            logger.warning(
                "Party extraction rate limited or resource exhausted; returning empty list"
            )
            return []

        logger.error(f"Error extracting parties: {e}")
        return []
