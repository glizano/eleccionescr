"""
Prompt templates for RAG agent system.
"""

from app.config import settings


def build_intent_classification_prompt(
    question: str, conversation_history: str | None = None
) -> str:
    """Build prompt for intent classification."""
    context_note = ""
    if conversation_history:
        context_note = f"\n\nCONTEXTO DE LA CONVERSACIÓN PREVIA:\n{conversation_history}\n"

    return f"""Eres un clasificador de intenciones para preguntas sobre planes de gobierno.{context_note}

Clasifica la pregunta en una de estas categorías:
- "specific_party": La pregunta es sobre UN TEMA O ASPECTO ESPECÍFICO de un partido (ej: educación, salud, seguridad)
- "party_general_plan": La pregunta pide un RESUMEN COMPLETO o GENERAL del plan de un partido específico
- "general_comparison": La pregunta es general o compara múltiples partidos
- "metadata_query": La pregunta pide INFORMACIÓN BÁSICA sobre un partido o candidato (nombre, candidato, siglas) - NO requiere buscar en el plan
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
- "¿Quién es el candidato del PLN?" → metadata_query (pregunta sobre info básica)
- "¿Cuál es el partido de Natalia Díaz?" → metadata_query (pregunta sobre info básica)
- "¿Qué significa FA?" → metadata_query (pregunta sobre info básica)
- "¿Cuál es el nombre completo del PUSC?" → metadata_query (pregunta sobre info básica)

IMPORTANTE: Si hay contexto de conversación previa y la pregunta es de seguimiento (ej: "Y el PIN?", "¿Y qué dice el PUSC?"):
- Si el contexto menciona un tema específico → specific_party
- Si el contexto no menciona tema específico → party_general_plan

Pregunta actual: {question}"""


def build_party_extraction_prompt(question: str, parties_info: str) -> str:
    """Build prompt for party extraction."""
    return f"""Extrae los partidos políticos mencionados en la pregunta.

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


def build_rag_response_prompt(question: str, contexts: list, intent: str) -> str:
    """Build prompt for final RAG response generation."""
    # Build context section with truncation
    truncate_length = settings.rag_context_truncate_length
    context_section = "---CONTEXT START---\n"

    for idx, ctx in enumerate(contexts):
        partido = ctx.payload.get("partido", "Unknown")
        text = ctx.payload.get("text", "")
        # Truncate each chunk to reduce tokens
        truncated_text = text[:truncate_length] + "..." if len(text) > truncate_length else text
        context_section += f"[Fuente {idx + 1}] Partido: {partido}\n{truncated_text}\n\n"

    context_section += "---CONTEXT END---"

    # Adjust instructions based on intent
    if intent == "general_comparison":
        specific_instructions = """
IMPORTANTE: Esta es una pregunta GENERAL o COMPARATIVA.
- Debes mencionar las propuestas de TODOS los partidos que aparecen en el contexto
- Organiza la respuesta por partido: "Según [Partido], ..."
- Si un partido no tiene información sobre el tema, no lo menciones
- Compara o contrasta las propuestas cuando sea relevante"""
    elif intent == "party_general_plan":
        specific_instructions = """
IMPORTANTE: Esta es una pregunta que solicita un RESUMEN GENERAL o COMPLETO del plan de un partido.
- Proporciona una visión INTEGRAL y COMPRENSIVA del plan basándote en todos los chunks disponibles
- Organiza la información por temas/áreas principales (educación, salud, economía, seguridad, etc.)
- Menciona los puntos clave y propuestas principales de cada área
- Usa un formato estructurado y fácil de leer
- Cita siempre: "Según [Partido], ..." """
    else:
        specific_instructions = """
IMPORTANTE: Esta es una pregunta sobre un partido ESPECÍFICO.
- Enfócate en las propuestas del partido mencionado
- Cita siempre: "Según [Partido], ..." """

    return f"""Eres un asistente especializado en planes de gobierno de Costa Rica 2026.

REGLAS ESTRICTAS:
1. Responde ÚNICAMENTE basándote en la información del contexto proporcionado
2. Cita SIEMPRE el partido político fuente
3. Si no hay información suficiente, responde: "No tengo información suficiente para responder esa pregunta"
4. Sé preciso, objetivo y neutral
5. No inventes datos ni hagas suposiciones
6. Usa un tono informativo y profesional

{specific_instructions}

{context_section}

Pregunta: {question}"""
