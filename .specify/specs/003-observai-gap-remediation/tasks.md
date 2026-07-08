# Tasks: ObservAI Platform Gap Remediation

**Input**: Design documents from `.specify/specs/003-observai-gap-remediation/`
- `spec.md` (user stories with priorities, 31 functional requirements, success criteria)
- `.specify/memory/constitution.md` (P2 TDD, P3 type safety, P4 build hygiene, P5 security)
- `backend/pyrightconfig.json`, `Makefile`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `docker-compose.prod.yml`, and the verified source files below.

> **Note on `plan.md`**: `/speckit.plan` was not run for this feature, so `setup-tasks.sh` could not resolve `plan.md`. Per the `/speckit.tasks` fallback ("Generate tasks based on what's available"), this `tasks.md` is derived directly from `spec.md` + the constitution. Tech stack and paths are taken from the constitution and the actual verified code. Each task references concrete, existing file paths so it is executable without further context.
>
> **Reality-check against the original gap list (verified during spec creation)**:
> - **M12 (Knowledge Base page)** is already implemented and wired — `frontend/src/components/KB/KBSearchPage.tsx` + route `/kb` in `frontend/src/App.tsx:39`. Treat as verify-only.
> - **L4 (corrupted env template)** could not be reproduced — `README.md` and `backend/.env.example` both show the correct `REDIS_URL`. Verify before any change (FR-031).
> - **H6/M13**: there is NO auth in the frontend (`frontend/src/api/client.ts` has no token logic, no login route in `App.tsx`); APM/Events/Fleet/RUM pages are missing (backend routes `datadog_routes/{apm,events,fleet,rum}.py` exist).

**Prerequisites**: `backend` runs under `uv` with `[dev]` extras; Postgres available for Alembic; `frontend` runs `npm ci`.

**Tests**: Included per story (TDD is mandated by constitution P2 and referenced in spec Assumptions). Datadog-dependent tests MUST carry `@pytest.mark.datadog` and be skippable without credentials.

**Organization**: Tasks grouped by user story (US1–US11) in priority order from `spec.md`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story this task belongs to (US1–US11)
- Exact file paths included in every task

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm toolchain and migration target so all subsequent stories can be built/tested.

- [ ] T001 Verify backend toolchain: `uv` venv with `[dev]` extras installed, `alembic` CLI available, and `pyright` resolves via `backend/pyrightconfig.json`
- [ ] T002 Verify frontend toolchain: `npm ci` succeeds in `frontend/` and `npm run test` is green on the current suite
- [ ] T003 [P] Provision a local migration target database and confirm `alembic upgrade head` currently applies cleanly (baseline before new revisions)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema changes that block US1 (user store) and US3 (runbook service). No user-story implementation may begin until these land.

- [ ] T004 Create `User` credential model in `backend/app/core/models/user.py` (fields: id UUID pk, username unique, password_hash, role, is_active, timestamps) and export it from `backend/app/core/models/__init__.py`
- [ ] T005 Generate Alembic revision creating the `users` table; register in `backend/alembic/versions/`
- [ ] T006 Add a nullable `service` column (String) to `Runbook` in `backend/app/core/models/self_healing.py` alongside existing fields
- [ ] T007 Generate Alembic revision adding `runbooks.service`; register in `backend/alembic/versions/`
- [ ] T008 Run `alembic upgrade head` locally and confirm both new revisions apply without error (depends on T005, T007)

**Checkpoint**: Schema supports real users and per-service runbooks. US1 and US3 may proceed.

---

## Phase 3: User Story 1 - Secure Authentication (Priority: P1)

**Goal**: Replace the hardcoded `admin/admin` backdoor with a real, hashed credential store, add rate-limiting + JWT `iss`/`aud` + refresh/revocation, and add the frontend login/logout flow that collects and sends the bearer token.

**Independent Test**: With a fresh DB, `admin`/`admin` is rejected; a created user logs in and gets a token with `iss`/`aud`; 10 rapid bad logins are throttled; a revoked/expired token is rejected; the UI login stores the token and attaches it to calls.

### Tests for User Story 1

- [ ] T009 [P] [US1] Contract test: login rejects `admin`/`admin` and wrong credentials, accepts a real user — `backend/tests/test_auth/test_login.py` (not datadog)
- [ ] T010 [P] [US1] Contract test: JWT carries `iss`/`aud` and is rejected when missing/invalid; rate-limit triggers after N failures — `backend/tests/test_auth/test_jwt.py`
- [ ] T011 [P] [US1] Frontend test: `LoginPage` stores token and `frontend/src/api/client.ts` attaches `Authorization: Bearer` — extend `frontend/src/api/client.test.tsx`

