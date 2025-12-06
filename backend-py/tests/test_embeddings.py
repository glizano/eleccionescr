"""
Tests for embedding providers.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_embedding_cache():
    """Reset embedding provider cache before each test"""
    from app.services import embeddings

    embeddings.get_embedding_provider.cache_clear()
    yield
    embeddings.get_embedding_provider.cache_clear()


class TestEmbeddingProviderAbstraction:
    """Test the embedding provider abstraction"""

    def test_sentence_transformers_provider_interface(self):
        """Test SentenceTransformersProvider has correct interface"""
        from app.services.embeddings import EmbeddingProvider, SentenceTransformersProvider

        # Verify it's a subclass of EmbeddingProvider
        assert issubclass(SentenceTransformersProvider, EmbeddingProvider)

    def test_openai_provider_interface(self):
        """Test OpenAIProvider has correct interface"""
        from app.services.embeddings import EmbeddingProvider, OpenAIProvider

        # Verify it's a subclass of EmbeddingProvider
        assert issubclass(OpenAIProvider, EmbeddingProvider)


class TestSentenceTransformersProvider:
    """Test the SentenceTransformers embedding provider"""

    @patch("sentence_transformers.SentenceTransformer")
    def test_initialization(self, mock_st_class):
        """Test SentenceTransformersProvider initialization"""
        mock_model = MagicMock()
        mock_st_class.return_value = mock_model

        from app.services.embeddings import SentenceTransformersProvider

        provider = SentenceTransformersProvider(model_name="test-model")

        mock_st_class.assert_called_once_with("test-model")
        assert provider.model_name == "test-model"
        assert provider.model == mock_model

    @patch("sentence_transformers.SentenceTransformer")
    def test_get_embedding_dimension(self, mock_st_class):
        """Test getting embedding dimension from SentenceTransformers"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st_class.return_value = mock_model

        from app.services.embeddings import SentenceTransformersProvider

        provider = SentenceTransformersProvider()
        dim = provider.get_embedding_dimension()

        assert dim == 384
        mock_model.get_sentence_embedding_dimension.assert_called_once()

    @patch("sentence_transformers.SentenceTransformer")
    def test_encode_texts(self, mock_st_class):
        """Test encoding texts with SentenceTransformers"""
        import numpy as np

        mock_model = MagicMock()
        mock_embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        mock_model.encode.return_value = mock_embeddings
        mock_st_class.return_value = mock_model

        from app.services.embeddings import SentenceTransformersProvider

        provider = SentenceTransformersProvider()
        result = provider.encode(["text1", "text2"])

        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]
        mock_model.encode.assert_called_once_with(["text1", "text2"], show_progress_bar=False)


