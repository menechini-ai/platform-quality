# ObservAI

> Open-source observability platform powered by the Datadog API for incident analysis, RCA (Root Cause Analysis), product health monitoring, SLO tracking, and self-healing automation.

ObservAI unifies your Datadog telemetry — metrics, logs, traces, monitors, SLOs, and incidents — behind a single FastAPI backend and a React dashboard, and adds higher-level capabilities: automated RCA, a maturity assessment engine, a runbook-driven self-healing workflow with human approval, and a knowledge base of recurring failure patterns.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start (Local Dev)](#quick-start-local-dev)
- [Environment Variables](#environment-variables)
- [Running with Docker](#running-with-docker)
- [API Reference](#api-reference)
- [Authentication](#authentication)
- [Testing](#testing)
- [Code Quality & Pre-commit](#code-quality--pre-commit)
- [CI/CD](#cicd)
- [Git Workflow (Gitflow)](#git-workflow-gitflow)
- [Makefile Cheatsheet](#makefile-cheatsheet)
- [License](#license)

---

## Features

- **🔍 Incident Management** — Import, track, and manage incidents with full per-incident timelines (events, status changes, notes). Write operations are protected by JWT auth.
- **🔬 RCA Engine** — Generate root-cause analysis reports that correlate metrics, logs, and traces for a given incident.
- **💚 Product Health & SLOs** — Health snapshots, summary, service catalog, stats, and forecasting; SLO/SLI definition and tracking with burn-rate context.
- **📊 Maturity Assessment** — Scores SRE observability maturity (Levels 0–5) across 8 dimensions by querying Datadog, with gap analysis and a levels reference.
- **🛠️ Self-Healing** — Runbook automation with a human-in-the-loop approval workflow: proposed auto-heal actions are approved or rejected before execution.
- **🤖 Knowledge Base** — Store RCA patterns (with a seed endpoint) for similarity matching and faster future diagnosis.
- **🧪 Analysis** — One-shot analysis endpoints for health, incidents, RCA, and self-healing that compose the underlying engines.
- **📡 Datadog Proxy** — A unified, typed API surface over Datadog: APM/services, error tracking, events, fleet, incidents, logs, metrics, monitors, RUM, SLOs, and synthetics — so the frontend never talks to Datadog directly.
- **📄 Reports** — Generate reports and automated postmortems from incidents.
- **🔐 Authentication** — JWT (HS256) login with a protected `/me` endpoint and route-level protection on incident mutations.

---

## Architecture

```
┌─────────────────────────────┐         ┌──────────────────────────────────┐
│   Frontend (React + Vite)   │  REST   │        Backend (FastAPI)          │
│   TypeScript + TanStack Q   │ ──────▶ │  /api/v1  (JWT-protected writes)  │
│   Port 3000 (nginx in prod) │ ◀────── │                                  │
└─────────────────────────────┘  JSON   │  auth · incidents · rca · health │
                                         │  self_healing · maturity · kb    │
                                         │  analysis · reports · datadog_*  │
                                         └───────────┬───────────┬──────────┘
                                                asyncpg│          │redis
                                                     ▼          ▼
                                            ┌────────────┐  ┌────────┐
                                            │ PostgreSQL │  │ Redis  │
                                            │   16       │  └────────┘
                                            └────────────┘
                                                     │
                                            Alembic migrations

        Backend also proxies to the Datadog API (metrics / logs / traces /
        monitors / SLOs / incidents / APM / RUM / synthetics / events).
```

**Request flow:** the React SPA calls `/api/v1/*`. Public reads work without auth; incident write operations and `/me` require a `Bearer` JWT. The backend uses the official `datadog-api-client` to fetch telemetry server-side (so Datadog credentials never reach the browser) and stores domain data (incidents, RCA reports, runbooks, maturity assessments, knowledge base, health snapshots) in PostgreSQL via SQLAlchemy 2.0 async, with Redis available for caching/queues.

---

## Tech Stack

| Layer        | Technology                                                                 |
|--------------|----------------------------------------------------------------------------|
| **Backend**  | Python ≥3.11 (CI on 3.12), FastAPI, Uvicorn, SQLAlchemy 2.0 (async), asyncpg, Alembic, Pydantic v2 |
| **Auth**     | `python-jose[cryptography]` (JWT HS256), `passlib[bcrypt]`                |
| **Datadog**  | `datadog-api-client`, `httpx`                                              |
| **Cache/Queue** | Redis                                                                     |
| **Frontend** | React 18, TypeScript 5.6, Vite 6, Tailwind CSS 3, React Router 6, TanStack Query 5, Recharts 2, lucide-react |
| **Frontend tests** | Vitest 4, React Testing Library, jsdom, ESLint 10                      |
| **Backend tests**  | pytest, pytest-asyncio                                                  |
| **Quality**  | Ruff, Ruff format, Pyright, Vulture (min-confidence 65), Gitleaks, pre-commit |
| **Infra**    | Docker, Docker Compose, PostgreSQL 16, Redis 7, Nginx (static serving), GHCR |
| **CI/CD**    | GitHub Actions                                                            |

---

## Project Structure

```
platform-quality/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory (routers, CORS, lifespan)
│   │   ├── core/                    # Config (pydantic-settings), DB session, models, schemas
│   │   ├── auth/                    # JWT login + get_current_user dependency
│   │   ├── incidents/               # Incident management + timelines
│   │   ├── rca/                     # Root Cause Analysis engine
│   │   ├── health/                  # Health snapshots, SLOs, stats, forecast
│   │   ├── self_healing/            # Runbooks + auto-heal actions (approval workflow)
│   │   ├── maturity/                # Maturity assessment engine + reports
│   │   ├── knowledge_base/          # RCA pattern store
│   │   ├── analysis/                # Composed analysis endpoints
│   │   ├── datadog/                 # Datadog API client wrapper (singleton)
│   │   └── datadog_routes/          # Per-domain Datadog proxy routers
│   ├── alembic/                     # DB migrations
│   ├── tests/                       # pytest suite (incl. datadog-marked tests)
│   ├── Dockerfile                   # Multi-stage, non-root (user `observai`)
│   └── pyproject.toml               # deps + ruff/pyright/vulture config
├── frontend/
│   ├── src/
│   │   ├── main.tsx                 # Entry point
│   │   ├── App.tsx                  # Routes (React Router)
│   │   ├── api/                     # API client + React Query hooks (client.ts, client.test.tsx)
│   │   ├── components/              # Pages + shared UI (Layout, ui/Sparkline, TagFilter, …)
│   │   └── test/                    # Shared test setup
│   ├── Dockerfile                   # Multi-stage node:20 → nginx:alpine
│   ├── nginx.conf                   # Static serving + immutable asset cache headers
│   └── vite.config.ts / vitest.config.ts
├── docker-compose.yml               # Dev stack (postgres, redis, migrate, backend, frontend)
├── docker-compose.prod.yml          # Prod stack (restart policies, mem/cpu limits, healthchecks)
├── .github/workflows/ci.yml         # CI (backend, frontend, docker→GHCR on main)
├── .pre-commit-config.yaml          # ruff, pyright, gitleaks, vulture, eslint, tsc, pytest, vitest
├── Makefile                         # Dev/test/lint/db shortcuts
└── README.md
```

---

## Prerequisites

- Python **≥ 3.11** (tested on 3.12)
- Node.js **20+**
- Docker & Docker Compose (for containerized runs)
- A Datadog **API Key + Application Key** (optional for UI browse; required for live telemetry)
- [`uv`](https://github.com/astral-sh/uv) for backend dependency management

---

## Quick Start (Local Dev)

```bash
# 1. Clone
git clone https://github.com/menechini-ai/platform-quality.git
cd platform-quality

# 2. Start infrastructure (Postgres + Redis) via Docker
make dev-db            # ≡ docker compose up -d postgres redis

# 3. Backend
cd backend
cp .env.example .env   # fill DATADOG_API_KEY / DATADOG_APP_KEY (optional) + a real SECRET_KEY
uv pip install -e ".[dev]"
alembic upgrade head                       # apply migrations
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. Frontend (new terminal)
cd ../frontend
npm install
npm run dev            # http://localhost:5173 (Vite dev server)
```

If you prefer Make targets instead of manual steps:

```bash
make install           # install backend + frontend deps
make dev-backend       # uvicorn with reload
make dev-frontend      # vite dev server
make db-migrate-dev    # alembic upgrade head (local, no Docker)
```

Once running, the interactive OpenAPI docs are at **http://localhost:8000/docs**.

---

## Environment Variables

Configure `backend/.env` (see `backend/.env.example`). All variables are read by `app/core/config.py` via pydantic-settings.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://observai:observai@localhost:5432/observai` | Async SQLAlchemy DB URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `DATADOG_API_KEY` | _(empty)_ | Datadog API key (enables live telemetry) |
| `DATADOG_APP_KEY` | _(empty)_ | Datadog Application key |
| `DATADOG_SITE` | `datadoghq.com` | Datadog site (e.g. `us5.datadoghq.com`) |
| `SECRET_KEY` | `change-me-in-production` | **Required in prod (≥ 32 chars).** Signs JWTs |
| `ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT lifetime |
| `API_V1_PREFIX` | `/api/v1` | API route prefix |
| `CORS_ORIGINS` | `["http://localhost:5173","http://localhost:3000"]` | Allowed CORS origins (JSON) |
| `DEBUG` | `true` | Debug mode |
| `SELF_HEALING_ENABLED` | `true` | Enable self-healing actions |
| `SELF_HEALING_APPROVAL_REQUIRED` | `true` | Require human approval before executing actions |

> Without `DATADOG_API_KEY`/`DATADOG_APP_KEY`, Datadog-dependent features degrade gracefully (endpoints return empty/zeroed data rather than erroring).

---

## Running with Docker

### Development stack

```bash
docker compose up -d          # postgres, redis, migrate, backend (:8000), frontend (:3000)
docker compose logs -f        # follow logs
docker compose down           # stop & remove
```

- `backend` healthcheck hits `GET /api/v1/health`.
- `frontend` is served by Vite's dev server (hot reload) and talks to the backend via `VITE_API_URL`.

### Production stack

`docker-compose.prod.yml` hardens the same services with `restart: unless-stopped`, memory/CPU limits, required `POSTGRES_PASSWORD` (via env), and healthchecks:

```bash
export POSTGRES_PASSWORD=<strong-password>
docker compose -f docker-compose.prod.yml up -d
```

The frontend image is a multi-stage build (`node:20-alpine` → `nginx:alpine`) that serves the static bundle on port **3000**, with `nginx.conf` setting `Cache-Control: public, immutable` on hashed assets.

---

## API Reference

All endpoints are prefixed with `/api/v1` unless noted. The root `GET /health` is a plain liveness probe.

### Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/login` | 🔓 | Exchange credentials for a JWT (`access_token`) |
| `GET`  | `/api/v1/me` | 🔒 | Return the current authenticated user |

🔒 = requires `Authorization: Bearer <token>`.

### Incidents

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET`  | `/api/v1/incidents` | 🔓 | List incidents |
| `GET`  | `/api/v1/incidents/summary` | 🔓 | Incident summary stats |
| `GET`  | `/api/v1/incidents/{id}` | 🔓 | Get one incident + timeline |
| `POST` | `/api/v1/incidents` | 🔒 | Create incident |
| `PATCH`| `/api/v1/incidents/{id}` | 🔒 | Update incident |
| `DELETE`| `/api/v1/incidents/{id}` | 🔒 | Delete incident |

### RCA / Analysis / Reports

| Method | Path | Description |
|--------|------|-------------|
| `GET`/`POST` | `/api/v1/rca`, `/api/v1/rca/{id}` | Root-cause analysis reports |
| `GET`/`POST` | `/api/v1/analysis`, `/api/v1/analysis/{id}` | Analysis results |
| `POST` | `/api/v1/analysis/health`, `/analysis/incident/{id}`, `/analysis/rca/{id}`, `/analysis/self-healing` | One-shot composed analysis |
| `GET`/`POST` | `/api/v1/reports`, `/api/v1/reports/{id}` | Reports |
| `POST` | `/api/v1/reports/postmortem/{incident_id}` | Auto-generated postmortem |

### Health & SLOs

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Liveness / latest health snapshots |
| `GET` | `/api/v1/readyz` | Readiness (DB + config) probe |
| `GET` | `/api/v1/health/snapshots`, `/summary`, `/catalog`, `/stats`, `/forecast` | Health detail views |
| `GET`/`POST` | `/api/v1/slos` | List / create SLOs |

### Self-Healing

| Method | Path | Description |
|--------|------|-------------|
| `GET`/`POST` | `/api/v1/runbooks`, `/api/v1/runbooks/{id}` | Runbook library |
| `GET` | `/api/v1/actions` | Pending auto-heal actions |
| `POST` | `/api/v1/actions/{id}/approve` | Approve an action |
| `POST` | `/api/v1/actions/{id}/reject` | Reject an action |

### Maturity & Knowledge Base

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/maturity`, `/api/v1/maturity/latest` | Assessments |
| `POST` | `/api/v1/maturity/assess` | Run a new assessment (queries Datadog) |
| `GET` | `/api/v1/maturity/gap?current=&target=` | Gap analysis |
| `GET` | `/api/v1/maturity/levels` | Level definitions |
| `GET`/`POST` | `/api/v1/kb`, `/api/v1/kb/{id}` | Knowledge base entries |
| `POST` | `/api/v1/kb/seed` | Seed default patterns |

### Datadog Proxy (server-side)

All proxy the official Datadog client; the browser never holds Datadog keys.

| Domain | Example endpoints |
|--------|-------------------|
| APM | `/api/v1/datadog/apm/services`, `/.../services/{name}/definition`, `/.../dependencies`, `/.../spans` |
| Error Tracking | `/api/v1/datadog/error-tracking/trackers`, `/.../trackers/{id}`, `POST /.../events` |
| Events | `/api/v1/datadog/events` (GET/POST), `/.../events/{id}` (GET/PUT/DELETE) |
| Fleet | `/api/v1/datadog/fleet/agents`, `/.../agents/{id}` |
| Incidents | `/api/v1/datadog/incidents` (GET/POST), `/.../incidents/{id}`, `/.../incidents/search` |
| Logs | `/api/v1/datadog/logs` (GET/POST), `/.../logs/aggregate` |
| Metrics | `/api/v1/datadog/metrics`, `/.../metrics/metadata`, `/.../metrics/list`, `/.../metrics/{name}/fields`, `/.../metrics/{name}/values` |
| Monitors | `/api/v1/datadog/monitors` (GET/POST), `/.../monitors/{id}`, `/.../monitors/search`, `/.../monitors/groups/{id}` |
| RUM | `/api/v1/datadog/rum` |
| SLOs | `/api/v1/datadog/slos` (GET/POST), `/.../slos/corrections`, `/.../slos/{id}/history` |
| Synthetics | `/api/v1/datadog/synthetics`, `/.../synthetics/{id}/results`, `/.../synthetics/browser/{id}/results` |

> See the live docs at `/docs` for full request/response schemas (generated from Pydantic models).

---

## Authentication

ObservAI uses **JWT (HS256)** signed with `SECRET_KEY`.

1. `POST /api/v1/login` with credentials → returns `{ "access_token": "...", "token_type": "bearer" }`.
2. Send the token on protected requests: `Authorization: Bearer <access_token>`.
3. `GET /api/v1/me` returns the authenticated user. Incident **write** operations (`POST`/`PATCH`/`DELETE` on `/incidents`) and `/me` are protected via the `get_current_user` dependency; reads remain public.

Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30). Set a strong `SECRET_KEY` (≥ 32 chars) in production — the app validates this at startup.

---

## Testing

### Backend (pytest)

```bash
cd backend
pytest tests/ -m "not datadog"          # unit tests, skips Datadog-dependent tests
pytest tests/ -m "not datadog" --cov=app --cov-report=term-missing
```

Tests under `tests/test_datadog_routes/` (and `tests/test_datadog/`) are auto-marked `@pytest.mark.datadog` and **skipped** unless `DD_API_KEY` + `DD_APP_KEY` are set, so the suite runs green without credentials.

### Frontend (Vitest)

```bash
cd frontend
npm test                                # ≡ vitest run
npm run test:watch                      # watch mode
```

Covers the API client (`client.test.tsx`), component smoke tests (`components.smoke.test.tsx`), the `DashboardPage`, and the `TagFilter` component.

---

## Code Quality & Pre-commit

Pre-commit runs a battery of hooks on every commit:

| Hook | Scope | Notes |
|------|-------|-------|
| `ruff` / `ruff-format` | backend | Lint + format (B008 ignored for `Depends`) |
| `pyright` | backend | Static type checking (`backend/pyrightconfig.json`) |
| `gitleaks` | all | Secret detection |
| `vulture` | backend | Dead-code detection (min-confidence 65) |
| `eslint` | frontend | Lint |
| `tsc` | frontend | TypeScript type check (`--noEmit`) |
| `pytest` | backend | Full test suite |
| `vitest` | frontend | Test suite |

```bash
pre-commit install     # enable hooks (one-time)
pre-commit run --all-files
```

---

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on pushes/PRs to `develop` and `main`:

- **backend** job — `uv` venv, `ruff`, `pyright`, `pytest -m "not datadog"`.
- **frontend** job — `npm ci`, ESLint, `tsc --noEmit`, Vitest, production build.
- **docker** job — **only on `main`** — builds and pushes backend + frontend images to **GHCR** (`ghcr.io/menechini-ai/...`).

---

## Git Workflow (Gitflow)

- Feature/fix branches branch off `develop`.
- Open PRs **against `develop`** (not `main`).
- Promotion to `main` happens via a `develop → main` release PR, which triggers the Docker build/push to GHCR.

Example: a feature branch `feature/tdd-complete` → PR to `develop`; once merged, a `develop → main` PR ships it.

---

## Makefile Cheatsheet

| Command | What it does |
|---------|--------------|
| `make install` | Install backend + frontend deps |
| `make dev-backend` / `make dev-frontend` | Run servers with hot reload |
| `make dev-db` | Start Postgres + Redis via Docker |
| `make db-migrate-dev` | `alembic upgrade head` (local) |
| `make db-migration MESSAGE="x"` | Autogenerate a migration |
| `make db-rollback` | Rollback last migration |
| `make test` / `make test-unit` | pytest (all / non-integration) |
| `make lint` / `make lint-fix` | Ruff check/format |
| `make typecheck` | `mypy app/` |
| `make up` / `make down` / `make build` / `make logs` | Docker Compose control |
| `make clean` | Remove caches (`__pycache__`, `.ruff_cache`, `node_modules`, …) |

---

## License

MIT
