"""
Tests for rate limiting in public API.
"""

import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with mocked agent."""
    from app.main import app

    # Mock the run_agent function to avoid complex dependencies
    with patch("app.main.run_agent") as mock_run_agent:
        mock_run_agent.return_value = {
            "answer": "Test answer from agent",
            "sources": [
                {
                    "partido": "PLN",
                    "filename": "test.txt",
                    "text": "Test source",
                    "doc_id": "doc1",
                    "chunk_index": 0,
                    "score": 0.95,
                }
            ],
            "contexts": ["context1", "context2"],
            "intent": "specific_party",
            "parties": ["PLN"],
            "steps": ["step1", "step2"],
        }

        yield TestClient(app)


def test_health_endpoint_always_available(client):
    """Test that health endpoint is always available without rate limiting."""

    # Make many requests to health endpoint
    for _ in range(10):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_ask_endpoint_public_access(client):
    """Test that /api/ask endpoint is publicly accessible without authentication."""

    response = client.post(
        "/api/ask",
        json={"question": "¿Qué propone el PLN sobre educación?"},
    )
    assert response.status_code == 200
    assert "answer" in response.json()
    assert "sources" in response.json()


def test_rate_limiting_per_minute(client):
    """Test that rate limiting per minute is enforced."""

    # Make many requests to trigger rate limiting (default is 10/min)
    responses = []
    for i in range(15):
        response = client.post(
            "/api/ask",
            json={"question": f"Test question {i}"},
        )
        responses.append(response)
        # Very small delay to avoid race conditions
        time.sleep(0.05)

    # Count success and rate-limited responses
    success_count = sum(1 for r in responses if r.status_code == 200)
    rate_limited_count = sum(1 for r in responses if r.status_code == 429)

    # Should have some rate limited responses
    assert rate_limited_count > 0, (
        f"Expected rate limiting, got {success_count} successes, {rate_limited_count} rate limited"
    )
    assert success_count > 0, "Should have some successful requests"


def test_rate_limiting_with_session_id(client):
    """Test that rate limiting works correctly with session_id for Langfuse tracking."""

    # Make requests with session_id
    responses = []
    for i in range(6):
        response = client.post(
            "/api/ask",
            json={
                "question": f"Test question {i}",
                "session_id": "test-session-123",
            },
        )
        responses.append(response)
        time.sleep(0.1)

    # Should still be rate limited by IP, not session_id
    rate_limited_count = sum(1 for r in responses if r.status_code == 429)

    assert rate_limited_count > 0, "Should have rate-limited requests"


def test_parties_endpoint_public(client):
    """Test that /api/parties endpoint is publicly accessible."""

    response = client.get("/api/parties")
    assert response.status_code == 200
    assert "parties" in response.json()
    assert isinstance(response.json()["parties"], list)
