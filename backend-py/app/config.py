from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "planes_gobierno"

    # LLM
    google_api_key: str
    google_model: str = "gemini-1.5-flash"

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

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