### Implementation for User Story 1

- [ ] T012 [US1] Implement password hashing + user store (create/get by username) in `backend/app/auth/service.py` using `passlib[bcrypt]` (already a dependency)
- [ ] T013 [US1] Add `role` to `UserInfo` and `get_current_user` in `backend/app/auth/deps.py`; validate `iss`/`aud` on token decode
- [ ] T014 [US1] Rewrite `login` in `backend/app/auth/router.py` to authenticate against the user store, enforce rate-limiting, and emit JWT with `iss`/`aud` + refresh support (remove the `admin`/`admin` literal at line 15)
- [ ] T015 [US1] Add rate-limit configuration to `backend/app/core/config.py` (e.g., `AUTH_RATE_LIMIT`) and a small in-memory/Redis limiter used by the login route
- [ ] T016 [US1] Create `frontend/src/components/Auth/LoginPage.tsx` (login form) and wire logout; store token in `localStorage`/memory
- [ ] T017 [US1] Attach bearer token in `frontend/src/api/client.ts` and add a `/login` route + redirect in `frontend/src/App.tsx`
- [ ] T018 [US1] Add a seed/create-user script or Alembic bootstrap so an initial operator account can be created (no default credentials shipped)

**Checkpoint**: US1 fully functional and testable independently. No hardcoded credentials remain.

---

## Phase 4: User Story 2 - Datadog Client Reliability (Priority: P1)

**Goal**: Fix the broken singleton so one instance is initialized once and reused, unify retry into a single policy applied to every call, and make `close()` safe to re-acquire.

**Independent Test**: Many concurrent calls create exactly one instance; every method (including `query_metrics`) uses the same retry policy; `close()` followed by a new request succeeds.

### Tests for User Story 2

- [ ] T019 [P] [US2] Unit test: concurrent `get_instance()`/`__init__` yields exactly one instance — `backend/tests/test_datadog/test_singleton.py`
- [ ] T020 [P] [US2] Unit test: `query_metrics` and `call()` both exercise one shared retry policy; `close()` then re-acquire works — `backend/tests/test_datadog/test_retry.py`

### Implementation for User Story 2

- [ ] T021 [US2] Fix singleton contract in `backend/app/datadog/client.py`: keep instance across calls, do not re-run init, do not set `_instance = None` in `close()` (use a reset/context pattern instead)
- [ ] T022 [US2] Unify retry logic: route `query_metrics` through the single `_call_with_retry` path (remove the duplicate `@retry` decorator) so all calls share one policy
- [ ] T023 [US2] Reuse one client instance in maturity data collection in `backend/app/maturity/service.py` / `backend/app/maturity/router_reports.py` (remove per-call create/close — gap M6)

**Checkpoint**: Datadog client survives concurrency and `close()`/re-init.

---

## Phase 5: User Story 3 - Self-Healing Correctness (Priority: P1)

**Goal**: Make self-healing analysis run without `AttributeError` (runbook `service`) and record `completed_at` on approve/reject.

**Independent Test**: Analysis runs for runbooks with/without a service and returns findings for 100% of runs; approved/rejected actions set both `executed_at` and `completed_at`.

### Tests for User Story 3

- [ ] T024 [P] [US3] Unit test: `analyze_self_healing` returns findings for runbooks with null `service` without error — `backend/tests/test_analysis/test_self_healing.py`
- [ ] T025 [P] [US3] Unit test: approve/reject sets `completed_at` — extend `backend/tests/test_self_healing/`

### Implementation for User Story 3

- [ ] T026 [US3] Ensure `Runbook.service` is read safely in `backend/app/analysis/self_healing_agent.py` (line 36) now that the column exists (depends on T006)
- [ ] T027 [US3] Set `completed_at` alongside `executed_at` on approve/reject in `backend/app/self_healing/router.py` (model field already exists in `backend/app/core/models/self_healing.py`)

**Checkpoint**: Self-healing analysis completes for every run without runtime errors.

---

## Phase 6: User Story 4 - Type-Safety Gate (Priority: P1)

**Goal**: Turn the type checker on and remove the forbidden lazy-annotation import from all schema/model files; align the local checker with CI/pre-commit.

**Independent Test**: A deliberately broken annotation in a changed file fails the gate; zero schema/model files contain `from __future__ import annotations`; `make typecheck` and CI use the same checker.

### Tests for User Story 4

