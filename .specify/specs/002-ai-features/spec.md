# Feature Specification: AI Capabilities for ObservAI Demo Lab

**Feature Directory**: `002-ai-features`

**Created**: 2026-07-08

**Status**: Draft

**Input**: Research report from `001-observai-platform/research.md` + existing `api-demo/` structure + Constitution

---

## User Stories

### User Story 1 — LLM Integration via LiteLLM (Priority: P1)

An SRE wants to query any LLM provider (OpenAI, Anthropic, local Ollama) through a single unified interface in the ObservAI demo lab. The system uses LiteLLM as a proxy layer, stores incident embeddings in pgvector for semantic KB search, and generates LLM-powered RCA reports.

**Why P1**: LiteLLM is the foundational dependency — all other AI features (agents, MCP, observability) depend on having a working LLM gateway first.

**Independent Test**: Can be tested by calling `llm_complete("hello")` with `litellm` mocked, verifying correct messages are sent. pgvector integration tested with `cosine_similarity` and mocked OpenAI embeddings.

**Acceptance Scenarios**:
1. **Given** an LLM API key configured, **When** the user calls `llm_complete()`, **Then** the response text is returned through LiteLLM.
2. **Given** a text string, **When** `embed_text()` is called, **Then** a float vector of correct dimension is returned.
3. **Given** two embedding vectors, **When** `cosine_similarity()` is called, **Then** the result is in [-1, 1].
4. **Given** a KB entry and an incident description, **When** semantic search is performed, **Then** the top-K most similar entries are returned.

---

### User Story 2 — Agent Orchestration with LangGraph (Priority: P2)

An SRE wants a multi-step AI agent pipeline that triages an incident, analyzes root cause, and suggests a runbook. The agent uses LangGraph for stateful orchestration with conditional edges (triage → recommend or stop).

**Why P2**: Builds on US1 (needs LiteLLM/LLM gateway). Dual-LLM pattern (reasoning + tool-call models) and SSE streaming add advanced capabilities.

**Independent Test**: Pipeline can be tested with mocked LLM responses — verify state transitions, conditional routing, and output structure.

**Acceptance Scenarios**:
1. **Given** an incident description, **When** the LangGraph pipeline runs, **Then** it produces `analysis` + `recommendation`.
2. **Given** an empty analysis, **When** `should_continue()` is evaluated, **Then** the pipeline stops (doesn't hallucinate).
3. **Given** a valid analysis, **When** `should_continue()` is evaluated, **Then** the recommendation node runs.

---

### User Story 3 — External Integration via MCP + Tool Budget (Priority: P3)

An SRE wants to connect external tools (Slack, Telegram) to the AI agent and set tool-usage budgets. The system implements the Model Context Protocol (MCP) server for standardized LLM-tool interaction.

**Why P3**: Depends on US1 (LLM) and US2 (agent orchestration). MCP enables the agent to call external tools with bounded execution.

**Independent Test**: MCP server can be tested independently by sending a valid MCP request and verifying the JSON-RPC response. Tool budget tested by exceeding limits and verifying enforcement.

**Acceptance Scenarios**:
1. **Given** an MCP server running, **When** a client sends a tool call request, **Then** the server responds with a valid JSON-RPC response.
2. **Given** a tool budget of N calls, **When** the agent exceeds N, **Then** subsequent calls are rejected.

---

### User Story 4 — Advanced AI Capabilities (Priority: P4)

An SRE wants synthetic RCA testing (via OpenSRE-style RL environment), AI-augmented self-healing (beyond the current rule-based `self_healing_agent.py`), and LLM observability via Langfuse for tracing LLM calls.

**Why P4**: Depends on all previous US. Langfuse integration needs LiteLLM (US1), synthetic testing needs agents (US2), AI self-healing needs MCP tools (US3).

**Independent Test**: Langfuse tracing can be tested by verifying spans/events are created during an LLM call. Synthetic RCA can be tested by running a simulated incident and measuring the quality of the generated RCA.

**Acceptance Scenarios**:
1. **Given** an LLM call, **When** Langfuse is configured, **Then** a trace with input/output/tokens is recorded.
2. **Given** a simulated failure, **When** synthetic RCA runs, **Then** it produces a root cause with accuracy score.

---

## Non-Requirements

- Real Slack/Telegram bot deployment (bot tokens, webhooks). Only the MCP integration point + demo stubs.
- Production-grade authentication for MCP server (demo only).
- Full pgvector production deployment (schema, migrations). Embedding storage is in-memory for the demo phase.
- Langfuse self-hosting. Point to Langfuse Cloud or skip if unconfigured.
