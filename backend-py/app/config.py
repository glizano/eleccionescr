from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(extra="ignore")

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "planes_gobierno"

    # LLM
    google_api_key: str = ""
    google_model: str = "gemini-2.5-flash"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    # Rate limiting
    max_requests_per_minute: int = 20

    # Logging
    log_level: str = "INFO"


settings = Settings()
