# Feature Specification: ObservAI Platform Gap Remediation

**Feature Branch**: `003-observai-gap-remediation`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description — "Análise Profunda de Gaps — ObservAI Platform": a deep, prioritized gap analysis of the ObservAI codebase covering 35 findings (5 critical, 8 high, 15 medium, 4 low) across production-breaking defects, security backdoors, broken reliability, disabled quality gates, CI/build gaps, and frontend inconsistencies. This spec remediates every listed gap, organized by severity into independently shippable, testable workstreams.

## Background & Motivation

ObservAI is a control layer over Datadog (FastAPI backend + React frontend). A recent deep code review identified defects that either break in production today (hardcoded `admin/admin` credentials, a self-healing analysis that raises `AttributeError` at runtime, a Datadog client whose singleton contract is violated under async load) or silently disable the project's own guardrails (the type checker is switched off, so broken type annotations ship unnoticed; CI never runs database migrations or checks that the lockfile matches the manifest).

The project's governing [ObservAI Constitution](../../.specify/memory/constitution.md) mandates: real user stores with hashed passwords (P5), enforced type checking with no `from __future__ import annotations` in schema/model files (P3), lockfile/manifest parity and working migrations in CI (P4), and every long-running service exposing a healthcheck (P4). Most gaps are direct violations of these ratified principles.

This spec closes the gap between the current code and the constitution + the promises made in `PLAN.md` (e.g., the multi-stage RCA engine). Each gap is traced to a functional requirement below (tagged with its source ID: C1–C5 critical, H1–H8 high, M1–M15 medium, L1–L4 low).

## User Scenarios & Testing *(mandatory)*

<!--
  Stories are prioritized by severity (P1 = critical/production-breaking or security,
  P2 = high, P3 = medium/low). Each is independently testable and deliverable.
  Gap source IDs are shown in parentheses for traceability.
-->

### User Story 1 - Operators can authenticate securely (Priority: P1)

A platform operator opens the application, is presented with a real login screen, and authenticates with a stored credential. Incorrect credentials are rejected; brute-force attempts are throttled; the issued token carries issuer/audience claims and can be revoked. No default or hardcoded credential exists anywhere.

**Why this priority**: C1 (hardcoded `admin/admin`) is a permanent backdoor — anyone can log in. C5 (no rate-limit, no refresh/revocation, JWT without `aud`/`iss`) enables brute force and token theft. These are the highest-severity security findings.

**Independent Test**: With a fresh database, attempting login with `admin/admin` MUST fail; login with a properly created user MUST succeed and return a token whose claims include issuer and audience; 10 rapid failed logins from one client MUST be throttled.

**Acceptance Scenarios**:

1. **Given** the system is running, **When** a caller submits `admin`/`admin` (or any default credential), **Then** authentication is rejected with an unauthorized response.
2. **Given** a registered user with a hashed password, **When** they submit correct credentials, **Then** they receive a signed token containing `iss` and `aud` claims.
3. **Given** an attacker makes repeated failed login attempts, **When** the rate limit is exceeded, **Then** further attempts are throttled for a cooling-off period.
4. **Given** a valid token, **When** it is revoked or expires, **Then** it is no longer accepted (refresh/revocation supported).

---

### User Story 2 - The Datadog client survives concurrent use (Priority: P1)

Under production concurrency the Datadog client reuses a single instance, initializes exactly once, applies one consistent retry/backoff policy to every call, and tears down cleanly without breaking the singleton contract.

**Why this priority**: C2 (singleton `__new__` creates the instance but `__init__` re-runs on every call; duplicated retry logic; `close()` sets the singleton to `None`) causes races in async load and inconsistent retry — connection loss on a primary code path. This is a production-breaking reliability defect.

**Independent Test**: Fire many concurrent requests through the client; assert exactly one underlying connection is created, every call (including metric queries) goes through the same retry policy, and `close()` can be followed by a successful re-acquire without leaving the singleton permanently dead.

**Acceptance Scenarios**:

1. **Given** the client is first used, **When** many calls arrive concurrently, **Then** exactly one client instance is initialized and reused.
2. **Given** a transient Datadog error, **When** any method is called (including metric queries), **Then** the single retry/backoff policy is applied consistently.
3. **Given** `close()` is called, **When** the next request arrives, **Then** a working client is re-created rather than raising on a dead singleton.

---

### User Story 3 - Self-healing analysis runs without crashing (Priority: P1)

An operator triggers the self-healing analysis. It completes and returns coverage and action-effectiveness findings for every runbook and action without a runtime error.

