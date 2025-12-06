"""
Tests for LLM providers.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.llm_providers.base import LLMProvider
from app.services.llm_providers.factory import create_llm_provider
from app.services.llm_providers.google_provider import GoogleProvider
from app.services.llm_providers.openai_provider import OpenAIProvider


class TestLLMProviderInterface:
    """Test the LLM provider interface."""

    def test_llm_provider_is_abstract(self):
        """Test that LLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LLMProvider()

    def test_provider_must_implement_generate_text(self):
        """Test that providers must implement generate_text method."""

        class IncompleteProvider(LLMProvider):
            @property
            def model_name(self) -> str:
                return "test"

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_provider_must_implement_model_name(self):
        """Test that providers must implement model_name property."""

        class IncompleteProvider(LLMProvider):
            def generate_text(self, prompt: str) -> str:
                return "test"

        with pytest.raises(TypeError):
            IncompleteProvider()


class TestGoogleProvider:
    """Test the Google Gemini provider."""

    @patch("app.services.llm_providers.google_provider.genai.Client")
    def test_google_provider_init(self, mock_client):
        """Test GoogleProvider initialization."""
        provider = GoogleProvider(api_key="test_key", model="gemini-2.5-flash")

        assert provider.model_name == "gemini-2.5-flash"
        mock_client.assert_called_once_with(api_key="test_key")

    @patch("app.services.llm_providers.google_provider.genai.Client")
    def test_google_provider_generate_text_success(self, mock_client):
        """Test successful text generation with Google provider."""
        # Setup mock response
        mock_part = MagicMock()
        mock_part.text = "Generated response"

        mock_content = MagicMock()
        mock_content.parts = [mock_part]

        mock_candidate = MagicMock()
        mock_candidate.content = mock_content
        mock_candidate.finish_reason = "STOP"

        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_client_instance

        provider = GoogleProvider(api_key="test_key")
        result = provider.generate_text("Test prompt")

        assert result == "Generated response"

    @patch("app.services.llm_providers.google_provider.genai.Client")
    def test_google_provider_generate_text_error(self, mock_client):
        """Test error handling in Google provider."""
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.side_effect = Exception("API Error")
        mock_client.return_value = mock_client_instance

        provider = GoogleProvider(api_key="test_key")
        result = provider.generate_text("Test prompt")

        assert "Error al generar respuesta" in result


class TestOpenAIProvider:
    """Test the OpenAI provider."""

    @patch("app.services.llm_providers.openai_provider.OpenAI")
    def test_openai_provider_init(self, mock_openai):
        """Test OpenAIProvider initialization."""
        provider = OpenAIProvider(api_key="test_key", model="gpt-4o-mini")

        assert provider.model_name == "gpt-4o-mini"
        mock_openai.assert_called_once_with(api_key="test_key")

    @patch("app.services.llm_providers.openai_provider.OpenAI")
    def test_openai_provider_generate_text_success(self, mock_openai):
        """Test successful text generation with OpenAI provider."""
        # Setup mock response
        mock_message = MagicMock()
        mock_message.content = "Generated response"

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client_instance

        provider = OpenAIProvider(api_key="test_key")
        result = provider.generate_text("Test prompt")

        assert result == "Generated response"

    @patch("app.services.llm_providers.openai_provider.OpenAI")
    def test_openai_provider_generate_text_error(self, mock_openai):
        """Test error handling in OpenAI provider."""
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client_instance

        provider = OpenAIProvider(api_key="test_key")
        result = provider.generate_text("Test prompt")

        assert "Error al generar respuesta" in result


class TestProviderFactory:
    """Test the provider factory."""

    @patch("app.services.llm_providers.factory.settings")
    @patch("app.services.llm_providers.google_provider.genai.Client")
    def test_create_google_provider(self, mock_genai, mock_settings):
        """Test creating a Google provider."""
        mock_settings.llm_provider = "google"
        mock_settings.google_api_key = "test_key"
        mock_settings.google_model = "gemini-2.5-flash"

        provider = create_llm_provider("google")

        assert isinstance(provider, GoogleProvider)
        assert provider.model_name == "gemini-2.5-flash"

    @patch("app.services.llm_providers.factory.settings")
    @patch("app.services.llm_providers.openai_provider.OpenAI")
    def test_create_openai_provider(self, mock_openai, mock_settings):
        """Test creating an OpenAI provider."""
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "test_key"
        mock_settings.openai_model = "gpt-4o-mini"

        provider = create_llm_provider("openai")

        assert isinstance(provider, OpenAIProvider)
        assert provider.model_name == "gpt-4o-mini"

    @patch("app.services.llm_providers.factory.settings")
    def test_create_provider_missing_google_key(self, mock_settings):
        """Test error when Google API key is missing."""
        mock_settings.llm_provider = "google"
        mock_settings.google_api_key = ""

        with pytest.raises(ValueError, match="Google API key is required"):
            create_llm_provider("google")

    @patch("app.services.llm_providers.factory.settings")
    def test_create_provider_missing_openai_key(self, mock_settings):
        """Test error when OpenAI API key is missing."""
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = ""

        with pytest.raises(ValueError, match="OpenAI API key is required"):
            create_llm_provider("openai")

    @patch("app.services.llm_providers.factory.settings")
    def test_create_provider_unknown_type(self, mock_settings):
        """Test error when provider type is unknown."""
        mock_settings.llm_provider = "unknown"

        with pytest.raises(ValueError, match="Unknown LLM provider type"):
            create_llm_provider("unknown")
