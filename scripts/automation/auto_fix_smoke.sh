#!/usr/bin/env bash
# auto_fix_smoke.sh — 自愈式 smoke test 循环
#
# 工作流：
#   1. 启动（或复用）后端 + 前端
#   2. 跑 pytest + frontend lint + build + smoke
#   3. 把失败日志写入 scripts/automation/logs/autofix_cycle_N.log
#   4. 如果失败，打印结构化 fix-prompt 供 Claude/Codex 直接复用
#   5. 等待用户确认（或 --auto-retry 参数无人值守重试）
#
# Usage:
#   scripts/automation/auto_fix_smoke.sh               # 跑一遍
#   scripts/automation/auto_fix_smoke.sh --backend     # 只验后端
#   scripts/automation/auto_fix_smoke.sh --frontend    # 只验前端
#   scripts/automation/auto_fix_smoke.sh --max-rounds 3 # 最多 3 轮

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

LOG_DIR="$PROJECT_ROOT/scripts/automation/logs"
mkdir -p "$LOG_DIR"

color() { printf '\033[%sm%s\033[0m' "$1" "$2"; }
info()  { echo "$(color 36 '[autofix]') $*"; }
fail()  { echo "$(color 31 '[autofix]') $*" >&2; }
pass()  { echo "$(color 32 '[autofix]') $*"; }

MAX_ROUNDS=1
DO_BACKEND=1
DO_FRONTEND=1
WRITE_PROMPT=1

while [ $# -gt 0 ]; do
    case "$1" in
        --backend)   DO_FRONTEND=0 ;;
        --frontend)  DO_BACKEND=0 ;;
        --max-rounds) MAX_ROUNDS=$2; shift ;;
        --no-prompt) WRITE_PROMPT=0 ;;
        -h|--help)
            grep '^#' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            fail "unknown arg: $1"; exit 2 ;;
    esac
    shift
done

CYCLE=0
TOTAL_FAILURES=()

run_backend_checks() {
    local cycle=$1
    local logfile="$LOG_DIR/autofix_backend_${cycle}.log"
    info "backend suite → $logfile"
    {
        echo "### pytest full suite"
        OPENAI_API_KEY=dummy .venv/bin/pytest -q 2>&1
        echo "---PYTEST_EXIT=$?"
    } > "$logfile" 2>&1

    if grep -q "^---PYTEST_EXIT=0" "$logfile"; then
        pass "backend pytest: PASS"
        return 0
    else
        fail "backend pytest: FAIL → $logfile"
        TOTAL_FAILURES+=("backend:$logfile")
        return 1
    fi
}

run_frontend_checks() {
    local cycle=$1
    local logfile="$LOG_DIR/autofix_frontend_${cycle}.log"
    info "frontend suite → $logfile"
    local failed=0
    {
        echo "### npm run lint"
        (cd frontend && npm run lint 2>&1)
        local lint_exit=$?
        echo "---LINT_EXIT=$lint_exit"
        [ $lint_exit -eq 0 ] || failed=1

        echo ""
        echo "### npm run build"
        (cd frontend && npm run build 2>&1)
        local build_exit=$?
        echo "---BUILD_EXIT=$build_exit"
        [ $build_exit -eq 0 ] || failed=1

        echo ""
        echo "### npm run test:smoke"
        (cd frontend && npm run test:smoke 2>&1)
        local smoke_exit=$?
        echo "---SMOKE_EXIT=$smoke_exit"
        [ $smoke_exit -eq 0 ] || failed=1
    } > "$logfile" 2>&1

    if grep -qE "---(LINT|BUILD|SMOKE)_EXIT=[^0]" "$logfile"; then
        fail "frontend suite: one or more failures → $logfile"
        TOTAL_FAILURES+=("frontend:$logfile")
        return 1
    else
        pass "frontend suite: PASS"
        return 0
    fi
}

write_fix_prompt() {
    local prompt_file="$LOG_DIR/autofix_prompt_$(date +%Y%m%d_%H%M%S).md"
    info "writing reusable fix-prompt → $prompt_file"
    {
        echo "# Auto-Fix Prompt (cycle $CYCLE)"
        echo ""
        echo "The following checks failed. Read the listed logs, identify root causes,"
        echo "and propose minimal patches. Prefer surgical fixes over refactors."
        echo ""
        echo "## Failed logs"
        for f in "${TOTAL_FAILURES[@]}"; do
            local path=${f#*:}
            echo "- \`$path\`"
        done
        echo ""
        echo "## Failure excerpts (tail 40 lines each)"
        for f in "${TOTAL_FAILURES[@]}"; do
            local path=${f#*:}
            echo ""
            echo "### $path"
            echo '```'
            tail -40 "$path" 2>/dev/null | sed 's/\r$//'
            echo '```'
        done
        echo ""
        echo "## Constraints"
        echo "- Do not change test assertions unless the test is objectively wrong"
        echo "- Do not disable lint rules to silence errors"
        echo "- Run the same failing command after the fix to confirm green"
    } > "$prompt_file"
    echo ""
    pass "prompt ready: $prompt_file"
    echo "   → paste into a Claude/Codex session to auto-fix"
}

overall_exit=0
while [ "$CYCLE" -lt "$MAX_ROUNDS" ]; do
    CYCLE=$((CYCLE + 1))
    echo ""
    info "=== Round $CYCLE / $MAX_ROUNDS ==="
    TOTAL_FAILURES=()
    [ $DO_BACKEND -eq 1 ]  && run_backend_checks "$CYCLE"  || true
    [ $DO_FRONTEND -eq 1 ] && run_frontend_checks "$CYCLE" || true

    if [ ${#TOTAL_FAILURES[@]} -eq 0 ]; then
        pass "✅ Round $CYCLE: all green"
        overall_exit=0
        break
    fi

    overall_exit=1
    [ $WRITE_PROMPT -eq 1 ] && write_fix_prompt

    if [ "$CYCLE" -lt "$MAX_ROUNDS" ]; then
        info "will retry in 3s (round $((CYCLE + 1)))"
        sleep 3
    fi
done

exit $overall_exit
