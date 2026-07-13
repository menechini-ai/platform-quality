"""Configuration loader with YAML + env override (Versus parity)."""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError


class AgentMode(StrEnum):
    """AI SRE Agent modes."""

    TRAINING = "training"
    SHADOW = "shadow"
    DETECT = "detect"


class LogSourceType(StrEnum):
    """Log source types."""

    FILE = "file"
    ELASTICSEARCH = "elasticsearch"


class RedactionConfig(BaseModel):
    """Redaction rules for sensitive data in logs."""

    enable: bool = True
    redact_ips: bool = False
    extra_patterns: list[str] = Field(default_factory=list)


class MinerConfig(BaseModel):
    """Pattern mining/clustering configuration."""

    similarity_threshold: float = 0.4
    tree_depth: int = 4
    max_children: int = 100


class RegexRule(BaseModel):
    """Named regex rule for pre-filtering log signals."""

    name: str
    pattern: str


class RegexConfig(BaseModel):
    """Regex pre-filter configuration."""

    default_pattern: str = "(?i)error|exception|fatal|panic"
    rules: list[RegexRule] = Field(default_factory=list)


class CatalogConfig(BaseModel):
    """Pattern catalog persistence configuration."""

    persist_interval: str = "30s"  # duration string
    auto_promote_after: int = 100  # sightings before "known"


class FileSourceConfig(BaseModel):
    """File-based log source."""

    path: str
    format: str = "text"  # text | json
    from_beginning: bool = True


class ElasticsearchSourceConfig(BaseModel):
    """Elasticsearch-based log source."""

    addresses: list[str]
    username: str | None = None
    password: str | None = None
    index: str
    time_field: str = "@timestamp"
    query: str = 'log.level:(error OR warn)'
    message_field: str = "message"
    page_size: int = 500


class LogSource(BaseModel):
    """Log source configuration."""

    name: str
    type: LogSourceType
    enable: bool = True
    file: FileSourceConfig | None = None
    elasticsearch: ElasticsearchSourceConfig | None = None
    rule_name: str | None = None


class AgentConfig(BaseModel):
    """AI SRE Agent configuration (Versus parity)."""

    enable: bool = False
    mode: AgentMode = AgentMode.TRAINING
    poll_interval: str = "30s"
    sources_path: str = "./agent_sources.yaml"
    sources: list[LogSource] = Field(default_factory=list)
    catalog: CatalogConfig = Field(default_factory=CatalogConfig)
    redaction: RedactionConfig = Field(default_factory=RedactionConfig)
    miner: MinerConfig = Field(default_factory=MinerConfig)
    regex: RegexConfig = Field(default_factory=RegexConfig)


class StorageConfig(BaseModel):
    """Storage backend configuration."""

    type: str = "file"  # file | redis | database
    file: dict | None = None
    redis: dict | None = None
    database: dict | None = None


class OnCallConfig(BaseModel):
    """On-call escalation configuration."""

    initialized_only: bool = True
    enable: bool = False
    wait_minutes: int = 3
    provider: str = "pagerduty"  # pagerduty | aws_incident_manager
    aws_incident_manager: dict | None = None
    pagerduty: dict | None = None


class NotificationsConfig(BaseModel):
    """Notification channels configuration."""

    slack: dict | None = None
    telegram: dict | None = None
    pagerduty: dict | None = None
    teams: dict | None = None
    email: dict | None = None
    lark: dict | None = None


