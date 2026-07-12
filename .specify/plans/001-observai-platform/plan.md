# Implementation Plan: ObservAI Platform

**Branch**: `001-observai-platform` | **Date**: 2026-07-08 | **Spec**: [spec.md](../specs/001-observai-platform/spec.md)

**Input**: Feature specification from `/specs/001-observai-platform/spec.md`

**Note**: This plan is filled in by the `/speckit.plan` command. It converts the SDD spec into an
executable, gitflow-routed build sequence. Research basis: [`PLAN.md`](../../PLAN.md) (benchmark +
roadmap) and the live codebase under `backend/app/`.

## Summary

ObservAI is an open-source, AI-augmented **control layer on Datadog** (not a replacement). The spec's
highest-priority outcomes are: (1) lock the continuous quality gates from PLAN.md §4 so future work
cannot regress (Phase A), and (2) drive the benchmark-informed roadmap A→E — mature RCA, an agentic/MCP
investigation layer, closed-loop self-healing/learning, and platform self-observability. The technical
approach is incremental: enforce CI/pre-commit contracts first, then refactor `rca/` into a multi-phase
pipeline, then add a provider-agnostic LLM + MCP server, then deepen HITL/learning, then dog-food
Datadog on ObservAI itself. All work is TDD-first and merged via gitflow
(feature → `develop` → `main`).

## Technical Context

**Language/Version**: Python ≥3.11 (CI 3.12); TypeScript 5.6 (frontend).

**Primary Dependencies**: FastAPI 0.115, Uvicorn, SQLAlchemy 2.0 (async) + `asyncpg`, `psycopg2-binary`
(sync driver for Alembic), Alembic, Pydantic v2, `datadog-api-client` 2.x, `python-jose` (JWT HS256) +
`passlib[bcrypt]`, Redis, Celery, Sentry, `tenacity`; frontend React 18 + Vite 6 + TanStack Query 5 +
Vitest 4 + RTL.

**Storage**: PostgreSQL (async via `asyncpg`; sync via `psycopg2-binary` for migrations). ORM models in
`backend/app/core/models/`, schema/models mirrored in `core/schemas/`.

**Testing**: `pytest` + `pytest-asyncio` + `pytest-cov` (backend, `not datadog` marker), `vitest` + RTL
(frontend); pre-commit (ruff, ruff-format, pyright, gitleaks, vulture ≥65, eslint, tsc, pytest,
vitest); GitHub Actions (backend / frontend / docker — docker on `main` only).

**Target Platform**: Linux containers (Docker multi-stage, non-root `observai`); Nginx-served React
frontend; GHCR push on `main`.

**Project Type**: Web service (FastAPI backend) + SPA frontend, orchestrated via docker-compose.

**Performance Goals**: `alembic upgrade head` succeeds in CI against throwaway Postgres; `pytest -m "not
datadog"` green with zero live Datadog calls; API p95 < 200ms for read endpoints (roadmap target).

**Constraints**: No secrets in repo (gitleaks); no `from __future__ import annotations` in schema/model
files (pyright/Pydantic); lockfile must match `package.json`; Docker must include `psycopg2-binary`;
Docker build/push only on `main`; no `--no-verify`; deps via `uv add`.

**Scale/Scope**: 11 backend routers under `/api/v1`; ~12 DB tables; roadmap spans 5 phases (A–E).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Constitution Principle | Status | Notes |
|---|---|---|
| 1. Domain Modularity | ✅ Pass | One router + service + schemas + models per domain already enforced (`auth`, `incidents`, `rca`, `health`, `self_healing`, `maturity`, `knowledge_base`, `analysis`, `datadog_routes`). |
| 2. Test-First / TDD | ✅ Pass (with work) | `@pytest.mark.datadog` convention + `not datadog` CI run established; Phase A locks it as a gate. New behavior ships with tests. |
| 3. Type Safety & Static Analysis | ✅ Pass (with work) | `pyright` clean on changed files required; `from __future__ import annotations` banned in schemas (PLAN.md §4.1). Phase A5 resolves `core/`+`rca/` warnings. |
| 4. Config & Build Hygiene | ✅ Pass | `package-lock.json` parity + Alembic-against-Postgres CI jobs (A3/A4); `psycopg2-binary` present. |
| 5. Security & HITL | ✅ Pass | JWT `get_current_user` on writes; HITL on `AutoHealAction` (pending→approved→executed); strong `SECRET_KEY` enforced in prod. |

