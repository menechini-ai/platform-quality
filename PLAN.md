# PLAN.md — ObservAI

> Living plan for the ObservAI platform: an open-source observability platform powered by the
> Datadog API for incident analysis, root-cause analysis (RCA), product health, maturity
> assessment, and self-healing automation — with agentic AI on top.
>
> This document is benchmarked against the best AI observability platforms that integrate with
> Datadog (see [§2](#2-benchmark-best-ai-observability-on-datadog) and [§7](#7-references)),
> and treats **code quality as a first-class, continuous objective** (see [§4](#4-code-quality-principles)).

---

## 1. Vision & Mission

**Mission.** Give SRE/Platform teams a single, AI-assisted control plane over their Datadog
telemetry — so that when an alert fires, the path from *symptom* → *root cause* → *remediation*
is fast, evidence-backed, and (where safe) automated with a human in the loop.

**North star.** Move from *dashboard-and-alert fatigue* to *agentic investigation*: the platform
correlates metrics, logs, traces, deployments, and topology; explains the causal chain in plain
language; proposes (and, with approval, executes) remediation; and continuously learns from
outcomes via the knowledge base and maturity engine.

**Non-goals.** We are **not** rebuilding Datadog. ObservAI is a thin, opinionated intelligence
layer *on top of* Datadog's API. We proxy and compose Datadog; we do not replace its ingestion.

---

## 2. Benchmark: Best AI Observability on Datadog

### 2.1 Commercial / category leaders

| Platform | What it does well | Lesson for ObservAI |
|----------|-------------------|--------------------|
| **Datadog Bits AI SRE** | Autonomous agent investigates *every* alert; reads metrics/logs/traces/**code**; **Agent Trace** view for transparency; Dev Agent opens PRs with fixes. | Transparency of AI reasoning + code-level remediation. |
| **Dynatrace Davis AI** | Causal AI, **deterministic** RCA, Smartscape topology mapping. | Topology/causal graph → explainable, auditable root cause. |
| **BigPanda** | Agentic event correlation on top of Datadog; incident intelligence. | Correlation layer that cuts noise before triage. |
| **PagerDuty AIOps** | Incident routing, escalation, on-call orchestration. | Mature incident-response workflow is its own product. |
| **Grafana Cloud** | Open-standards (OpenTelemetry) observability + ML. | Standards-first avoids lock-in. |
| **LogicMonitor Edwin / CloudThinker / Sherlocks.ai** | Agentic assistants; **graduated autonomy**; Slack-native; audit trails. | Start at "recommend", grow to "auto-remediate" per environment. |

**Category trend (2026):** the inflection point is *agentic AIOps* — systems that don't just detect,
but **investigate, correlate, and execute** (with approval). Evaluation now includes transparency
and auditability, not just correlation accuracy.

### 2.2 Open-source reference implementations (AI + Datadog)

| Repo | Relevance to ObservAI | Practices to adopt |
|------|-----------------------|--------------------|
| **[atul-007/Sre-Agent](https://github.com/atul-007/Sre-Agent)** | Closest to our RCA: AI SRE agent that correlates Datadog signals + Claude reasoning. | Multi-phase investigation (**Discovery → Breadth → Depth → Conclusion**), dependency-chain tracking (root cause / propagator / victim), clean module layout, Pydantic models, `structlog`, `tenacity`. |
| **[BrianIsaac/Cerberus](https://github.com/BrianIsaac/Cerberus)** | AI-agent observability framework *on* Datadog (FastAPI + `uv`). | Governance-as-code, shared observability module, **MCP server**, dynamic dashboards. |
| **[DataDog/pup](https://github.com/DataDog/pup)** | Official Datadog CLI: 200+ commands across 33+ API domains, AI-agent-ready + ACP server. | Comprehensive, consistent API-surface coverage; first-class agent interface. |
| **[viamus/mcp-datadog](https://github.com/viamus/mcp-datadog)** | MCP server exposing Datadog (logs/metrics/traces/monitors) to AI agents (C#). | MCP server shape: `Configuration / Models / Services / Tools`. |

### 2.3 Where ObservAI stands (gap analysis)

| Capability | Status | Benchmark gap |
|------------|--------|---------------|
| Datadog proxy (REST) | ✅ `datadog_routes/*` | Coverage narrower than `pup`; no agent/MCP interface. |
| Incident mgmt + timelines | ✅ `incidents/` | Mature. |
| RCA engine | 🟡 `rca/` | Single-pass; no multi-phase investigation or dependency-chain propagation (Sre-Agent/Dynatrace). |
| Health & SLOs | ✅ `health/` | Mature. |
| Maturity assessment | ✅ `maturity/` | **Unique strength** — keep & deepen. |
| Knowledge base | ✅ `knowledge_base/` | **Unique strength** — keep & deepen. |
| Self-healing (runbooks + approval) | ✅ `self_healing/` | HITL present; not agentic/graduated-autonomy. |
| Agentic / LLM investigation | ❌ | Missing (Bits AI / CloudThinker). |
| MCP / agent interface | ❌ | Missing (pup / mcp-datadog / Cerberus). |
| Platform self-observability | ❌ | Missing (Cerberus "eat our own dog food"). |

---

## 3. Current State (snapshot)

- **Backend:** FastAPI + Uvicorn, SQLAlchemy 2.0 (async) + `asyncpg`, Alembic, Pydantic v2,
  `python-jose` (JWT HS256) + `passlib[bcrypt]`, `datadog-api-client`, Redis, Celery, Sentry,
  `tenacity`. Python ≥3.11 (CI 3.12).
- **Frontend:** React 18 + TypeScript 5.6 + Vite 6, Tailwind 3, React Router 6, TanStack Query 5,
  Recharts 2, lucide-react, Vitest 4 + RTL.
- **Modules:** `auth`, `incidents`, `rca`, `health`, `self_healing`, `maturity`, `knowledge_base`,
  `analysis`, `datadog`, `datadog_routes`.
- **Infra:** Docker (multi-stage, non-root `observai`), `docker-compose.yml` (dev) +
  `docker-compose.prod.yml` (limits/healthchecks), Nginx for frontend, GHCR push on `main`.
- **Quality gates:** pre-commit (ruff, ruff-format, pyright, gitleaks, vulture ≥65, eslint, tsc,
  pytest, vitest) + GitHub Actions (backend / frontend / docker).
- **Workflow:** Gitflow — features → `develop` → `main`.

**Known hygiene fixes already landed (this session):** `psycopg2-binary` added so Alembic runs in
Docker; frontend `eslint` pinned to `^10.0.0` to match lockfile; Datadog route tests auto-marked
`@pytest.mark.datadog` and skipped without creds; `test_run_assessment` de-flaked (no env-dependent
assertions); Pydantic `ForwardRef('UUID')` import bug fixed.

---

## 4. Code-Quality Principles

These are **non-negotiable** and checked continuously (pre-commit + CI). Regressions here block merge.

1. **Typing is real.** Pydantic v2 models at every boundary; `pyright` clean on changed files.
   *Ban `from __future__ import annotations` in schema/model files* — it broke Pydantic resolution
   (`ForwardRef('UUID')`) once; prefer explicit imports.
2. **Lint & format automatically.** `ruff` + `ruff-format` (pre-commit). No lint noise in PRs.
3. **No dead code.** `vulture --min-confidence 65` passes.
4. **No secrets.** `gitleaks` passes; `.env.example` is the only place defaults live; real secrets
   come from CI/secret store.
5. **Tests are deterministic & environment-independent.** New tests that touch Datadog **must**
   carry `@pytest.mark.datadog` (auto-skipped without `DD_API_KEY`/`DD_APP_KEY`). No `assert 3 == 0`
   style env-dependent assertions. Frontend: Vitest + RTL per component.
6. **TDD for behavior.** New endpoints/features ship with tests first; the `datadog` marker pattern
   keeps CI green without credentials.
7. **Modularity.** One router + service + schemas + models per domain. `datadog_routes/` stays a
   *thin, uniform* proxy over `datadog-api-client` (mirror `pup`'s consistent command surface).
8. **API consistency.** Uniform response models, centralized error handling, auth via
   `Depends(get_current_user)` on writes. `/docs` (FastAPI) is the contract — keep it accurate.
9. **Config & build hygiene.** `package-lock.json` **must** match `package.json` (CI parity check).
   The Docker image **must** include the sync DB driver (`psycopg2-binary`) so `alembic upgrade head`
   works; non-root user; healthchecks on every long-running service.
10. **Security by default.** Strong `SECRET_KEY` (≥32 chars, enforced in prod); Pydantic input
    validation; scoped CORS; JWT short expiry.
11. **Dog-food observability.** Instrument ObservAI *with* Datadog (APM/logs/metrics) so the platform
    watches itself (Cerberus pattern).
12. **Docs stay alive.** README + this PLAN.md updated when a module is added or its contract changes.

---

## 5. Roadmap

Each phase has explicit **quality objectives** and **done criteria**. Phases are sequential; waves
within a phase may run in parallel.

### Phase A — Foundations & Regression Prevention
*Goal: lock in the quality gates from §4 so future work can't regress.*

- **A1.** CI contract: every PR runs ruff, pyright, vulture, gitleaks, `pytest -m "not datadog"`,
  frontend eslint/tsc/vitest. Docker build+push only on `main`.
- **A2.** Formalize the `@pytest.mark.datadog` convention (doc + CI guard that fails if a
  Datadog-touching test isn't marked/skippable).
- **A3.** Add a lockfile↔`package.json` parity check to CI (fails fast on mismatch).
- **A4.** Add a CI job that runs `alembic upgrade head` against a throwaway Postgres (proves the
  Docker migration path end-to-end).
- **A5.** Resolve `pyright` warnings in `core/` and `rca/`; enforce "no `from __future__ import
  annotations` in schemas".
- **Done:** pre-commit 7/7 + CI green on a deliberately-broken-PR smoke test.

### Phase B — Mature the RCA Engine  *(benchmark: Sre-Agent, Dynatrace)*
*Goal: move from single-pass RCA to evidence-backed, multi-phase investigation.*

- **B1.** Refactor `rca/` into a pipeline: **Discovery → Breadth → Depth → Conclusion** with explicit
  Pydantic state models (mirror Sre-Agent).
- **B2.** Add service-map / dependency-chain traversal; label services as *root cause / propagator /
  victim* and render the cascade path.
- **B3.** `structlog` structured logs + `tenacity` retries on every Datadog call (mirror Sre-Agent's
  resilience).
- **B4.** Produce confidence-scored RCA reports with the full dependency path.
- **B5.** Unit-test each phase with a mocked Datadog client (TDD).
- **Done:** RCA report includes dependency chain + confidence; 100% phase coverage with mocks.

### Phase C — Agentic / AI Investigation Layer  *(benchmark: Bits AI SRE, CloudThinker, pup)*
*Goal: natural-language investigation + an agent interface.*

- **C1.** Provider-agnostic LLM reasoning module for NL RCA summaries + suggested remediations.
- **C2.** Expose ObservAI **and** Datadog operations via an **MCP server** (shape: `Configuration /
  Models / Services / Tools`, per `mcp-datadog`/`Cerberus`) so coding agents can drive investigations.
- **C3.** **Graduated autonomy**: observer → recommend → approve → auto-remediate, selectable
  per-environment, with a full audit trail (CloudThinker lesson).
- **C4.** "Agent Trace" transparency view for AI reasoning (Bits AI lesson).
- **Done:** an agent can invoke an investigation over MCP and receive a cited RCA; autonomy level is
  configurable and logged.

### Phase D — Self-Healing & Maturity Maturity  *(benchmark: PagerDuty, BigPanda, Dynatrace)*
*Goal: close the loop from detection to learning.*

- **D1.** Expand runbook library + parameterized, validated actions.
- **D2.** Harden HITL: signed approvals, audit log, safe rollback (build on existing
  approve/reject).
- **D3.** Feed self-healing outcomes back into `maturity/` and `knowledge_base/` (continuous
  learning loop — our differentiator).
- **D4.** SLO / error-budget automation from `health/`.
- **Done:** a remediated incident updates maturity score + KB; audit log is queryable.

### Phase E — Platform Self-Observability  *(benchmark: Cerberus)*
*Goal: eat our own dog food.*

- **E1.** Instrument ObservAI with its own Datadog: investigation latency, RCA success rate,
  self-healing action counts, auth events.
- **E2.** Ship a platform-health dashboard.
- **Done:** ObservAI monitors ObservAI; dashboard live.

---

## 6. Definition of Done (per change)

A change is **Done** when **all** hold:

- [ ] Pre-commit 7/7 hooks pass on changed files.
- [ ] CI green (backend + frontend; docker on `main`).
- [ ] New behavior has tests; Datadog-touching tests are marked & skippable without creds.
- [ ] `pyright` clean on changed files; no new `vulture` findings.
- [ ] API contract (`/docs`) updated if a route changed.
- [ ] README and/or this PLAN.md updated if a module was added/changed.
- [ ] No env-dependent test assertions; no hardcoded secrets; lockfile matches `package.json`.
- [ ] Merged via gitflow (feature → `develop` → `main`).

---

## 7. References

- Datadog Bits AI SRE — https://www.datadoghq.com/blog/bits-ai-sre/
- Dynatrace Davis AI — https://www.dynatrace.com/platform/davis-ai/
- BigPanda + Datadog — https://www.bigpanda.io/blog/datadog-integration/
- Grafana Cloud — https://grafana.com/products/cloud/
- atul-007/Sre-Agent (AI RCA on Datadog) — https://github.com/atul-007/Sre-Agent
- BrianIsaac/Cerberus (AI-agent observability on Datadog) — https://github.com/BrianIsaac/Cerberus
- DataDog/pup (Datadog CLI, 33+ domains) — https://github.com/DataDog/pup
- viamus/mcp-datadog (MCP server for Datadog) — https://github.com/viamus/mcp-datadog
- OpenObserve (open-source observability) — https://github.com/openobserve/openobserve
