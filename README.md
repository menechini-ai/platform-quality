# ObservAI

Open-source observability platform powered by Datadog API for incident analysis, RCA (Root Cause Analysis), product health monitoring, and self-healing automation.

## Architecture

```
Frontend (React + Vite + TypeScript)
    ↕ REST + WebSocket
Backend (FastAPI + Python)
    ↕ asyncpg
PostgreSQL
```

## Features

- **🔍 Incident Analysis** — Import and manage incidents from Datadog with full timeline tracking
- **🔬 RCA Engine** — Automatic root cause analysis correlating metrics, logs, and traces
- **💚 Product Health** — SLO/SLI tracking, burn-rate alerts, health score compositing
- **🛠️ Self-Healing** — Runbook automation with approval workflows for remediation actions
- **🤖 Knowledge Base** — Store RCA patterns with similarity matching for faster future diagnosis

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Datadog API Key + Application Key

### Setup

```bash
# Clone and enter the project
cd observai

# Backend
cd backend
cp .env.example .env  # Set your Datadog API keys
uv pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (new terminal)
cd ../frontend
npm install
npm run dev
```

### Docker Compose (full stack)

```bash
docker compose up -d
```

## API Documentation

Once running, visit `http://localhost:8000/docs` for the interactive OpenAPI docs.

## Project Structure

```
observai/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory
│   │   ├── core/                    # Config, DB, models, schemas
│   │   ├── datadog/                 # Datadog API client wrapper
│   │   ├── incidents/               # Incident management
│   │   ├── rca/                     # Root Cause Analysis
│   │   ├── health/                  # Health & SLO tracking
│   │   └── self_healing/           # Runbooks & auto-heal actions
│   ├── alembic/                     # DB migrations
│   └── tests/                       # Test suite
├── frontend/
│   └── src/
│       ├── components/              # React components
│       ├── api/                     # API client
│       ├── hooks/                   # Custom hooks
│       ├── types/                   # TypeScript types
│       └── utils/                   # Utilities
├── docker-compose.yml
├── Makefile
└── README.md
```

## License

MIT
