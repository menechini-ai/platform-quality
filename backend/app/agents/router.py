"""Agent pipeline API router — triage → recommendation with SSE streaming."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.langgraph_pipeline import build_pipeline, run_pipeline
from app.agents.streaming_handler import stream_pipeline

router = APIRouter()


class AnalyzeRequest(BaseModel):
    incident_id: str
    description: str


class AnalyzeResponse(BaseModel):
    incident_id: str
    analysis: str | None
    recommendation: str | None


@router.post("/agents/analyze", response_model=AnalyzeResponse)
async def analyze_incident(data: AnalyzeRequest):
    """Run the LangGraph agent pipeline on an incident."""
    result = await run_pipeline(data.incident_id, data.description)
    return AnalyzeResponse(
        incident_id=data.incident_id,
        analysis=result.get("analysis"),
        recommendation=result.get("recommendation"),
    )


@router.get("/agents/analyze/{incident_id}/stream")
async def stream_analysis(incident_id: str, description: str = ""):
    """Stream the LangGraph agent pipeline execution via SSE."""
    if not description:
        raise HTTPException(status_code=400, detail="description query param is required")

    pipeline = build_pipeline()
    initial: dict[str, Any] = {
        "messages": [{"role": "user", "content": description}],
        "incident_id": incident_id,
        "analysis": None,
        "recommendation": None,
    }

    return StreamingResponse(
        stream_pipeline(initial, pipeline),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
