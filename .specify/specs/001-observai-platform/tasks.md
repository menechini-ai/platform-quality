# Tasks: ObservAI Platform

**Input**: Design documents from `/specs/001-observai-platform/` (spec.md, plan.md)

**Prerequisites**: plan.md (required), spec.md (required for user stories).

**Tests**: REQUIRED — the spec mandates TDD (FR-021) and a `@pytest.mark.datadog` convention
(FR-020). Every functional task pairs with a test task.

**Organization**: Tasks grouped by user story (US1–US5) + cross-cutting quality (QC) so each story
ships as an independently testable increment. Branch per gitflow: `001-observai-platform` off
`develop`, PR → `develop`, then release PR `develop → main`.

**Format**: `[ID] [P?] [Story] Description`

---

## Phase A: Setup & Quality Gates (blocks all stories)

- [ ] T001 [P] QC — Add CI contract job running ruff, pyright, vulture ≥65, gitleaks, `pytest -m "not datadog"`, and frontend eslint/tsc/vitest (`.github/workflows/ci.yml`); docker build/push gated to `main` only.
- [ ] T002 [P] QC — Add CI guard that fails if a test touching Datadog lacks `@pytest.mark.datadog` (scan for `datadog-api-client`/`Datadog` usage without the marker); document the convention.
- [ ] T003 [P] QC — Add `package-lock.json` ↔ `package.json` parity check to CI (fails fast on mismatch).
- [ ] T004 [P] QC — Add CI job running `alembic upgrade head` against a throwaway Postgres (proves Docker migration path).
- [ ] T005 [P] QC — Resolve `pyright` warnings in `backend/app/core/` and `backend/app/rca/`; add lint rule banning `from __future__ import annotations` in `core/models/` and `core/schemas/`.
- [ ] T006 QC — Smoke test: open a deliberately-broken PR and assert the relevant hook/CI guard fails (pre-commit 7/7 + CI green verification per SC-001).

---

## Phase 1: User Story 1 — AI-assisted RCA (P1)

- [ ] T010 US1 — Verify incident CRUD + RCA endpoints exist and return `RcaReportRead` with `root_cause` and confidence (`backend/app/incidents/router.py`, `backend/app/rca/router.py`). Add/adjust tests in `backend/tests/test_rca/`.
- [ ] T011 [P] US1 — Test: `POST /api/v1/rca` returns 201 with non-null `root_cause`; `GET /api/v1/rca/{id}` returns full report; unauthenticated POST returns 401 (no persistence).
- [ ] T012 US1 — (Roadmap B1) Refactor `backend/app/rca/` into pipeline Discovery→Breadth→Depth→Conclusion with explicit Pydantic state models; add `dependency_chain` field to `RcaReport` (`core/models/rca.py`, `core/schemas/rca.py`).
- [ ] T013 [P] US1 — Test: each RCA phase covered with mocked Datadog client (TDD); report includes labeled chain (root cause/propagator/victim) + confidence (SC-007).

---

## Phase 2: User Story 2 — Uniform Datadog Proxy (P1)

- [ ] T020 US2 — Verify all `datadog_routes/*` routers registered under `/api/v1` with tags `datadog-*` (`backend/app/main.py`); assert via OpenAPI schema test.
- [ ] T021 [P] US2 — Test: with no `DD_API_KEY`/`DD_APP_KEY`, `pytest -m "not datadog"` runs zero Datadog tests and is green (SC-002).
- [ ] T022 US2 — (Roadmap) Standardize uniform response models + centralized error handling across `datadog_routes/*` (mirror `pup`); ensure no raw stack traces leak on missing creds.

---

## Phase 3: User Story 3 — Maturity & Knowledge Base (P2)

- [ ] T030 US3 — Verify `GET /api/v1/maturity`, `POST /api/v1/maturity/assess` (`overall_level` in `range(6)`, `overall_score` 0–100), `GET /api/v1/maturity/reports`; `POST /api/v1/kb`, `POST /api/v1/kb/seed` (`backend/app/maturity/`, `backend/app/knowledge_base/`).
- [ ] T031 [P] US3 — Test: de-flaked assessment asserts `overall_level in range(6)` (no env-dependent value); KB seed returns 201; reports list returns `Report` records.

