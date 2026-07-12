# Datadog RCA Kit - V3 Plan (2026-07-12)

V1: collector + diagnosis (fallback) ✅
V2: real LLM + APM spans + structured RCA ✅

## V3: ReAct Agent + Runbook Automation + MTTR Analytics

### Core Idea
Agente ReAct que itera: **observe → reason → act (fetch more) → conclude**. Para incidentes complexos onde o primeiro fetch não basta.

### Tasks

| # | Task | Descrição |
|---|------|-----------|
| 1 | **ReAct Loop Engine** | `investigate_react()` — max 5 turns, cada turn: LLM decide próximo `fetch_*` tool, executa, atualiza context |
| 2 | **Tool Registry** | `fetch_logs`, `fetch_spans`, `fetch_metrics`, `fetch_monitors`, `fetch_events`, `search_incidents`, `get_incident` — cada um retorna `SignalResult` |
| 3 | **Runbook Generator** | De `similar_incidents` + LLM → markdown runbook com `detection`, `diagnosis`, `mitigation`, `prevention` sections |
| 4 | **MTTR Breakdown** | Modelo `MttrBreakdown` com timestamps: `detected_at`, `triaged_at`, `diagnosed_at`, `mitigated_at`, `resolved_at`; calcula MTTD/MTTI/MTTK/MTTA/MTTR |
| 5 | **Progressive Delivery** | Feature flag `datadog_kit_v3` + canary config (rollout %) |
| 6 | **Test E2E ReAct** | POST com `mode=react`, valida multi-turn + runbook output |

### Architecture

```
POST /investigate (mode=react)
    │
    ▼
ReActAgent(max_turns=5)
    │
    ├── Turn 1: fetch_all() → initial context
    │
    ├── Turn 2-N: LLM chooses tool → execute → add to context
    │     Tools: fetch_logs(query, time_range), fetch_spans(service, duration),
    │            fetch_metrics(query), fetch_monitors(state), search_incidents(query)
    │
    └── Final: analyze(context) → RCA + runbook + mttr_breakdown
```

### Models (new)

```python
class ReActTurn(BaseModel):
    turn: int
    thought: str
    action: str  # tool name
    action_input: dict
    observation: str  # tool result summary

class Runbook(BaseModel):
    title: str
    detection: list[str]
    diagnosis: list[str]
    mitigation: list[str]
    prevention: list[str]
    references: list[str]  # similar incident IDs

class MttrBreakdown(BaseModel):
    detected_at: datetime
    triaged_at: datetime | None
    diagnosed_at: datetime | None
    mitigated_at: datetime | None
    resolved_at: datetime | None
    mttd_seconds: float | None
    mtti_seconds: float | None
    mttk_seconds: float | None
    mtta_seconds: float | None
    mttr_seconds: float | None
```

### API Extension

```python
class InvestigationRequest(BaseModel):
    ...
    mode: Literal["single", "react"] = "single"
    max_turns: int = 5
    generate_runbook: bool = False

class InvestigationResponse(BaseModel):
    ...
    react_trace: list[ReActTurn] | None = None
    runbook: Runbook | None = None
    mttr_breakdown: MttrBreakdown | None = None
```