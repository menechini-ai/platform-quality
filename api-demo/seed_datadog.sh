#!/usr/bin/env bash
# Datadog Seed — send monitors, events, logs, and error tracking
# for all named APIs with distinct tags (service, env, tier, team).
#
# Usage:
#   bash api-demo/seed_datadog.sh
#   # or with explicit keys:
#   DATADOG_API_KEY=xxx DATADOG_APP_KEY=yyy bash api-demo/seed_datadog.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
API_KEY="${DATADOG_API_KEY:-}"
APP_KEY="${DATADOG_APP_KEY:-}"
SITE="${DATADOG_SITE:-us5.datadoghq.com}"

if [ -z "$API_KEY" ]; then
    if [ -f "$DIR/../backend/.env" ]; then
        API_KEY=$(grep '^DATADOG_API_KEY=' "$DIR/../backend/.env" | cut -d'=' -f2 | tr -d '"' | head -1)
        APP_KEY=$(grep '^DATADOG_APP_KEY=' "$DIR/../backend/.env" | cut -d'=' -f2 | tr -d '"' | head -1)
    fi
fi

if [ -z "$API_KEY" ]; then
    echo "ERROR: DATADOG_API_KEY not set. Provide via env var or add to backend/.env"
    exit 1
fi

green()  { printf "\033[32m%s\033[0m\n" "$1"; }
yellow() { printf "\033[33m%s\033[0m\n" "$1"; }
red()    { printf "\033[31m%s\033[0m\n" "$1"; }
dim()    { printf "\033[2m%s\033[0m" "$1"; }

API_BASE="https://api.$SITE"
LOG_INTAKE="https://http-intake.logs.$SITE"

HDR="DD-API-KEY: $API_KEY"
HDR_APP=""
if [ -n "$APP_KEY" ]; then HDR_APP="DD-APPLICATION-KEY: $APP_KEY"; fi

# Services list — each row: name,tags_comma,tags_json
SVCS=(
    "api-gateway,service:api-gateway,env:prod,tier:infra,team:observai"
    "user-service,service:user-service,env:prod,tier:backend,team:observai"
    "payment-service,service:payment-service,env:prod,tier:backend,team:observai"
    "order-service,service:order-service,env:staging,tier:backend,team:observai"
    "notification-service,service:notification-service,env:dev,tier:backend,team:observai"
    "observai-frontend,service:observai-frontend,env:prod,tier:frontend,project:observai,team:observai"
    "observai-backend,service:observai-backend,env:prod,tier:backend,project:observai,team:observai"
    "observai-worker,service:observai-worker,env:staging,tier:worker,project:observai,team:observai"
)

FAIL=0
TOTAL=0
OK=0

make_tags_json() {
    local tags="$1"
    local result=""
    while [ -n "$tags" ]; do
        local part="${tags%%,*}"
        if [ -n "$result" ]; then result="$result,"; fi
        result="$result\"$part\""
        if [ "$tags" = "$part" ]; then
            tags=""
        else
            tags="${tags#*,}"
        fi
    done
    echo "[$result]"
}

call_api() {
    local desc="$1" method="$2" url="$3" body="$4"
    TOTAL=$((TOTAL + 1))
    printf "  [%s] %-50s … " "$method" "$desc"
    local tmpfile respfile
    tmpfile=$(mktemp)
    respfile=$(mktemp)
    printf '%s' "$body" > "$tmpfile"
    local response
    response=$(curl -s -o "$respfile" -w '%{http_code}' -X "$method" "$url" \
        -H "$HDR" -H "Content-Type: application/json" \
        ${HDR_APP:+-H "$HDR_APP"} \
        -d @"$tmpfile" 2>&1) || true
    if [ "$response" = "200" ] || [ "$response" = "201" ] || [ "$response" = "202" ]; then
        green "HTTP $response"
        OK=$((OK + 1))
    else
        local err
        err=$(head -c 200 "$respfile" 2>/dev/null || true)
        if echo "$err" | grep -q "Duplicate"; then
            yellow "DUPLICATE (exists already)"
            OK=$((OK + 1))
        else
            red "HTTP $response"
            if [ -n "$err" ]; then
                echo "       ↳ ERR: $err" >&2
            fi
            FAIL=1
        fi
    fi
    rm -f "$tmpfile" "$respfile"
}

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Seeding Datadog — all 8 services"
echo "  Site: $SITE"
echo "════════════════════════════════════════════════════════════"
echo ""

