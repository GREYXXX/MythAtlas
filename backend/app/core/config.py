from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MythAtlas API"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://mythatlas:mythatlas@localhost:5432/mythatlas"

    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://localhost:8080,http://127.0.0.1:8080,"
        "http://localhost,http://127.0.0.1"
    )

    admin_token: str = "dev-admin-change-me"

    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    # OpenAI embedding model — dimensions fixed at 768 to match local model output
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 768

    # Local embedding via Ollama (used when OPENAI_API_KEY is not set)
    ollama_base_url: str = "http://localhost:11434"
    local_embedding_model: str = "nomic-embed-text"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def cors_origin_list() -> list[str]:
    return [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]
