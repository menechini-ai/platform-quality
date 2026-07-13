"""Admin router for AI SRE Agent management (Versus parity)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.analysis.agent_service import (
    AgentMode,
    get_agent,
    start_agent,
    stop_agent,
)
from app.core.config_loader import load_config
from app.core.gateway_auth import gateway_auth

router = APIRouter(dependencies=[Depends(gateway_auth)])


class SourceStatus(BaseModel):
    name: str
    type: str
    enable: bool
    cursor_position: int | None = None
    last_timestamp: str | None = None


class AgentStats(BaseModel):
    state: str
    mode: str
    sources: int
    patterns: int
    total_sightings: int
    trie_nodes: int


@router.get("/agent/status", response_model=AgentStats)
async def agent_status():
    """Get AI SRE Agent status."""
    agent = get_agent()
    return AgentStats(
        state=agent.state.value,
        mode=agent.mode.value,
        sources=len(agent.sources),
        patterns=len(agent.miner.signature_to_pattern),
        total_sightings=sum(p["sightings"] for p in agent.miner.signature_to_pattern.values()),
        trie_nodes=agent.miner._count_nodes(agent.miner.root),
    )


@router.get("/agent/sources", response_model=list[SourceStatus])
async def agent_sources():
    """Get configured log sources and their cursor positions."""
    agent = get_agent()
    result = []
    for s in agent.sources:
        cursor = agent.cursors.get(s.name)
        if cursor:
            pos = cursor.last_position
            ts = cursor.es_scroll_id
        else:
            pos = None
            ts = None
        result.append(
            SourceStatus(
                name=s.name,
                type=s.type.value,
                enable=s.enable,
                cursor_position=pos,
                last_timestamp=ts,
            )
        )
    return result


@router.post("/agent/start")
async def agent_start():
    """Start the AI SRE Agent."""
    await start_agent()
    return {"status": "started"}


@router.post("/agent/stop")
async def agent_stop():
    """Stop the AI SRE Agent."""
    await stop_agent()
    return {"status": "stopped"}


@router.post("/agent/mode")
async def agent_set_mode(mode: str = Query(..., pattern="^(training|shadow|detect)$")):
    """Set agent mode (training|shadow|detect)."""
    agent = get_agent()
    if agent.mode.value == mode:
        return {"status": "unchanged", "mode": mode}

    valid_transitions = {
        "training": ["shadow", "detect"],
        "shadow": ["detect", "training"],
        "detect": ["shadow", "training"],
    }

    if mode not in valid_transitions.get(agent.mode.value, []):
        raise HTTPException(400, f"Invalid mode transition from {agent.mode.value} to {mode}")

    await stop_agent()
    agent.mode = AgentMode(mode)
    await start_agent()

    return {"status": "mode changed", "mode": mode}


@router.get("/agent/patterns")
async def agent_patterns(
    source: str | None = None,
    rule: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """List learned patterns from the catalog."""
    agent = get_agent()
    patterns = agent.miner.get_all_patterns()

    if source:
        patterns = [p for p in patterns if p.get("source_name") == source]
    if rule:
        patterns = [p for p in patterns if p.get("rule_name") == rule]
    if status:
        patterns = [p for p in patterns if p.get("status") == status]

    return {
        "total": len(patterns),
        "limit": limit,
        "offset": offset,
        "patterns": patterns[offset : offset + limit],
    }


@router.post("/agent/patterns/{pattern_hash}/promote")
async def agent_promote_pattern(pattern_hash: str):
    """Manually promote a pattern to 'known' status."""
    agent = get_agent()
    pattern = agent.miner.get_pattern(pattern_hash)
    if not pattern:
        raise HTTPException(404, "Pattern not found")

    pattern["status"] = "known"
    pattern["sightings"] = max(pattern.get("sightings", 0), agent._auto_promote_threshold)
    return {"status": "promoted", "pattern": pattern}


@router.post("/agent/patterns/{pattern_hash}/ignore")
async def agent_ignore_pattern(pattern_hash: str):
    """Mark a pattern as ignored (won't trigger incidents)."""
    agent = get_agent()
    pattern = agent.miner.get_pattern(pattern_hash)
    if not pattern:
        raise HTTPException(404, "Pattern not found")

    pattern["status"] = "ignored"
    return {"status": "ignored", "pattern": pattern}


@router.get("/config")
async def get_config():
    """Get current configuration (sanitized)."""
    cfg = load_config()
    return {
        "name": cfg.name,
        "host": cfg.host,
        "port": cfg.port,
        "public_host": cfg.public_host,
        "agent": {
            "enable": cfg.agent.enable,
            "mode": cfg.agent.mode.value,
            "poll_interval": cfg.agent.poll_interval,
            "sources_count": len(cfg.agent.sources),
            "catalog": cfg.agent.catalog.model_dump(),
            "redaction": cfg.agent.redaction.model_dump(),
            "miner": cfg.agent.miner.model_dump(),
            "regex": cfg.agent.regex.model_dump(),
        },
        "storage": cfg.storage.model_dump(),
        "oncall": cfg.oncall.model_dump(),
        "notifications": {k: bool(v) for k, v in cfg.notifications.model_dump().items()},
    }


@router.post("/catalog/export")
async def export_catalog():
    """Export pattern catalog for backup."""
    agent = get_agent()
    return {"patterns": agent.miner.export_catalog()}


@router.post("/catalog/import")
async def import_catalog(catalog: dict):
    """Import pattern catalog from backup."""
    agent = get_agent()
    agent.miner.import_catalog(catalog.get("patterns", []))
    return {"status": "imported", "count": len(catalog.get("patterns", []))}
