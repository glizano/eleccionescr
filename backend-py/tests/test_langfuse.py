"""
Tests for the Langfuse service integration.
"""

from unittest.mock import patch

import pytest


def test_langfuse_disabled_by_default():
    """Test that Langfuse client returns None when disabled."""
    from app.services.langfuse_service import get_langfuse_client

    # Clear the cache to ensure fresh state
    get_langfuse_client.cache_clear()

    with patch("app.services.langfuse_service.settings") as mock_settings:
        mock_settings.langfuse_enabled = False
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""

        client = get_langfuse_client()
        assert client is None


def test_langfuse_trace_context_manager_disabled():
    """Test that langfuse_trace yields None when disabled."""
    from app.services.langfuse_service import get_langfuse_client, langfuse_trace

    # Clear the cache
    get_langfuse_client.cache_clear()

    with patch("app.services.langfuse_service.settings") as mock_settings:
        mock_settings.langfuse_enabled = False
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""

        with langfuse_trace("test-trace") as trace:
            assert trace is None


def test_langfuse_missing_keys_disables_client():
    """Test that missing keys result in None client even if enabled."""
    from app.services.langfuse_service import get_langfuse_client

    # Clear the cache
    get_langfuse_client.cache_clear()

    with patch("app.services.langfuse_service.settings") as mock_settings:
        mock_settings.langfuse_enabled = True
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""
        mock_settings.langfuse_host = "https://cloud.langfuse.com"

        client = get_langfuse_client()
        assert client is None


def test_create_generation_returns_none_when_trace_is_none():
    """Test that create_generation returns None when trace is None."""
    from app.services.langfuse_service import create_generation

    result = create_generation(
        trace=None,
        name="test-generation",
        model="gemini-2.5-flash",
        input_text="test input",
    )
    assert result is None


def test_shutdown_langfuse_handles_no_client():
    """Test that shutdown_langfuse doesn't fail when no client exists."""
    from app.services.langfuse_service import get_langfuse_client, shutdown_langfuse

    # Clear the cache
    get_langfuse_client.cache_clear()

    with patch("app.services.langfuse_service.settings") as mock_settings:
        mock_settings.langfuse_enabled = False
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""

        # Should not raise an exception
        shutdown_langfuse()


@pytest.mark.asyncio
async def test_llm_generate_text_with_none_trace():
    """Test that generate_text works with langfuse_trace=None."""
    from unittest.mock import MagicMock

    with patch("app.services.llm.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "Test response"
        mock_candidate.content.parts = [mock_part]
        mock_response.candidates = [mock_candidate]
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        from app.services.llm import generate_text

        result = generate_text("Test prompt", langfuse_trace=None)
        assert result == "Test response"
