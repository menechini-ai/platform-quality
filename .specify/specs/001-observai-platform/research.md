# Research Report: AI Observability Platforms & Agentic AI for SRE

**Date**: 2026-07-08
**Context**: Benchmarking for ObservAI — open-source AI-augmented observability platform on Datadog
**Scope**: Best AI observability platforms (commercial + open-source) + AI agent patterns for SRE + fit analysis for ObservAI

---

## 1. Commercial AI Observability Platforms (Market Leaders)

| Platform | AI Feature | Key Differentiator | Pricing |
|---|---|---|---|
| **Datadog Bits AI SRE** | Autonomous agent investigates every alert; reads metrics/logs/traces/code; Agent Trace view; Dev Agent opens PRs | Deepest Datadog integration; code-level RCA | Included in Datadog enterprise |
| **Dynatrace Davis AI** | Causal AI, deterministic RCA, Smartscape topology mapping | Causal graph → explainable auditable root cause | Enterprise license |
| **Grafana Cloud (Grafana Intelligence)** | AI SRE dashboards, anomaly detection, OpenTelemetry-native | Open standards, no lock-in | Free tier + paid |
| **New Relic AI** | AIOps, anomaly detection, broad observability coverage | Widest entity coverage (mobile, browser, infra, APM) | Per-seat pricing |
| **Splunk AI** | ML-based log analysis, SIEM + observability | Enterprise security + compliance | Enterprise (most expensive) |
| **OpsPilot AI** | Highest G2 satisfaction (73.69); AI SRE teammate; OTel-native autonomous operations | Perfect 10.0 Product Direction; 1-2 day deployment | Commercial |
| **PagerDuty AIOps** | Incident routing, escalation, on-call orchestration + AI | Mature incident-response workflow | $20-40/user/month |
| **BigPanda** | Agentic event correlation on top of Datadog | Correlation layer that cuts noise before triage | Enterprise |
| **Resolve.ai** | Autonomous incident remediation | Full closed-loop remediation | Enterprise |

### Key Market Trends (2026)

1. **Agentic AIOps** is the inflection point — systems don't just detect, they **investigate, correlate, and execute** (with approval).
2. **OpenTelemetry-native** AI is winning — teams want to keep their existing observability stack and add AI on top, not replace it.
3. **Graduated autonomy** is the standard pattern: start at "recommend", grow to "auto-remediate" per environment.
4. **MCP (Model Context Protocol)** has become the standard for AI-tool integration in observability.
5. **Explainability** is non-negotiable — every RCA must link back to evidence.

---

## 2. Open-Source AI SRE / Agentic Incident Management Platforms

| Project | Stars | Language | Agent Framework | License | Key Feature |
|---|---|---|---|---|---|
| **OpenSRE** (Tracer-Cloud) | 7.6k | Python | Custom + LangGraph | Apache 2.0 | 60+ tool integrations; RL environment; synthetic RCA testing |
| **Aurora** (Arvo-AI) | 364 | Python + TS | LangGraph | Apache 2.0 | Multi-cloud agentic investigation; sandboxed K8s pods; Memgraph knowledge graph |
| **IncidentFox** | 638 | Python + TS | Multi-agent | Apache 2.0 + BSL | 45+ integrations; Slack-native; specialist sub-agents |
| **OnGrid** | 382 | Go + TS | Coordinator + Specialist | Apache 2.0 | Zero inbound ports; browser SSH; multi-channel (Slack/Telegram) |
| **Kubernaut** | 20 | Go | Custom + MCP/A2A | Apache 2.0 | Full OODA loop for K8s; MCP + A2A protocol support |
| **AIOps MCP** | New | Python | 6 specialist agents | Apache 2.0 | MCP-native; Claude/ChatGPT/Cursor integration; 10-second RCA |
| **Scorching AIOps** | New | Python + Go + Rust | LangGraph + Ollama | Apache 2.0 | eBPF + causal graph (Neo4j) + full OODA loop |
| **Kronveil** | New | Go + TS | Custom LLM agent | Apache 2.0 | 10M events/sec; Bedrock Claude; anomaly detection |
| **APO (AutoPilot Observability)** | 378 | Go + TS | AI agent workflows | Apache 2.0 | OTel + eBPF + LLM; alert validity + RCA workflows |
| **SLAR** | 14 | JS + Go + Python | Claude Agent SDK | AGPL-3.0 | AI on-call platform; MCP tools; mobile app |
| **Akmatori** | 26 | Go + TS | Skills-based agents | Apache 2.0 | Agent Skills format; cron investigations; multi-LLM |
| **AegisOps** | New | Python | LangGraph ReAct | Not specified | Multi-tier memory (episodic/semantic/procedural); policy-gated actions |

