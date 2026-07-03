"""Configuration — loaded from environment variables with sensible defaults.

Uses pydantic-settings so every value is typed and validated at startup.
One Settings object, cached for the process lifetime.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API keys
    anthropic_api_key: str = ""

    # Models — Haiku for the four operational agents (cheap, fast),
    # Sonnet for the supervisor (synthesis across all agent outputs).
    operational_model: str = "claude-haiku-4-5"
    supervisor_model: str = "claude-sonnet-5"

    # Database — SQLAlchemy URL. SQLite for zero-setup local dev,
    # postgresql+asyncpg://user:pass@host/aegis in production.
    database_url: str = "sqlite+aiosqlite:///./aegis.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # Limits
    max_tokens_per_agent: int = 4096
    max_tokens_supervisor: int = 8192
    max_retries: int = 3

    # Trend agent live web search (Anthropic server-side tool).
    # Disable to run fully key-budget-free trend analysis from model knowledge.
    enable_web_search: bool = True
    max_web_searches: int = 5

    # Memory retrieval
    memory_top_k: int = 5

    # Observability
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
