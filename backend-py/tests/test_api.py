"""
Tests for the backend API endpoints.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient


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
                    "text": "El PLN propone una reforma educativa integral",
                    "filename": "pln_education.txt",
                    "doc_id": "doc1",
                    "chunk_index": 0,
                },
            ),
            Mock(
                id=2,
                score=0.87,
                payload={
                    "partido": "PUSC",
                    "text": "El PUSC enfatiza la educación técnica",
                    "filename": "pusc_education.txt",
                    "doc_id": "doc2",
                    "chunk_index": 1,
                },
            ),
        ]
    )
    return mock_client


@pytest.fixture
def mock_embedding_vector():
    """Mock embedding generation."""
    return [0.1, 0.2, 0.3, 0.4, 0.5]


@pytest.fixture
def mock_llm_text():
    """Mock LLM text generation."""
    return (
        "El PLN propone una reforma educativa integral que incluye la modernización "
        "de infraestructura y la capacitación docente. "
        "El PUSC enfatiza la educación técnica como complemento a la educación tradicional."
    )


@pytest.fixture
def client(mock_qdrant_client, mock_embedding_vector, mock_llm_text):
    """Create a test client with all services mocked."""
    from app.main import app
    from app.services import llm as llm_module

    # Clear LLM client cache before patching
    if hasattr(llm_module.get_client, 'cache_clear'):
        llm_module.get_client.cache_clear()

    patcher_client_getter = patch("app.services.qdrant.get_qdrant_client")
    patcher_embed = patch("app.services.embeddings.generate_embedding")
    patcher_llm_client = patch("app.services.llm.get_client")
    patcher_classifier = patch("app.agents.classifier.generate_text")

    mock_get_qdrant = patcher_client_getter.start()
    mock_embed = patcher_embed.start()
    mock_get_llm_client = patcher_llm_client.start()
    mock_classifier = patcher_classifier.start()

    # Mock the Qdrant client getter to return our mock client
    mock_get_qdrant.return_value = mock_qdrant_client
    mock_embed.return_value = mock_embedding_vector
    
    # Mock the LLM client to return a mock that generates our text
    mock_llm_client = MagicMock()
    mock_response = MagicMock()
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock(text=mock_llm_text)]
    mock_llm_client.models.generate_content.return_value = mock_response
    mock_get_llm_client.return_value = mock_llm_client
    
    mock_classifier.side_effect = ["specific_party", "PLN"]

    yield TestClient(app)

    patcher_client_getter.stop()
    patcher_embed.stop()
    patcher_llm_client.stop()
    patcher_classifier.stop()


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_parties_endpoint(client):
    """Test the parties list endpoint."""
    response = client.get("/api/parties")
    assert response.status_code == 200
    data = response.json()
    assert "parties" in data
    assert isinstance(data["parties"], list)
    assert "PLN" in data["parties"]
    assert "PUSC" in data["parties"]


def test_ask_endpoint_specific_party(client):
    """Test asking a question about a specific party."""
    response = client.post(
        "/api/ask",
        json={"question": "¿Qué propone el PLN sobre educación?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert "agent_trace" in data
    trace = data["agent_trace"]
    assert "intent" in trace
    assert trace["intent"] in ["specific_party", "general_comparison"]
    assert len(data["sources"]) > 0
    assert data["sources"][0]["partido"] in ["PLN", "PUSC"]


def test_ask_endpoint_general_question(client):
    """Test asking a general/comparative question."""
    response = client.post(
        "/api/ask",
        json={"question": "¿Qué proponen los partidos sobre salud?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert "agent_trace" in data
    assert len(data["sources"]) > 0


def test_ask_endpoint_empty_question(client):
    """Test that empty questions are rejected."""
    response = client.post(
        "/api/ask",
        json={"question": ""},
    )
    assert response.status_code == 422


def test_ask_endpoint_missing_question(client):
    """Test that missing question field is rejected."""
    response = client.post(
        "/api/ask",
        json={},
    )
    assert response.status_code == 422
