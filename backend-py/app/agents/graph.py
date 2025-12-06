import logging
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.classifier import classify_intent, extract_parties
from app.services.embeddings import generate_embedding
from app.services.langfuse_service import langfuse_trace
from app.services.llm import generate_text
from app.services.qdrant import search_qdrant

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Shared state across all agents"""

    question: str
    intent: str
    parties: list[str]
    contexts: list
    answer: str
    sources: list
    steps: list[str]  # Track execution steps
    langfuse_trace: Any  # Langfuse trace for observability


def classify_intent_node(state: AgentState) -> AgentState:
    """Node: Classify user intent"""
    logger.info("[Agent] Classifying intent...")

    intent = classify_intent(state["question"])

    return {**state, "intent": intent, "steps": state.get("steps", []) + [f"Intent: {intent}"]}


def extract_parties_node(state: AgentState) -> AgentState:
    """Node: Extract party names from question"""
    logger.info("[Agent] Extracting parties...")

    parties = extract_parties(state["question"])

    return {**state, "parties": parties, "steps": state.get("steps", []) + [f"Parties: {parties}"]}


def rag_search_node(state: AgentState) -> AgentState:
    """Node: Execute RAG search with appropriate filters"""
    logger.info("[Agent] Executing RAG search...")

    # Generate embedding
    query_vector = generate_embedding(state["question"])

    # Determine search strategy based on intent
    if state["intent"] == "specific_party" and state.get("parties"):
        # Strategy 1: Specific party - get more chunks from that party
        partido_filter = state["parties"][0]
        logger.info(f"[Agent] Filtering by party: {partido_filter}")

        contexts = search_qdrant(query_vector=query_vector, partido_filter=partido_filter, limit=5)

    elif state["intent"] == "general_comparison":
        # Strategy 2: General question - get chunks from multiple parties
        logger.info("[Agent] General question - searching across all parties")

        # First, get top results without filter
        all_results = search_qdrant(
            query_vector=query_vector,
            partido_filter=None,
            limit=15,  # Get more results initially
        )

        # Group by party and take top 2-3 from each
        from collections import defaultdict

        by_party = defaultdict(list)

        for ctx in all_results:
            partido = ctx.payload.get("partido", "Unknown")
            by_party[partido].append(ctx)

        # Take top 2 chunks from each party (up to 5 parties)
        contexts = []
        for _partido, chunks in sorted(by_party.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
            contexts.extend(chunks[:2])  # Top 2 from each party

        # Sort by score to keep best overall
        contexts = sorted(contexts, key=lambda x: x.score, reverse=True)[:10]

        logger.info(
            f"[Agent] Retrieved chunks from {len(by_party)} parties: {list(by_party.keys())}"
        )

    else:
        # Strategy 3: Unclear - default search
        logger.info("[Agent] Unclear intent - default search")
        contexts = search_qdrant(query_vector=query_vector, partido_filter=None, limit=5)

    return {
        **state,
        "contexts": contexts,
        "steps": state.get("steps", []) + [f"Retrieved {len(contexts)} chunks"],
    }


def generate_response_node(state: AgentState) -> AgentState:
    """Node: Generate final response with citations"""
    logger.info("[Agent] Generating response...")

    # Build context section (truncate to avoid token limits)
    context_section = "---CONTEXT START---\n"
    for idx, ctx in enumerate(state["contexts"]):
        partido = ctx.payload.get("partido", "Unknown")
        text = ctx.payload.get("text", "")
        # Truncate each chunk to max 500 chars to reduce tokens
        truncated_text = text[:500] + "..." if len(text) > 500 else text
        context_section += f"[Fuente {idx + 1}] Partido: {partido}\n{truncated_text}\n\n"
    context_section += "---CONTEXT END---"

    # Adjust instructions based on intent
    if state["intent"] == "general_comparison":
        specific_instructions = """
IMPORTANTE: Esta es una pregunta GENERAL o COMPARATIVA.
- Debes mencionar las propuestas de TODOS los partidos que aparecen en el contexto
- Organiza la respuesta por partido: "Según [Partido], ..."
- Si un partido no tiene información sobre el tema, no lo menciones
- Compara o contrasta las propuestas cuando sea relevante"""
    else:
        specific_instructions = """
