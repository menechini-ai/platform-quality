.PHONY: install backend frontend dev db test lint safety clean \
        db-migrate db-migrate-dev db-migration db-rollback db-rollback-dev \
        up down build logs help

# ─── Install ──────────────────────────────────────────────────────

install: backend-install frontend-install

backend-install:
	cd backend && uv pip install -e ".[dev]"

frontend-install:
	cd frontend && npm install

# ─── Development ──────────────────────────────────────────────────

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev-db:
	docker compose up -d postgres redis

# ─── Database ─────────────────────────────────────────────────────

db-migrate:          ## Apply pending migrations (via Docker one-shot)
	docker compose run --rm migrate

db-migrate-dev:      ## Apply pending migrations (local, no Docker)
	cd backend && alembic upgrade head

db-migration:        ## Create new migration with MESSAGE="name"
	cd backend && alembic revision --autogenerate -m "$(message)"

db-rollback:         ## Rollback last migration
	cd backend && alembic downgrade -1

db-rollback-dev:     ## Rollback last migration (local, no Docker)
	cd backend && alembic downgrade -1

# ─── Docker ───────────────────────────────────────────────────────

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

# ─── Tests ────────────────────────────────────────────────────────

test:
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=term-missing

test-unit:
	cd backend && python -m pytest tests/ -v -m "not integration"

test-watch:
	cd backend && ptw -- --cov=app

# ─── Lint / Type Check ────────────────────────────────────────────

lint:
	cd backend && ruff check app/ tests/
	cd backend && ruff format --check app/ tests/

lint-fix:
	cd backend && ruff check --fix app/ tests/
	cd backend && ruff format app/ tests/

typecheck:
	cd backend && mypy app/

# ─── Safety ───────────────────────────────────────────────────────

safety:
	cd backend && uv pip list --format=json | uv audit --quiet || true

# ─── Clean ────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov

# ─── Help ─────────────────────────────────────────────────────────

help:
	@echo "ObservAI Development Commands"
	@echo "============================="
	@echo "make install         - Install all dependencies"
	@echo "make dev-backend     - Run backend (uvicorn reload)"
	@echo "make dev-frontend    - Run frontend (vite dev)"
	@echo "make dev-db          - Start PostgreSQL & Redis"
	@echo ""
	@echo "Database:"
	@echo "make db-migrate      - Apply migrations (Docker one-shot)"
	@echo "make db-migrate-dev  - Apply migrations (local, no Docker)"
	@echo "make db-migration    - Create new migration (MESSAGE=name)"
	@echo "make db-rollback     - Rollback last migration"
	@echo ""
	@echo "Quality:"
	@echo "make test            - Run all tests with coverage"
	@echo "make lint            - Run ruff linter"
	@echo "make typecheck       - Run mypy type checker"
	@echo "make safety          - Run uv audit"
	@echo ""
	@echo "Docker:"
	@echo "make up              - Full stack via Docker Compose"
	@echo "make down            - Stop Docker Compose"
