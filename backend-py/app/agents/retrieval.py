"""
Retrieval strategies for RAG search.
"""

import logging
from typing import Any

from app.config import settings
from app.party_metadata import PARTIES_METADATA
from app.services.embeddings import generate_embedding
from app.services.qdrant import search_qdrant
from app.utils.logging import sanitize_for_log

logger = logging.getLogger(__name__)


def search_specific_party(question: str, party_abbr: str, langfuse_trace: Any = None) -> list:
    """
    Strategy 1: Search for specific topic within a party's plan.

    Returns focused chunks from the specified party.
    """
    logger.info(f"[Retrieval] Specific topic for party: {sanitize_for_log(party_abbr)}")

    from app.services.langfuse_service import langfuse_span

    with langfuse_span(
        langfuse_trace,
        name="rag_search_specific_party",
        metadata={
            "party": party_abbr,
            "strategy": "specific_party",
            "limit": settings.rag_specific_party_limit,
        },
        input_data={"question": question, "party": party_abbr},
    ) as span:
        query_vector = generate_embedding(question)
        contexts = search_qdrant(
            query_vector=query_vector,
            partido_filter=party_abbr,
            limit=settings.rag_specific_party_limit,
        )

        if span:
            try:
                span.end(
                    output={
                        "num_results": len(contexts),
                        "avg_score": (
                            sum(c.score for c in contexts) / len(contexts) if contexts else 0
                        ),
                        "scores": [c.score for c in contexts[:5]],
                    }
                )
            except Exception:
                pass

    return contexts


def search_general_party_plan(question: str, party_abbr: str, langfuse_trace: Any = None) -> list:
    """
    Strategy 2: Search for comprehensive overview of a party's plan.

    Returns more chunks to provide a complete picture.
    """
    logger.info(f"[Retrieval] General plan overview for party: {sanitize_for_log(party_abbr)}")

    from app.services.langfuse_service import langfuse_span

    with langfuse_span(
        langfuse_trace,
        name="rag_search_general_plan",
        metadata={
            "party": party_abbr,
            "strategy": "general_plan",
            "limit": settings.rag_general_plan_limit,
        },
        input_data={"question": question, "party": party_abbr},
    ) as span:
        query_vector = generate_embedding(question)
        contexts = search_qdrant(
            query_vector=query_vector,
            partido_filter=party_abbr,
            limit=settings.rag_general_plan_limit,
        )

        if span:
            try:
                span.end(
                    output={
                        "num_results": len(contexts),
                        "avg_score": (
                            sum(c.score for c in contexts) / len(contexts) if contexts else 0
                        ),
                        "scores": [c.score for c in contexts[:5]],
                    }
                )
            except Exception:
                pass

    return contexts


def search_general_comparison(question: str, langfuse_trace: Any = None) -> list:
    """
    Strategy 3: Search across all parties with fair distribution.

    Ensures all parties get representation in the results.
    """
    logger.info("[Retrieval] General comparison - per-party targeted search")

    from app.services.langfuse_service import langfuse_span

    with langfuse_span(
        langfuse_trace,
        name="rag_search_comparison",
        metadata={
            "strategy": "general_comparison",
            "per_party_limit": settings.rag_comparison_per_party,
            "max_total": settings.rag_comparison_max_total,
        },
        input_data={"question": question},
    ) as span:
        query_vector = generate_embedding(question)

        # Get party abbreviations
        try:
            party_abbrs = [p["abbreviation"] for p in PARTIES_METADATA]
        except Exception:
            party_abbrs = []

        per_party_limit = settings.rag_comparison_per_party
        max_contexts = settings.rag_comparison_max_total

        per_party_results: dict[str, list] = {}
        missing: list[str] = []

        # Query each party independently
        for abbr in party_abbrs:
            try:
                results = search_qdrant(
                    query_vector=query_vector, partido_filter=abbr, limit=per_party_limit
                )
                if results:
                    results = sorted(results, key=lambda r: r.score, reverse=True)
                    per_party_results[abbr] = results[:per_party_limit]
                else:
                    missing.append(abbr)
            except Exception:
                missing.append(abbr)

        # Assemble contexts fairly: round-robin distribution
        contexts: list = []

        # Round 1: One chunk per party
        for abbr in party_abbrs:
            party_chunks = per_party_results.get(abbr, [])
            if party_chunks:
                contexts.append(party_chunks[0])
            if len(contexts) >= max_contexts:
                break

        # Round 2: Second chunk per party (if budget allows)
        if len(contexts) < max_contexts:
            for abbr in party_abbrs:
                party_chunks = per_party_results.get(abbr, [])
                if len(party_chunks) > 1:
                    contexts.append(party_chunks[1])
                if len(contexts) >= max_contexts:
                    break

        # Log coverage
        covered = sorted({c.payload.get("partido", "Unknown") for c in contexts})
        logger.info(
            f"[Retrieval] Coverage: {len(covered)} parties -> {covered} "
            f"({len(contexts)} chunks); missing: {missing}"
        )

        if span:
            try:
                span.end(
                    output={
                        "num_results": len(contexts),
                        "parties_covered": covered,
                        "parties_missing": missing,
                        "avg_score": (
                            sum(c.score for c in contexts) / len(contexts) if contexts else 0
                        ),
                        "party_distribution": {
                            party: len([c for c in contexts if c.payload.get("partido") == party])
                            for party in covered
                        },
                    }
                )
            except Exception:
                pass

    return contexts


def search_default(question: str, langfuse_trace: Any = None) -> list:
    """
    Strategy 4: Default search when intent is unclear.
    """
    logger.info("[Retrieval] Default search (unclear intent)")

    from app.services.langfuse_service import langfuse_span

    with langfuse_span(
        langfuse_trace,
        name="rag_search_default",
        metadata={
            "strategy": "default",
            "limit": settings.rag_default_limit,
        },
        input_data={"question": question},
    ) as span:
        query_vector = generate_embedding(question)
        contexts = search_qdrant(
            query_vector=query_vector, partido_filter=None, limit=settings.rag_default_limit
        )

        if span:
            try:
                parties_found = list({c.payload.get("partido", "Unknown") for c in contexts})
                span.end(
                    output={
                        "num_results": len(contexts),
                        "parties_found": sorted(parties_found),
                        "avg_score": (
                            sum(c.score for c in contexts) / len(contexts) if contexts else 0
                        ),
                        "scores": [c.score for c in contexts[:5]],
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to update span: {e}")

    return contexts