**Why this priority**: C3 — `analyze_self_healing` reads `rb.service` but the `Runbook` model has no `service` column, raising `AttributeError` at runtime and breaking the entire analysis. L3 (approve/reject sets `executed_at` but not `completed_at`) is a related data-integrity gap.

**Independent Test**: With runbooks present (some with a service, some without), invoke the analysis; assert it returns a result for 100% of runs and that approved/rejected actions record a completion timestamp.

**Acceptance Scenarios**:

1. **Given** runbooks exist, **When** self-healing analysis runs, **Then** it reads each runbook's service (defaulting safely when absent) and returns findings with no error.
2. **Given** an auto-heal action is approved or rejected, **When** the state change is persisted, **Then** both `executed_at` and `completed_at` are recorded.

---

### User Story 4 - The type-safety gate is actually enforced (Priority: P1)

The project's static type checker runs in a real checking mode and blocks changes that violate the project's typing rules; schema/model files never use the forbidden lazy-annotation import.

**Why this priority**: C4 (type checker `typeCheckingMode: "off"`) disables the entire typing gate the constitution requires, so broken annotations ship silently. H2 (forbidden `from __future__ import annotations` appears in 44 schema/model files) is the concrete violation it was masking. M5 (Makefile uses a different checker than pre-commit/CI) means "green locally" ≠ "green in CI".

**Independent Test**: Introduce a deliberately broken type annotation in a changed file; assert the type checker reports it and CI fails. Assert zero schema/model files contain the forbidden import.

**Acceptance Scenarios**:

1. **Given** a changed file with a type error, **When** the type checker runs, **Then** it reports the error and the gate fails.
2. **Given** the codebase, **When** scanned for the forbidden lazy-annotation import in schema/model files, **Then** zero occurrences remain.
3. **Given** a developer runs the local type-check command, **When** it completes, **Then** it uses the same checker and rules as CI.

---

### User Story 5 - RCA explains root cause via Datadog correlation (Priority: P2)

When an incident's RCA is generated, the system correlates Datadog signals through an explicit multi-stage pipeline (Discovery → Breadth → Depth → Conclusion) and stores a structured analysis, rather than merely persisting free-text the user typed.

**Why this priority**: H1 — `POST /rca` is single-pass CRUD that stores whatever the caller submits; none of the `PLAN.md` Phase B pipeline exists, so "RCA engine" does not analyze anything.

**Independent Test**: Generate an RCA for a representative incident; assert the stored report captures the distinct pipeline stages and references correlated Datadog signals, not just user-supplied text.

**Acceptance Scenarios**:

1. **Given** an incident with associated Datadog metrics/logs, **When** RCA generation runs, **Then** it produces Discovery, Breadth, Depth, and Conclusion stages.
2. **Given** a generated report, **When** retrieved, **Then** it reflects correlated evidence rather than only caller-provided fields.

---

### User Story 6 - Database sessions don't commit on reads (Priority: P2)

Read-only API requests open a session, read data, and close without performing an empty commit; only mutating requests commit.

**Why this priority**: H3 — the session dependency commits after every request, including reads, creating empty transactions that lock pool connections and add avoidable overhead.

**Independent Test**: Issue a GET request; assert no commit is issued on the session (observe via a test double / query log).

**Acceptance Scenarios**:

1. **Given** a read request, **When** it completes, **Then** the session is closed without an empty commit.
2. **Given** a write request, **When** it succeeds, **Then** the transaction is committed; on error it is rolled back.

---

### User Story 7 - Frontend authenticates and matches the design system (Priority: P2)

The browser app shows a login/logout flow, collects the bearer token, and uses it on protected calls (so incident PATCH/DELETE work from the UI). All pages use the shared design-system tokens; the incident detail view refreshes data via query invalidation instead of a full page reload.

**Why this priority**: H6 (no login UI, token never collected → protected routes unusable from browser), H4 (Reports page hardcodes a Catppuccin palette, breaking visual consistency), M10 (full `window.location.reload()` instead of invalidating the query).

**Independent Test**: Log in through the UI, perform an incident state change that requires an authorized call, and confirm it succeeds; confirm Reports renders with design-system classes and incident detail updates without a full reload.

**Acceptance Scenarios**:

1. **Given** an unauthenticated user, **When** they open the app, **Then** they are prompted to log in and the token is stored for subsequent calls.
2. **Given** a logged-in user, **When** they change an incident via PATCH/DELETE, **Then** the call carries the bearer token and succeeds.
3. **Given** the Reports page, **When** rendered, **Then** it uses design-system tokens (no hardcoded theme hex values).
4. **Given** an incident detail update, **When** data changes, **Then** the view refreshes via query invalidation, not a full reload.

---

### User Story 8 - CI proves the build is reproducible and migrates cleanly (Priority: P2)

Continuous integration fails fast when the lockfile diverges from the manifest, and it applies database migrations to head so a broken migration is caught before deploy.

**Why this priority**: H7 (no package-lock ↔ package.json parity check) and H8 (no `alembic upgrade head` in CI) — both are constitution P4 requirements and both let production-breaking mismatches reach deploy undetected. M8 (no structured logging despite the constitution requiring it) and M15 (inconsistent dead-code threshold) are quality-gate gaps in the same area.

**Independent Test**: Deliberately edit `package.json` without updating the lockfile; assert CI fails. Provision a fresh database in CI; assert migrations apply to head without error.

**Acceptance Scenarios**:

1. **Given** a manifest/lockfile mismatch, **When** CI runs, **Then** it fails fast with a clear message.
2. **Given** a fresh database, **When** CI runs migrations, **Then** they apply to head successfully.
3. **Given** application logs, **When** emitted, **Then** they are structured (machine-parseable) per the constitution.
4. **Given** the dead-code checker, **When** configured, **Then** its threshold matches across pre-commit and dependency definitions.

---

### User Story 9 - Timestamps are uniformly timezone-aware (Priority: P2)

All health/forecast/stats responses use timezone-aware timestamps consistently so serialization never raises.

**Why this priority**: H5 — `health/router.py` mixes naive `datetime.utcnow()` with aware `datetime.now(UTC)`; Pydantic raises when a naive value lands in an aware field.

**Independent Test**: Call `/health/forecast` and `/health/stats`; assert all returned timestamps are timezone-aware and serialize without error.

**Acceptance Scenarios**:

1. **Given** a request to a health endpoint returning timestamps, **When** the response is built, **Then** every timestamp is timezone-aware.
2. **Given** mixed legacy call sites, **When** consolidated, **Then** no naive `datetime` is used.

---

### User Story 10 - Dependency and dead-code hygiene (Priority: P3)

The dependency manifest contains only what the running system uses (or intentionally reserves); demo/junk files are removed; confusing internal names are clarified; agent guidance docs are populated.

**Why this priority**: M1/M2 (Celery + Redis configured but no tasks/workers/usage), M3 (gunicorn in deps, never used), M4 (pytz in deps, unused), M9 (aresponses/factory-boy dev deps unused), M14 (api-demo junk files), L1 (confusing `dd_incidents_router` import name), L2 (placeholder `AGENTS.md`), L4 (corrupted env template — *could not be reproduced in current tree; verify before fixing*).

**Independent Test**: Audit the manifest against actual imports; assert no unused top-level runtime dependency remains unless explicitly scoped as roadmap infra; assert junk files are gone and `AGENTS.md` contains real guidance.

**Acceptance Scenarios**:

1. **Given** the dependency manifest, **When** audited against usage, **Then** unused runtime deps are removed or documented as intended future infra.
2. **Given** the repository, **When** scanned, **Then** demo/junk files (e.g., api-demo scratch files) are removed.
3. **Given** the agent guidance file, **When** read, **Then** it provides real, actionable onboarding guidance.
4. **Given** the environment template, **When** reviewed, **Then** it is valid and parseable (verify L4 claim first).

---

### User Story 11 - Frontend feature completeness (Priority: P3)

The browser app provides pages for the backend capabilities that already exist but lack UI: Knowledge Base, and the Datadog surfaces (APM, Events, Fleet, RUM). The production frontend container exposes a healthcheck.

**Why this priority**: M12/M13 (backend routes exist with no UI), M11 (production frontend container has no healthcheck, violating constitution P4).

**Independent Test**: Navigate to each missing page from the UI; assert it renders real data from its backend route; assert the production container declares a healthcheck.

**Acceptance Scenarios**:

1. **Given** a logged-in user, **When** they open the Knowledge Base page, **Then** it displays KB content from the backend.
2. **Given** a logged-in user, **When** they open APM/Events/Fleet/RUM pages, **Then** each renders its backend data.
3. **Given** the production compose file, **When** inspected, **Then** the frontend service declares a healthcheck.

---

### Edge Cases