---

## Phase 4: User Story 4 — Self-Healing with HITL (P2)

- [ ] T040 US4 — Verify `Runbook` + `AutoHealAction` models and HITL status lifecycle (`backend/app/core/models/self_healing.py`, `backend/app/self_healing/router.py`): default `pending`; executes only when `approved`.
- [ ] T041 [P] US4 — Test: unapproved action `status=pending` & `executed_at=null`; approve→running→success|failed sets timestamps; reject never executes and records `rejected`.
- [ ] T042 US4 — (Roadmap D2) Harden HITL: signed approvals + queryable audit log + safe rollback path.

---

## Phase 5: User Story 5 — Quality Gates (P1, cross-cutting)

- [ ] T050 US5 — Verify pre-commit passes 7/7 on changed files; `pyright` clean; `vulture --min-confidence 65` clean; frontend eslint/tsc/vitest green (SC-001, SC-006).
- [ ] T051 [P] US5 — Test: missing `datadog` marker on a credentialed test fails the CI guard (T002); lockfile mismatch fails parity check (T003).

---

## Phase 6: Roadmap (SHOULD — tracked as SDD backlog, non-blocking for v1)

- [ ] T060 [P] C — Add provider-agnostic LLM reasoning module for NL RCA summaries + suggested remediations (FR-025).
- [ ] T061 [P] C — Expose ObservAI + Datadog ops via MCP server (`Configuration/Models/Services/Tools`, FR-026).
- [ ] T062 [P] C/D — Graduated autonomy (observer→recommend→approve→auto-remediate) per environment with audit trail (FR-027).
- [ ] T063 [P] D — Feed self-healing outcomes → `maturity/` + `knowledge_base/` continuous-learning loop (FR-029).
- [ ] T064 [P] E — Dog-food ObservAI with its own Datadog APM/logs/metrics + platform-health dashboard (FR-028).

---

## Phase 7: Tag & Period Filtering (per-path + global) (P2, cross-cutting)

- [ ] T070 [P] F — Add `DatadogFilter` Pydantic schema (`tags: list[str]`, `period ∈ {1d,7d,15d,30d}`) in `app/datadog/schemas.py`; add `DATADOG_DEFAULT_TAGS` + `DATADOG_DEFAULT_PERIOD` to `app/core/config.py` (P3: no `from __future__ import annotations`).
- [ ] T071 [P] F — Test (unit, no Datadog): `DatadogFilter` validates `period` enum; `compose_filters(global, request)` AND-merges tags and falls back to global period.
- [ ] T072 F — Add `app/datadog/filters.py::compose_filters` + period→`from`/`to` mapping + per-domain translation table; wire into `DatadogClient` call path (P1: logic in `app/datadog/`, not routers).
- [ ] T073 [P] F — Test (unit, no Datadog): period `7d` → correct `from`/`to`; per-domain tag translation produces the expected native kwargs (monitors/logs/incidents/metrics/…).
- [ ] T074 F — Accept `tags` + `period` on every `datadog_routes/*` list/search endpoint; retire ad-hoc `monitor_tags`/inline `tags`; keep domain `query` where needed.
- [ ] T075 [P] F — Test: `GET /api/v1/datadog/monitors?tags=env:prod` with `DATADOG_DEFAULT_TAGS=team:sre` asserts merged request params (mock client); `@pytest.mark.datadog` integration test for one domain.
- [ ] T076 F — Update OpenAPI docs (`/docs`) + README Datadog Proxy section to document `tags` + `period`.

---

## Gitflow & Delivery

- All tasks land on branch `001-observai-platform` (off `develop`); PR → `develop`; release PR `develop → main`.
- Docker build/push only on `main` (FR-030, plan Phase A).
- No `--no-verify`; Python deps added via `uv add` (FR-030).
- Mark task done only when its test passes and pre-commit/CI are green.