- [ ] T028 [P] [US4] Regression test: a known-broken type annotation in a scratch file fails `pyright` (CI guard) — document in `backend/tests/test_types/README.md` or a pinned negative test

### Implementation for User Story 4

- [ ] T029 [US4] Set `typeCheckingMode` to an active mode (e.g., `basic`) in `backend/pyrightconfig.json` (currently `"off"` at line 10)
- [ ] T030 [US4] Remove `from __future__ import annotations` from all 44 schema/model files under `backend/app` (e.g., `backend/app/core/models/*.py`, `backend/app/core/schemas/*.py`, `backend/app/datadog/client.py`, `backend/app/rca/router.py`, `backend/app/health/router.py`, `backend/app/maturity/*.py`, etc.)
- [ ] T031 [US4] Change `make typecheck` in `Makefile` (line 78) from `mypy app/` to `pyright app/ alembic/` to match pre-commit/CI
- [ ] T032 [US4] Run `pyright app/ alembic/` and fix or justify every reported error on changed files until clean

**Checkpoint**: Type checker is enforced and green on changed files; forbidden import eliminated.

---

## Phase 7: User Story 5 - RCA Correlation Engine (Priority: P2)

**Goal**: Implement the multi-stage RCA pipeline (Discovery → Breadth → Depth → Conclusion) that correlates Datadog signals, instead of persisting caller-supplied text.

**Independent Test**: Generating RCA for a representative incident yields structured stages with correlated Datadog evidence; retrieving it reflects the pipeline output.

### Tests for User Story 5

- [ ] T033 [P] [US5] Contract test: generated RCA contains Discovery/Breadth/Depth/Conclusion stages referencing Datadog signals — `backend/tests/test_rca/test_pipeline.py` (datadog-marked where it hits live API)
- [ ] T034 [P] [US5] Integration test: `POST /rca/{id}/generate` stores a structured report, not caller free-text — `backend/tests/test_rca/test_router.py`

### Implementation for User Story 5

- [ ] T035 [US5] Implement the pipeline stages in `backend/app/llm/rca_service.py` (Discovery → Breadth → Depth → Conclusion) using Datadog correlation
- [ ] T036 [US5] Extend `RcaReport` model/schema in `backend/app/core/models/rca.py` + `backend/app/core/schemas/rca.py` to store pipeline stages/evidence
- [ ] T037 [US5] Wire the pipeline into `backend/app/rca/router.py` `generate_llm_rca` (line 77) so generation runs the engine; keep `POST /rca` for manual overrides

**Checkpoint**: RCA is an engine, not a form.

---

## Phase 8: User Story 6 - Database Transaction Correctness (Priority: P2)

**Goal**: Stop committing empty transactions on read-only requests.

**Independent Test**: A GET request issues no commit on the session (verified via a session spy/test double).

### Tests for User Story 6

- [ ] T038 [P] [US6] Unit test: read requests via `get_db` perform no `commit`; write requests commit, errors roll back — `backend/tests/test_core/test_db.py`

### Implementation for User Story 6

- [ ] T039 [US6] Fix `get_db` in `backend/app/core/db.py` (lines 16–26) to commit only on mutation and roll back on error (no commit after yield for reads)

**Checkpoint**: No empty commits on reads; pool overhead reduced.

---

## Phase 9: User Story 7 - Frontend Auth & Design Consistency (Priority: P2)

**Goal**: Enforce auth on protected routes from the browser and fix visual/UX inconsistencies (design-system tokens on Reports, query invalidation instead of full reload on Incident detail). Builds on US1's login/token.

**Independent Test**: Authenticated user can PATCH/DELETE an incident from the UI (bearer attached); Reports renders with design-system classes; incident detail updates without a full reload.

### Tests for User Story 7

- [ ] T040 [P] [US7] Frontend test: incident PATCH/DELETE from UI carries bearer and succeeds — extend `frontend/src/components/Incidents/`
- [ ] T041 [P] [US7] Frontend test: `ReportsPage` uses design-system tokens (no hardcoded hex); `IncidentDetailPage` invalidates query instead of `window.location.reload()`

### Implementation for User Story 7

- [ ] T042 [US7] Add a route guard / protected-route wrapper in `frontend/src/App.tsx` that redirects unauthenticated users to login (depends on T017)
- [ ] T043 [US7] Replace hardcoded Catppuccin hex (`#1e1e2e`, `#313244`, `#11111b`, `#45475a`) in `frontend/src/components/Reports/ReportsPage.tsx` with design-system tokens (Tailwind `bg-surface-*`, `bg-brand-*`)
- [ ] T044 [US7] Replace `window.location.reload()` at `frontend/src/components/Incidents/IncidentDetailPage.tsx:85` with TanStack Query invalidation/refetch