No constitution violations. Complexity Tracking table not required.

## Project Structure

### Documentation (this feature)

```text
specs/001-observai-platform/
├── spec.md              # /speckit.specify output (DONE)
├── plan.md              # This file (/speckit.plan output)
└── tasks.md             # /speckit.tasks output

plans/001-observai-platform/
└── plan.md              # Symlinked/duplicated plan reference
```

### Source Code (repository root)

```text
backend/app/
├── analysis/        # incident/rca/health/self-healing orchestration agents + router
├── auth/            # deps (get_current_user), router, schemas
├── core/
│   ├── config.py    # pydantic-settings; API_V1_PREFIX=/api/v1
│   ├── db.py        # async engine/session
│   ├── models/      # SQLAlchemy tables (incident, rca, health, maturity, kb, self_healing, report, analysis)
│   └── schemas/     # Pydantic request/response
├── datadog/         # client, formatters, write_guard
├── datadog_routes/  # thin uniform proxy: apm, events, fleet, incidents, logs, metrics(_explore), monitors, rum, slos, synthetics, error_tracking
├── health/          # product/SLO status router
├── incidents/       # CRUD + summary router
├── knowledge_base/  # KB router (+/seed)
├── maturity/        # assessment router + reports router + service
├── rca/             # router (single-pass today → multi-phase pipeline in Phase B)
└── self_healing/    # runbook + auto-heal router (HITL)
```

**Structure Decision**: Real directories captured above; no restructuring required. Phases A–E add
behavior inside these modules; Phase B refactors `rca/` internally only.

## Phases (execution order)

**Phase A — Foundations & Regression Prevention** (blocks everything else)
- A1 CI contract: ruff, pyright, vulture, gitleaks, `pytest -m "not datadog"`, frontend eslint/tsc/vitest; docker build/push on `main` only.
- A2 Formalize `@pytest.mark.datadog` (doc + CI guard failing on unmarked credentialed tests).
- A3 Lockfile↔`package.json` parity check in CI.
- A4 CI job: `alembic upgrade head` against throwaway Postgres.
- A5 Resolve `pyright` warnings in `core/`+`rca/`; enforce no `from __future__ import annotations` in schemas.

**Phase B — Mature the RCA Engine** (benchmark: Sre-Agent, Dynatrace)
- B1 Refactor `rca/` → pipeline Discovery→Breadth→Depth→Conclusion with Pydantic state models.
- B2 Service-map / dependency-chain traversal; label root cause / propagator / victim.
- B3 `structlog` + `tenacity` on every Datadog call.
- B4 Confidence-scored reports with full dependency path.
- B5 Unit-test each phase with mocked Datadog client (TDD).

**Phase C — Agentic / AI Investigation Layer** (benchmark: Bits AI SRE, CloudThinker, pup)
- C1 Provider-agnostic LLM reasoning module (NL summaries + suggested remediations).
- C2 MCP server (`Configuration / Models / Services / Tools`) over ObservAI + Datadog ops.
- C3 Graduated autonomy (observer→recommend→approve→auto-remediate), per-environment, audited.
- C4 "Agent Trace" transparency view for AI reasoning.

**Phase D — Self-Healing & Maturity Loop** (benchmark: PagerDuty, BigPanda, Dynatrace)
- D1 Expand runbook library + parameterized validated actions.
- D2 Harden HITL: signed approvals, audit log, safe rollback.
- D3 Feed self-healing outcomes → `maturity/` + `knowledge_base/` (continuous learning).
- D4 SLO / error-budget automation from `health/`.

