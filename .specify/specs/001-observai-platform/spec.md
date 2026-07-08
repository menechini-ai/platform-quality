# Feature Specification: ObservAI Platform

**Feature Branch**: `001-observai-platform`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description: "/speckit.specify @PLAN.md — generate the formal specification for the ObservAI platform from PLAN.md, grounded in the actual codebase and benchmarked against the best AI observability platforms that integrate with Datadog. Enforce research, planning, tasks, TDD, SDD, code quality, and gitflow throughout."

> This spec is the SDD (Spec-Driven Development) artifact for the ObservAI platform. It is
> derived from [`PLAN.md`](../../PLAN.md) and the project [`constitution.md`](../../.specify/memory/constitution.md),
> and is grounded in the code that already exists under `backend/app/`. Where PLAN.md specifies
> *direction* (phases A–E), this spec specifies *requirements* (FR / SC) and *entities* that must hold
> for every change. Every requirement below is checkable against the running system or the test suite.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - SRE investigates an incident with AI-assisted RCA (Priority: P1)

An on-call SRE gets paged from a Datadog monitor. They open ObservAI, see the incident with its
timeline, and trigger an RCA. ObservAI correlates metrics/logs/traces/deployments, produces a
confidence-scored root-cause report with the dependency chain, and links relevant knowledge-base
articles and a suggested runbook.

**Why this priority**: This is the core loop the whole platform exists for — symptom → root cause →
remediation. Without it, every other module is ornamentation.

**Independent Test**: Can be fully tested by creating an `Incident`, calling `POST /api/v1/rca` (or
`POST /api/v1/analysis/incident/{id}`), and asserting a persisted `RcaReport` is returned with a
`root_cause` and a confidence score. Delivers value with mocks (no live Datadog needed).

**Acceptance Scenarios**:

1. **Given** an authenticated user and an existing incident, **When** they POST to `/api/v1/rca` with the incident id, **Then** a `RcaReport` is created and returned with `status_code 201` and a non-null `root_cause`.
2. **Given** a stored RCA, **When** the user GETs `/api/v1/rca/{rca_id}`, **Then** the full report (including dependency chain and confidence) is returned.
3. **Given** an unauthenticated request, **When** they POST to `/api/v1/rca`, **Then** the API returns `401` and no report is created.

---

### User Story 2 - Platform exposes a uniform Datadog proxy (Priority: P1)

A platform engineer needs one consistent, authenticated API surface over Datadog's 33+ API domains
(monitors, events, logs, metrics, APM, SLOs, RUM, synthetics, fleet, error-tracking, incidents)
instead of wiring the `datadog-api-client` into every consumer.

**Why this priority**: The proxy (`datadog_routes/*`) is the substrate every other module builds on;
it is already implemented and must be locked in as a contract.

**Independent Test**: Can be fully tested by asserting each `datadog_routes/*` router is registered
under `/api/v1` (tags `datadog-*`) and that a no-credential request to any route returns either a
clean auth error or is `@pytest.mark.datadog`-skipped in CI.

**Acceptance Scenarios**:

1. **Given** the app is built, **When** the OpenAPI schema is generated, **Then** it exposes routers tagged `datadog-monitors`, `datadog-events`, `datadog-logs`, `datadog-metrics`, `datadog-apm`, `datadog-incidents`, `datadog-fleet`, `datadog-rum`, `datadog-synthetics`, `datadog-slos`, `datadog-errors`.
2. **Given** no `DD_API_KEY`/`DD_APP_KEY`, **When** CI runs `pytest -m "not datadog"`, **Then** zero Datadog-touching tests execute and the suite is green.

---

### User Story 3 - Maturity and knowledge base deepen over time (Priority: P2)

An SRE lead runs a maturity assessment to see the team's observability posture (0–5 across
dimensions), and contributors grow the knowledge base so future investigations are faster.

**Why this priority**: These are ObservAI's stated *unique strengths* in PLAN.md §2.3 and must be
preserved and deepened, not regressed.

**Independent Test**: Can be fully tested by `POST /api/v1/maturity/assess` (returns an assessment
with `overall_level` in `range(6)` and per-dimension scores) and `POST /api/v1/kb` + `POST
/api/v1/kb/seed` (no env-dependent assertions).

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they GET `/api/v1/maturity`, **Then** a list of assessments with `overall_level` (0–5) and `overall_score` (0–100) is returned.
2. **Given** a KB entry payload, **When** they POST `/api/v1/kb`, **Then** a `KnowledgeBaseRead` is persisted (`201`).
3. **Given** a maturity assessment exists, **When** they GET `/api/v1/maturity/reports`, **Then** generated `Report` records are returned.