IMPORTANTE: Esta es una pregunta sobre un partido ESPECÍFICO.
- Enfócate en las propuestas del partido mencionado
- Cita siempre: "Según [Partido], ..." """

    # Build complete prompt
    prompt = f"""Eres un asistente especializado en planes de gobierno de Costa Rica 2026.

REGLAS ESTRICTAS:
1. Responde ÚNICAMENTE basándote en la información del contexto proporcionado
2. Cita SIEMPRE el partido político fuente
3. Si no hay información suficiente, responde: "No tengo información suficiente para responder esa pregunta"
4. Sé preciso, objetivo y neutral
5. No inventes datos ni hagas suposiciones
6. Usa un tono informativo y profesional

{specific_instructions}

{context_section}

Pregunta: {state["question"]}"""

    try:
        logger.info(f"[Agent] Invoking LLM with {len(state['contexts'])} contexts...")
        logger.info(f"[Agent] Intent: {state['intent']}")

        # Pass Langfuse trace to LLM for observability
        trace = state.get("langfuse_trace")
        answer = generate_text(prompt, langfuse_trace=trace)

        logger.info(f"[Agent] Generated answer length: {len(answer)}")
        logger.info(f"[Agent] Answer preview: {answer[:200]}")

        # Extract sources
        sources = []
        for ctx in state["contexts"]:
            sources.append(
                {
                    "partido": ctx.payload.get("partido", "Unknown"),
                    "filename": ctx.payload.get("filename", ""),
                    "text": ctx.payload.get("text", "")[:200] + "...",
                    "doc_id": ctx.payload.get("doc_id", ""),
                    "chunk_index": ctx.payload.get("chunk_index", 0),
                    "score": ctx.score,
                }
            )

        return {
            **state,
            "answer": answer,
            "sources": sources,
            "steps": state.get("steps", []) + ["Response generated"],
        }

    except Exception as e:
        logger.error(f"[Agent] Error generating response: {e}", exc_info=True)
        return {
            **state,
            "answer": f"Error al generar respuesta: {str(e)}",
            "sources": [],
            "steps": state.get("steps", []) + [f"Error: {str(e)}"],
        }


def route_by_intent(state: AgentState) -> str:
    """Conditional edge: Route based on intent"""
    intent = state.get("intent", "unclear")

    if intent == "specific_party":
        return "extract_parties"
    else:
        # For general or unclear, go directly to RAG
        return "rag_search"


def build_agent_graph():
    """Build the LangGraph agent workflow"""

    # Create graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("extract_parties", extract_parties_node)
    workflow.add_node("rag_search", rag_search_node)
    workflow.add_node("generate_response", generate_response_node)

    # Set entry point
    workflow.set_entry_point("classify_intent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {"extract_parties": "extract_parties", "rag_search": "rag_search"},
    )

    # Add regular edges
    workflow.add_edge("extract_parties", "rag_search")
    workflow.add_edge("rag_search", "generate_response")
    workflow.add_edge("generate_response", END)

    # Compile
    return workflow.compile()


# Create the compiled graph
agent_graph = build_agent_graph()


def run_agent(question: str, session_id: str | None = None) -> dict:
    """
    Run the agent graph with a question

    Args:
        question: The user's question
        session_id: Optional session ID for tracking

    Returns: Final state with answer, sources, and trace
    """
    logger.info(f"[Agent] Starting workflow for question: {question[:100]}...")

    # Create Langfuse trace for observability
    with langfuse_trace(
        name="agent-workflow",
        session_id=session_id,
        metadata={"question_length": len(question)},
    ) as trace:
        initial_state = {
            "question": question,
            "intent": "",
            "parties": [],
            "contexts": [],
            "answer": "",
            "sources": [],
            "steps": [],
            "langfuse_trace": trace,
        }

        # Run the graph
        final_state = agent_graph.invoke(initial_state)

        # Update trace with final results if available
        if trace:
            try:
                trace.update(
                    output={
                        "answer_length": len(final_state.get("answer", "")),
                        "sources_count": len(final_state.get("sources", [])),
                        "intent": final_state.get("intent", ""),
                        "parties_detected": final_state.get("parties", []),
                        "steps": final_state.get("steps", []),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to update Langfuse trace: {e}")

    logger.info(f"[Agent] Workflow completed. Steps: {final_state['steps']}")

    return final_state
