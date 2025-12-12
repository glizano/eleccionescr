"""
Embeddings service using LangChain providers.

Provides a flexible interface to switch between different embedding providers.
"""

import logging
from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from app.config import settings

# Import HuggingFace only if available (dev dependency)
try:
    from langchain_huggingface import HuggingFaceEmbeddings

    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_provider() -> Embeddings:
    """Get the configured embedding provider (cached).

    Returns:
        A LangChain Embeddings instance configured based on settings.
    """
    provider_type = settings.embedding_provider
    model_name = settings.embedding_model

    if provider_type == "openai":
        # For OpenAI, use a default model if the configured model doesn't match OpenAI format
        if model_name.startswith("sentence-transformers/"):
            model_name = "text-embedding-3-small"
        embeddings = OpenAIEmbeddings(
            model=model_name,
            api_key=settings.openai_api_key,
        )
        logger.info(f"Initialized OpenAI embeddings provider with model: {model_name}")
        return embeddings
    else:
        # Default to HuggingFace (sentence-transformers) if available
        if not HUGGINGFACE_AVAILABLE:
            logger.error(
                "HuggingFace embeddings not available in this deployment. "
                "Please set EMBEDDING_PROVIDER=openai and provide OPENAI_API_KEY, "
                "or install dev dependencies: uv sync --group dev"
            )
            raise ValueError(
                "HuggingFace embeddings not available. "
                "Use EMBEDDING_PROVIDER=openai or install dev dependencies."
            )
        embeddings = HuggingFaceEmbeddings(model_name=model_name)
        logger.info(f"Initialized HuggingFace embeddings provider with model: {model_name}")
        return embeddings


def generate_embedding(text: str) -> list[float]:
    """Generate embedding for a single text.

    Args:
        text: The text to embed.

    Returns:
        The embedding vector as a list of floats.
    """
    provider = get_embedding_provider()
    return provider.embed_query(text)


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts.

    Args:
        texts: List of texts to embed.

    Returns:
        List of embedding vectors.
    """
    provider = get_embedding_provider()
    return provider.embed_documents(texts)


def get_embedding_dimension() -> int:
    """Get the dimension of the embedding vectors.

    Returns:
        The dimension size of embedding vectors.
    """
    provider = get_embedding_provider()
    # Get dimension by encoding a dummy text
    test_embedding = provider.embed_query("test")
    return len(test_embedding)
