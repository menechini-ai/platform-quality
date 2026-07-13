"""Agent configuration models (Versus parity)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
    format: Literal["text", "json"] = "text"
    from_beginning: bool = True


class ElasticsearchSourceConfig(BaseModel):
    """Elasticsearch-based log source."""

    addresses: list[str]
    username: str | None = None
    password: str | None = None
    index: str
    time_field: str = "@timestamp"
    query: str = "log.level:(error OR warn)"
    message_field: str = "message"
    page_size: int = 500


class LogSource(BaseModel):
    """Log source configuration."""

    name: str
    type: Literal["file", "elasticsearch"]
    enable: bool = True
    file: FileSourceConfig | None = None
    elasticsearch: ElasticsearchSourceConfig | None = None
    rule_name: str | None = None


class AgentConfig(BaseModel):
    """AI SRE Agent configuration (Versus parity)."""

    enable: bool = False
    mode: Literal["training", "shadow", "detect"] = "training"
    poll_interval: str = "30s"
    sources_path: str = "./agent_sources.yaml"
    sources: list[LogSource] = Field(default_factory=list)
    catalog: CatalogConfig = Field(default_factory=CatalogConfig)
    redaction: RedactionConfig = Field(default_factory=RedactionConfig)
    miner: MinerConfig = Field(default_factory=MinerConfig)
    regex: RegexConfig = Field(default_factory=RegexConfig)


class StorageConfig(BaseModel):
    """Storage backend configuration."""

    type: Literal["file", "redis", "database"] = "file"
    file: dict | None = None
    redis: dict | None = None
    database: dict | None = None


class OnCallConfig(BaseModel):
    """On-call escalation configuration."""

    initialized_only: bool = True
    enable: bool = False
    wait_minutes: int = 3
    provider: Literal["aws_incident_manager", "pagerduty"] = "pagerduty"
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