**Checkpoint**: Frontend enforces auth and matches the design system; no full reloads.

---

## Phase 10: User Story 8 - CI / Build Integrity & Logging (Priority: P2)

**Goal**: Make CI fail fast on lockfile/manifest mismatch and run migrations to head; adopt structured logging; align the dead-code threshold.

**Independent Test**: A deliberate `package.json`/lockfile mismatch fails CI; migrations apply to head on a fresh DB; logs are structured.

### Tests for User Story 8

- [ ] T045 [P] [US8] CI contract test: drift `package.json` without updating lockfile → CI fails (run locally via `npm ci` parity assertion)
- [ ] T046 [P] [US8] CI contract test: `alembic upgrade head` against a fresh DB succeeds in the backend job

### Implementation for User Story 8

- [ ] T047 [US8] Add an explicit lockfile↔manifest parity check to `.github/workflows/ci.yml` frontend job (assert `package-lock.json` matches `package.json`)
- [ ] T048 [US8] Add an `alembic upgrade head` step (against the CI Postgres service) to the backend job in `.github/workflows/ci.yml`
- [ ] T049 [US8] Add structured logging setup in `backend/app/core/logging_config.py` (structlog) and wire it in `backend/app/__init__.py` / `backend/app/main.py`; replace stdlib `logging` calls where appropriate (M8)
- [ ] T050 [US8] Align dead-code threshold: ensure `.pre-commit-config.yaml` vulture `--min-confidence 65` (line 34) matches any threshold declared in `backend/pyproject.toml` dependency-groups; reconcile if inconsistent (M15)

**Checkpoint**: CI proves reproducible builds and clean migrations; logs are structured.

---

## Phase 11: User Story 9 - Timestamp Correctness (Priority: P2)

**Goal**: Use timezone-aware timestamps uniformly in health endpoints.

**Independent Test**: `/health/forecast` and `/health/stats` return only aware timestamps and serialize without error.

### Tests for User Story 9

- [ ] T051 [P] [US9] Unit test: health forecast/stats responses contain only aware datetimes — `backend/tests/test_health/test_timestamps.py`

### Implementation for User Story 9

- [ ] T052 [US9] Replace naive `datetime.utcnow()` with `datetime.now(UTC)` at `backend/app/health/router.py:297` and `:416` (and any other naive sites) so all timestamps are aware

**Checkpoint**: No naive/aware mix; serialization never raises.

---

## Phase 12: User Story 10 - Dependency & Repository Hygiene (Priority: P3)

**Goal**: Remove unused runtime dependencies (or document reserved infra), delete demo/junk files, clarify the confusing router import name, populate `AGENTS.md`, and verify the env template.

**Independent Test**: Manifest audit shows no unused top-level runtime dep unless scoped as roadmap; junk files gone; `AGENTS.md` has real guidance.

### Tests for User Story 10

- [ ] T053 [P] [US10] Manifest audit test: no import resolves to a removed dependency; CI import-check passes — `backend/tests/test_deps/`

### Implementation for User Story 10

- [ ] T054 [US10] Decide Celery/Redis (M1/M2): either implement minimal real usage (worker + one task) or document as reserved roadmap infra in `README.md`; do not leave configured-but-dead
- [ ] T055 [US10] Remove unused runtime deps from `backend/pyproject.toml`: `gunicorn` (M3), `pytz` (M4); remove unused dev deps `aresponses`/`factory-boy` (M9) unless a test uses them
- [ ] T056 [US10] Delete demo/junk files `api-demo/_old_dd_test.py.bak` and `api-demo/_test_backend.py` (M14)
- [ ] T057 [US10] Rename `dd_incidents_router` → `datadog_incidents_router` in `backend/app/main.py` (lines 49, 80) for clarity (L1)
- [ ] T058 [US10] Expand `AGENTS.md` with real onboarding guidance (structure, commands, conventions) instead of the SPECKIT placeholder (L2)
- [ ] T059 [US10] Verify `REDIS_URL` in `README.md` and `backend/.env.example` is valid (L4 claim was not reproduced — confirm before editing; fix only if actually corrupted)

**Checkpoint**: Clean manifest, no junk, clear names, useful agent docs.

---

## Phase 13: User Story 11 - Frontend Feature Completeness (Priority: P3)

**Goal**: Provide the missing Datadog UI pages (APM/Events/Fleet/RUM), confirm the KB page works, and add a healthcheck to the production frontend container.

