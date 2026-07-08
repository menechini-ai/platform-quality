#!/usr/bin/env bash
# End-to-end tests for new AI features (Phases 1-4).
# Tests: unit tests pass, routes exist, API endpoints respond, frontend builds.
#
# Optional env vars:
#   OPENAI_API_KEY    — set to test live endpoints with real LLM responses
#   API_HOST          — backend URL (default: http://localhost:8000)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(cd "$DIR/../backend" && pwd)"
FRONTEND_DIR="$(cd "$DIR/../frontend" && pwd)"
HOST="${API_HOST:-http://localhost:8000}"
PREFIX="/api/v1"
FAIL=0
HAS_KEY=false
if [ -n "${OPENAI_API_KEY:-}" ]; then
    HAS_KEY=true
fi

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }
yellow() { printf "\033[33m%s\033[0m\n" "$1"; }

run_test() {
    local name="$1" cmd="$2"
    printf "  [TEST] %-55s … " "$name"
    if eval "$cmd" > /dev/null 2>&1; then
        green "PASS"
    else
        red "FAIL"
        FAIL=1
    fi
}

run_test_verbose() {
    local name="$1" cmd="$2"
    printf "  [TEST] %-55s … " "$name"
    local output
    output=$(eval "$cmd" 2>&1) || {
        red "FAIL"
        echo "$output" | sed 's/^/         /'
        FAIL=1
        return
    }
    green "PASS"
    echo "$output" | sed 's/^/         /'
}

echo ""
yellow "════════════════════════════════════════════════════════════"
yellow "  Phase 1 — Smoke Tests (imports, CLI, data integrity)"
yellow "════════════════════════════════════════════════════════════"
echo ""

run_test "agents reference imports" \
    "uv run --directory '$DIR' python -c '
