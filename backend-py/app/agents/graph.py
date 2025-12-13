import logging
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.classifier import classify_intent, extract_parties
from app.agents.prompts import build_rag_response_prompt
from app.agents.retrieval import (
    search_default,
    search_general_comparison,
    search_general_party_plan,
    search_specific_party,
)
from app.party_metadata import CANDIDATE_TO_PARTY, PARTIES_METADATA, PARTY_NAME_TO_ABBR
from app.services.langfuse_service import langfuse_trace
from app.services.llm import generate_text

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
    conversation_history: str | None  # Context from previous messages


def rate_limited_node(state: AgentState) -> AgentState:
    """Node: Stop workflow when LLM is rate limited."""
    logger.warning("[Agent] Workflow stopped due to LLM rate limit/resource exhaustion")

    return {
        **state,
        "answer": "El servicio de IA está ocupado (429). Intenta de nuevo en unos segundos.",
        "sources": [],
        "contexts": [],
        "steps": state.get("steps", []) + ["Rate limited"],
    }


def classify_intent_node(state: AgentState) -> AgentState:
    """Node: Classify user intent"""
    logger.info("[Agent] Classifying intent...")

    conversation_history = state.get("conversation_history")
    intent = classify_intent(state["question"], conversation_history)

    return {**state, "intent": intent, "steps": state.get("steps", []) + [f"Intent: {intent}"]}


def extract_parties_node(state: AgentState) -> AgentState:
    """Node: Extract party names from question"""
    logger.info("[Agent] Extracting parties...")

    parties = extract_parties(state["question"])

    return {**state, "parties": parties, "steps": state.get("steps", []) + [f"Parties: {parties}"]}


def rag_search_node(state: AgentState) -> AgentState:
    """Node: Execute RAG search with appropriate filters"""
    logger.info("[Agent] Executing RAG search...")

    question = state["question"]
    intent = state["intent"]
    parties = state.get("parties", [])

    # Determine search strategy based on intent
    if intent == "specific_party" and parties:
        contexts = search_specific_party(question, parties[0])
    elif intent == "party_general_plan" and parties:
        contexts = search_general_party_plan(question, parties[0])
    elif intent == "general_comparison":
        contexts = search_general_comparison(question)
    else:
        contexts = search_default(question)

    return {
        **state,
        "contexts": contexts,
        "steps": state.get("steps", []) + [f"Retrieved {len(contexts)} chunks"],
    }


def generate_response_node(state: AgentState) -> AgentState:
    """Node: Generate final response with citations"""
    logger.info("[Agent] Generating response...")

    # Build prompt using centralized builder
    prompt = build_rag_response_prompt(
        question=state["question"], contexts=state["contexts"], intent=state["intent"]
    )

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


def metadata_query_node(state: AgentState) -> AgentState:
    """Node: Answer metadata questions directly without RAG"""
    logger.info("[Agent] Answering metadata query...")

    question = state["question"].lower()

    # Build comprehensive answer from metadata
    answer_parts = []

    # Check if asking about a specific candidate
    for candidate, party_abbr in CANDIDATE_TO_PARTY.items():
        if any(part.lower() in question for part in candidate.split() if len(part) > 4):
            party_data = next(
                (p for p in PARTIES_METADATA if p["abbreviation"] == party_abbr), None
            )
            if party_data:
                answer_parts.append(
                    f"{candidate} es el candidato presidencial del partido {party_data['name']} ({party_abbr})."
                )

    # Check if asking about a specific party abbreviation
    for party in PARTIES_METADATA:
        abbr = party["abbreviation"]
        if abbr.lower() in question:
            if "candidato" in question:
                answer_parts.append(
                    f"El candidato presidencial del {party['name']} ({abbr}) es {party['candidate']}."
                )
            elif "nombre" in question or "significa" in question:
                answer_parts.append(f"{abbr} significa {party['name']}.")
            elif "partido" in question and not answer_parts:  # General info
                answer_parts.append(
                    f"El {party['name']} ({abbr}) tiene como candidato presidencial a {party['candidate']}."
                )

    # Check if asking about party by full name
    for party_name, party_abbr in PARTY_NAME_TO_ABBR.items():
        if party_name.lower() in question:
            party_data = next(
                (p for p in PARTIES_METADATA if p["abbreviation"] == party_abbr), None
            )
            if party_data and not answer_parts:
                if "candidato" in question:
                    answer_parts.append(
                        f"El candidato presidencial del {party_name} es {party_data['candidate']}."
                    )
                elif "sigla" in question:
                    answer_parts.append(f"La sigla del {party_name} es {party_abbr}.")

    # Fallback: provide general info about all parties
    if not answer_parts:
        if "candidatos" in question or "partidos" in question:
            answer_parts.append(
                "Los 20 partidos inscritos para las elecciones de Costa Rica 2026 son:\n\n"
            )
            for party in PARTIES_METADATA:
                answer_parts.append(
                    f"- **{party['abbreviation']}** ({party['name']}): {party['candidate']}"
                )
        else:
            answer_parts.append(
                "No pude identificar exactamente qué información necesitas. ¿Podrías ser más específico?"
            )

    answer = "\n".join(answer_parts)

    logger.info(f"[Agent] Metadata answer generated: {answer[:100]}...")

    return {
        **state,
        "answer": answer,
        "sources": [],  # No sources for metadata queries
        "contexts": [],
        "steps": state.get("steps", []) + ["Answered from metadata"],
    }


