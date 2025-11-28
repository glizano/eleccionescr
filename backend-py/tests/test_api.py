"""
Tests for the backend API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from app.main import app

    return TestClient(app)


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
    # Check for known parties
    assert "PLN" in data["parties"]
    assert "PUSC" in data["parties"]


@pytest.mark.asyncio
async def test_ask_endpoint_specific_party(client):
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
    # Check agent trace
    trace = data["agent_trace"]
    assert "intent" in trace
    assert trace["intent"] in ["specific_party", "general_comparison"]


@pytest.mark.asyncio
async def test_ask_endpoint_general_question(client):
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


def test_ask_endpoint_empty_question(client):
    """Test that empty questions are rejected."""
    response = client.post(
        "/api/ask",
        json={"question": ""},
    )
    assert response.status_code == 422  # Validation error


def test_ask_endpoint_missing_question(client):
    """Test that missing question field is rejected."""
    response = client.post(
        "/api/ask",
        json={},
    )
    assert response.status_code == 422  # Validation error