- **Concurrent Datadog calls during a rolling deploy**: the singleton must survive `close()`/re-init without permanently dying (C2).
- **Runbooks created before the `service` column exists**: migration must backfill/default safely and analysis must not crash on nulls (C3).
- **Token expiry vs. in-flight request**: refresh/revocation must not orphan valid in-flight calls (C5).
- **CI on a fork / environment without a database**: the migration step must be conditional/skippable without failing the whole pipeline (H8).
- **Datadog credentials absent**: the client must degrade gracefully and not crash startup (C2, constitution P2 test-isolation).
- **Lockfile mismatch introduced in a feature branch**: parity check must fail loudly in CI, not silently at deploy (H7).
- **Timestamp serialization with mixed naive/aware values**: must never raise; all values normalized to aware UTC (H5).

## Requirements *(mandatory)*

### Functional Requirements

**Authentication & Security**

- **FR-001**: System MUST store user credentials in a real credential store with salted password hashing; no plaintext or default credentials (e.g., `admin/admin`) may exist. *(C1)*
- **FR-002**: System MUST reject login for any unknown username or incorrect password with an unauthorized response. *(C1)*
- **FR-003**: System MUST throttle authentication attempts (rate limiting) to resist brute force. *(C5)*
- **FR-004**: System MUST support token refresh and/or revocation so a stolen token is not permanently valid. *(C5)*
- **FR-005**: System MUST issue JWTs that include `iss` and `aud` claims and MUST validate those claims on every protected request. *(C5)*
- **FR-006**: System MUST provide a frontend login/logout flow that collects and stores the bearer token and attaches it to authorized API calls. *(H6)*
- **FR-007**: System MUST allow incident PATCH/DELETE operations to succeed from the browser once authenticated. *(H6)*

**Datadog Client Reliability**

- **FR-008**: System MUST guarantee a single Datadog client instance is initialized exactly once and reused; `close()` MUST NOT permanently break the ability to acquire a new instance. *(C2)*
- **FR-009**: System MUST apply one consistent retry/backoff policy to every Datadog call, including metric queries (no duplicated retry logic). *(C2)*
- **FR-010**: System MUST reuse a single Datadog client instance across maturity data collection rather than creating/closing one per call. *(M6)*

**Self-Healing Correctness**

- **FR-011**: System MUST model a `service` attribute on runbooks and MUST read it in self-healing analysis without raising. *(C3)*
- **FR-012**: System MUST set `completed_at` (in addition to `executed_at`) when an auto-heal action is approved or rejected. *(L3)*

**Type Safety & Quality Gate**

- **FR-013**: System MUST run the static type checker in an active checking mode (not disabled) on changed files and MUST fail the gate on violations. *(C4)*
- **FR-014**: System MUST NOT use `from __future__ import annotations` in any schema or model file. *(H2)*
- **FR-015**: System MUST run the same type checker and rules locally (Makefile), in pre-commit, and in CI. *(M5)*

**RCA Engine**

- **FR-016**: System MUST generate RCA reports via an explicit multi-stage correlation pipeline (Discovery → Breadth → Depth → Conclusion) over Datadog signals, not by persisting caller-supplied text. *(H1)*

**Database Transactions**

- **FR-017**: System MUST NOT commit an empty transaction on read-only requests; sessions MUST commit only on mutations and roll back on error. *(H3)*

**Timestamp Correctness**

- **FR-018**: System MUST use timezone-aware timestamps uniformly across health/forecast/stats responses. *(H5)*

**Frontend Consistency & Completeness**

- **FR-019**: System MUST render the Reports page using the shared design-system tokens, with no hardcoded theme hex values. *(H4)*
- **FR-020**: System MUST refresh incident detail data via query invalidation rather than a full page reload. *(M10)*
- **FR-021**: System MUST provide frontend pages for Knowledge Base, APM, Events, Fleet, and RUM backed by existing routes. *(M12, M13)*
- **FR-022**: System MUST declare a healthcheck on the production frontend container. *(M11)*

**CI / Build Integrity & Logging**

- **FR-023**: CI MUST fail fast when the lockfile diverges from the package manifest. *(H7)*
- **FR-024**: CI MUST apply database migrations to head against a provisioned database. *(H8)*
- **FR-025**: System MUST emit structured (machine-parseable) logs. *(M8)*
- **FR-026**: The dead-code checker threshold MUST be consistent between pre-commit configuration and dependency definitions. *(M15)*

**Dependency & Repository Hygiene**

