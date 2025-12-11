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

    # Embeddings
    embedding_provider: Literal["sentence_transformers", "openai"] = "sentence_transformers"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_api_key: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    # Rate limiting
    max_requests_per_minute: int = 20

    # Logging
    log_level: str = "INFO"


settings = Settings()
