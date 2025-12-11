"""
Tests for LLM providers using LangChain abstractions.
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.language_models import BaseChatModel

from app.services.llm_providers.factory import create_llm_provider


class TestGoogleProvider:
    """Test the Google Gemini provider using LangChain."""

    @patch("app.services.llm_providers.google_provider.ChatGoogleGenerativeAI")
    def test_google_provider_creation(self, mock_chat_class):
        """Test Google provider creation with LangChain."""
        from app.services.llm_providers.google_provider import create_google_chat_model

        mock_chat_model = MagicMock()
        mock_chat_model.model_name = "gemini-2.5-flash"
        mock_chat_class.return_value = mock_chat_model

        chat_model = create_google_chat_model(
            api_key="test_key", model="gemini-2.5-flash", safety_threshold="BLOCK_MEDIUM_AND_ABOVE"
        )

        assert isinstance(chat_model, MagicMock)  # Would be ChatGoogleGenerativeAI in real usage
        mock_chat_class.assert_called_once()
        call_kwargs = mock_chat_class.call_args[1]
        assert call_kwargs["model"] == "gemini-2.5-flash"
        assert call_kwargs["google_api_key"] == "test_key"
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_output_tokens"] == 2048

    @patch("app.services.llm_providers.google_provider.ChatGoogleGenerativeAI")
    def test_google_provider_generate_text(self, mock_chat_class):
        """Test text generation with Google provider."""
        from app.services.llm_providers.google_provider import create_google_chat_model

        mock_response = MagicMock()
        mock_response.content = "Generated response"

        mock_chat_model = MagicMock()
        mock_chat_model.invoke.return_value = mock_response
        mock_chat_class.return_value = mock_chat_model

        chat_model = create_google_chat_model(api_key="test_key")
        result = chat_model.invoke("Test prompt")

        assert result.content == "Generated response"
        mock_chat_model.invoke.assert_called_once_with("Test prompt")


class TestOpenAIProvider:
    """Test the OpenAI provider using LangChain."""

    @patch("app.services.llm_providers.openai_provider.ChatOpenAI")
    def test_openai_provider_creation(self, mock_chat_class):
        """Test OpenAI provider creation with LangChain."""
        from app.services.llm_providers.openai_provider import create_openai_chat_model

        mock_chat_model = MagicMock()
        mock_chat_model.model_name = "gpt-4o-mini"
        mock_chat_class.return_value = mock_chat_model

        chat_model = create_openai_chat_model(api_key="test_key", model="gpt-4o-mini")

        assert isinstance(chat_model, MagicMock)  # Would be ChatOpenAI in real usage
        mock_chat_class.assert_called_once()
        call_kwargs = mock_chat_class.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["api_key"] == "test_key"
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_tokens"] == 2048

    @patch("app.services.llm_providers.openai_provider.ChatOpenAI")
    def test_openai_provider_generate_text(self, mock_chat_class):
        """Test text generation with OpenAI provider."""
        from app.services.llm_providers.openai_provider import create_openai_chat_model

        mock_response = MagicMock()
        mock_response.content = "Generated response"

        mock_chat_model = MagicMock()
        mock_chat_model.invoke.return_value = mock_response
        mock_chat_class.return_value = mock_chat_model

        chat_model = create_openai_chat_model(api_key="test_key")
        result = chat_model.invoke("Test prompt")

        assert result.content == "Generated response"
        mock_chat_model.invoke.assert_called_once_with("Test prompt")


class TestProviderFactory:
    """Test the provider factory."""

    @patch("app.services.llm_providers.factory.settings")
    @patch("app.services.llm_providers.google_provider.ChatGoogleGenerativeAI")
    def test_create_google_provider(self, mock_chat_class, mock_settings):
        """Test creating a Google provider via factory."""
        mock_settings.llm_provider = "google"
        mock_settings.google_api_key = "test_key"
        mock_settings.google_model = "gemini-2.5-flash"
        mock_settings.google_safety_threshold = "BLOCK_MEDIUM_AND_ABOVE"

        mock_chat_model = MagicMock(spec=BaseChatModel)
        mock_chat_model.model_name = "gemini-2.5-flash"
        mock_chat_class.return_value = mock_chat_model

        chat_model = create_llm_provider("google")

        assert chat_model is not None
        assert hasattr(chat_model, "invoke")

    @patch("app.services.llm_providers.factory.settings")
    @patch("app.services.llm_providers.openai_provider.ChatOpenAI")
    def test_create_openai_provider(self, mock_chat_class, mock_settings):
        """Test creating an OpenAI provider via factory."""
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "test_key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_chat_model = MagicMock(spec=BaseChatModel)
        mock_chat_model.model_name = "gpt-4o-mini"
        mock_chat_class.return_value = mock_chat_model

        chat_model = create_llm_provider("openai")

        assert chat_model is not None
        assert hasattr(chat_model, "invoke")

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
