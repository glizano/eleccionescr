"""
Tests for the checkpointer/conversational memory functionality.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client."""
    mock_client = MagicMock()
    mock_client.query_points.return_value = Mock(
        points=[
            Mock(
                id=1,
                score=0.95,
                payload={
                    "partido": "PLN",
                    "text": "El PLN propone educación de calidad",
                    "filename": "pln_plan.txt",
                    "doc_id": "doc1",
                    "chunk_index": 0,
                },
            ),
        ]
    )
    return mock_client


@pytest.fixture
def mock_embedding_vector():
    """Mock embedding generation."""
    return [0.1, 0.2, 0.3, 0.4, 0.5]


def test_checkpointer_with_session_id(mock_qdrant_client, mock_embedding_vector):
    """Test that checkpointer uses session_id as thread_id"""
    from app.agents.graph import run_agent

    with (
        patch("app.services.qdrant.get_qdrant_client") as mock_get_qdrant,
        patch("app.services.embeddings.generate_embedding") as mock_embed,
        patch("app.services.llm.generate_text") as mock_generate_text,
        patch("app.agents.classifier.classify_intent") as mock_classifier,
        patch("app.agents.classifier.extract_parties") as mock_extractor,
    ):
        mock_get_qdrant.return_value = mock_qdrant_client
        mock_embed.return_value = mock_embedding_vector
        mock_generate_text.return_value = "El PLN tiene un plan educativo sólido."
        mock_classifier.return_value = "specific_party"
        mock_extractor.return_value = ["PLN"]

        # First call with session_id
        result1 = run_agent(
            question="¿Qué propone el PLN sobre educación?", session_id="test-session-123"
        )

        assert result1 is not None
        assert "answer" in result1
        assert result1["answer"] == "El PLN tiene un plan educativo sólido."

        # Second call with same session_id should maintain context
        result2 = run_agent(question="¿Y sobre salud?", session_id="test-session-123")

        assert result2 is not None
        assert "answer" in result2


def test_checkpointer_without_session_id(mock_qdrant_client, mock_embedding_vector):
    """Test that checkpointer works with default thread_id when no session_id provided"""
    from app.agents.graph import run_agent

    with (
        patch("app.services.qdrant.get_qdrant_client") as mock_get_qdrant,
        patch("app.services.embeddings.generate_embedding") as mock_embed,
        patch("app.services.llm.generate_text") as mock_generate_text,
        patch("app.agents.classifier.classify_intent") as mock_classifier,
    ):
        mock_get_qdrant.return_value = mock_qdrant_client
        mock_embed.return_value = mock_embedding_vector
        mock_generate_text.return_value = "Respuesta general sobre partidos."
        mock_classifier.return_value = "general_comparison"

        # Call without session_id
        result = run_agent(question="¿Qué proponen los partidos sobre educación?")

        assert result is not None
        assert "answer" in result
        assert result["answer"] == "Respuesta general sobre partidos."


def test_checkpointer_different_sessions(mock_qdrant_client, mock_embedding_vector):
    """Test that different session_ids maintain separate checkpointed states"""
    from app.agents.graph import run_agent

    with (
        patch("app.services.qdrant.get_qdrant_client") as mock_get_qdrant,
        patch("app.services.embeddings.generate_embedding") as mock_embed,
        patch("app.services.llm.generate_text") as mock_generate_text,
        patch("app.agents.classifier.classify_intent") as mock_classifier,
        patch("app.agents.classifier.extract_parties") as mock_extractor,
    ):
        mock_get_qdrant.return_value = mock_qdrant_client
        mock_embed.return_value = mock_embedding_vector
        mock_generate_text.return_value = "Respuesta del PLN."
        mock_classifier.return_value = "specific_party"
        mock_extractor.return_value = ["PLN"]

        # Call with session_id A
        result_a = run_agent(question="¿Qué propone el PLN?", session_id="session-a")
        assert result_a is not None
        assert "answer" in result_a

        # Call with session_id B (different session)
        result_b = run_agent(question="¿Qué propone el PLN?", session_id="session-b")
        assert result_b is not None
        assert "answer" in result_b

        # Both should work independently
        assert result_a["answer"] == result_b["answer"]