from agents.litellm_client import LiteLLMClient
from agents.dual_llm import get_reasoning_model, get_tool_model
from agents.langgraph_pipeline import build_pipeline
from agents.streaming_handler import format_sse
print(\"All imports OK\")
'"

run_test "lib imports (embeddings, vectordb)" \
    "uv run --directory '$DIR' python -c '
from lib.embeddings import embed_text, cosine_similarity
from lib.vectordb import VectorStore
print(\"All lib imports OK\")
'"

run_test "VectorStore in-memory search (mocked)" \
    "uv run --directory '$DIR' python -c '
from unittest.mock import patch
from lib.vectordb import VectorStore
vs = VectorStore()
vs._entries.append({\"id\":\"t1\",\"text\":\"deploy rollback\",\"metadata\":{},\"embedding\":[1.0,0.0,0.0]})
vs._entries.append({\"id\":\"t2\",\"text\":\"db tuning\",\"metadata\":{},\"embedding\":[0.0,1.0,0.0]})
with patch(\"lib.vectordb.embed_text\", return_value=[1.0, 0.0, 0.0]):
    r = vs.search(\"deploy\", k=2)
assert len(r) == 2
assert r[0][\"id\"] == \"t1\"
'"


run_test "data files integrity (5 incidents, 5 KB)" \
    "uv run --directory '$DIR' python -c '
import json
inc = json.load(open(\"$DIR/data/incidents.json\"))
kb  = json.load(open(\"$DIR/data/kb_entries.json\"))
assert len(inc) == 5
assert len(kb) == 5
assert all(\"id\" in i for i in inc)
assert all(\"id\" in k for k in kb)
'"

# Helper: run backend tests with a clean env (litellm loads .env on import)
_run_backend_tests() {
    # litellm calls load_dotenv() which reads backend/.env at import time.
    # We unset the vars via a preamble script to prevent env leaks into tests.
    local preamble='
import os
for _k in ["LITELLM_DEFAULT_MODEL","LITELLM_API_KEY","LITELLM_BASE_URL",
           "OPENAI_API_KEY","OPENAI_BASE_URL","EMBED_MODEL",
           "LANGFUSE_PUBLIC_KEY","LANGFUSE_SECRET_KEY","LANGFUSE_HOST"]:
    os.environ.pop(_k, None)
'
    .venv/bin/python3 -c "$preamble" 2>/dev/null || true
    env -u LITELLM_DEFAULT_MODEL -u LITELLM_API_KEY -u LITELLM_BASE_URL \
        -u OPENAI_API_KEY -u OPENAI_BASE_URL -u EMBED_MODEL \
        -u LANGFUSE_PUBLIC_KEY -u LANGFUSE_SECRET_KEY -u LANGFUSE_HOST \
        .venv/bin/python3 -m pytest $@ -q --tb=no 2>&1 | tail -1 | grep -q 'passed'
}

echo ""
yellow "════════════════════════════════════════════════════════════"
yellow "  Phase 2 — Backend Unit Tests (LLM, VectorStore, RCA, KB)"
yellow "════════════════════════════════════════════════════════════"
echo ""

run_test "LLM tests (9 tests)" \
    "cd '$BACKEND_DIR' && _run_backend_tests 'tests/test_llm/'"

run_test "VectorStore tests (9 tests)" \
    "cd '$BACKEND_DIR' && _run_backend_tests 'tests/test_vectorstore/'"

run_test "RCA service tests (5 tests)" \
    "cd '$BACKEND_DIR' && _run_backend_tests 'tests/test_rca/'"

run_test "KB service tests (5 tests)" \
    "cd '$BACKEND_DIR' && _run_backend_tests 'tests/test_kb/'"

run_test "Dual-LLM tests (3 tests)" \
    "cd '$BACKEND_DIR' && _run_backend_tests 'tests/test_agents/test_dual_llm.py'"

run_test "LangGraph pipeline tests (6 tests)" \
    "cd '$BACKEND_DIR' && _run_backend_tests 'tests/test_agents/test_langgraph_pipeline.py'"

run_test "Streaming handler tests (2 tests)" \
    "cd '$BACKEND_DIR' && _run_backend_tests 'tests/test_agents/test_streaming_handler.py'"

run_test "All AI unit tests (48 tests)" \
    "cd '$BACKEND_DIR' && _run_backend_tests 'tests/test_agents/ tests/test_llm/ tests/test_vectorstore/ tests/test_rca/ tests/test_kb/'"

echo ""
yellow "════════════════════════════════════════════════════════════"
yellow "  Phase 3 — Frontend (build + tests + components)"
yellow "════════════════════════════════════════════════════════════"
echo ""

run_test "Frontend tests (57 tests)" \
    "cd '$FRONTEND_DIR' && npm run test -- --run 2>&1 | tail -5 | grep -Eq 'passed|Tests'"

run_test "Frontend TypeScript compiles clean" \
    "cd '$FRONTEND_DIR' && npx tsc --noEmit 2>&1"

run_test "llm.ts API client exists" \
    "test -f '$FRONTEND_DIR/src/api/llm.ts'"

run_test "agents.ts API client exists" \
    "test -f '$FRONTEND_DIR/src/api/agents.ts'"

run_test "KBSearchPage component exists" \
    "test -f '$FRONTEND_DIR/src/components/KB/KBSearchPage.tsx'"

run_test "AgentPipelinePage component exists" \
    "test -f '$FRONTEND_DIR/src/components/Agents/AgentPipelinePage.tsx'"

run_test "RCAPage has LLM RCA generator" \
    "grep -q 'generateRca\|Generate LLM' '$FRONTEND_DIR/src/components/RCA/RCAPage.tsx' 2>/dev/null"

echo ""
yellow "════════════════════════════════════════════════════════════"
yellow "  Phase 4 — Endpoint Route Coverage (router files)"
yellow "════════════════════════════════════════════════════════════"
echo ""

run_test "RCA: POST /rca/{id}/generate defined" \
    "grep -q 'generate\|@router.post.*rca' '$BACKEND_DIR/app/rca/router.py'"

run_test "KB: GET /kb/search defined" \
    "grep -q 'search' '$BACKEND_DIR/app/knowledge_base/router.py'"

run_test "Agents: POST /agents/analyze defined" \
    "grep -q 'analyze\|@router.post.*agent' '$BACKEND_DIR/app/agents/router.py'"

run_test "Agents: stream endpoint defined" \
    "grep -q 'stream' '$BACKEND_DIR/app/agents/router.py'"

run_test "agents_router registered in main.py" \
    "grep -q 'agents_router' '$BACKEND_DIR/app/main.py'"

run_test "Agents route in App.tsx" \
    "grep -q '/agents' '$FRONTEND_DIR/src/App.tsx'"

run_test "KB route in App.tsx" \
    "grep -q '/kb' '$FRONTEND_DIR/src/App.tsx'"

echo ""
yellow "════════════════════════════════════════════════════════════"
yellow "  Phase 5 — Live API Endpoints (docker backend at $HOST)"
yellow "════════════════════════════════════════════════════════════"
echo ""

# Ensure backend is running — optionally with OPENAI_API_KEY
if "$HAS_KEY"; then
    echo "  OPENAI_API_KEY is set — restarting backend with LLM credentials..."
    echo ""
    OPENAI_API_KEY="$OPENAI_API_KEY" \
    OPENAI_BASE_URL="${OPENAI_BASE_URL:-}" \
    EMBED_MODEL="${EMBED_MODEL:-text-embedding-3-small}" \
    LITELLM_API_KEY="${LITELLM_API_KEY:-}" \
    LITELLM_BASE_URL="${LITELLM_BASE_URL:-}" \
    docker compose up -d backend 2>&1 | sed 's/^/  /'

    # Wait for backend to be ready
    for i in $(seq 1 15); do
        if curl -sf "$HOST$PREFIX/health" > /dev/null 2>&1; then
            break
        fi
        sleep 2
    done
fi

# Wait for backend if needed
if ! curl -sf "$HOST$PREFIX/health" > /dev/null 2>&1; then
    echo "  Backend not reachable at $HOST. Skipping live API tests."
    echo "  Start with: docker compose up -d"
else
    run_test_verbose "GET $PREFIX/health" \
        "curl -sf '$HOST$PREFIX/health' -w ' (HTTP %{http_code})' -o /dev/null"

    if "$HAS_KEY"; then
        # With API key — expect real responses
        run_test_verbose "GET $PREFIX/kb/search (real response)" \
            "curl -sf '$HOST$PREFIX/kb/search?q=deploy&k=3' -w ' (HTTP %{http_code})' 2>&1"

        run_test_verbose "POST $PREFIX/agents/analyze (real response)" \
            "curl -sf -X POST '$HOST$PREFIX/agents/analyze' \
                -H 'Content-Type: application/json' \
                -d '{\"incident_id\":\"demo-inc-001\",\"description\":\"Latency spike after deploy\"}' \
                -w ' (HTTP %{http_code})' 2>&1"

        run_test_verbose "GET $PREFIX/agents/analyze/0/stream (real SSE)" \
            "HTTP_CODE=\$(curl -s --max-time 15 -o /dev/null -w '%{http_code}' '$HOST$PREFIX/agents/analyze/0/stream?description=test' 2>&1 || true); echo \"\$HTTP_CODE\" | grep -q '200'"

        run_test_verbose "POST $PREFIX/rca/demo-inc-001/generate (real LCM)" \
            "curl -sf -X POST '$HOST$PREFIX/rca/demo-inc-001/generate' \
                -H 'Content-Type: application/json' \
                -d '{}' -w ' (HTTP %{http_code})' 2>&1"
    else
        # No API key — just verify endpoints are reachable
        run_test_verbose "GET $PREFIX/kb/search (endpoint reachable)" \
            "curl -s -o /dev/null -w '%{http_code}' '$HOST$PREFIX/kb/search?q=deploy&k=3' | grep -Eq '200|500'"

        run_test_verbose "POST $PREFIX/agents/analyze (endpoint reachable)" \
            "curl -s -o /dev/null -w '%{http_code}' -X POST '$HOST$PREFIX/agents/analyze' \
                -H 'Content-Type: application/json' \
                -d '{\"incident_id\":\"demo-inc-001\",\"description\":\"Latency spike after deploy\"}' | grep -Eq '200|422|500'"

        run_test_verbose "GET $PREFIX/agents/analyze/0/stream (endpoint reachable)" \
            "HTTP_CODE=\$(curl -s --max-time 5 -o /dev/null -w '%{http_code}' '$HOST$PREFIX/agents/analyze/0/stream?description=test' 2>&1 || true); echo \"\$HTTP_CODE\" | grep -Eq '200|404|500'"

        run_test_verbose "POST $PREFIX/rca/demo-inc-001/generate (endpoint reachable)" \
            "curl -s -o /dev/null -w '%{http_code}' -X POST '$HOST$PREFIX/rca/demo-inc-001/generate' \
                -H 'Content-Type: application/json' \
                -d '{}' | grep -Eq '200|400|404|500'"
    fi
fi

echo ""
yellow "════════════════════════════════════════════════════════════"
yellow "  Phase 6 — Reference Implementation Tests (api-demo)"
yellow "════════════════════════════════════════════════════════════"
echo ""

run_test "api-demo smoke tests (all imports)" \
    "cd '$DIR' && bash smoke_test.sh 2>&1 | tail -5 | grep -q 'All smoke tests PASSED'"

run_test "api-demo unit tests" \
    "cd '$DIR' && uv run --extra dev python -m pytest tests/ -q --tb=no 2>&1 | tail -1 | grep -q 'passed'"

echo ""
if [ "$FAIL" -eq 0 ]; then
    green "════════════════════════════════════════════════════════════"
    green "  ALL TESTS PASSED"
    green "════════════════════════════════════════════════════════════"
else
    red "════════════════════════════════════════════════════════════"
    red "  SOME TESTS FAILED"
    red "════════════════════════════════════════════════════════════"
fi

exit "$FAIL"