### Deep Dive: Top 3 Most Relevant

#### 1. OpenSRE (Tracer-Cloud) ⭐ 7.6k
**Why it matters**: Most mature open-source AI SRE framework. Has 60+ integrations including Datadog, Grafana, PagerDuty, Kubernetes. Built-in synthetic RCA testing and RL training environment.
**Architecture**: Agent tool-calling loop → structured investigation → evidence-backed root cause. Supports MCP, ACP, OpenClaw protocols.
**Stack**: Python, LangGraph (agent orchestration), Neo4j (knowledge graph), LiteLLM (multi-provider LLM), PostgreSQL.

#### 2. Aurora (Arvo-AI) ⭐ 364
**Why it matters**: Purpose-built for multi-cloud incident management with LangGraph agent orchestration. Strong security model (sandboxed pods, SigmaHQ guardrails, NeMo input rail).
**Architecture**: Alert webhooks → LangGraph agents → 30+ tools → structured RCA → postmortem generation
**Stack**: Python/Flask/Celery, LangGraph, Next.js frontend, Memgraph (graph DB), Weaviate (vector store), PostgreSQL

#### 3. IncidentFox ⭐ 638
**Why it matters**: Slack-native AI SRE with multi-agent architecture. Learns from codebase, Slack history, and past incidents.
**Architecture**: Slack bot → orchestrator → specialist agents (K8s, AWS, metrics, code) → RCA + fix suggestions
**Stack**: Python, multi-agent orchestration, 45+ integrations, 24 LLM providers

---

## 3. AI Agent Frameworks for Observability

| Framework | Use Case in Observability | Key Pattern |
|---|---|---|
| **LangGraph** | Agent orchestration (Aurora, OpenSRE, Scorching, AegisOps) | StateGraph with nodes for each investigation phase |
| **LangChain** | Tool-calling LLM chains for data analysis | @tool decorator for observability APIs |
| **LiteLLM** | Multi-provider LLM proxy (18+ providers) | Single interface for any LLM |
| **MCP (Model Context Protocol)** | AI-tool integration standard | MCP server exposes observability tools to any LLM client |
| **A2A (Agent-to-Agent)** | Multi-agent coordination | Google's protocol for agent collaboration |
| **Claude Agent SDK** | Single-agent Slack integration (used by SLAR) | Lightweight agent definition |
| **AutoGen / CrewAI** | Multi-agent teams | Less common in SRE, more in general automation |

### Agent Architecture Patterns for Observability

**Pattern 1: Pipeline Agent** (ObservAI current plan)
```
Alert → Discovery → Breadth Analysis → Depth Analysis → Conclusion
```
Used by: OpenSRE, ObservAI (planned)

**Pattern 2: Multi-Agent Specialist** (most popular in 2026)
```
Supervisor/Orchestrator
  ├── Log Agent (CloudWatch, Datadog Logs, Loki)
  ├── Infra Agent (Grafana, Prometheus, K8s)
  ├── Change Agent (GitHub, ArgoCD, CI/CD)
  ├── Docs Agent (RAG over runbooks, postmortems)
  └── Impact Agent (business metrics, revenue)
```
Used by: AIOps MCP, IncidentFox, OnGrid, Aurora

**Pattern 3: OODA Loop** (full autonomous cycle)
```
Observe → Analyze → Plan → Apply → Verify
```
Used by: Scorching AIOps, Kubernaut

**Pattern 4: ReAct + Memory**
```
Thought → Action → Observation → (episodic/semantic/procedural memory)
```
Used by: AegisOps

---

## 4. LLM Observability / Tracing Tools (for monitoring AI itself)

| Tool | License | OTel-native | Self-host | Stars | Key Feature |
|---|---|---|---|---|---|
| **Langfuse** | MIT | Yes (v3 SDK) | Yes | 29.8k | Most adopted OSS tracer |
| **Arize Phoenix** | ELv2 | Yes (+OpenInference) | Yes (1 container) | ~10k | Agent-native eval + trajectory |
| **OpenLLMetry** (Traceloop) | Apache 2.0 | Yes (pure OTel) | Yes (SDK to any backend) | 7.2k | Zero-lock LLM instrumentation |
| **SigNoz** | MIT | Yes | Yes | 27.5k | One backend for traces, logs, metrics + LLM |
| **Datadog LLM Obs** | Proprietary | Ingests OTel | No | — | Deepest integration if on Datadog |
| **Braintrust** | Proprietary | No (eval-first) | Enterprise | ~5k | Best eval/experiment workflow |

