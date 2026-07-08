<!--
SYNC IMPACT REPORT — ObservAI Constitution
Version change: (template, unfilled) -> 1.0.0  [INITIAL ADOPTION]
Modified principles: none (initial fill of placeholder template)
Added sections:
  - Core Principles P1-P5 (Domain Modularity; Test-First/TDD; Type Safety & Static Analysis; Config & Build Hygiene; Security & HITL)
  - Section 2: Architecture & Technology Constraints
  - Section 3: Development Workflow & Quality Gates
  - Governance (amendment procedure, semver, compliance review)
Removed sections: none
Templates requiring updates:
  - .specify/templates/plan-template.md        ✅ updated (Constitution Check gates filled from P1-P5 + workflow)
  - .specify/templates/spec-template.md         ⚠ pending (no Constitution Check section; generic; aligned by reference)
  - .specify/templates/tasks-template.md        ⚠ pending (generic; notes tests optional - see P2 tension; aligned via plan gate)
  - .specify/templates/checklist-template.md    ⚠ pending (generic sample; no change required)
Follow-up TODOs:
  - RATIFICATION_DATE recorded as initial adoption (2026-07-08); if a prior ratification date exists, amend.
  - Consider adding a Constitution Check gate to spec-template.md in a future pass.
-->

# ObservAI Constitution

## Core Principles

### I. Domain Modularity (Thin Proxy Over Datadog)

Every feature is a self-contained module composed of `router` + `service` + `schemas` +
`models`. Business logic MUST live in services, never in routers. All Datadog access is
centralized in `app/datadog/client.py` and exposed only through the uniform `datadog_routes/`
proxy. ObservAI composes and intelligently layers on top of Datadog — it MUST NOT reimplement
Datadog's ingestion or telemetry pipeline.

**Rationale**: keeps the codebase navigable and unit-testable, prevents SDK/secret sprawl, and
makes the Datadog surface auditable in one place.

### II. Test-First / TDD (NON-NEGOTIABLE)

Tests are written and MUST be failing before implementation (Red-Green-Refactor). New behavior
ships with tests. Datadog-dependent tests MUST carry `@pytest.mark.datadog` (auto-skipped without
`DD_API_KEY`/`DD_APP_KEY`); the frontend uses Vitest + React Testing Library per component. Tests
MUST be deterministic and environment-independent — no assertions whose expected value changes with
live data (e.g., hard-coded `overall_level == 0` when Datadog is configured).

**Rationale**: CI MUST be green without credentials, and tests MUST be reproducible locally and in
CI. Fragile, env-dependent tests block commits and erode trust in the suite.

### III. Type Safety & Static Analysis

Pydantic v2 models are REQUIRED at every boundary. `pyright` MUST be clean on changed files.
`ruff` + `ruff-format` are enforced via pre-commit; `vulture` (min-confidence 65) guards dead code;
`gitleaks` guards secrets. `from __future__ import annotations` is FORBIDDEN in schema/model files
— it broke Pydantic `ForwardRef` resolution once and will again.

**Rationale**: the codebase is async and type-heavy; static analysis catches integration and
serialization bugs that runtime tests miss.

### IV. Configuration & Build Hygiene

`package-lock.json` MUST match `package.json` (CI parity check fails fast on mismatch).
`.env.example` is the single source of default configuration; real secrets come from CI/secret
store, never the repository. The Docker image MUST include the sync DB driver (`psycopg2-binary`)
so `alembic upgrade head` runs; it runs as a non-root user (`observai`); every long-running service
MUST declare a healthcheck.

**Rationale**: reproducible builds and a working migration path are prerequisites for any deploy.

### V. Security & Human-in-the-Loop

JWT (HS256) with a strong `SECRET_KEY` (≥32 chars, enforced in production); all inputs validated by
Pydantic; CORS scoped to known origins. Self-healing / remediation actions are gated behind explicit
human approval. Autonomy is graduated — observe → recommend → approve → auto-remediate, selectable
per environment, with a full audit trail. Datadog API keys are server-side ONLY; they MUST NOT reach
the browser.

**Rationale**: autonomous action on production requires accountability and blast-radius control;
secret exposure is a hard failure.

## Architecture & Technology Constraints

- **Backend**: FastAPI + Uvicorn, SQLAlchemy 2.0 (async) + asyncpg, Alembic, Pydantic v2,
  `python-jose` (JWT) + `passlib[bcrypt]`, `datadog-api-client`, Redis, Celery, Sentry, `tenacity`.
  Python ≥3.11 (CI on 3.12).
- **Frontend**: React 18 + TypeScript 5.6 + Vite 6, Tailwind 3, React Router 6, TanStack Query 5,
  Recharts 2, lucide-react, Vitest 4 + RTL.
- **Infra**: Docker (multi-stage, non-root), `docker-compose.yml` (dev) +
  `docker-compose.prod.yml` (limits/healthchecks), Nginx for frontend static serving, GHCR image
  push on `main`.
- ObservAI is a control layer ON Datadog. Do not rebuild Datadog capabilities; proxy and compose them.
- Any AI / agentic layer MUST be provider-agnostic and MUST expose operations through a stable
  interface (REST now; MCP later).

## Development Workflow & Quality Gates

- **Gitflow**: features branch from `develop`; PRs target `develop`; promotion to `main` is via a
  `develop → main` release PR (which triggers the Docker build/push to GHCR).
- **Pre-commit (all MUST pass)**: ruff, ruff-format, pyright, gitleaks, vulture (≥65), eslint, tsc,
  pytest, vitest.
- **CI (GitHub Actions)**: backend (ruff, pyright, `pytest -m "not datadog"`); frontend (eslint,
  `tsc --noEmit`, vitest, build); docker (build + push to GHCR, `main` only).
- **Definition of Done (every change)**: pre-commit 7/7 pass; CI green; new behavior tested with
  Datadog-touching tests marked/skippable; `/docs` contract updated if a route changed; README and/or
  `PLAN.md` updated if a module changed; no env-dependent tests; no hardcoded secrets; lockfile
  matches `package.json`.
- The constitution supersedes ad-hoc practice. When a PR risks a principle, the trade-off MUST be
  documented in the PR description.

## Governance

The constitution is the project's highest-order practice document and supersedes conflicting local
conventions.

- **Amendments**: open a PR against this file with a Sync Impact Report (version bump + rationale).
- **Versioning**: semantic versioning — MAJOR = principle removal or incompatible redefinition;
  MINOR = new principle/section or materially expanded guidance; PATCH = clarifications/wording.
- **Compliance**: all PRs/reviews MUST verify compliance with the relevant principles (Constitution
  Check in `plan-template.md`). Complexity MUST be justified. The Constitution Check gate in
  `/speckit.plan` output is re-verified after Phase 1 design and before implementation.

**Version**: 1.0.0 | **Ratified**: 2026-07-08 | **Last Amended**: 2026-07-08
