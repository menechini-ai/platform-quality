#!/usr/bin/env bash
# Smoke tests for api-demo — verifies CLI entry points are functional.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
FAIL=0

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }

run_test() {
    local name="$1" cmd="$2"
    printf "  [SMOKE] %-45s … " "$name"
    if eval "$cmd" > /dev/null 2>&1; then
        green "PASS"
    else
        red "FAIL"
        FAIL=1
    fi
}

run_test "litellm_client --help"    "uv run --directory '$DIR' python -m agents.litellm_client --help"
run_test "langgraph_pipeline --help" "uv run --directory '$DIR' python -m agents.langgraph_pipeline --help"
run_test "mcp_server --help"        "uv run --directory '$DIR' python -m agents.mcp_server --help"
run_test "tool_budget --help"       "uv run --directory '$DIR' python -m agents.tool_budget --help"
run_test "synthetic_rca --help"     "uv run --directory '$DIR' python -m agents.synthetic_rca --help"
run_test "pytest collect"           "uv run --directory '$DIR' --extra dev python -m pytest '$DIR/tests/' --collect-only -q"
run_test "import embeddings"        "uv run --directory '$DIR' python -c 'from lib.embeddings import embed_text, cosine_similarity'"
run_test "import vectordb"          "uv run --directory '$DIR' python -c 'from lib.vectordb import VectorStore'"
run_test "import litellm_client"    "uv run --directory '$DIR' python -c 'from agents.litellm_client import LiteLLMClient, llm_complete'"
run_test "import langgraph_pipeline" "uv run --directory '$DIR' python -c 'from agents.langgraph_pipeline import build_pipeline, run_pipeline'"
run_test "import dual_llm"          "uv run --directory '$DIR' python -c 'from agents.dual_llm import get_reasoning_model, get_tool_model'"
run_test "import streaming"         "uv run --directory '$DIR' python -c 'from agents.streaming_handler import format_sse, stream_pipeline'"
run_test "import mcp_server"        "uv run --directory '$DIR' python -c 'from agents.mcp_server import list_tools, call_tool, handle_request'"
run_test "import tool_budget"       "uv run --directory '$DIR' python -c 'from agents.tool_budget import ToolBudget'"
run_test "import langfuse"          "uv run --directory '$DIR' python -c 'from agents.langfuse import LangfuseTracer'"
run_test "import synthetic_rca"     "uv run --directory '$DIR' python -c 'from agents.synthetic_rca import evaluate_pipeline, load_incidents'"
run_test "import ai_self_healing"   "uv run --directory '$DIR' python -c 'from agents.ai_self_healing import AISelfHealing'"

echo ""
if [ "$FAIL" -eq 0 ]; then
    green "All smoke tests PASSED"
else
    red "Some smoke tests FAILED"
    exit 1
fi
