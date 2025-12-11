"""
Tests for authentication and rate limiting.
"""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest
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
                    "text": "Test response text",
                    "filename": "test.txt",
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


@pytest.fixture
def mock_llm_text():
    """Mock LLM text generation."""
    return "Test response from LLM"


def create_test_client(require_auth=False, api_key="test-api-key"):
    """Create a test client with authentication settings."""
    # Need to reload the module to pick up new settings
    import importlib
    import sys

    # Clear modules to force reload
    modules_to_clear = [k for k in sys.modules.keys() if k.startswith("app.")]
    for mod in modules_to_clear:
        del sys.modules[mod]

    # Mock settings before importing app
    with patch("app.config.settings") as mock_settings:
        mock_settings.require_auth = require_auth
        mock_settings.api_key = api_key
        mock_settings.max_requests_per_minute = 5
        mock_settings.langfuse_enabled = False
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""

        # Mock all the service dependencies
        with (
            patch("app.services.qdrant.get_qdrant_client") as mock_get_qdrant,
            patch("app.services.embeddings.generate_embedding") as mock_embed,
            patch("app.services.llm.get_client") as mock_get_llm_client,
            patch("app.agents.classifier.generate_text") as mock_classifier,
        ):
            # Setup mocks
            mock_client = MagicMock()
            mock_client.query_points.return_value = Mock(
                points=[
                    Mock(
                        id=1,
                        score=0.95,
                        payload={
                            "partido": "PLN",
                            "text": "Test response",
                            "filename": "test.txt",
                            "doc_id": "doc1",
                            "chunk_index": 0,
                        },
                    ),
                ]
            )
            mock_get_qdrant.return_value = mock_client
            mock_embed.return_value = [0.1, 0.2, 0.3]

            mock_llm_client = MagicMock()
            mock_response = MagicMock()
            mock_response.candidates = [MagicMock()]
            mock_response.candidates[0].content.parts = [
                MagicMock(text="Test LLM response")
            ]
            mock_llm_client.models.generate_content.return_value = mock_response
            mock_get_llm_client.return_value = mock_llm_client

            mock_classifier.side_effect = ["specific_party", "PLN"]

            from app.main import app

            return TestClient(app)


def test_health_endpoint_no_auth():
    """Test that health endpoint doesn't require authentication."""
    client = create_test_client(require_auth=True, api_key="secret-key")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ask_endpoint_without_auth_when_disabled():
    """Test that API works without authentication when auth is disabled."""
    client = create_test_client(require_auth=False)
    response = client.post(
        "/api/ask",
        json={"question": "¿Qué propone el PLN sobre educación?"},
    )
    assert response.status_code == 200
    assert "answer" in response.json()


def test_ask_endpoint_requires_auth_when_enabled():
    """Test that API requires authentication when enabled."""
    client = create_test_client(require_auth=True, api_key="secret-key")
    response = client.post(
        "/api/ask",
        json={"question": "¿Qué propone el PLN sobre educación?"},
    )
    assert response.status_code == 401
    assert "Missing API key" in response.json()["detail"]


def test_ask_endpoint_with_valid_api_key():
    """Test that API works with valid API key."""
    client = create_test_client(require_auth=True, api_key="secret-key")
    response = client.post(
        "/api/ask",
        json={"question": "¿Qué propone el PLN sobre educación?"},
        headers={"X-API-Key": "secret-key"},
    )
    assert response.status_code == 200
    assert "answer" in response.json()


def test_ask_endpoint_with_invalid_api_key():
    """Test that API rejects invalid API key."""
    client = create_test_client(require_auth=True, api_key="secret-key")
    response = client.post(
        "/api/ask",
        json={"question": "¿Qué propone el PLN sobre educación?"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]


def test_rate_limiting_enforced():
    """Test that rate limiting is enforced."""
    client = create_test_client(require_auth=False)

    # Make requests up to the limit (5 per minute in test config)
    responses = []
    for _ in range(6):
        response = client.post(
            "/api/ask",
            json={"question": "¿Qué propone el PLN sobre educación?"},
        )
        responses.append(response)
        # Small delay to avoid race conditions
        time.sleep(0.1)

    # First 5 should succeed
    success_count = sum(1 for r in responses if r.status_code == 200)
    rate_limited_count = sum(1 for r in responses if r.status_code == 429)

    # Should have at least one rate limited response
    assert rate_limited_count > 0, f"Expected rate limiting, got {success_count} successes"


def test_rate_limiting_with_authentication():
    """Test that rate limiting works with authentication enabled."""
    client = create_test_client(require_auth=True, api_key="secret-key")

    # Make multiple requests with valid API key
    responses = []
    for _ in range(6):
        response = client.post(
            "/api/ask",
            json={"question": "Test question"},
            headers={"X-API-Key": "secret-key"},
        )
        responses.append(response)
        time.sleep(0.1)

    # Should have both successful and rate-limited responses
    success_count = sum(1 for r in responses if r.status_code == 200)
    rate_limited_count = sum(1 for r in responses if r.status_code == 429)

    assert success_count > 0, "Should have some successful requests"
    assert rate_limited_count > 0, "Should have some rate-limited requests"
