# ObservAI API Demo Lab

Multi-provider LLM gateway, LangGraph agent orchestration, MCP tool server, and LLM observability — all containerized with Docker.

## Quick Start

```bash
# Set environment variables (copy and edit)
cp api-demo/.env.example api-demo/.env

# Run all tests
make api-demo-test

# Build the Docker image
make api-demo-build

# Run inside container
docker compose --profile demo run api-demo
```

## User Stories

### US1 — LLM Integration with LiteLLM

Single unified LLM gateway with semantic KB search.

```bash
# Basic completion
uv run --directory api-demo python -m agents.litellm_client --prompt "analyze CPU spike"

# With knowledge base context
uv run --directory api-demo python -m agents.litellm_client --prompt "analyze incident" --kb
```

Tests: `uv run --directory api-demo --extra dev python -m pytest tests/test_lib/ tests/test_agents/test_litellm_client.py -v`

### US2 — Agent Orchestration with LangGraph

Multi-step dual-LLM pipeline (reasoning model + tool model).

```bash
uv run --directory api-demo python -m agents.langgraph_pipeline \
  --incident "API latency spike detected at 95th percentile"
```

Tests: `uv run --directory api-demo --extra dev python -m pytest tests/test_agents/test_dual_llm.py tests/test_agents/test_langgraph_pipeline.py tests/test_agents/test_streaming.py -v`

### US3 — External Integration via MCP + Tool Budget

JSON-RPC tool server with rate-limited dispatch.

```bash
# Interactive MCP demo (reads JSON-RPC from stdin)
uv run --directory api-demo python -m agents.mcp_server --port 8100

# Tool budget demo
uv run --directory api-demo python -m agents.tool_budget --max 5
```

Tests: `uv run --directory api-demo --extra dev python -m pytest tests/test_agents/test_mcp_server.py tests/test_agents/test_tool_budget.py -v`

### US4 — Advanced AI Capabilities

Langfuse observability, synthetic RCA evaluation, and AI self-healing.

```bash
# Synthetic RCA evaluation
uv run --directory api-demo python -m agents.synthetic_rca

# Langfuse tracing (set LANGFUSE_SECRET_KEY first)
uv run --directory api-demo python -c "from agents.langfuse import LangfuseTracer; print('ok')"
```

Tests: `uv run --directory api-demo --extra dev python -m pytest tests/test_agents/test_langfuse.py tests/test_agents/test_synthetic_rca.py tests/test_agents/test_ai_self_healing.py -v`

## Full Test Suite

```bash
uv run --directory api-demo --extra dev python -m pytest tests/ -v
```

Expected: **87 tests** across embeddings, vectordb, litellm, langgraph, dual-llm, streaming, mcp, tool_budget, langfuse, synthetic_rca, and ai_self_healing modules.

## Environment Variables

See [`.env.example`](.env.example) for all required variables. Key ones:

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | — | OpenAI / LiteLLM provider |
| `LITELLM_API_KEY` | — | LiteLLM proxy auth |
| `LITELLM_DEFAULT_MODEL` | `gpt-4o` | Default LLM model |
| `EMBED_MODEL` | `text-embedding-3-small` | Embedding model |
| `LANGFUSE_SECRET_KEY` | — | Langfuse observability |
| `DATADOG_API_KEY` | — | Datadog telemetry |

## Project Layout

```
api-demo/
├── agents/
│   ├── litellm_client.py       # US1: LiteLLM proxy
│   ├── langgraph_pipeline.py   # US2: LangGraph pipeline (dual-LLM)
│   ├── dual_llm.py             # US2: Reasoning + tool models
│   ├── streaming_handler.py    # US2: SSE streaming
│   ├── mcp_server.py           # US3: MCP tool server
│   ├── tool_budget.py          # US3: Rate limiter
│   ├── langfuse.py             # US4: LLM observability
│   ├── synthetic_rca.py        # US4: RCA evaluation
│   └── ai_self_healing.py      # US4: Remediation agent
├── lib/
│   ├── embeddings.py           # embed_text + cosine_similarity
│   └── vectordb.py             # In-memory vector store
├── data/
│   ├── incidents.json          # Incident fixtures
│   └── kb_entries.json         # KB fixtures
├── tests/
│   ├── test_lib/               # Unit tests for lib/
│   └── test_agents/            # Unit tests for agents/
├── Dockerfile                  # Multi-stage container
├── pyproject.toml              # Dependencies + tool config
└── .env.example                # Environment template
```
