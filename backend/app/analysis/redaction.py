"""Redaction middleware for sensitive data (Versus parity)."""

from __future__ import annotations

import contextlib
import re
from re import Pattern
from typing import Any

from app.core.config_loader import RedactionConfig, load_config


class RedactionEngine:
    """
    Redacts sensitive information from log lines before they reach the LLM.

    Versus parity: configurable regex patterns + built-in defaults.
    """

    DEFAULT_PATTERNS: list[Pattern] = [
        # API keys / tokens
        re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd)\s*[:=]\s*\S+"),
        # Authorization headers
        re.compile(r"(?i)authorization:\s*Bearer\s+\S+"),
        re.compile(r"(?i)authorization:\s*Basic\s+\S+"),
        # AWS keys
        re.compile(r"AKIA[0-9A-Z]{16}"),
        # Generic secrets
        re.compile(r"(?i)(secret|pwd|password)\s*[:=]\s*\S+"),
        # Credit cards (basic)
        re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
        # Emails
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    ]

    def __init__(self, config: RedactionConfig | None = None):
        self.config = config or RedactionConfig()
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> list[Pattern]:
        patterns = list(self.DEFAULT_PATTERNS)
        if self.config.redact_ips:
            patterns.append(re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"))
        for p in self.config.extra_patterns:
            with contextlib.suppress(re.error):
                patterns.append(re.compile(p))
        return patterns

    def redact(self, text: str) -> str:
        """Apply all redaction patterns to text."""
        result = text
        for pattern in self.patterns:
            result = pattern.sub("[REDACTED]", result)
        return result

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact sensitive fields in a dict recursively."""
        result = {}
        for k, v in data.items():
            if isinstance(v, str):
                result[k] = self.redact(v)
            elif isinstance(v, dict):
                result[k] = self.redact_dict(v)
            elif isinstance(v, list):
                result[k] = [
                    self.redact_dict(i)
                    if isinstance(i, dict)
                    else (self.redact(i) if isinstance(i, str) else i)
                    for i in v
                ]
            else:
                result[k] = v
        return result


# Global redaction engine (initialized on first use)
_redaction_engine: RedactionEngine | None = None


def get_redaction_engine() -> RedactionEngine:
    """Get or create the global redaction engine."""
    global _redaction_engine
    if _redaction_engine is None:
        try:
            cfg = load_config()
            _redaction_engine = RedactionEngine(cfg.agent.redaction)
        except Exception:
            _redaction_engine = RedactionEngine()
    return _redaction_engine


def redact_log_line(line: str) -> str:
    """Convenience function to redact a single log line."""
    return get_redaction_engine().redact(line)


def redact_for_llm(data: dict[str, Any] | str) -> dict[str, Any] | str:
    """Redact data before sending to LLM."""
    engine = get_redaction_engine()
    if isinstance(data, str):
        return engine.redact(data)
    return engine.redact_dict(data)
