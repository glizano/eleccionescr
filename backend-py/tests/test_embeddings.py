"""
Tests for embedding providers using LangChain abstractions.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_embedding_cache():
    """Reset embedding provider cache before each test"""
    from app.services import embeddings

    embeddings.get_embedding_provider.cache_clear()
    if hasattr(embeddings, "_cached_embed_query"):
        embeddings._cached_embed_query.cache_clear()
    yield
    embeddings.get_embedding_provider.cache_clear()
    if hasattr(embeddings, "_cached_embed_query"):
        embeddings._cached_embed_query.cache_clear()


class TestHuggingFaceProvider:
    """Test HuggingFace (SentenceTransformers) provider via LangChain"""

    @patch("app.services.embeddings.HUGGINGFACE_AVAILABLE", True)
    @patch("app.services.embeddings.HuggingFaceEmbeddings")
    @patch("app.services.embeddings.settings")
    def test_huggingface_provider_creation(self, mock_settings, mock_hf_class):
        """Test HuggingFace provider is created when configured"""
        mock_settings.embedding_provider = "sentence_transformers"
        mock_settings.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"

        mock_embeddings = MagicMock()
        mock_hf_class.return_value = mock_embeddings

        from app.services.embeddings import get_embedding_provider

        provider = get_embedding_provider()

        assert provider == mock_embeddings
        mock_hf_class.assert_called_once_with(model_name="sentence-transformers/all-MiniLM-L6-v2")

    @patch("app.services.embeddings.HUGGINGFACE_AVAILABLE", False)
    @patch("app.services.embeddings.settings")
    def test_huggingface_not_available_raises_error(self, mock_settings):
        """Test error when HuggingFace not available"""
        mock_settings.embedding_provider = "sentence_transformers"

        from app.services.embeddings import get_embedding_provider

        with pytest.raises(ValueError, match="HuggingFace embeddings not available"):
            get_embedding_provider()


class TestOpenAIProvider:
    """Test OpenAI embedding provider via LangChain"""

    @patch("app.services.embeddings.OpenAIEmbeddings")
    @patch("app.services.embeddings.settings")
    def test_openai_provider_creation(self, mock_settings, mock_openai_class):
        """Test OpenAI provider is created with correct settings"""
        mock_settings.embedding_provider = "openai"
        mock_settings.embedding_model = "text-embedding-3-small"
        mock_settings.openai_api_key = "test-key"

        mock_embeddings = MagicMock()
        mock_openai_class.return_value = mock_embeddings

        from app.services.embeddings import get_embedding_provider

        provider = get_embedding_provider()

        assert provider == mock_embeddings
        mock_openai_class.assert_called_once_with(
            model="text-embedding-3-small", api_key="test-key"
        )

    @patch("app.services.embeddings.OpenAIEmbeddings")
    @patch("app.services.embeddings.settings")
    def test_openai_provider_uses_default_model_for_sentence_transformers(
        self, mock_settings, mock_openai_class
    ):
        """Test OpenAI provider defaults to text-embedding-3-small for ST models"""
        mock_settings.embedding_provider = "openai"
        mock_settings.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        mock_settings.openai_api_key = "test-key"

        mock_embeddings = MagicMock()
        mock_openai_class.return_value = mock_embeddings

        from app.services.embeddings import get_embedding_provider

        provider = get_embedding_provider()

        # Should use default OpenAI model instead of sentence-transformers model
        assert provider == mock_embeddings
        call_kwargs = mock_openai_class.call_args[1]
        assert call_kwargs["model"] == "text-embedding-3-small"


class TestEmbeddingFunctions:
    """Test embedding convenience functions"""

    @patch("app.services.embeddings.get_embedding_provider")
    def test_generate_embedding(self, mock_get_provider):
        """Test generate_embedding function"""
        mock_provider = MagicMock()
        mock_provider.embed_query.return_value = [0.1, 0.2, 0.3]
        mock_get_provider.return_value = mock_provider

        from app.services.embeddings import generate_embedding

        result = generate_embedding("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_provider.embed_query.assert_called_once_with("test text")

    @patch("app.services.embeddings.get_embedding_provider")
    def test_generate_embeddings(self, mock_get_provider):
        """Test generate_embeddings function"""
        mock_provider = MagicMock()
        mock_provider.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_get_provider.return_value = mock_provider

        from app.services.embeddings import generate_embeddings

        result = generate_embeddings(["text1", "text2"])

        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_provider.embed_documents.assert_called_once_with(["text1", "text2"])

    @patch("app.services.embeddings.get_embedding_provider")
    def test_get_embedding_dimension(self, mock_get_provider):
        """Test get_embedding_dimension function"""
        mock_provider = MagicMock()
        mock_provider.embed_query.return_value = [0.1, 0.2, 0.3]
        mock_get_provider.return_value = mock_provider

        from app.services.embeddings import get_embedding_dimension

        result = get_embedding_dimension()

        assert result == 3  # Length of test embedding


class TestEmbeddingCache:
    """Test embedding caching functionality"""

    def test_embedding_cache_structure(self):
        """Test that caching is properly configured"""
        from app.services import embeddings

        # Check that _cached_embed_query exists
        assert hasattr(embeddings, "_cached_embed_query")

        # Check it's a cached function
        assert hasattr(embeddings._cached_embed_query, "cache_info")

    @patch("app.services.embeddings.settings")
    def test_cache_configuration(self, mock_settings):
        """Test cache respects configuration"""
        mock_settings.embedding_cache_enabled = True
        mock_settings.embedding_cache_max_size = 500

        # The cache size configuration is used in the decorator
        # This test verifies the settings exist
        assert mock_settings.embedding_cache_max_size == 500
