"""Global configuration via pydantic-settings."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
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
        if not v or v == "change-me-in-production":
            import os

            if os.environ.get("ENV", "").lower() in ("production", "prod"):
                raise ValueError(
                    "SECRET_KEY must be changed from default in production. "
                    "Set a strong key (≥32 chars) via environment or .env"
                )
        return v

    # --- PostgreSQL ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./observai.db"

    # --- Redis (cache + celery broker) ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Datadog ---
    DATADOG_API_KEY: str | None = None
    DATADOG_APP_KEY: str | None = None
    DATADOG_SITE: str = "datadoghq.com"

    # --- LLM ---
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"

    # --- Auth ---
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # --- Self-healing ---
    SELF_HEALING_ENABLED: bool = False
    SELF_HEALING_APPROVAL_REQUIRED: bool = True

    # --- Celery ---
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # --- Vector Store (pgvector) ---
    VECTOR_DB_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/vectordb"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536
    SIMILARITY_THRESHOLD: float = 0.75
    MAX_SIMILAR_INCIDENTS: int = 5

    # --- Self-healing / Playbook Executor ---
    SELF_HEALING_APPROVAL_REQUIRED: bool = True
    SELF_HEALING_DRY_RUN_DEFAULT: bool = False
    SELF_HEALING_MAX_PARALLEL_STEPS: int = 1
    PLAYBOOK_DEFAULT_TIMEOUT_SECONDS: int = 300

    # --- Notifications ---
    SLACK_WEBHOOK_URL: str | None = None
    SLACK_BOT_TOKEN: str | None = None
    SLACK_DEFAULT_CHANNEL: str = "#alerts"
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None
    PAGERDUTY_INTEGRATION_KEY: str | None = None
    PAGERDUTY_API_URL: str = "https://events.pagerduty.com/v2/enqueue"

    # --- Feature Flags / Canary ---
    ENABLE_VECTOR_SEARCH: bool = True
    ENABLE_REACT_AGENT: bool = True
    ENABLE_PLAYBOOK_EXECUTOR: bool = True
    ENABLE_NOTIFICATIONS: bool = True
    ENABLE_FEEDBACK_API: bool = True
    CANARY_PERCENTAGE: int = 10
    CANARY_ENABLED: bool = False


settings = Settings()