def route_by_intent(state: AgentState) -> str:
    """Conditional edge: Route based on intent"""
    intent = state.get("intent", "unclear")

    if intent == "rate_limited":
        return "rate_limited"
    if intent == "metadata_query":
        return "metadata_query"
    elif intent in ["specific_party", "party_general_plan"]:
        return "extract_parties"
    else:
        # For general_comparison or unclear, go directly to RAG
        return "rag_search"


def build_agent_graph():
    """Build the LangGraph agent workflow"""

    # Create graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("rate_limited", rate_limited_node)
    workflow.add_node("extract_parties", extract_parties_node)
    workflow.add_node("metadata_query", metadata_query_node)
    workflow.add_node("rag_search", rag_search_node)
    workflow.add_node("generate_response", generate_response_node)

    # Set entry point
    workflow.set_entry_point("classify_intent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "rate_limited": "rate_limited",
            "metadata_query": "metadata_query",
            "extract_parties": "extract_parties",
            "rag_search": "rag_search",
        },
    )

    # Add regular edges
    workflow.add_edge("extract_parties", "rag_search")
    workflow.add_edge("rag_search", "generate_response")
    workflow.add_edge("generate_response", END)
    workflow.add_edge("metadata_query", END)  # Metadata queries end directly
    workflow.add_edge("rate_limited", END)

    # Compile
    return workflow.compile()


# Create the compiled graph
agent_graph = build_agent_graph()


def run_agent(
    question: str, session_id: str | None = None, conversation_history: str | None = None
) -> dict:
    """
    Run the agent graph with a question

    Args:
        question: The user's question
        session_id: Optional session ID for tracking
        conversation_history: Optional context from previous messages

    Returns: Final state with answer, sources, and trace
    """
    logger.info(f"[Agent] Starting workflow for question: {question[:100]}...")

    # Create Langfuse trace for observability
    with langfuse_trace(
        name="agent-workflow",
        session_id=session_id,
        metadata={
            "question_length": len(question),
            "has_history": conversation_history is not None,
        },
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
            "conversation_history": conversation_history,
        }

        # Run the graph
        final_state = agent_graph.invoke(initial_state)

        # Update Langfuse trace with final workflow results (for analytics/debugging)
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


async def run_agent_stream(
    question: str, session_id: str | None = None, conversation_history: str | None = None
):
    """
    Run agent workflow with streaming response.

    Yields chunks as they're generated:
    - {"type": "token", "content": "..."} for each text token
    - {"type": "metadata", "data": {...}} for sources and trace at the end
    """
    with langfuse_trace(
        name="agent_workflow_stream",
        session_id=session_id,
        metadata={"question": question, "has_history": conversation_history is not None},
    ) as trace:
        # First, run the full workflow to get context and sources
        initial_state = {
            "question": question,
            "intent": "",
            "parties": [],
            "contexts": [],
            "answer": "",
            "sources": [],
            "steps": [],
            "langfuse_trace": trace,
            "conversation_history": conversation_history,
        }

        # Run through classification and retrieval
        logger.info("[Agent Stream] Starting workflow...")

        # Classify intent
        state = classify_intent_node(initial_state)

        # Route based on intent and extract parties if needed
        intent = state["intent"]
        if intent in ["specific_party", "party_general_plan"]:
            state = extract_parties_node(state)

        # Execute RAG search
        state = rag_search_node(state)

        # Now stream the answer generation
        logger.info("[Agent Stream] Streaming answer generation...")

        # Use streaming LLM
        from app.services.llm import generate_text_stream

        prompt = build_rag_response_prompt(
            state["question"], state["contexts"], state.get("conversation_history")
        )

        full_answer = ""
        async for token in generate_text_stream(prompt):
            full_answer += token
            yield {"type": "token", "content": token}

        # Build sources from contexts (Qdrant ScoredPoint objects)
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

        # Update state with final answer
        state["answer"] = full_answer
        state["sources"] = sources
        state["steps"].append("Generated streaming answer")

        # Update Langfuse trace
        if trace:
            try:
                trace.update(
                    output={
                        "answer_length": len(full_answer),
                        "sources_count": len(sources),
                        "intent": state["intent"],
                        "parties_detected": state["parties"],
                        "steps": state["steps"],
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to update Langfuse trace: {e}")

        # Send metadata at the end
        yield {
            "type": "metadata",
            "data": {
                "sources": sources,
                "agent_trace": {
                    "intent": state["intent"],
                    "parties_detected": state["parties"],
                    "chunks_retrieved": len(state["contexts"]),
                    "steps": state["steps"],
                },
                "session_id": session_id,
            },
        }

        logger.info(f"[Agent Stream] Workflow completed. Steps: {state['steps']}")
