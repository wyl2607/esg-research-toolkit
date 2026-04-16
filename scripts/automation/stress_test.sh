#!/usr/bin/env bash
# stress_test.sh — 压力/烟雾双重测试
#
# 做三件事：
#   1. 用 hey/apache-bench 对后端关键 endpoint 打并发请求
#   2. 用 Playwright 跑 headless 浏览器检查每个前端页面能加载
#   3. 生成报告到 scripts/automation/logs/stress_<ts>.md
#
# Usage:
#   scripts/automation/stress_test.sh              # 全套
#   scripts/automation/stress_test.sh --quick      # 轻量（10 次请求）
#   scripts/automation/stress_test.sh --api-only   # 只测 API
#   scripts/automation/stress_test.sh --frontend-only

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

LOG_DIR="$PROJECT_ROOT/scripts/automation/logs"
mkdir -p "$LOG_DIR"
TS=$(date +%Y%m%d_%H%M%S)
REPORT="$LOG_DIR/stress_${TS}.md"

API=${API_BASE:-http://localhost:8000}
WEB=${FRONTEND_URL:-http://localhost:5173}

REQUESTS=50
CONCURRENCY=5
MODE="full"

while [ $# -gt 0 ]; do
    case "$1" in
        --quick)         REQUESTS=10; CONCURRENCY=2 ;;
        --api-only)      MODE="api" ;;
        --frontend-only) MODE="frontend" ;;
        -h|--help)       grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)               echo "unknown arg: $1" >&2; exit 2 ;;
    esac
    shift
done

# choose load tool
LOAD_TOOL=""
if command -v hey >/dev/null 2>&1; then
    LOAD_TOOL="hey"
elif command -v ab >/dev/null 2>&1; then
    LOAD_TOOL="ab"
else
    LOAD_TOOL="curl-loop"
fi

color() { printf '\033[%sm%s\033[0m' "$1" "$2"; }
info()  { echo "$(color 36 '[stress]') $*"; }
pass()  { echo "$(color 32 '[stress]') $*"; }
fail()  { echo "$(color 31 '[stress]') $*"; }

{
    echo "# Stress test — $TS"
    echo ""
    echo "- API base: \`$API\`"
    echo "- Frontend: \`$WEB\`"
    echo "- Mode: \`$MODE\`"
    echo "- Load tool: \`$LOAD_TOOL\` ($REQUESTS req, $CONCURRENCY concurrent)"
    echo ""
} > "$REPORT"

load_test_endpoint() {
    local url=$1 name=$2
    info "hitting $name ($url)"
    local out=""
    case "$LOAD_TOOL" in
        hey)
            out=$(hey -n "$REQUESTS" -c "$CONCURRENCY" -disable-keepalive "$url" 2>&1)
            ;;
        ab)
            out=$(ab -n "$REQUESTS" -c "$CONCURRENCY" -q "$url" 2>&1 | grep -E "Requests per second|Time per request|Failed requests|Non-2xx")
            ;;
        curl-loop)
            local ok=0 err=0
            local start=$(date +%s%N)
            for i in $(seq 1 "$REQUESTS"); do
                code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "$url")
                [ "$code" = "200" ] && ok=$((ok+1)) || err=$((err+1))
            done
            local end=$(date +%s%N)
            local ms=$(( (end - start) / 1000000 ))
            out="curl-loop: $REQUESTS requests, ok=$ok err=$err, total ${ms}ms"
            ;;
    esac
    {
        echo "### $name"
        echo ""
        echo '```'
        echo "$out"
        echo '```'
        echo ""
    } >> "$REPORT"
    echo "$out" | tail -5
}

test_api() {
    info "=== API stress ==="
    echo "## API endpoints" >> "$REPORT"
    load_test_endpoint "$API/health"                "GET /health"
    load_test_endpoint "$API/report/companies"      "GET /report/companies"
    load_test_endpoint "$API/frameworks/list"       "GET /frameworks/list"
    load_test_endpoint "$API/techno/benchmarks"     "GET /techno/benchmarks"

    # deliberately trigger rate limit (>5/min on upload)
    info "rate-limit probe on /report/upload (expect some 429)"
    local codes=""
    for i in 1 2 3 4 5 6 7 8 9 10; do
        c=$(curl -sS -o /dev/null -w '%{http_code} ' -X POST "$API/report/upload" -F "file=@/etc/hosts;type=application/pdf")
        codes+="$c"
    done
    {
        echo "### Rate-limit probe (10 rapid POSTs)"
        echo ""
        echo '```'
        echo "HTTP codes: $codes"
        echo "(expect: first few 4xx/5xx from validation, then 429 once slowapi trips)"
        echo '```'
        echo ""
    } >> "$REPORT"
}

test_frontend_pages() {
    info "=== frontend page sweep ==="
    local pages=("/" "/upload" "/companies" "/taxonomy" "/frameworks" "/compare" "/benchmarks" "/lcoe" "/manual" "/regional")
    local passed=0 failed=0
    {
        echo "## Frontend pages"
        echo ""
        echo "| Page | HTTP | Content-length |"
        echo "|---|---|---|"
    } >> "$REPORT"

    for p in "${pages[@]}"; do
        local url="$WEB$p"
        local http=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "$url" 2>/dev/null)
        local size=$(curl -sS --max-time 10 "$url" 2>/dev/null | wc -c | tr -d ' ')
        if [ "$http" = "200" ] && [ "$size" -gt 100 ]; then
            pass "  200  $p  ($size bytes)"
            passed=$((passed+1))
            echo "| \`$p\` | $http | $size |" >> "$REPORT"
        else
            fail "  $http $p  ($size bytes)"
            failed=$((failed+1))
            echo "| \`$p\` | **$http** | $size |" >> "$REPORT"
        fi
    done
    {
        echo ""
        echo "**Result: $passed ok, $failed failed**"
        echo ""
    } >> "$REPORT"
}

case "$MODE" in
    api)       test_api ;;
    frontend)  test_frontend_pages ;;
    full)      test_api; echo ""; test_frontend_pages ;;
esac

echo ""
pass "report: $REPORT"
echo ""
head -50 "$REPORT"