---

## 5. ObservAI: Current State Analysis

### What Exists ✅
- FastAPI backend with modular architecture (router + service + schemas + models)
- Datadog API client (full proxy over Datadog's 33+ API domains)
- Incident management CRUD
- RCA reports (keyword-based KB matching, NOT LLM-powered)
- Self-healing runbook + action system with HITL approval
- Knowledge base (SQL-based keyword pattern matching)
- Product health & SLO tracking
- Maturity assessment engine
- Analysis agent endpoints (4 rule-based agents)
- JWT authentication
- PostgreSQL + SQLAlchemy async
- Frontend React + Vite + TanStack Query

### What's Missing ❌
- **No LLM integration at all** — zero LLM/OpenAI/Anthropic dependencies; all "agents" are rule-based Python functions
- **No LangGraph/LangChain** — no agent orchestration framework
- **No vector store** — KB is SQL keyword matching, no semantic search or RAG
- **No MCP server** — no way for external AI agents to interact with ObservAI
- **No causal/topology graph** — no service dependency mapping
- **No LLM tracing** — no observability over AI calls
- **No streaming RCA** — all synchronous request-response
- **No self-learning** — KB doesn't learn from new incidents automatically
- **No agentic workflows** — analysis agents are sequential, not dynamic

---

## 6. Recommendations for ObservAI

### Priority 1: Add LLM Foundation (Quick Wins)

| What | Why | How | Effort |
|---|---|---|---|
| **LiteLLM** | Single interface for any LLM provider (OpenAI, Anthropic, Ollama, etc.) | Add `litellm` dependency | 1 day |
| **pgvector** | Semantic search over KB + runbooks | Add `pgvector` extension to PostgreSQL; embed KB entries on save | 2 days |
| **LLM-powered RCA** | Replace keyword matching with real AI analysis | Use LiteLLM to call Claude/GPT for root cause analysis from incident context | 3 days |

### Priority 2: Agent Orchestration (Medium-Term)

| What | Why | How | Effort |
|---|---|---|---|
| **LangGraph integration** | Industry standard for agent orchestration | Port analysis agents to LangGraph StateGraph with proper phases | 5 days |
| **Multi-agent pipeline** | Specialist agents for different domains | Supervisor + sub-agents (LogAgent, MetricAgent, ChangeAgent, KBAgent) | 5 days |
| **Streaming investigations** | Real-time agent progress | SSE streaming from LangGraph nodes | 2 days |

### Priority 3: Self-Learning & RAG (Medium-Term)

| What | Why | How | Effort |
|---|---|---|---|
| **Incident → KB auto-ingestion** | KB grows automatically from resolved incidents | Extract patterns from RCA reports and store as KB entries with embeddings | 3 days |
| **RAG over runbooks** | Agent reads runbooks automatically during investigation | Chunk runbooks → embed → store in pgvector; search during investigation | 2 days |
| **Similar incident matching** | Faster diagnosis via past patterns | Vector similarity search over past incidents | 2 days |

### Priority 4: MCP Server & External Integration (Long-Term)

| What | Why | How | Effort |
|---|---|---|---|
| **MCP server for ObservAI** | Any LLM client can interact with ObservAI | Expose investigation, RCA, KB as MCP tools | 3 days |
| **Slack integration** | Natural interaction channel | ObservAI bot receives alerts, posts RCA summaries | 3 days |
| **ChatOps investigation** | "Why is payment service slow?" in Slack | LangGraph agent + MCP tools accessible via chat | 4 days |

### Priority 5: Full Agentic Capabilities (Long-Term)

| What | Why | How | Effort |
|---|---|---|---|
| **Triggered auto-investigation** | Alerts auto-spawn agent investigation | Webhook → LangGraph agent → investigation → Slack summary | 3 days |
| **Predictive anomaly detection** | Find issues before they page | Statsmodels/ML on Datadog metrics | 5 days |
| **Self-healing with AI** | AI selects and proposes runbooks | Match incident patterns to runbooks via embeddings + LLM reasoning | 4 days |
| **Postmortem generation** | Auto-generate postmortems from RCA | LLM summary of incident timeline + RCA + actions taken | 2 days |

---

## 7. Technology Choices for ObservAI

| Component | Recommended | Alternatives | Rationale |
|---|---|---|---|
| **LLM Provider** | Anthropic Claude (primary) + OpenAI (fallback) | Ollama (air-gapped) | Best for reasoning/long-context; LiteLLM handles routing |
| **LLM Proxy** | LiteLLM | Direct API, OpenRouter | Single interface for 18+ providers; cost tracking |
| **Agent Framework** | LangGraph | LangChain, CrewAI | Most mature for observability agents; used by Aurora, OpenSRE |
| **Vector Store** | pgvector (existing PostgreSQL) | Weaviate, Qdrant | No new infrastructure; works with existing PostgreSQL |
| **Graph DB** | PostgreSQL adjacency lists (start) → Neo4j (scale) | Memgraph | For service topology / blast radius |
| **LLM Tracing** | Langfuse (MIT, self-hosted) | Arize Phoenix, SigNoz | Most adopted OSS; MIT license; OTel-native |
| **MCP** | Built-in Python MCP server | Separate MCP service | Growing standard; any LLM client can use ObservAI |
| **Frontend** | Existing React + TanStack Query | — | Add AI chat component + agent trace view |
| **Async Tasks** | Existing Celery + Redis | — | Already in stack; use for long-running agent investigations |
| **Embeddings** | OpenAI `text-embedding-3-small` or `nomic-embed-text` (local) | Claude embeddings | 1536d vectors; pgvector compatible |

---

## 8. Competitive Positioning

ObservAI's unique advantages vs. alternatives:
1. **Thin layer on Datadog** — if you're already on Datadog, ObservAI adds AI without replacing anything
2. **Open source + self-hosted** — data never leaves your infrastructure
3. **HITL by default** — safe self-healing with human approval
4. **Modular by constitution** — easy to add/remove capabilities

Gap to close vs. OpenSRE/Aurora:
- Need LLM integration urgently (largest gap)
- Need LangGraph for agent orchestration
- Need vector search for KB
- Need triggered auto-investigation
- Need ChatOps/Slack integration

---

---

## 9. Análise Detalhada dos 3 Repositórios Referenciados

### 9.1 OpenObserve (openobserve/openobserve) ⭐ 19.7k

**URL**: https://github.com/openobserve/openobserve
**Licença**: AGPL-3.0
**Linguagem**: TypeScript + Rust (backend em Rust, frontend em Vue)
**Criado**: Fev 2023 | **Último release**: v0.91.1 (Jul 2026)

#### O que é
OpenObserve (O2) é uma plataforma de observabilidade **completa** — logs, métricas, traces, RUM, dashboards, alertas — tudo em um único binário. É posicionado como alternativa open-source ao Datadog, Splunk e Elasticsearch, com **custo de armazenamento 140x menor**.

#### Arquitetura
- **Backend**: Rust (single binary, memory-safe, alta performance)
- **Armazenamento**: Parquet columnar + S3-native (custos 140x menores que Elasticsearch)
- **Frontend**: Vue.js
- **Protocolo**: OpenTelemetry nativo (ingere OTLP)
- **Deploy**: Binário único — deploy em <2 minutos

#### Funcionalidades Principais
| Funcionalidade | Descrição |
|---|---|
| **Logs Management** | Full-text search, SQL queries, Parquet columnar storage |
| **Distributed Tracing** | Gantt charts, service maps, OTel-native |
| **Métricas & Dashboards** | SQL + PromQL, 19+ tipos de gráfico |
| **RUM (Real User Monitoring)** | Performance tracking, error logging, session replay |
| **Pipelines** | Enrich, redact, reduce, normalize on ingest |
| **Alertas** | Threshold-based + anomaly detection |
| **LLM Observability** | Tracing de prompts, tokens, eval tracking, custo por span |
| **AI SRE Agent** | RCA automático, correlação multi-sinal, summarization |
| **Anomaly Detection** | Statistical baseline modeling, correlated signal detection |
| **AI Assistant** | Perguntas em linguagem natural → queries otimizadas |

#### AI SRE Agent
O AI SRE Agent do OpenObserve é construído em 3 camadas:
1. **Pattern Recognition**: Reduz milhões de linhas de log a ~100 representativas
2. **Rule-based Correlation**: Motor de correlação manual baseado em regras
3. **LLM Layer**: Análise final via LLM (Claude, GPT, ou qualquer provedor)

**Status**: Disponível para revisão humana; auto-remediação em roadmap.

#### LLM Observability
- Tracing de ponta-a-ponta (prompt → tool call → response)
- Custo por token por span (com pricing customizável por modelo)
- Integração com OpenTelemetry, LangChain, LangFuse
- Eval automático: amostragem + LLM evaluator (factual grounding, coherence, relevance)
- Suporte a OpenAI, Anthropic, Google, Mistral, Meta, self-hosted

#### OpenObserve vs ObservAI

| Aspecto | OpenObserve | ObservAI |
|---|---|---|
| **Foco** | Plataforma completa de observabilidade (logs + métricas + traces + RUM) | Camada de inteligência sobre Datadog |
| **Stack** | Rust + Vue.js (single binary) | Python/FastAPI + React |
| **Storage** | Parquet + S3 (140x mais barato) | PostgreSQL (via Datadog API) |
| **AI** | Built-in (AI SRE, LLM Obs, Anomaly Detection) | Rule-based agents (sem LLM ainda) |
| **Licença** | AGPL-3.0 (open core, ~1% enterprise) | AGPL-3.0 (a verificar) |
| **Maturidade** | Production-ready (2.5 PB/dia no maior cliente) | Em desenvolvimento |
| **OpenTelemetry** | Nativo | Via Datadog API |

#### O que podemos aprender com OpenObserve
1. **Rust para performance**: Single binary, deploy em <2 min, storage 140x mais barato
2. **AI SRE em camadas**: Pattern recognition → rule correlation → LLM (abordagem pragmática para contexto limitado)
3. **LLM Observabilidade integrada**: Tracing de LLM como parte da plataforma, não add-on
4. **OpenTelemetry-native**: Sem lock-in, qualquer stack se integra
5. **Query em linguagem natural**: "Mostra erros do payment service na última hora" → query otimizada

**Conclusão para ObservAI**: OpenObserve é mais um **concorrente/alternativa** do que uma peça integrável. Se o objetivo for oferecer observabilidade full-stack (não apenas uma camada sobre Datadog), vale considerar migrar para OpenObserve como base. Para o escopo atual de "camada inteligente sobre Datadog", os patterns de AI SRE (camadas, LLM Obs) são referência de design.

---

### 9.2 OpenSRE (swapnildahiphale/OpenSRE) ⭐ 81

**URL**: https://github.com/swapnildahiphale/OpenSRE
**Licença**: Apache 2.0
**Linguagem**: Python (LangGraph)
**Estrelas**: 81 | **Forks**: 17

#### O que é
OpenSRE (por Swapnil Dahiphale) é um **AI SRE agent** focado em investigação autônoma de incidentes de produção. Ele combina **memória episódica** (lembra de incidentes passados) com um **Neo4j knowledge graph** (mapeia dependências de serviço) e **46 skills production-ready** para ferramentas como Datadog, Grafana, PagerDuty, Elasticsearch, Kubernetes e AWS.

#### Arquitetura

```
                    Slack / Web UI / API
                           |
              ┌────────────┼────────────┐
              ↓            ↓            ↓
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Slack Bot│ │ Web UI   │ │ REST API │
        │ (Socket  │ │ (Next.js)│ │          │
        │  Mode)   │ │ :3002    │ │          │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             └─────────────┼────────────┘
                           ↓
                    ┌──────────────┐
                    │  SRE Agent   │
                    │  - LangGraph │
                    │  - 46 Skills │
                    │  - Memory    │
                    │  :8001       │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ↓            ↓            ↓
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Config   │ │ LiteLLM  │ │ Neo4j    │
        │ Service  │ │ Proxy    │ │ Knowledge│
        │ (Postgres│ │ :4001    │ │ Graph    │
        │  :8081)  │ │          │ │ :7475    │
        └──────────┘ └──────────┘ └──────────┘
```

#### LangGraph Pipeline
```
init_context → memory_lookup / kg_context → planner → 
parallel subagents (Send()) → synthesizer → writeup → memory_store
```

#### Stack Tecnológica
| Componente | Tecnologia |
|---|---|
| Agent Orchestration | LangGraph (planner → subagents → synthesizer) |
| Backend API | FastAPI (SSE streaming) |
| Web Console | Next.js |
| LLM Proxy | LiteLLM (18+ providers) |
| Knowledge Graph | Neo4j (service topology, blast radius) |
| Storage | PostgreSQL (config, episodes, agent state) |
| Memory | Episodic memory (multi-factor similarity) |

#### 46 Skills (categorias)
| Categoria | Skills |
|---|---|
| **Observability** | Coralogix, Grafana, Elasticsearch, Datadog, Splunk, New Relic, Honeycomb, Jaeger, Sentry, Loki, VictoriaLogs, VictoriaMetrics, Amplitude |
| **Incidents** | PagerDuty, Incident.io, Opsgenie, Blameless, FireHydrant |
| **Infrastructure** | Kubernetes, AWS, Docker, GCP, Azure, Neo4j |
| **Databases** | PostgreSQL, MySQL, Snowflake, BigQuery |
| **Streaming** | Kafka |
| **Platform** | Vercel, flagd (OpenFeature) |
| **Project & Docs** | GitLab, Jira, Linear, Notion, ClickUp, Sourcegraph, Google Docs |
| **Investigation** | RCA, observability methodology, metrics analysis, remediation, KB (RAPTOR), incident comms |

#### O que podemos aprender com OpenSRE (swapnildahiphale)
1. **Episodic Memory**: Similaridade multi-fator (alert type 0.5, service 0.3, resolved status 0.2) — padrão valioso para o KB do ObservAI
2. **Knowledge Graph**: Neo4j para blast radius — ObservAI poderia implementar com pgvector + adjacency lists inicialmente
3. **LangGraph Send()**: Fan-out paralelo para sub-agents — padrão ideal para análise multi-sinal
4. **Progressive Skill Loading**: Metadados (~100 tokens) carregados primeiro, conteúdo completo on-demand — eficiente para muitos tools
5. **LiteLLM Proxy**: Interface única para 18+ provedores — evitar lock-in de LLM
6. **Slack Integration**: Canal primário de interação — @mention → investigação → resumo no thread

**Conclusão para ObservAI**: Este OpenSRE é um **fork independente** do Tracer-Cloud OpenSRE com **arquitetura mais modular** (LangGraph explícito, Neo4j, memória episódica). É excelente referência de design para agentes SRE. A stack (FastAPI + LangGraph + LiteLLM + PostgreSQL) é quase idêntica à base do ObservAI, facilitando a adoção dos patterns.

---

### 9.3 OpenSRE (Tracer-Cloud/opensre) ⭐ 7.6k

**URL**: https://github.com/Tracer-Cloud/opensre
**Licença**: Apache 2.0
**Linguagem**: Python
**Estrelas**: 7.6k | **Forks**: 994 | **Contribuidores**: 210

#### O que é
OpenSRE (Tracer-Cloud) é um **framework open-source para construir AI SRE agents**, com ambição de ser o "SWE-bench para SRE" — um ambiente de treinamento e avaliação para agentes de resposta a incidentes. Conecta 60+ ferramentas, define workflows customizáveis e investiga incidentes na própria infraestrutura.

#### Filosofia
> "Build for AI SRE the kind of training and evaluation ground that SWE-bench gave coding agents."

OpenSRE não é apenas um agente — é uma **infraestrutura de avaliação** com:
- **Testes sintéticos**: Cenários de RCA pontuados com red herrings adversariais
- **Testes E2E**: Cloud real (Kubernetes, EC2, CloudWatch, Lambda, ECS Fargate, Flink)
- **LLM-judge**: Grading baseado em rubrica para cada investigação

#### Arquitetura (Dual-LLM)

| Componente | Função |
|---|---|
| **Reasoning Model** | LLM pesado para análise complexa (ex: Claude Opus, GPT-4o) |
| **Toolcall Model** | LLM leve para seleção de ferramentas e planejamento |
| **Planner** | Decide o que investigar (tool budget: 10 tools/passo, max 50) |
| **Executor** | Executa tools contra integrações reais |
| **Synthesizer** | Constrói relatório estruturado com evidências |
| **Publish** | Posta sumário no Slack/PagerDuty |

#### Investigação Pipeline
```
onboard → fetch_alert_context → reason_across_systems → 
generate_report → suggest_next_steps → post_summary
```

#### Dual-LLM Design (diferencial chave)
Separa responsabilidades entre dois modelos especializados:
- **Reasoning**: Análise profunda, diagnóstico, sumarização (modelo caro)
- **Toolcall**: Seleção de tools, extração de parâmetros (modelo barato)

**Isso reduz custos de API significativamente** — o modelo caro só é chamado quando necessário.

#### Integrações (60+)
| Categoria | Integrações |
|---|---|
| **LLM Providers** | Anthropic, OpenAI, Ollama, Gemini, OpenRouter, Bedrock, Codex CLI |
| **Observability** | Grafana (Loki/Mimir/Tempo), Datadog, Honeycomb, Coralogix, CloudWatch, Sentry, Elasticsearch, Better Stack |
| **Infrastructure** | Kubernetes, AWS (S3, Lambda, EKS, EC2, Bedrock), GCP, Azure |
| **Databases** | PostgreSQL, MySQL, MongoDB, ClickHouse |
| **Incident Management** | PagerDuty, Opsgenie, Jira, Alertmanager |
| **Protocols** | MCP, ACP, OpenClaw |

#### Diferenciais
1. **Tool Budget**: Default 10 tools/passo, max 50 — controle de custo
2. **Evidence-backed RCA**: Toda conclusão linkada aos dados que a suportam
3. **Validity Scoring**: Confiança quantificada nas claims de root cause
4. **Synthetic RCA Suites**: Testes com ground truth + red herrings
5. **4 modos de esforço**: low (barato/rápido), medium, high, max (exaustivo)
6. **MCP Nativo**: Suporte a MCP, ACP e OpenClaw

#### Limitações Atuais (público-alvo alpha)
- Sem approval workflow para remediation
- Integrações rasas (~100 linhas cada) — edge cases não tratados
- Benchmark não publicado formalmente
- Telemetria opt-out (PostHog + Sentry)

#### O que podemos aprender com Tracer-Cloud OpenSRE
1. **Dual-LLM Architecture**: Pattern essencial para economia de custos — usar modelo barato para tool selection, modelo caro só para reasoning
2. **Tool Budget**: Controle explícito de custo por investigação
3. **Synthetic RCA Testing**: Testar agente com cenários sintéticos antes de produção
4. **Effort Levels**: low/medium/high/max — trade-off explícito entre qualidade e custo
5. **MCP Ecosystem**: Suporte a MCP como protocolo de integração
6. **Evidence-backed**: Cada conclusão deve linkar à evidência (transparência)

**Conclusão para ObservAI**: Este é o projeto **mais relevante** dos 3 — framework completo para AI SRE agents com o ecossistema mais maduro (7.6k stars, 210 contribuidores). A arquitetura dual-LLM e o tool budget são patterns que ObservAI deveria adotar. O foco em synthetic testing e evaluation é algo que nenhuma outra plataforma open-source tem.

---

## 10. Comparativo Direto: OpenObserve vs OpenSRE (swapnildahiphale) vs OpenSRE (Tracer-Cloud)

| Aspecto | OpenObserve | OpenSRE (swapnildahiphale) | OpenSRE (Tracer-Cloud) |
|---|---|---|---|
| **Stars** | 19.7k | 81 | 7.6k |
| **Foco** | Plataforma completa de observabilidade | AI SRE Agent autônomo | Framework para AI SRE Agents |
| **Stack** | Rust + Vue | Python/LangGraph + Next.js | Python/LangGraph |
| **Licença** | AGPL-3.0 | Apache 2.0 | Apache 2.0 |
| **AI Pattern** | Built-in (pattern → rules → LLM) | Memória episódica + KG + LangGraph | Dual-LLM (reasoning + toolcall) |
| **Storage** | Parquet + S3 | PostgreSQL + Neo4j | PostgreSQL |
| **LLM Obs** | Nativo (tracing + eval) | Não | LangSmith |
| **MCP** | Não | Não | Sim (MCP, ACP, OpenClaw) |
| **Benchmark** | Não | Não | Sim (synthetic RCA + e2e) |
| **Production Ready** | Sim (2.5 PB/dia) | Em desenvolvimento | Alpha |
| **Self-hosted** | Sim (single binary) | Sim (Docker Compose) | Sim (Vercel, EC2, ECS) |

---

## 11. Análise de Fit: O que usar no ObservAI

### Para o Core da Plataforma

| Componente | Escolha | Por quê |
|---|---|---|
| **Base de observabilidade** | Manter Datadog API | ObservAI é uma camada sobre Datadog, não um substituto. OpenObserve seria relevante se quiséssemos ser uma plataforma completa. |
| **LLM Integration** | LiteLLM (padrão dos 2 OpenSREs) | Interface única para 18+ provedores. Swapnildahiphale OpenSRE e Tracer-Cloud OpenSRE ambos usam. |
| **Agent Framework** | LangGraph (swapnildahiphale OpenSRE) | Mais maduro para agentes SRE. Send() para fan-out paralelo. |
| **Memory/Knowledge Graph** | pgvector (início) → Neo4j (escala) | Swapnildahiphale OpenSRE prova o valor do Neo4j para blast radius. Começar com pgvector no PostgreSQL existente. |
| **Dual-LLM** | Sim (Tracer-Cloud pattern) | Reasoning model + Toolcall model reduz custos significativamente. |
| **LLM Tracing** | Langfuse (MIT, self-hosted, 29.8k ⭐) | OpenObserve prova que LLM Obs é essencial. Langfuse é o padrão da indústria. |
| **MCP** | Sim (Tracer-Cloud pattern) | Protocolo padrão para integração AI → ferramentas. |

### Para Features Específicas

| Feature | Inspiração | Prioridade |
|---|---|---|
| **Episodic Memory** | swapnildahiphale OpenSRE (similaridade multi-fator) | Alta |
| **Tool Budget** | Tracer-Cloud OpenSRE (default 10, max 50) | Alta |
| **Effort Levels** | Tracer-Cloud OpenSRE (low/medium/high/max) | Média |
| **Synthetic RCA Testing** | Tracer-Cloud OpenSRE (scored suites + red herrings) | Média |
| **Query em Linguagem Natural** | OpenObserve (AI Assistant) | Média |
| **LLM Eval Automático** | OpenObserve (amostragem + LLM evaluator) | Baixa |
| **Slack-Native** | swapnildahiphale OpenSRE (@mention → investigação) | Alta |
| **Progressive Skill Loading** | swapnildahiphale OpenSRE (~100 tokens metadata) | Média |

### Roadmap sugerido para ObservAI

**Fase 1 (Agora) — Fundação LLM**
1. Adicionar LiteLLM como dependência
2. Adicionar pgvector ao PostgreSQL
3. Substituir keyword-matching do KB por embeddings semânticos
4. Adicionar LLM-powered RCA (usando contexto do incidente)

**Fase 2 (Curto prazo) — Agentes**
1. Migrar analysis agents rule-based para LangGraph StateGraph
2. Implementar dual-LLM (toolcall barato, reasoning caro)
3. Adicionar streaming SSE para investigações em tempo real
4. Episodic memory para o KB (aprender de incidentes passados)

**Fase 3 (Médio prazo) — Automação**
1. MCP server para ObservAI (qualquer LLM client pode usar)
2. Slack/Telegram integration (auto-investigação em chat)
3. Tool budget + effort levels
4. Triggered auto-investigation (alerta → agente → RCA)

**Fase 4 (Longo prazo) — Maturidade**
1. Synthetic RCA testing (benchmark para o agente)
2. Self-healing com AI (seleção de runbook via embeddings + LLM)
3. LLM Observability (Langfuse)
4. Knowledge Graph (Neo4j para blast radius)

---

## 12. References

### Repositórios Referenciados pelo Usuário
- [OpenObserve](https://github.com/openobserve/openobserve) — 19.7k ⭐, AGPL-3.0. Plataforma completa de observabilidade (logs, métricas, traces, RUM, LLM Obs) em Rust
- [OpenSRE (swapnildahiphale)](https://github.com/swapnildahiphale/OpenSRE) — 81 ⭐, Apache 2.0. AI SRE agent com memória episódica + Neo4j knowledge graph + 46 skills
- [OpenSRE (Tracer-Cloud)](https://github.com/Tracer-Cloud/opensre) — 7.6k ⭐, Apache 2.0. Framework open-source para AI SRE agents, 60+ integrações, dual-LLM, synthetic RCA testing

### Outras Plataformas Open-Source
- [Aurora by Arvo AI](https://github.com/Arvo-AI/aurora) — 364 ⭐, Apache 2.0
- [IncidentFox](https://github.com/incidentfox/incidentfox) — 638 ⭐, Apache 2.0 + BSL
- [OnGrid](https://github.com/ongridio/ongrid) — 382 ⭐, Apache 2.0
- [APO (AutoPilot Observability)](https://github.com/CloudDetail/apo) — 378 ⭐, Apache 2.0
- [Scorching AIOps](https://github.com/necrustulum/scorching-aiops) — Apache 2.0
- [Kronveil](https://github.com/kronveil/kronveil) — Apache 2.0
- [Kubernaut](https://github.com/jordigilh/kubernaut) — Apache 2.0
- [AIOps MCP](https://github.com/Elvisaryan/aiops-mcp) — Apache 2.0
- [SLAR](https://github.com/SlarOps/slar) — AGPL-3.0
- [Akmatori](https://github.com/akmatori/akmatori) — Apache 2.0
- [AegisOps](https://github.com/aitch-cmd/AegisOps-DRI-Autonomous-SRE-Agent) — LangGraph + Ollama

### LLM Observability & Tracing
- [Langfuse](https://github.com/langfuse/langfuse) — 29.8k ⭐, MIT
- [Arize Phoenix](https://github.com/Arize-AI/phoenix) — ~10k ⭐, ELv2
- [tracesage](https://github.com/kjgpta/tracesage) — LangChain/LangGraph tracing local-first, MIT

### Artigos & Comparativos
- [OpsPilot AI Comparison](https://opspilot.com/best-ai-sre-tools-for-opentelemetry-2026/) — G2-based evaluation
- [AI Agent Observability Tools](https://www.morphllm.com/ai-agent-observability-tools) — 2026 comparison
- [OpenObserve lowers storage costs by 140x](https://www.techzine.eu/blogs/analytics/140020/openobserve-lowers-observability-storage-costs-by-140x/) — Techzine, Mar 2026
