#!/usr/bin/env bash
# Real-environment test runner using api-demo to seed data and run RCA tests
# Usage: bash api-demo/test_real_env.sh
# Requires: DD_API_KEY, DD_APP_KEY environment variables

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"

# Colors
green()  { printf "\033[32m%s\033[0m\n" "$1"; }
yellow() { printf "\033[33m%s\033[0m\n" "$1"; }
red()    { printf "\033[31m%s\033[0m\n" "$1"; }
dim()    { printf "\033[2m%s\033[0m\n" "$1"; }

# Load keys from backend/.env if not set
if [ -z "${DD_API_KEY:-}" ] && [ -f "$ROOT/backend/.env" ]; then
    DD_API_KEY=$(grep '^DATADOG_API_KEY=' "$ROOT/backend/.env" | cut -d'=' -f2 | tr -d '"' | head -1)
    DD_APP_KEY=$(grep '^DATADOG_APP_KEY=' "$ROOT/backend/.env" | cut -d'=' -f2 | tr -d '"' | head -1)
    export DD_API_KEY DD_APP_KEY
fi

if [ -z "${DD_API_KEY:-}" ] || [ -z "${DD_APP_KEY:-}" ]; then
    red "ERROR: DD_API_KEY and DD_APP_KEY must be set"
    echo "  export DD_API_KEY=*** DD_APP_KEY=yyy"
    echo "  Or add to backend/.env"
    exit 1
fi

SITE="${DD_SITE:-us5.datadoghq.com}"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ObservAI Real-Environment Test Runner"
echo "  Site: $SITE"
echo "════════════════════════════════════════════════════════════"
echo ""

# Step 1: Seed test data
echo "🌱 Step 1: Seeding test data..."
uv run --directory "$DIR" python test_real_env.py --api-key "$DD_API_KEY" --app-key "$DD_APP_KEY" --site "$SITE" --seed-only

SEED_EXIT=$?
if [ $SEED_EXIT -ne 0 ]; then
    red "❌ Seeding failed"
    exit $SEED_EXIT
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Step 2: Running RCA integration tests"
echo "════════════════════════════════════════════════════════════"
echo ""

# Step 2: Run integration tests
uv run --directory "$ROOT/backend" pytest tests/test_rca/test_integration_realenv.py -v -m datadog --tb=short

TEST_EXIT=$?

echo ""
if [ $TEST_EXIT -eq 0 ]; then
    green "✅ All integration tests passed!"
else
    red "❌ Some tests failed (exit code: $TEST_EXIT)"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Done"
echo "════════════════════════════════════════════════════════════"

exit $TEST_EXIT