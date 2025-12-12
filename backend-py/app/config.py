from typing import Literal

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(extra="ignore")

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "planes_gobierno"

    # LLM Provider Selection
    llm_provider: Literal["google", "openai"] = "google"

    # Google LLM
    google_api_key: str = ""
    google_model: str = "gemini-2.5-flash"
    google_safety_threshold: Literal[
        "BLOCK_NONE", "BLOCK_ONLY_HIGH", "BLOCK_MEDIUM_AND_ABOVE", "BLOCK_LOW_AND_ABOVE"
    ] = "BLOCK_MEDIUM_AND_ABOVE"

    # OpenAI LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Langfuse
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_enabled: bool = False

    # Embeddings (use openai for production to reduce Docker image size)
    embedding_provider: Literal["sentence_transformers", "openai"] = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_cache_enabled: bool = True
    embedding_cache_max_size: int = 1000

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    # Rate limiting (para controlar costos de LLM en servicio público)
    # Límites por IP (usuarios anónimos)
    max_requests_per_minute: int = 10
    max_requests_per_hour: int = 30
    max_requests_per_day: int = 100

    # RAG Search Limits
    rag_specific_party_limit: int = 5
    rag_general_plan_limit: int = 15
    rag_comparison_per_party: int = 2
    rag_comparison_max_total: int = 40
    rag_default_limit: int = 5
    rag_context_truncate_length: int = 500

    # LLM Retry & Timeout
    llm_timeout_seconds: int = 30
    llm_retry_max_attempts: int = 3
    llm_retry_initial_delay: float = 1.0
    llm_retry_max_delay: float = 60.0
    llm_retry_exponential_base: float = 2.0

    # Circuit Breaker
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60

    # Logging
    log_level: str = "INFO"
    structured_logging: bool = False


settings = Settings()