---

### User Story 4 - Self-healing executes with a human in the loop (Priority: P2)

A runbook triggers on an incident; the system stages an action (restart / scale / rollback / webhook)
and waits for explicit approval before executing, recording the audit trail.

**Why this priority**: Closes the loop detection → remediation, and the HITL gate is a hard security
requirement from the constitution (Security & HITL principle).

**Independent Test**: Can be fully tested by creating a `Runbook` and an `AutoHealAction`, asserting
default `status="pending"`, then PATCHing to `approved`/`rejected` and asserting the audit fields
(`requested_at`, `executed_at`) update.

**Acceptance Scenarios**:

1. **Given** an unapproved `AutoHealAction`, **When** a query returns it, **Then** its `status` is `pending` and `executed_at` is null.
2. **Given** an approved action, **When** the executor runs it, **Then** `status` transitions to `running`→`success|failed` and `executed_at`/`completed_at` are set.
3. **Given** a rejected action, **When** inspected, **Then** it is never executed and recorded as `rejected`.

---

### User Story 5 - Quality gates prevent regression on every change (Priority: P1)

A contributor opens a PR. Pre-commit (ruff, ruff-format, pyright, gitleaks, vulture ≥65, eslint, tsc,
pytest, vitest) and CI (backend / frontend / docker) run, and any Datadog-touching test without the
`datadog` marker blocks merge.

**Why this priority**: PLAN.md §4 makes code quality non-negotiable; a platform that cannot protect
its own quality cannot be trusted to protect production.

**Independent Test**: Can be verified by running pre-commit on a deliberately-broken file and
asserting the relevant hook fails; and by a CI smoke test where a PR missing the `datadog` marker on a
credentialed test fails the guard.

**Acceptance Scenarios**:

1. **Given** a changed Python file, **When** pre-commit runs, **Then** `pyright` is clean and `vulture --min-confidence 65` reports no dead code on it.
2. **Given** a test that calls Datadog, **When** it lacks `@pytest.mark.datadog`, **Then** CI fails with a clear "mark or skip" error.
3. **Given** `package.json` edited without regenerating `package-lock.json`, **When** CI runs, **Then** the lockfile-parity check fails fast.

---

### Edge Cases

- What happens when Datadog credentials are absent? → All `datadog`-marked tests are skipped; proxy routes return a clean auth/configuration error, never a 500 stack trace.
- How does the system handle an env-dependent maturity score? → `overall_level` is validated to `range(6)`; tests never assert a specific live value (de-flaked per PLAN.md §3).
- What happens if `alembic upgrade head` runs in Docker without `psycopg2-binary`? → Blocked at build; the sync driver is a required runtime dep (PLAN.md §3, §4.9).
- What happens on a Pydantic model file that uses `from __future__ import annotations`? → Forbidden in schema/model files; CI/lint must reject it (PLAN.md §4.1).
- How are breaking API changes handled? → `/docs` (FastAPI) is the contract and must stay accurate; any route change updates README/PLAN.md.

---

## Requirements *(mandatory)*

### Functional Requirements

**Core API & Auth**

- **FR-001**: System MUST expose all domain routers under a single versioned prefix `settings.API_V1_PREFIX` (`/api/v1`), including `auth`, `incidents`, `rca`, `health`, `self_healing`, `maturity`, `reports`, `knowledge-base`, `analysis`, and the `datadog-*` proxies.
- **FR-002**: System MUST authenticate users via JWT (HS256) using `get_current_user` as a `Depends` on all write endpoints and on protected reads (incident POST/PATCH/DELETE, `/me`).
- **FR-003**: System MUST reject unauthenticated requests to protected routes with `401` and without persisting side effects.
- **FR-004**: System MUST expose an unauthenticated `/health` liveness endpoint returning `{"status": "ok"}`.

**Incidents**

- **FR-005**: System MUST support full CRUD on incidents: `GET /api/v1/incidents`, `GET /api/v1/incidents/summary`, `GET /api/v1/incidents/{id}`, `POST /api/v1/incidents` (201), `PATCH /api/v1/incidents/{id}`, `DELETE /api/v1/incidents/{id}` (204).
- **FR-006**: System MUST return an incident summary (counts by status/severity) from `GET /api/v1/incidents/summary`.

