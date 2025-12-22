"""
Tests for the checkpointer/conversational memory functionality.
"""

from unittest.mock import patch


def _get_config_from_call(mock_graph):
    """Helper to extract config from mock_graph.invoke call args"""
    call_args = mock_graph.invoke.call_args
    return call_args[1].get("config") or call_args[0][1]


def test_checkpointer_with_session_id():
    """Test that run_agent uses session_id correctly for checkpointer"""

    # Mock the agent graph at a high level to avoid loading all dependencies
    with patch("app.agents.graph.agent_graph") as mock_graph:
        # Configure mock to return expected state
        mock_graph.invoke.return_value = {
            "question": "¿Qué propone el PLN sobre educación?",
            "intent": "specific_party",
            "parties": ["PLN"],
            "contexts": [{"partido": "PLN", "text": "El PLN propone educación de calidad"}],
            "answer": "El PLN tiene un plan educativo sólido.",
            "sources": [
                {
                    "partido": "PLN",
                    "filename": "pln_plan.txt",
                    "text": "El PLN propone educación de calidad",
                    "doc_id": "doc1",
                    "chunk_index": 0,
                    "score": 0.95,
                }
            ],
            "steps": ["Intent: specific_party", "Parties: ['PLN']", "Retrieved 1 chunks"],
            "langfuse_trace": None,
            "conversation_history": None,
        }

        from app.agents.graph import run_agent

        # First call with session_id
        result1 = run_agent(
            question="¿Qué propone el PLN sobre educación?", session_id="test-session-123"
        )

        assert result1 is not None
        assert "answer" in result1
        assert result1["answer"] == "El PLN tiene un plan educativo sólido."

        # Verify that agent_graph.invoke was called with correct config
        config = _get_config_from_call(mock_graph)
        assert config["configurable"]["thread_id"] == "test-session-123"

        # Second call with same session_id
        result2 = run_agent(question="¿Y sobre salud?", session_id="test-session-123")

        assert result2 is not None
        # Verify it uses the same thread_id
        config = _get_config_from_call(mock_graph)
        assert config["configurable"]["thread_id"] == "test-session-123"


def test_checkpointer_without_session_id():
    """Test that checkpointer works with default thread_id when no session_id provided"""

    with patch("app.agents.graph.agent_graph") as mock_graph:
        mock_graph.invoke.return_value = {
            "question": "¿Qué proponen los partidos sobre educación?",
            "intent": "general_comparison",
            "parties": [],
            "contexts": [],
            "answer": "Respuesta general sobre partidos.",
            "sources": [],
            "steps": ["Intent: general_comparison"],
            "langfuse_trace": None,
            "conversation_history": None,
        }

        from app.agents.graph import run_agent

        # Call without session_id
        result = run_agent(question="¿Qué proponen los partidos sobre educación?")

        assert result is not None
        assert "answer" in result
        assert result["answer"] == "Respuesta general sobre partidos."

        # Verify that thread_id defaults to "default"
        config = _get_config_from_call(mock_graph)
        assert config["configurable"]["thread_id"] == "default"


def test_checkpointer_different_sessions():
    """Test that different session_ids use different thread_ids"""

    with patch("app.agents.graph.agent_graph") as mock_graph:
        mock_graph.invoke.return_value = {
            "question": "¿Qué propone el PLN?",
            "intent": "specific_party",
            "parties": ["PLN"],
            "contexts": [],
            "answer": "Respuesta del PLN.",
            "sources": [],
            "steps": ["Intent: specific_party"],
            "langfuse_trace": None,
            "conversation_history": None,
        }

        from app.agents.graph import run_agent

        # Call with session_id A
        result_a = run_agent(question="¿Qué propone el PLN?", session_id="session-a")
        assert result_a is not None
        assert "answer" in result_a

        # Verify thread_id for session A
        config = _get_config_from_call(mock_graph)
        assert config["configurable"]["thread_id"] == "session-a"

        # Call with session_id B (different session)
        result_b = run_agent(question="¿Qué propone el PLN?", session_id="session-b")
        assert result_b is not None
        assert "answer" in result_b

        # Verify thread_id for session B
        config = _get_config_from_call(mock_graph)
        assert config["configurable"]["thread_id"] == "session-b"

        # Both should work independently with different thread_ids
        assert result_a["answer"] == result_b["answer"]