**Independent Test**: APM/Events/Fleet/RUM pages render real backend data; KB page verified; production frontend container declares a healthcheck.

### Tests for User Story 11

- [ ] T060 [P] [US11] Frontend smoke test: APM/Events/Fleet/RUM pages mount and fetch — extend `frontend/src/components/components.smoke.test.tsx`
- [ ] T061 [P] [US11] Verify KB page `frontend/src/components/KB/KBSearchPage.tsx` renders real data from its backend route (M12 — already implemented; confirm only)

### Implementation for User Story 11

- [ ] T062 [US11] Create `frontend/src/components/APM/ApmPage.tsx`, `Events/EventsPage.tsx`, `Fleet/FleetPage.tsx`, `RUM/Rumpage.tsx` backed by `frontend/src/api/` clients for the existing `datadog_routes/{apm,events,fleet,rum}.py`
- [ ] T063 [US11] Register the new pages as routes in `frontend/src/App.tsx` (e.g., `/apm`, `/events`, `/fleet`, `/rum`)
- [ ] T064 [US11] Add a `healthcheck` to the `frontend` service in `docker-compose.prod.yml` (currently missing — M11), per constitution P4

**Checkpoint**: All backend capabilities have matching UI; production frontend is health-checked.

---

## Phase 14: Polish & Cross-Cutting Concerns

**Purpose**: Final verification that all 35 gaps are closed and quality gates pass end-to-end.

- [ ] T065 Run full backend gate: `ruff check app/ tests/`, `pyright app/ alembic/`, `pytest tests/ -m "not datadog"`, `pre-commit run --all-files`
- [ ] T066 Run full frontend gate: `npm run lint`, `npx tsc --noEmit`, `npm run test`, `npm run build`
- [ ] T067 Perform a gap-by-gap closure review against `spec.md` FR-001–FR-031 and record status for each of the 35 source findings (C1–C5, H1–H8, M1–M15, L1–L4)
- [ ] T068 Manually exercise the top critical flows: login rejection of defaults, self-healing analysis run, concurrent Datadog calls, and a fresh-DB `alembic upgrade head` in CI

**Checkpoint**: Every quality gate is green; all 35 gaps accounted for and verified.

---

## Dependencies (Story Completion Order)

```
Phase 1 Setup ──► Phase 2 Foundational (T004–T008)
                        │
        ┌───────────────┼───────────────────────────────┐
        ▼               ▼                                ▼
   US1 Auth         US3 Self-Healing                US2 Datadog Client
   (T009–T018)      (T024–T027, needs T006)         (T019–T023)
        │
        ▼
   US7 Frontend Auth & Design (T040–T044, needs T017 from US1)

US4 Type Gate (T028–T032) ── independent, do early (unblocks clean CI)
US5 RCA (T033–T037) ── independent
US6 DB Tx (T038–T039) ── independent
US8 CI/Logging (T045–T050) ── independent (depends on pyright on in US4)
US9 Timestamps (T051–T052) ── independent
US10 Hygiene (T053–T059) ── independent
US11 Frontend Completeness (T060–T064) ── independent

Phase 14 Polish (T065–T068) ── after all stories
```

**Notes**:
- US1 and US3 are the only stories that depend on Phase 2 (schema). All other stories are independent and can run in parallel once Phase 2 lands.
- US7 depends on US1 (login/token) and is safe to start only after T017.
- US4 (type gate) is recommended early because turning `pyright` on will surface errors across the codebase that other stories should fix as they touch files.

## Parallel Execution Examples

- **Wave A (after Phase 2)**: US2, US4, US5, US6, US8, US9, US10, US11 can all start in parallel — they touch disjoint files.
- **Wave B**: Within US4, T030 (remove future import across 44 files) can be parallelized file-by-file; T031/T032 are sequential after.
- **Wave C**: Within US11, T062 (four new page components) is fully parallelizable; T063 (route registration) is sequential after.

## Implementation Strategy

- **MVP (ship first)**: US1 (secure auth) + US3 (self-healing crash) + US2 (Datadog client) — the four critical/security stories that break or backdoor production. These alone close C1–C3 and the core of C5.
- **Then**: US4 (type gate) early to stop regressions; US6/US9 (correctness); US7/US8 (frontend auth + CI integrity); US5 (RCA engine).
- **Last**: US10/US11 (hygiene + UI completeness) and Polish.
- Each story is an independently deployable, testable increment; merge per story behind the existing gitflow (feature → `develop` → `main`).