**RCA & Analysis**

- **FR-007**: System MUST provide RCA endpoints: `GET /api/v1/rca`, `GET /api/v1/rca/{id}`, `POST /api/v1/rca` (201), each returning `RcaReportRead` with root cause and confidence.
- **FR-008**: System MUST provide analysis orchestration: `POST /api/v1/analysis/incident/{id}`, `POST /api/v1/analysis/rca/{id}`, `POST /api/v1/analysis/health`, `POST /api/v1/analysis/self-healing`, returning `AnalysisResultRead` (201).
- **FR-009**: System MUST (roadmap B) evolve RCA from single-pass to a multi-phase pipeline **Discovery → Breadth → Depth → Conclusion** with explicit Pydantic state models and a labeled dependency chain (root cause / propagator / victim).

**Health & Maturity**

- **FR-010**: System MUST provide health endpoints returning product/SLO status from `app/health/router.py`.
- **FR-011**: System MUST provide maturity assessment: `GET /api/v1/maturity`, `POST /api/v1/maturity/assess`, returning `overall_level` (0–5) and `overall_score` (0–100) with per-dimension JSON.
- **FR-012**: System MUST generate maturity `Report` records accessible via `GET /api/v1/maturity/reports`.

**Knowledge Base & Self-Healing**

- **FR-013**: System MUST support `GET/POST /api/v1/kb`, `GET /api/v1/kb/{id}`, and `POST /api/v1/kb/seed` (201) for knowledge-base growth.
- **FR-014**: System MUST model `Runbook` (name, triggers, ordered steps, `is_active`) and `AutoHealAction` (action_type ∈ restart|scale|rollback|script|webhook, status lifecycle pending→approved→running→success|failed|rejected).
- **FR-015**: System MUST enforce HITL: an `AutoHealAction` MUST NOT execute until its `status` is `approved`; rejections and executions MUST be recorded with timestamps for audit.

**Datadog Proxy**

