# Tasks: AI Capabilities — Backend & Frontend Integration

**Feature**: `002-ai-features`
**Input**: Design documents from `/specs/002-ai-features/` (spec.md, plan.md)
**Branch**: `002-ai-features-bff` off `develop`, PR → `develop`

**Scope**: Integrate the 4 AI user stories (prototyped in `api-demo/`) into the main `backend/` (FastAPI) and `frontend/` (React) codebases, following the Constitution's Domain Modularity pattern (`router` + `service` + `schemas` + where applicable).

**Tests**: Required per Constitution P2 (Test-First/TDD). Backend tests use `pytest` with mocked LLM/OpenAI. Frontend tests use Vitest + React Testing Library.

---

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: Parallelizable (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps to user stories: US1 (LLM), US2 (Agents), US3 (External), US4 (Advanced)

---

## Phase 1: Setup & Dependencies

**Purpose**: Ensure all packages, config, and DB schema are ready before any US start.

- [ ] T001 P — Add LiteLLM to `backend/pyproject.toml`: `litellm>=1.50.0`
- [ ] T002 P — Add LangGraph + LangChain deps to `backend/pyproject.toml`: `langgraph>=0.3.0`, `langchain-core>=0.3.0`, `langchain-openai>=0.3.0`, `langchain-community>=0.3.0`
- [ ] T003 P — Add MCP + Langfuse deps to `backend/pyproject.toml`: `mcp>=1.2.0`, `langfuse>=2.0.0`, `sse-starlette>=2.0.0`
- [ ] T004 P — Add `pgvector` dependency to `backend/pyproject.toml`: `pgvector` or `sqlalchemy-pgvector`
- [ ] T005 P — Add frontend LLM deps to `frontend/package.json`: `@tanstack/react-query` (if not present), `react-markdown` (for LLM output rendering)
- [ ] T006 — Update `backend/.env.example` with LLM vars: `LITELLM_API_KEY`, `LITELLM_BASE_URL`, `LITELLM_DEFAULT_MODEL`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `EMBED_MODEL`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
- [ ] T007 — Create pgvector migration in `backend/app/core/models/`: add `embedding` vector column to `knowledge_base` table and `incident` table (dimension=1536 for text-embedding-3-small)

---

## Phase 2: Foundational — Core LLM & Embedding Service

**Purpose**: LiteLLM client and embedding service that ALL user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T010 — Create `backend/app/llm/__init__.py` with `LiteLLMClient` class: wraps `litellm.completion`, reads env vars (`LITELLM_API_KEY`, `LITELLM_BASE_URL`, `LITELLM_DEFAULT_MODEL`), supports streaming. Port from `api-demo/agents/litellm_client.py`
- [ ] T011 — Create `backend/app/llm/service.py` with embedding helpers: `embed_text(text) -> list[float]` using `openai` SDK + `EMBED_MODEL`, `cosine_similarity(a, b) -> float`. Port from `api-demo/lib/embeddings.py`
- [ ] T012 — Add tests for `backend/app/llm/`: `test_litellm_client.py`, `test_embeddings.py` — mock `litellm.completion` and `openai.Embedding.create`, verify correct model/config passed
- [ ] T013 — Create `backend/app/vectorstore/__init__.py` + `service.py`: `VectorStore` class with `add_embedding(text, metadata)`, `search(query, k=3)` using `embed_text` + `cosine_similarity`. Integrates with SQLAlchemy pgvector column when available, falls back to in-memory. Port from `api-demo/lib/vectordb.py`
- [ ] T014 — Add tests for `backend/app/vectorstore/`: test search with known vectors, edge cases (empty store, no matches)

---

## Phase 3: User Story 1 — LLM-Powered RCA & Semantic KB (P1)

**Goal**: Existing RCA and KB endpoints gain LLM superpowers — LLM-generated RCA reports and semantic KB search.
**Independent Test**: `pytest backend/tests/test_rca/ backend/tests/test_kb/ -v` — verify LLM-call mocking + pgvector queries.

- [ ] T020 [P] [US1] Add `llm_rca` field + embedding column to `backend/app/core/models/incident.py`: `embedding vector(1536)`, `llm_rca Text nullable`
- [ ] T021 [P] [US1] Add `embedding` column to `backend/app/core/models/knowledge_base.py`: `embedding vector(1536)`
- [ ] T022 [P] [US1] Update `backend/app/core/schemas/incident.py`: add `llm_rca: str | None` to `IncidentRead`
- [ ] T023 [P] [US1] Update `backend/app/core/schemas/knowledge_base.py`: add `embedding: list[float] | None` to `KnowledgeBaseCreate`/`Read`
- [ ] T024 [US1] Create `backend/app/llm/rca_service.py`: `generate_rca(incident_id, description) -> str` that calls `LiteLLMClient.complete()` with incident context, stores result in `incident.llm_rca`
- [ ] T025 [US1] Add tests for `rca_service.py`: mock `LiteLLMClient`, verify RCA text is generated and stored
- [ ] T026 [US1] Update `backend/app/rca/router.py`: add `POST /rca/{incident_id}/generate` endpoint that calls `rca_service.generate_rca()`, returns `IncidentRead` with `llm_rca` populated
- [ ] T027 [US1] Create `backend/app/llm/kb_service.py`: `search_kb(query, k=3) -> list[KbEntry]` that embeds query → pgvector similarity search → returns top-K entries
- [ ] T028 [US1] Add tests for `kb_service.py`: mock embed_text + pgvector, verify correct K results
- [ ] T029 [US1] Update `backend/app/knowledge_base/router.py`: add `GET /kb/search?q=...&k=3` endpoint that calls `kb_service.search_kb()`
- [ ] T030 [US1] Create `frontend/src/api/llm.ts`: API client with `generateRca(incidentId)`, `searchKb(query, k)` functions using `api<T>()` helper
- [ ] T031 [US1] Update `frontend/src/components/RCA/RCAPage.tsx`: add "Generate RCA" button per incident that calls `generateRca()` and displays the LLM output using `react-markdown`
- [ ] T032 [US1] Create `frontend/src/components/KB/KBSearchBar.tsx`: search input + results dropdown using `searchKb()` with debounce, displays KB entries with similarity score
- [ ] T033 [US1] Register `/kb` route in `frontend/src/App.tsx`: add `KBSearchPage` component with search bar + results list
- [ ] T034 [US1] Add frontend tests for KB search and RCA generation components: `frontend/src/components/KB/KBSearchBar.test.tsx`, mock API responses

---

## Phase 4: User Story 2 — LangGraph Agent Orchestration (P2)

**Goal**: Backend exposes a LangGraph pipeline endpoint; frontend shows the agent's triage→recommendation flow with SSE streaming.
**Independent Test**: `pytest backend/tests/test_agents/ -v` — mocked LLM, verify state transitions.

- [ ] T040 [P] [US2] Create `backend/app/agents/__init__.py` + `dual_llm.py`: `get_reasoning_model()` and `get_tool_model()` using `ChatOpenAI` (gpt-4o + gpt-4o-mini, temp=0). Port from `api-demo/agents/dual_llm.py`
- [ ] T041 [P] [US2] Create `backend/app/agents/langgraph_pipeline.py`: `build_pipeline()` → compiled `StateGraph` with `triage_incident` (reasoning model) and `generate_recommendation` (tool model). `run_pipeline(incident_id, description)`. Port from `api-demo/agents/langgraph_pipeline.py`
- [ ] T042 [US2] Add tests for `backend/app/agents/`: mock both models, verify pipeline returns analysis + recommendation, verify `should_continue` conditional routing
- [ ] T043 [US2] Create `backend/app/agents/router.py`: `POST /agents/analyze` — accepts `incident_id` + `description`, runs `run_pipeline()`, returns full state. `GET /agents/analyze/{id}/stream` — SSE streaming endpoint using `StreamingResponse` + `stream_pipeline()` from `streaming_handler.py`
- [ ] T044 [US2] Create `backend/app/agents/streaming_handler.py`: async generator `stream_pipeline(state, pipeline)` that yields SSE events (`data: {"node": "...", "output": "..."}\n\n`). Port from `api-demo/agents/streaming_handler.py`
- [ ] T045 [US2] Add tests for streaming handler: verify SSE event format, verify generator yields per-node output
- [ ] T046 [US2] Register agent router in `backend/app/main.py`: `app.include_router(agents_router, prefix="/api/v1", tags=["agents"])`
- [ ] T047 [US2] Create `frontend/src/api/agents.ts`: `analyzeIncident(incidentId, description)`, `streamAnalysis(incidentId)` functions
- [ ] T048 [US2] Create `frontend/src/components/Agents/AgentPipelinePage.tsx`: input form (incident ID + description), "Run Analysis" button, real-time streaming output display showing triage → recommendation flow
- [ ] T049 [US2] Register `/agents` route in `frontend/src/App.tsx`
- [ ] T050 [US2] Add frontend tests: mock SSE stream, verify component renders triage + recommendation

---

## Phase 5: User Story 3 — MCP + Slack/Telegram + Tool Budget (P3)

**Goal**: Backend MCP endpoint for tool dispatch, Slack/Telegram webhook receivers, tool budget enforcement.
**Independent Test**: `pytest backend/tests/test_mcp/ -v` — mock tool handlers, verify JSON-RPC dispatch.

- [ ] T060 [P] [US3] Create `backend/app/mcp/__init__.py` + `server.py`: `list_tools()`, `call_tool(name, args)` with dispatch to `search_kb`, `get_incident`, `suggest_runbook`. Port from `api-demo/agents/mcp_server.py`
- [ ] T061 [P] [US3] Create `backend/app/mcp/tool_budget.py`: `ToolBudget(max_calls, window_seconds)` — sliding-window rate limiter. Port from `api-demo/agents/tool_budget.py`
- [ ] T062 [US3] Wire tool budget into MCP server: check `ToolBudget.allow_call()` before dispatching each tool call
- [ ] T063 [US3] Add tests for MCP + tool budget: mock handlers, test list/call/unknown/budget-exceeded
- [ ] T064 [US3] Create `backend/app/mcp/router.py`: `POST /mcp/tools/list` → returns tool list; `POST /mcp/tools/call` — JSON-RPC dispatch with budget check. Used by frontend and external tools
- [ ] T065 [US3] Register MCP router in `backend/app/main.py`
- [ ] T066 [P] [US3] Create `backend/app/integrations/slack/webhook.py`: Slack slash-command handler that parses `/observe <query>` → calls MCP `call_tool` → responds to Slack. Verify Slack signing secret
- [ ] T067 [P] [US3] Create `backend/app/integrations/telegram/webhook.py`: Telegram bot webhook that receives `/investigate <incident_id>` → calls LangGraph pipeline → responds with analysis
- [ ] T068 [US3] Add integration tests for both webhooks: mock MCP + LangGraph, verify response format
- [ ] T069 [US3] Register webhook routers in `backend/app/main.py`
- [ ] T070 [US3] Update `backend/app/core/schemas/` if needed: add Slack/Telegram config to env settings

---

## Phase 6: User Story 4 — Langfuse Observability + Synthetic RCA + AI Self-Healing (P4)

**Goal**: Langfuse tracing on all LLM calls, synthetic RCA evaluation endpoint, AI self-healing with approval gate.
**Independent Test**: `pytest backend/tests/test_llm/ backend/tests/test_self_healing/ -v`

- [ ] T080 [P] [US4] Create `backend/app/llm/langfuse.py`: `LangfuseTracer` wrapper that configures `litellm.success_callback = ["langfuse"]` when `LANGFUSE_SECRET_KEY` is set. Graceful skip otherwise. Port from `api-demo/agents/langfuse.py`
- [ ] T081 [US4] Wire Langfuse into `backend/app/llm/__init__.py`: import and init `LangfuseTracer` on module load if env vars present
- [ ] T082 [US4] Add tests for Langfuse wrapper: verify callback set with key, no-op without key
- [ ] T083 [P] [US4] Create `backend/app/llm/synthetic_rca.py`: `evaluate_pipeline(incidents) -> dict` that runs LangGraph pipeline against known incidents (from DB or fixture), compares output vs expected root cause, returns accuracy score. Port from `api-demo/agents/synthetic_rca.py`
- [ ] T084 [P] [US4] Create `backend/app/agents/ai_self_healing.py`: `AISelfHealing(auto_approve=False)` class with `analyze(incident_id, description)` and `execute()` methods. Uses LangGraph pipeline, supports approval gate. Port from `api-demo/agents/ai_self_healing.py`
- [ ] T085 [US4] Add tests for synthetic_rca: mock pipeline, verify accuracy scoring
- [ ] T086 [US4] Add tests for ai_self_healing: mock pipeline, test approval gate, test execute flow
- [ ] T087 [US4] Update `backend/app/self_healing/router.py`: add `POST /actions/{action_id}/ai-recommend` that calls `AISelfHealing.analyze()`, stores recommendation as draft auto-heal action
- [ ] T088 [US4] Create `backend/app/llm/synthetic_rca_router.py`: `POST /llm/evaluate` — runs synthetic RCA evaluation, returns accuracy report
- [ ] T089 [US4] Wire synthetic RCA + self-healing routers into `backend/app/main.py`
- [ ] T090 [US4] Create `frontend/src/api/llm.ts` (extend): add `evaluatePipeline()`, `getAIRecommendation(actionId)` functions
- [ ] T091 [US4] Create `frontend/src/components/RCA/SyntheticRCAPage.tsx`: "Run Evaluation" button, displays accuracy dashboard (total, correct, accuracy %)
- [ ] T092 [US4] Update `frontend/src/components/SelfHealing/SelfHealingPage.tsx`: add "AI Recommend" button per action, calls `getAIRecommendation()`, shows LLM recommendation with approve/reject
- [ ] T093 [US4] Register new routes in `frontend/src/App.tsx`: `/rca/evaluate`, update `/self-healing` page

---

## Phase 7: Polish & Cross-Cutting

**Purpose**: Finalize integration — full test suite passes, env config, docs.

- [ ] T100 — Run full backend test suite: `pytest backend/tests/ -v` — all existing + new tests pass
- [ ] T101 — Run frontend test suite: `cd frontend && npx vitest run` — all tests pass
- [ ] T102 — Update `docker-compose.yml` to pass new LLM env vars to backend service
- [ ] T103 — Add `backend/app/llm/` and `backend/app/agents/` to `backend/README.md` API section
- [ ] T104 — Add frontend KB + Agents + Synthetic RCA pages to `frontend/src/App.tsx` nav menu
- [ ] T105 — Final lint: `ruff check backend/app/llm/ backend/app/agents/ backend/app/mcp/ backend/app/integrations/` — clean

---

## Dependency Graph

```
Phase 1 ──► Phase 2 ──► US1 ──► US2 ──► US3 ──► US4 ──► Phase 7
(SETUP)     (CORE)     (P1)    (P2)    (P3)    (P4)    (POLISH)
              │          │        │        │        │
        T010-T014   T020-T034 T040-T050 T060-T070 T080-T093
                    (15 tasks) (11 tasks) (11 tasks) (14 tasks)
```

## Parallel Execution Opportunities

| Story | Parallel Group A | Parallel Group B |
|-------|-----------------|-----------------|
| **US1** | T020 (model), T021 (model), T030 (frontend API) | T022 (schema), T023 (schema) |
| **US2** | T040 (dual_llm), T044 (streaming) | T041 (pipeline) |
| **US3** | T060 (MCP server), T061 (tool budget) | T066 (Slack), T067 (Telegram) |
| **US4** | T080 (Langfuse), T083 (synthetic RCA), T084 (self-healing) | T090 (frontend API), T091 (frontend page) |

## Independent Test Criteria

| Story | Command | Expected |
|-------|---------|----------|
| **US1** | `pytest backend/tests/test_llm/ backend/tests/test_rca/ backend/tests/test_kb/ -v` | 15+ tests, all pass |
| **US2** | `pytest backend/tests/test_agents/ -v` | 8+ tests, all pass |
| **US3** | `pytest backend/tests/test_mcp/ -v` | 10+ tests, all pass |
| **US4** | `pytest backend/tests/test_llm/ backend/tests/test_self_healing/ -v` | 10+ tests, all pass |

## MVP Scope

**MVP = US1 + US2 (P1 + P2)**: LLM-powered RCA + semantic KB + LangGraph agent pipeline.
- Backend: LLM service → enhanced RCA/KB endpoints → agent pipeline
- Frontend: RCA page with "Generate RCA" → KB search page → Agent pipeline page

US3 (MCP + Slack/Telegram) and US4 (Langfuse + synthetic RCA + self-healing) extend the foundation and can be delivered incrementally.