- **FR-027**: The dependency manifest MUST contain only runtime dependencies that are used or explicitly scoped as reserved future infrastructure (Celery/Redis); unused ones MUST be removed. *(M1, M2, M3, M4, M9)*
- **FR-028**: Repository MUST NOT contain demo/junk scratch files (e.g., api-demo `.bak`/test scratch files). *(M14)*
- **FR-029**: Internal router import names MUST be clear and unambiguous. *(L1)*
- **FR-030**: Agent guidance file (`AGENTS.md`) MUST contain actionable onboarding guidance, not a placeholder. *(L2)*
- **FR-031**: Environment template MUST be valid and parseable. *(L4 — verify claim before fixing; not reproduced in current tree)*

### Key Entities *(include if feature involves data)*

- **User / Credential**: identity with hashed secret and role; replaces the hardcoded default. Drives FR-001–FR-007.
- **Runbook**: automation playbook; MUST carry a `service` attribute (new column) so self-healing can group by service. Drives FR-011.
- **AutoHealAction**: recorded remediation; tracks `executed_at` and `completed_at` lifecycle. Drives FR-012.
- **RcaReport**: analysis output; MUST capture pipeline stages and correlated Datadog evidence rather than free text. Drives FR-016.
- **DatadogClient**: shared singleton wrapper; contract = init-once, single retry policy, safe teardown. Drives FR-008–FR-010.
- **CI Quality Gates**: the set of enforced checks — type checking, lockfile parity, migration-to-head, dead-code threshold, structured logging. Drives FR-013–FR-015, FR-023–FR-026.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 5 critical gaps (C1–C5) are closed and verified; zero hardcoded or default credentials remain in the codebase.
- **SC-002**: A security exercise confirms login cannot be bypassed, rejects incorrect credentials, throttles repeated failures, and issues/revokes tokens with `iss`/`aud` claims.
- **SC-003**: Self-healing analysis completes successfully for 100% of runs (including runbooks without a service and approved/rejected actions) with no runtime errors.
- **SC-004**: The type checker is enforced and blocks non-compliant changes in CI; zero schema/model files contain the forbidden lazy-annotation import.
- **SC-005**: RCA generation produces a multi-stage, Datadog-correlated analysis for representative incidents (not a stored free-text form).
- **SC-006**: Read-only API paths perform no commit/empty transaction, measured by a session test double confirming zero commits on GET.
- **SC-007**: CI build is reproducible: a deliberate lockfile/manifest mismatch fails CI, and migrations apply to head on a fresh database.
- **SC-008**: Frontend authentication works end-to-end from the browser; protected incident PATCH/DELETE calls succeed with the bearer token.
- **SC-009**: All covered frontend pages render with the shared design system; no hardcoded theme palettes remain; incident detail refreshes without a full reload.
- **SC-010**: The dependency manifest contains no unused top-level runtime dependencies; demo/junk files are removed; `AGENTS.md` provides real guidance.

## Assumptions

- **Verification basis**: C1–C5, H1–H6, H8, M1, M3, M4, M6, M9, M10, M11, M12, M13, L1, L2 were directly verified against the current code at spec time. The count of files using the forbidden import (FR-014) is 44, higher than the "20+" estimated in the source analysis.
- **L4 not reproduced**: The corrupted `REDIS_URL` template described in L4 could NOT be found — both `README.md` and `backend/.env.example` show the correct `REDIS_URL=redis://localhost:6379/0`. FR-031 is included but must be re-verified before any change is made.
- **Intended vs. dead infrastructure**: Celery and Redis are named in the constitution as part of the target architecture, so FR-027 treats them as "reserved future infrastructure" — the decision to implement minimal real usage vs. document as roadmap is left to implementation, but unused *runtime* deps that are not reserved must be removed.
- **Auth mechanism retained**: The existing JWT (HS256) approach from the constitution is retained; this spec hardens it (hashing, rate-limit, refresh/revocation, `aud`/`iss`) rather than replacing it.
- **Frontend design system**: A shared design-system token set already exists and is used by other pages; Reports (FR-019) and new pages (FR-021) adopt it.
- **RCA generation exists**: An LLM RCA generation route already exists; the gap (FR-016) is the missing correlation pipeline, not the LLM call itself.
- **Scope**: All 35 listed gaps are in scope for this feature, delivered as the prioritized, independently testable stories above. No gap is deferred without an explicit roadmap note.
- **Testing discipline**: Per constitution P2, new behavior ships with failing-first tests; Datadog-dependent tests remain skippable without credentials so CI stays green without secrets.