class TestOpenAIProvider:
    """Test the OpenAI embedding provider"""

    @patch("openai.OpenAI")
    def test_initialization_with_api_key(self, mock_openai_class):
        """Test OpenAIProvider initialization with API key"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        from app.services.embeddings import OpenAIProvider

        provider = OpenAIProvider(model_name="text-embedding-3-small", api_key="test-key")

        mock_openai_class.assert_called_once_with(api_key="test-key")
        assert provider.model_name == "text-embedding-3-small"
        assert provider.client == mock_client

    def test_initialization_without_api_key_raises_error(self):
        """Test OpenAIProvider raises error without API key"""
        from app.services.embeddings import OpenAIProvider

        # Temporarily clear the openai_api_key setting
        with patch("app.services.embeddings.settings") as mock_settings:
            mock_settings.openai_api_key = ""

            with pytest.raises(ValueError, match="OpenAI API key is required"):
                OpenAIProvider(api_key=None)

    @patch("openai.OpenAI")
    def test_get_embedding_dimension_known_models(self, mock_openai_class):
        """Test getting embedding dimension for known OpenAI models"""
        from app.services.embeddings import OpenAIProvider

        provider_small = OpenAIProvider(model_name="text-embedding-3-small", api_key="test-key")
        provider_large = OpenAIProvider(model_name="text-embedding-3-large", api_key="test-key")
        provider_ada = OpenAIProvider(model_name="text-embedding-ada-002", api_key="test-key")

        assert provider_small.get_embedding_dimension() == 1536
        assert provider_large.get_embedding_dimension() == 3072
        assert provider_ada.get_embedding_dimension() == 1536

    @patch("openai.OpenAI")
    def test_encode_texts(self, mock_openai_class):
        """Test encoding texts with OpenAI"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3]),
            MagicMock(embedding=[0.4, 0.5, 0.6]),
        ]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.embeddings import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key")
        result = provider.encode(["text1", "text2"])

        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]
        mock_client.embeddings.create.assert_called_once()

    @patch("openai.OpenAI")
    def test_encode_cleans_newlines(self, mock_openai_class):
        """Test that encode replaces newlines in text"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2])]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.embeddings import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key")
        provider.encode(["text with\nnewline"])

        # Verify the newline was replaced
        call_args = mock_client.embeddings.create.call_args
        assert call_args.kwargs["input"] == ["text with newline"]


class TestProviderSelection:
    """Test provider selection based on configuration"""

    @patch("sentence_transformers.SentenceTransformer")
    @patch("app.services.embeddings.settings")
    def test_select_sentence_transformers_provider(self, mock_settings, mock_st_class):
        """Test selecting SentenceTransformers provider"""
        mock_settings.embedding_provider = "sentence_transformers"
        mock_settings.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"

        from app.services.embeddings import SentenceTransformersProvider, get_embedding_provider

        provider = get_embedding_provider()

        assert isinstance(provider, SentenceTransformersProvider)

    @patch("openai.OpenAI")
    @patch("app.services.embeddings.settings")
    def test_select_openai_provider(self, mock_settings, mock_openai_class):
        """Test selecting OpenAI provider"""
        mock_settings.embedding_provider = "openai"
        mock_settings.embedding_model = "text-embedding-3-small"
        mock_settings.openai_api_key = "test-key"

        from app.services.embeddings import OpenAIProvider, get_embedding_provider

        provider = get_embedding_provider()

        assert isinstance(provider, OpenAIProvider)

    @patch("openai.OpenAI")
    @patch("app.services.embeddings.settings")
    def test_openai_provider_uses_default_model_if_sentence_transformers_model_configured(
        self, mock_settings, mock_openai_class
    ):
        """Test that OpenAI provider uses default model when configured with sentence-transformers"""
        mock_settings.embedding_provider = "openai"
        mock_settings.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        mock_settings.openai_api_key = "test-key"

        from app.services.embeddings import get_embedding_provider

        provider = get_embedding_provider()

        # Should use default OpenAI model instead of sentence-transformers model
        assert provider.model_name == "text-embedding-3-small"


class TestConvenienceFunctions:
    """Test convenience functions"""

    @patch("app.services.embeddings.get_embedding_provider")
    def test_generate_embedding(self, mock_get_provider):
        """Test generate_embedding function"""
        mock_provider = MagicMock()
        mock_provider.encode_single.return_value = [0.1, 0.2, 0.3]
        mock_get_provider.return_value = mock_provider

        from app.services.embeddings import generate_embedding

        result = generate_embedding("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_provider.encode_single.assert_called_once_with("test text")

    @patch("app.services.embeddings.get_embedding_provider")
    def test_generate_embeddings(self, mock_get_provider):
        """Test generate_embeddings function"""
        mock_provider = MagicMock()
        mock_provider.encode.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_get_provider.return_value = mock_provider

        from app.services.embeddings import generate_embeddings

        result = generate_embeddings(["text1", "text2"])

        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_provider.encode.assert_called_once_with(["text1", "text2"])

    @patch("app.services.embeddings.get_embedding_provider")
    def test_get_embedding_dimension(self, mock_get_provider):
        """Test get_embedding_dimension function"""
        mock_provider = MagicMock()
        mock_provider.get_embedding_dimension.return_value = 384
        mock_get_provider.return_value = mock_provider

        from app.services.embeddings import get_embedding_dimension

        result = get_embedding_dimension()

        assert result == 384
        mock_provider.get_embedding_dimension.assert_called_once()