class RootConfig(BaseModel):
    """Root configuration (Versus-style)."""

    name: str = "observai"
    host: str = "0.0.0.0"
    port: int = 8000
    public_host: str | None = None
    gateway_secret: str | None = None
    storage: StorageConfig = Field(default_factory=StorageConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    oncall: OnCallConfig = Field(default_factory=OnCallConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    redis: dict | None = None


def _expand_env(obj: Any) -> Any:
    """Recursively expand ${VAR} or $VAR in strings."""
    if isinstance(obj, str):
        return os.path.expandvars(obj)
    if isinstance(obj, dict):
        return {k: _expand_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env(v) for v in obj]
    return obj


def load_config(path: str | Path | None = None) -> RootConfig:
    """
    Load configuration from YAML file with environment variable expansion.

    Priority: env var > YAML file > defaults
    """
    config_dict: dict[str, Any] = {}

    # 1. Load from YAML if provided
    if path:
        path = Path(path)
        if path.exists():
            with path.open() as f:
                config_dict = yaml.safe_load(f) or {}
        else:
            raise FileNotFoundError(f"Config file not found: {path}")

    # 2. Expand environment variables in loaded config
    config_dict = _expand_env(config_dict)

    # 3. Apply env var overrides for common root fields
    env_overrides = {
        "name": os.getenv("OBSERVAI_NAME"),
        "host": os.getenv("OBSERVAI_HOST"),
        "port": int(os.getenv("OBSERVAI_PORT", "0")) or None,
        "public_host": os.getenv("OBSERVAI_PUBLIC_HOST"),
        "gateway_secret": os.getenv("GATEWAY_SECRET"),
    }
    config_dict.update({k: v for k, v in env_overrides.items() if v is not None})

    # 4. Handle nested env overrides for agent
    agent_env = {
        "enable": os.getenv("AGENT_ENABLE"),
        "mode": os.getenv("AGENT_MODE"),
        "poll_interval": os.getenv("AGENT_POLL_INTERVAL"),
        "sources_path": os.getenv("AGENT_SOURCES_PATH"),
    }
    if any(v is not None for v in agent_env.values()):
        config_dict.setdefault("agent", {})
        config_dict["agent"].update({k: v for k, v in agent_env.items() if v is not None})

    # 5. Handle storage env
    storage_env = {"type": os.getenv("STORAGE_TYPE")}
    if any(v is not None for v in storage_env.values()):
        config_dict.setdefault("storage", {})
        config_dict["storage"].update({k: v for k, v in storage_env.items() if v is not None})

    # 6. Handle redis env
    redis_env = {
        "host": os.getenv("REDIS_HOST"),
        "port": int(os.getenv("REDIS_PORT", "0")) or None,
        "password": os.getenv("REDIS_PASSWORD"),
        "db": int(os.getenv("REDIS_DB", "0")),
    }
    if any(v is not None for v in redis_env.values()):
        config_dict.setdefault("redis", {})
        config_dict["redis"].update({k: v for k, v in redis_env.items() if v is not None})

    # 7. Validate and return
    try:
        return RootConfig(**config_dict)
    except ValidationError as e:
        raise ValueError(f"Config validation failed: {e}") from e


def load_agent_sources(path: str | Path) -> list[LogSource]:
    """Load agent log sources from separate YAML file."""
    path = Path(path)
    if not path.exists():
        return []

    with path.open() as f:
        data = yaml.safe_load(f) or {}

    sources_data = data.get("sources", [])
    sources = []
    for src in sources_data:
        src = _expand_env(src)
        if src.get("type") == "file" and src.get("file"):
            src["file"] = FileSourceConfig(**src["file"])
        elif src.get("type") == "elasticsearch" and src.get("elasticsearch"):
            src["elasticsearch"] = ElasticsearchSourceConfig(**src["elasticsearch"])
        sources.append(LogSource(**src))
    return sources


# Re-export for convenience
__all__ = [
    "load_config",
    "load_agent_sources",
    "RootConfig",
    "AgentConfig",
    "AgentMode",
    "LogSource",
    "LogSourceType",
    "FileSourceConfig",
    "ElasticsearchSourceConfig",
    "RedactionConfig",
    "MinerConfig",
    "RegexConfig",
    "RegexRule",
    "CatalogConfig",
    "StorageConfig",
    "OnCallConfig",
    "NotificationsConfig",
]
