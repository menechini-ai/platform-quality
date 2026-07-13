"""AI SRE Agent Service (Versus parity)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import aiofiles
import httpx

from app.analysis.miner import get_miner
from app.analysis.redaction import get_redaction_engine, redact_log_line
from app.core.config_loader import (
    AgentConfig,
    AgentMode,
    LogSource,
    LogSourceType,
    load_config,
)
from app.core.db import async_session_factory
from app.core.models.incident import Incident, IncidentTimeline

logger = logging.getLogger(__name__)


class AgentState(StrEnum):
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class SourceCursor:
    """Track position in log source."""

    source_name: str
    file_path: str | None = None
    last_position: int = 0
    es_scroll_id: str | None = None
    last_timestamp: str | None = None


class AgentService:
    """
    AI SRE Agent - learns log patterns, detects anomalies.

    Modes:
    - training: learn patterns, no alerts
    - shadow: learn + log "would have alerted", no real alerts
    - detect: create incidents for unknown patterns
    """

    def __init__(self):
        self.config: AgentConfig | None = None
        self.mode: AgentMode = AgentMode.TRAINING
        self.state = AgentState.STOPPED
        self.sources: list[LogSource] = []
        self.cursors: dict[str, SourceCursor] = {}
        self.miner = get_miner()
        self.redaction = get_redaction_engine()
        self._task: asyncio.Task | None = None
        self._poll_interval = 30
        self._auto_promote_threshold = 100

    async def initialize(self) -> None:
        """Load config and initialize sources."""
        try:
            cfg = load_config()
            self.config = cfg.agent
            self.mode = self.config.mode
            self.sources = [s for s in self.config.sources if s.enable]
            self._poll_interval = self._parse_interval(self.config.poll_interval)
            self._auto_promote_threshold = self.config.catalog.auto_promote_after
            self.state = AgentState.RUNNING
            logger.info(
                "Agent initialized in %s mode with %d sources",
                self.mode.value,
                len(self.sources),
            )
        except Exception as e:
            logger.error("Agent init failed: %s", e)
            self.state = AgentState.ERROR
            raise

    def _parse_interval(self, interval: str) -> int:
        """Parse interval string (e.g., '30s', '1m') to seconds."""
        interval = interval.strip().lower()
        if interval.endswith("s"):
            return int(interval[:-1])
        if interval.endswith("m"):
            return int(interval[:-1]) * 60
        if interval.endswith("h"):
            return int(interval[:-1]) * 3600
        return 30

    async def start(self) -> None:
        """Start the agent polling loop."""
        if self.state != AgentState.RUNNING:
            await self.initialize()
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._poll_loop())
            logger.info("Agent polling loop started")

    async def stop(self) -> None:
        """Stop the agent."""
        self.state = AgentState.STOPPED
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("Agent stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop - checks all sources for new log lines."""
        while self.state == AgentState.RUNNING:
            try:
                for source in self.sources:
                    await self._process_source(source)
            except Exception as e:
                logger.error("Poll loop error: %s", e)
            await asyncio.sleep(self._poll_interval)

    async def _process_source(self, source: LogSource) -> None:
        """Process a single log source."""
        cursor = self.cursors.get(source.name)
        if source.type == LogSourceType.FILE:
            await self._process_file_source(source, cursor)
        elif source.type == LogSourceType.ELASTICSEARCH:
            await self._process_es_source(source, cursor)

    async def _process_file_source(
        self, source: LogSource, cursor: SourceCursor | None
    ) -> None:
        """Read new lines from file source."""
        if not source.file:
            return
        path = Path(source.file.path)
        if not path.exists():
            logger.warning("Log file not found: %s", path)
            return

        if cursor is None:
            cursor = SourceCursor(source_name=source.name, file_path=str(path))
            self.cursors[source.name] = cursor

        async with aiofiles.open(path) as f:
            await f.seek(cursor.last_position)
            lines = await f.readlines()
            cursor.last_position = await f.tell()

        for line in lines:
            line = line.strip()
            if not line:
                continue
            await self._process_line(line, source.name, source)

    async def _process_es_source(
        self, source: LogSource, cursor: SourceCursor | None
    ) -> None:
        """Query Elasticsearch for new log entries."""
        if not source.elasticsearch:
            return

        es = source.elasticsearch
        url = f"{es.addresses[0]}/{es.index}/_search"
        auth = (es.username, es.password) if es.username else None

        query = {
            "size": es.page_size,
            "query": {
                "bool": {
                    "must": [{"query_string": {"query": es.query}}],
                    "filter": [
                        {
                            "range": {
                                es.time_field: {
                                    "gt": cursor.last_timestamp or "now-1h"
                                }
                            }
                        }
                    ],
                }
            },
            "sort": [{es.time_field: "asc"}],
        }

        async with httpx.AsyncClient(auth=auth, timeout=30.0) as client:
            resp = await client.post(url, json=query)
            resp.raise_for_status()
            data = resp.json()

        hits = data.get("hits", {}).get("hits", [])
        for hit in hits:
            msg = hit["_source"].get(es.message_field, "")
            if msg:
                await self._process_line(msg, source.name, source)

        if hits:
            cursor.last_timestamp = hits[-1]["_source"].get(es.time_field)

    async def _process_line(self, line: str, source_name: str, source: LogSource) -> None:
        """Process a single log line through redaction + miner."""
        # 1. Redact sensitive data
        redacted = redact_log_line(line)

        # 2. Check regex pre-filter
        if not self._matches_regex_filter(redacted):
            return

        # 3. Feed to miner
        sig_hash = self.miner.insert(redacted, source_name, source.rule_name)

        # 4. In detect mode, check if pattern is new
        if self.mode == AgentMode.DETECT:
            pattern = self.miner.get_pattern(sig_hash)
            if pattern and pattern["sightings"] == 1:
                # First time seeing this pattern - potential incident
                await self._create_incident_from_pattern(pattern, source_name)

    def _matches_regex_filter(self, line: str) -> bool:
        """Check if line matches any regex rule or default pattern."""
        rules = self.config.regex.rules
        default = self.config.regex.default_pattern

        for rule in rules:
            if re.search(rule.pattern, line, re.IGNORECASE):
                return True

        if default and re.search(default, line, re.IGNORECASE):
            return True

        return not (rules or default)  # If no rules, match all

    async def _create_incident_from_pattern(
        self, pattern: dict, source_name: str
    ) -> None:
        """Create incident for previously unseen pattern."""
        async with async_session_factory() as session:
            incident = Incident(
                title=f"New anomaly detected: {pattern.get('rule_name', 'unknown pattern')}",
                description=(
                    f"AI SRE Agent detected a previously unseen log pattern from "
                    f"{source_name}.\n\nExample: {pattern['example_line'][:500]}"
                ),
                severity="SEV-3",  # Default, LLM can refine
                status="active",
                service=source_name,
                failure_pattern="anomaly",
                tags=["ai-agent", "auto-detected", pattern.get("rule_name", "unknown")],
                llm_rca=None,
            )
            session.add(incident)
            await session.flush()

            # Add timeline event
            timeline = IncidentTimeline(
                incident_id=incident.id,
                event_type="created",
                content=(
                    f"Auto-detected by AI SRE Agent. Pattern: {pattern['hash']}. "
                    f"Source: {source_name}"
                ),
                author="ai-sre-agent",
            )
            session.add(timeline)
            await session.commit()

            logger.warning(
                "Created incident %s for new pattern %s", incident.id, pattern["hash"]
            )

    def get_stats(self) -> dict:
        """Get agent statistics."""
        return {
            "state": self.state.value,
            "mode": self.mode.value,
            "sources": len(self.sources),
            "patterns": self.miner.stats(),
            "cursors": {
                k: {"position": v.last_position, "es_scroll": v.es_scroll_id is not None}
                for k, v in self.cursors.items()
            },
        }


# Global agent instance
_agent: AgentService | None = None


def get_agent() -> AgentService:
    """Get or create global agent service."""
    global _agent
    if _agent is None:
        _agent = AgentService()
    return _agent


async def start_agent() -> None:
    """Start the global agent."""
    agent = get_agent()
    await agent.start()


async def stop_agent() -> None:
    """Stop the global agent."""
    global _agent
    if _agent:
        await _agent.stop()
        _agent = None