for row in "${SVCS[@]}"; do
    svc="${row%%,*}"
    tags="${row#*,}"
    tag_list_json=$(make_tags_json "$tags")
    ts=$(date +%s)
    echo ""
    dim "--- $svc ($tags) ---"
    echo ""

    # 1. Logs (3 per service)
    call_api "log: info" POST "$LOG_INTAKE/api/v2/logs" \
        "[{\"ddsource\":\"python\",\"ddtags\":\"$tags\",\"hostname\":\"seed-$svc\",\"service\":\"$svc\",\"message\":\"$svc — health check passed\",\"status\":\"info\",\"timestamp\":$ts}]"

    call_api "log: warn" POST "$LOG_INTAKE/api/v2/logs" \
        "[{\"ddsource\":\"python\",\"ddtags\":\"$tags\",\"hostname\":\"seed-$svc\",\"service\":\"$svc\",\"message\":\"$svc — latency spike detected (p99 > 500ms)\",\"status\":\"warn\",\"timestamp\":$ts}]"

    call_api "log: error" POST "$LOG_INTAKE/api/v2/logs" \
        "[{\"ddsource\":\"python\",\"ddtags\":\"$tags\",\"hostname\":\"seed-$svc\",\"service\":\"$svc\",\"message\":\"$svc — Connection timeout after 30s\",\"status\":\"error\",\"timestamp\":$ts}]"

    # 2. Events (2 per service)
    call_api "event: info" POST "$API_BASE/api/v1/events" \
        "{\"title\":\"[$svc] Deployment completed\",\"text\":\"$svc — v2.3.1 rolled out successfully\",\"alert_type\":\"info\",\"tags\":\"$tags\",\"host\":\"seed-$svc\",\"date_happened\":$ts}"

    call_api "event: warning" POST "$API_BASE/api/v1/events" \
        "{\"title\":\"[$svc] Error rate breach\",\"text\":\"$svc — error rate exceeded 5% threshold\",\"alert_type\":\"warning\",\"tags\":\"$tags\",\"host\":\"seed-$svc\",\"date_happened\":$ts}"

    # 3. Error Tracking (3 per service)
    call_api "error: ValueError" POST "$LOG_INTAKE/api/v2/logs" \
        "[{\"ddsource\":\"python\",\"ddtags\":\"$tags,error.kind:ValueError\",\"hostname\":\"seed-$svc\",\"service\":\"$svc\",\"message\":\"[$svc] ValueError: invalid customer_id format\",\"status\":\"error\",\"timestamp\":$ts}]"

    call_api "error: TimeoutError" POST "$LOG_INTAKE/api/v2/logs" \
        "[{\"ddsource\":\"python\",\"ddtags\":\"$tags,error.kind:TimeoutError\",\"hostname\":\"seed-$svc\",\"service\":\"$svc\",\"message\":\"[$svc] TimeoutError: upstream service did not respond within 30s\",\"status\":\"error\",\"timestamp\":$ts}]"

    call_api "error: DatabaseError" POST "$LOG_INTAKE/api/v2/logs" \
        "[{\"ddsource\":\"python\",\"ddtags\":\"$tags,error.kind:DatabaseError\",\"hostname\":\"seed-$svc\",\"service\":\"$svc\",\"message\":\"[$svc] DatabaseError: connection pool exhausted\",\"status\":\"error\",\"timestamp\":$ts}]"

    # 4. Monitors (only if APP_KEY is set)
    if [ -n "$APP_KEY" ]; then
        call_api "monitor: CPU" POST "$API_BASE/api/v1/monitor" \
            "{\"name\":\"ObservAI — $svc CPU > 80%\",\"type\":\"query alert\",\"query\":\"avg(last_5m):avg:system.cpu.user{$tags} > 80\",\"message\":\"$svc CPU high\",\"tags\":$tag_list_json}"

        call_api "monitor: Latency" POST "$API_BASE/api/v1/monitor" \
            "{\"name\":\"ObservAI — $svc Latency > 500ms\",\"type\":\"metric alert\",\"query\":\"avg(last_5m):avg:trace.servlet.request.duration{$tags} > 500\",\"message\":\"$svc latency spike\",\"tags\":$tag_list_json}"
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Results"
echo "════════════════════════════════════════════════════════════"
echo "  Total calls: $TOTAL"
echo "  Succeeded:   $OK"
echo "  Failed:      $((TOTAL - OK))"
echo ""

if [ "$FAIL" -eq 0 ]; then
    green "All data sent successfully to Datadog ($SITE)"
else
    red "Some calls failed — check your API keys and permissions"
    exit 1
fi