- **FR-016**: System MUST expose a thin, uniform proxy over `datadog-api-client` for at least: monitors, events, logs, metrics (incl. metrics-explore), APM, incidents, fleet, RUM, synthetics, SLOs, error-tracking.
- **FR-017**: System MUST centralize error handling and use uniform response models across all `datadog_routes/*` routers (mirror `pup`'s consistent command surface, PLAN.md §4.7).

**Quality, Testing & SDD (cross-cutting)**

- **FR-018**: System MUST keep `pyright` clean on every changed Python file and MUST forbid `from __future__ import annotations` in schema/model files (PLAN.md §4.1).
- **FR-019**: System MUST pass `ruff`, `ruff-format`, `gitleaks`, and `vulture --min-confidence 65` on changed files in pre-commit.
- **FR-020**: System MUST mark every Datadog-touching test with `@pytest.mark.datadog` (auto-skipped without `DD_API_KEY`/`DD_APP_KEY`); CI runs `pytest -m "not datadog"`.
- **FR-021**: System MUST ship tests for new behavior (TDD) and MUST NOT contain env-dependent test assertions (no `assert 3 == 0`-style live-value checks).
- **FR-022**: System MUST keep `package-lock.json` in lockstep with `package.json` (CI parity check, PLAN.md §4.9).
- **FR-023**: System MUST build a Docker image that includes the sync DB driver (`psycopg2-binary`) so `alembic upgrade head` succeeds, runs as non-root `observai`, and defines healthchecks on long-running services (PLAN.md §4.9).
- **FR-024**: System MUST run frontend quality gates: `eslint`, `tsc`, and `vitest` (RTL) per component, in pre-commit and CI.

**Roadmap (benchmark-driven) — tracked as the SDD backlog**

- **FR-025**: System SHOULD add an agentic/LLM investigation layer with a provider-agnostic reasoning module for NL RCA summaries and suggested remediations (Phase C, benchmark: Bits AI SRE, CloudThinker).
- **FR-026**: System SHOULD expose ObservAI + Datadog operations via an MCP server (`Configuration / Models / Services / Tools` shape, Phase C, benchmark: `pup`, `mcp-datadog`, Cerberus).
- **FR-027**: System SHOULD implement graduated autonomy (observer → recommend → approve → auto-remediate) selectable per environment, with a full audit trail (Phase C/D, benchmark: CloudThinker, PagerDuty).
- **FR-028**: System SHOULD dog-food its own observability by instrumenting ObservAI with Datadog APM/logs/metrics and shipping a platform-health dashboard (Phase E, benchmark: Cerberus).
- **FR-029**: System SHOULD feed self-healing outcomes back into `maturity/` and `knowledge_base/` to form a continuous-learning loop (Phase D, differentiator per PLAN.md §2.3).

**Workflow**

- **FR-030**: Every change MUST be merged via gitflow: feature/fix branch off `develop` → PR to `develop` → release PR `develop → main`; Docker build/push runs only on `main`. No `--no-verify`; Python deps added via `uv add`.

### Key Entities *(include if feature involves data)*

- **Incident**: an alert/ticket under investigation. Attributes: id (UUID), title, description, status, severity, timestamps. Related to RcaReport and AutoHealAction.
- **RcaReport**: root-cause analysis result. Attributes: id, incident_id, root_cause, confidence, dependency_chain (root cause / propagator / victim), created_at. Returned as `RcaReportRead`.
- **AnalysisResult**: orchestration output of an investigation pass. Attributes: id, type (incident/rca/health/self-healing), summary, created_at. Returned as `AnalysisResultRead`.
- **MaturityAssessment**: SRE observability posture snapshot. Attributes: id, overall_level (0–5), overall_score (0–100), dimensions (JSON), raw Datadog data, created_at.
- **Report**: generated document (executive | monthly | team_health | postmortem | investigation). Attributes: id, report_type, title, content (Markdown), tags, metadata.
- **KnowledgeBaseEntry**: a KB article. Attributes: id, title, content, tags. Returned as `KnowledgeBaseRead`.
- **Runbook**: automated remediation recipe. Attributes: id, name, description, triggers (JSON), steps (ordered JSON), is_active.
- **AutoHealAction**: a staged remediation action. Attributes: id, incident_id (FK, nullable), monitor_id, action_type, action_config (JSON), triggered_by (auto|manual), status lifecycle, result (JSON), requested/executed/completed timestamps.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `pre-commit` 7/7 hooks pass on every changed file in CI, and a deliberately-broken PR fails the smoke test (PLAN.md §5 Phase A Done).
- **SC-002**: `pytest -m "not datadog"` is green in CI with zero Datadog calls and zero env-dependent assertions.
- **SC-003**: `alembic upgrade head` succeeds against a throwaway Postgres in CI (proves the Docker migration path end-to-end, PLAN.md A4).
- **SC-004**: Every existing domain router is reachable under `/api/v1` with an accurate OpenAPI `/docs` contract.
- **SC-005**: A new incident can be created and an RCA report generated with a non-null root cause and confidence score, fully exercised with mocks (no live Datadog).
- **SC-006**: Lockfile↔`package.json` parity check fails fast on mismatch; Docker image runs `alembic` as non-root and serves `/api/v1/health` with `200`.
- **SC-007**: (Phase B target) RCA reports include a labeled dependency chain and a confidence score, with 100% phase coverage via mocks (PLAN.md §5 B Done).
- **SC-008**: (Phase C target) An external agent can drive an investigation over the MCP server and receive a cited RCA; autonomy level is configurable and logged.

---

## Assumptions

- Target users are SRE / Platform / DevOps engineers who already operate Datadog; ObservAI is a control layer *on* Datadog, not a replacement (PLAN.md §1 non-goals).
- Datadog credentials (`DD_API_KEY`, `DD_APP_KEY`) are supplied via CI secret store / `.env`; they are not committed (constitution Security principle).
- Backend runs Python ≥3.11 (CI 3.12) with FastAPI + SQLAlchemy 2.0 async + Alembic; frontend is React 18 + TS 5.6 + Vite 6 + Vitest.
- The repo uses gitflow; `develop` is the integration branch and `main` is production-promotion only.
- Benchmark references (Bits AI SRE, Dynatrace Davis, BigPanda, Sre-Agent, Cerberus, pup, mcp-datadog) describe *capabilities to adopt*, not libraries to vendor.
- The spec is forward-looking; FR-025–FR-029 (SHOULD) are roadmap items tracked as the SDD task backlog and are not blocking for v1.