**Phase E — Platform Self-Observability** (benchmark: Cerberus)
- E1 Instrument ObservAI with its own Datadog (latency, RCA success, self-heal counts, auth events).
- E2 Ship platform-health dashboard.

**Phase F — Tag & Period Filtering (per-path + global)** (cross-cutting Datadog proxy)
- F1 Shared `DatadogFilter` schema: `tags: list[str]` (AND) + `period ∈ {1d,7d,15d,30d}` → `from`/`to`.
- F2 Individual filter on every `datadog_routes/*` list/search endpoint (retire ad-hoc `tags`/`monitor_tags`/`query` inconsistencies).
- F3 Global filter via settings (`DATADOG_DEFAULT_TAGS`, `DATADOG_DEFAULT_PERIOD`), merged AND in `app/datadog/`.
- F4 `compose_filters` + period mapping + per-domain translation in `app/datadog/` (routers stay thin, P1).
- F5 Unit tests for merge/period/translation; per-domain tests `@pytest.mark.datadog` (TDD).

## Definition of Done (per change)

Pre-commit 7/7 + CI green (backend + frontend; docker on `main`); new behavior has tests; Datadog tests
marked & skippable; `pyright` clean on changed files; no new `vulture` findings; `/docs` updated if a
route changed; README/PLAN.md updated if a module changed; no env-dependent assertions; merged via
gitflow.

## Tag & Period Filtering (Feature Addition)

**Summary**: Today each `datadog_routes/*` router declares query params inline and inconsistently — only
`monitors.py` exposes `tags`/`monitor_tags`; `incidents`/`logs`/`rum` use a free-form `query` string; the
rest have none. There is no shared schema and no global/cross-path filter. This addition introduces one
uniform `DatadogFilter` (tags + period) accepted individually on every path, plus a global default
applied to all paths, with all composition logic centralized in `app/datadog/`.

**Technical Approach**
- *Shared schema* — `app/datadog/schemas.py::DatadogFilter`: `tags: list[str] | None` (Datadog
  `key:value`, AND-combined) and `period: Literal["1d","7d","15d","30d"] | None`. `period` maps to
  `from_ts = now − N·86400`, `to_ts = now`. No `from __future__ import annotations`.
- *Individual filter* — every `datadog_routes/*` list/search endpoint accepts `tags` + `period` (and keeps
  a domain `query` where the Datadog API needs free text). Ad-hoc `monitor_tags`/inline `tags` are unified
  into the shared model.
- *Global filter* — `app/core/config.py` adds `DATADOG_DEFAULT_TAGS: list[str]` and
  `DATADOG_DEFAULT_PERIOD: Literal[...] | None`. A `compose_filters(global, request)` helper in
  `app/datadog/filters.py` AND-merges tags and applies the global period as fallback.
- *Per-domain translation* — `DatadogClient` (or per-method kwargs) maps the uniform filter to each
  domain's native param: monitors `tags`/`monitor_tags`; logs & spans `filter.tags` + `from`/`to`;
  incidents/events/rum `query` with `tags:...`; metrics `query{...}` / `filter[tags]`;
  SLOs/synthetics/fleet/error-tracking/apm `tags` / `filter[tags]`.
- *Constitution* — P1: composition/translation in `app/datadog/`, routers stay thin. P2: TDD; integration
  tests `@pytest.mark.datadog`. P3: Pydantic v2 schema, `pyright` clean.

**Affected files**: `app/datadog/schemas.py` (new), `app/datadog/filters.py` (new), `app/core/config.py`,
`app/datadog/client.py`, `app/datadog_routes/{monitors,incidents,logs,rum,metrics,metrics_explore,apm,
events,fleet,slos,synthetics,error_tracking}.py`, `backend/tests/test_datadog_routes/test_filters.py`
(new, unit) + per-domain `@pytest.mark.datadog` tests.

**Branch**: `feature/tag-filters` off `develop` → PR to `develop`.
