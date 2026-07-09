"""Global configuration via pydantic-settings."""

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # extra="forbid" is the pydantic-settings default but breaks when
        # host env (e.g. OpenAI vars) leaks into Docker containers.
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "ObservAI"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        import os

        env = os.environ.get("ENV", "").lower()
        if (not v or v == "change-me-in-production") and env in ("production", "prod"):
            raise ValueError(
                "SECRET_KEY must be changed from default in production. "
                "Set a strong key (≥32 chars) via environment or .env"
            )
        if env in ("production", "prod") and len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production.")
        return v

    # --- PostgreSQL ---
    DATABASE_URL: str = "postgresql+asyncpg://observai:observai@localhost:5432/observai"

    # --- Redis (cache + celery broker) ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Datadog ---
    DATADOG_API_KEY: str | None = None
    DATADOG_APP_KEY: str | None = None
    DATADOG_SITE: str = "datadoghq.com"

    # --- Datadog global filter (applied to every datadog_routes/* call) ---
    DATADOG_DEFAULT_TAGS: list[str] = []
    DATADOG_DEFAULT_PERIOD: Literal["1d", "7d", "15d", "30d"] | None = None

    # --- Auth ---
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "observai-platform"
    JWT_AUDIENCE: str = "observai-platform"
    AUTH_RATE_LIMIT: int = 5
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60
    INITIAL_ADMIN_USERNAME: str | None = None
    INITIAL_ADMIN_PASSWORD: str | None = None

    # --- Self-healing ---
    SELF_HEALING_ENABLED: bool = False
    SELF_HEALING_APPROVAL_REQUIRED: bool = True

    # --- Celery ---
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # --- LLM / AI ---
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    EMBED_MODEL: str = "text-embedding-3-small"
    LITELLM_API_KEY: str | None = None
    LITELLM_BASE_URL: str | None = None
    LITELLM_DEFAULT_MODEL: str = "gpt-4o"
    LANGFUSE_PUBLIC_KEY: str | None = None
    LANGFUSE_SECRET_KEY: str | None = None
    LANGFUSE_HOST: str | None = None


settings = Settings()
