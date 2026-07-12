# Implementation Plan: AI Capabilities for ObservAI Demo Lab

**Feature Directory**: `002-ai-features`
**Branch Pattern**: `002-ai-features` off `develop`, PR → `develop`

---

## Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| LLM Gateway | **LiteLLM** v1.50+ | Multi-provider proxy (OpenAI, Anthropic, Ollama, etc.) |
| Embeddings | **OpenAI** `text-embedding-3-small` via `openai` SDK | Industry-standard embeddings for semantic search |
| Vector Storage | **pgvector** or **in-memory** numpy arrays | Demo flexibility — no mandatory Postgres dependency |
| Agent Framework | **LangGraph** v0.3+ + **LangChain Core** v0.3+ | Stateful DAG orchestration with conditional edges |
| Dual-LLM | Separate ChatOpenAI instances for reasoning vs tool-call | Architecture pattern from OpenSRE (swapnildahiphale) |
| MCP Server | **mcp** Python SDK v1.2+ | Standard Model Context Protocol for tool integration |
| LLM Observability | **Langfuse** | Open-source LLM tracing (traces, spans, token counts) |
| Streaming | **SSE** (Server-Sent Events) via FastAPI StreamingResponse | Real-time agent output |
| Test Framework | **pytest** v8+ with pytest-asyncio | Unit tests with mocked LLM/OpenAI |

---

## Project Structure

All new code lives in `api-demo/` (the existing Datadog telemetry lab). No changes to `backend/app/`.

```
api-demo/
├── agents/
│   ├── litellm_client.py        # US1: LiteLLM proxy
│   ├── langgraph_pipeline.py     # US2: LangGraph agent (EXISTS)
│   ├── dual_llm.py               # US2: Reasoning + Toolcall models
│   ├── streaming_handler.py      # US2: SSE streaming
│   ├── mcp_server.py             # US3: MCP protocol server
│   └── tool_budget.py            # US3: Tool-usage budget enforcement
├── lib/
│   ├── embeddings.py             # US1: pgvector/numpy embeddings (EXISTS)
│   └── vectordb.py               # US1: In-memory vector store
├── data/
│   ├── incidents.json            # US1: Demo incident fixtures (EXISTS)
│   └── kb_entries.json           # US1: Knowledge-base fixtures (EXISTS)
├── scenarios/                    # Existing — unchanged
├── tests/
│   ├── test_lib/
│   │   └── test_embeddings.py    # US1: 15 tests (EXISTS)
│   ├── test_agents/
│   │   ├── test_litellm_client.py    # US1: 6 tests (EXISTS)
│   │   ├── test_langgraph_pipeline.py # US2: 8 tests (EXISTS)
│   │   ├── test_dual_llm.py         # US2
│   │   ├── test_streaming.py        # US2
│   │   ├── test_mcp_server.py       # US3
│   │   └── test_tool_budget.py      # US3
│   └── test_lib/
│       └── test_vectordb.py         # US1
├── pyproject.toml               # Dependencies (EXISTS)
└── Dockerfile                   # Docker image (EXISTS)
```

---

## Implementation Order

```
Phase 1: Setup ───────────────► Phase 2: Foundational ───► US1: LLM Integration ──► US2: Agent Orchestration ──► US3: External ──► US4: Advanced
                                    │                          │                          │                       │
                                    │                          │                          │                       │
                                    ▼                          ▼                          ▼                       ▼
                              api-demo already              litellm_client.py            langgraph_pipeline.py     mcp_server.py         langfuse.py
                              organized (DONE)              + embeddings.py              + dual_llm.py             + tool_budget.py       + synthetic_rca.py
                                                            + vectordb.py                + streaming_handler.py                          + ai_self_healing.py
                                                            + semantic KB search                                               
```

---

## Key Decisions

1. **LiteLLM over direct OpenAI/Anthropic SDK**: Matches OpenSRE pattern. Single interface for all providers. No vendor lock-in.
2. **In-memory vector store first, pgvector later**: Demo/test speed. No dependency on Postgres for unit tests.
3. **LangGraph over LangChain AgentExecutor**: More explicit state control, conditional edges, easier to test each node.
4. **Dual-LLM pattern**: Reasoning model (slow, smart) for analysis + Tool-call model (fast, cheap) for tool execution. Pattern from OpenSRE and LangGraph docs.
5. **MCP over custom tool protocol**: Standard protocol adopted by Claude, LangChain, and the broader AI ecosystem.
6. **Langfuse over custom LLM observability**: Open-source, LiteLLM integration built-in, traces/spans/ token usage out of the box.
7. **All code in api-demo/**: Zero risk of breaking existing ObservAI backend. Demo lab is sandboxed.

---

## Dependencies

```
US1 (LLM Integration) — no deps
  └── US2 (Agent Orchestration) — depends on US1 (needs LLM)
       └── US3 (External Integration) — depends on US2 (needs agents)
            └── US4 (Advanced AI) — depends on US3 (needs MCP tools)
```
