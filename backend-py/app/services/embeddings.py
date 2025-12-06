import logging
from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers"""

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Return the dimension of the embedding vectors"""
        pass

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode a list of texts into embeddings"""
        pass

    def encode_single(self, text: str) -> list[float]:
        """Encode a single text into an embedding"""
        return self.encode([text])[0]


class SentenceTransformersProvider(EmbeddingProvider):
    """Embedding provider using sentence-transformers library"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        logger.info(f"Loaded SentenceTransformers model: {model_name}")

    def get_embedding_dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return [embedding.tolist() for embedding in embeddings]


class OpenAIProvider(EmbeddingProvider):
    """Embedding provider using OpenAI API"""

    # Map of model names to their embedding dimensions
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(self, model_name: str = "text-embedding-3-small", api_key: str | None = None):
        from openai import OpenAI

        self.model_name = model_name
        # Handle both None and empty string cases
        resolved_api_key = api_key if api_key else settings.openai_api_key
        if not resolved_api_key:
            raise ValueError("OpenAI API key is required for OpenAI embedding provider")
        self.client = OpenAI(api_key=resolved_api_key)
        logger.info(f"Initialized OpenAI embedding provider with model: {model_name}")

    def get_embedding_dimension(self) -> int:
        return self.MODEL_DIMENSIONS.get(self.model_name, 1536)

    def encode(self, texts: list[str]) -> list[list[float]]:
        # OpenAI recommends replacing newlines for better results
        cleaned_texts = [text.replace("\n", " ") for text in texts]
        response = self.client.embeddings.create(input=cleaned_texts, model=self.model_name)
        return [data.embedding for data in response.data]


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    """Get the configured embedding provider (cached)"""
    provider_type = settings.embedding_provider
    model_name = settings.embedding_model

    if provider_type == "openai":
        # For OpenAI, use a default model if no specific model is configured
        # or the configured model doesn't match OpenAI format
        if model_name.startswith("sentence-transformers/"):
            model_name = "text-embedding-3-small"
        return OpenAIProvider(model_name=model_name)
    else:
        # Default to sentence-transformers
        return SentenceTransformersProvider(model_name=model_name)


def generate_embedding(text: str) -> list[float]:
    """Generate embedding for text"""
    provider = get_embedding_provider()
    return provider.encode_single(text)


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts"""
    provider = get_embedding_provider()
    return provider.encode(texts)


def get_embedding_dimension() -> int:
    """Get the dimension of the embedding vectors"""
    provider = get_embedding_provider()
    return provider.get_embedding_dimension()
