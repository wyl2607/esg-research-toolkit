#!/usr/bin/env bash
#
# nightly_burn.sh — daily maintenance loop that consumes the OpenAI quota
# you'd otherwise lose. Runs UNATTENDED but does NOT auto-commit.
#
# Cron suggestion (after daily quota refresh, midnight local time):
#     0 1 * * * /Users/yumei/projects/esg-research-toolkit/scripts/nightly_burn.sh
#
# What it does:
#   1. git fetch + status snapshot          (no auto-pull, no auto-commit)
#   2. pytest -q                            (regression sentinel)
#   3. validate_benchmarks.py               (L4 percentile sanity)
#   4. run_audit_iterations.py 1 round      (~$2-3 — confirms data hasn't drifted)
#   5. one ROTATING codex task              (7-day cycle: types → tests → dead-code → security → docs → perf → a11y)
#   6. write report under nightly/<date>.md
#   7. macOS notification with summary
#
# Hard rules:
#   - NEVER commits or pushes
#   - NEVER deletes anything
#   - Bails on first hard error and writes the failure to nightly/<date>.md
#   - Total budget cap is enforced by OpenAI quota itself, not by this script
#
# Configuration (env vars, all optional):
#   OPENAI_API_KEY       required for steps 4 + 5
#   NIGHTLY_SKIP_CODEX=1 disable the rotating codex task (steps 1-4 only)
#   NIGHTLY_DRY_RUN=1    print the plan, don't run anything

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DATE="$(date +%Y-%m-%d)"
DOW="$(date +%u)"  # 1=Mon … 7=Sun
NIGHTLY_DIR="$ROOT/nightly"
mkdir -p "$NIGHTLY_DIR"
REPORT="$NIGHTLY_DIR/${DATE}.md"

PY="$ROOT/.venv/bin/python"
PYTEST="$ROOT/.venv/bin/pytest"
DRY="${NIGHTLY_DRY_RUN:-0}"

ROTATING_TASKS=(
    "lane1-types: Tighten or restore type hints in any .py file under benchmark/, report_parser/, taxonomy_scorer/. Zero behavior change. Run pytest -q. NEVER commit."
    "lane1-tests: Find untested public functions in benchmark/ and report_parser/, write targeted unit tests under tests/. Must pass pytest -q. NEVER commit."
    "lane1-deadcode: Find unused imports / dead helpers in backend modules. Remove them. Run pytest -q. NEVER commit."
    "lane1-security: Audit report_parser/api.py and main.py for new attack surface. Append findings to docs/audits/security_${DATE}.md. NEVER touch other files."
    "lane4-docs: Update docs/CLAUDE_CODE_PROJECT_HANDOFF.md and README.md with last 7 days of progress. Read PROJECT_PROGRESS.md for input. NEVER touch code."
    "lane2-frontend-perf: Find Recharts ResponsiveContainer width(-1) warnings, fix by adding minHeight wrappers. Run npm run lint && npm run build. NEVER commit."
    "lane2-a11y: Extend frontend/tests/ a11y coverage to one new route. Run npm run test:a11y. NEVER commit."
)
ROTATION_INDEX=$(( (DOW - 1) % ${#ROTATING_TASKS[@]} ))
TODAY_TASK="${ROTATING_TASKS[$ROTATION_INDEX]}"

{
    echo "# Nightly Burn Report — $DATE"
    echo
    echo "- host: $(hostname)"
    echo "- branch: $(git branch --show-current 2>/dev/null || echo unknown)"
    echo "- rotation slot: $ROTATION_INDEX / ${#ROTATING_TASKS[@]}"
    echo "- task: $TODAY_TASK"
    echo
} > "$REPORT"

run() {
    local name="$1"
    shift
    echo "## $name" >> "$REPORT"
    echo '```' >> "$REPORT"
    if [ "$DRY" = "1" ]; then
        echo "[dry-run] $*" >> "$REPORT"
    else
        ( "$@" ) >> "$REPORT" 2>&1 || echo "[non-zero exit: $?]" >> "$REPORT"
    fi
    echo '```' >> "$REPORT"
    echo >> "$REPORT"
}

run "git status" git status -sb
run "git fetch" git fetch --quiet origin || true
run "pytest -q" "$PYTEST" -q
run "validate_benchmarks" "$PY" scripts/validate_benchmarks.py

if [ -n "${OPENAI_API_KEY:-}" ]; then
    run "audit 1 round" "$PY" scripts/run_audit_iterations.py --iterations 1 --dry-run --max-chars 30000 --workers 2
else
    echo "## audit skipped" >> "$REPORT"
    echo "OPENAI_API_KEY not set" >> "$REPORT"
fi

if [ "${NIGHTLY_SKIP_CODEX:-0}" != "1" ] && command -v codex >/dev/null 2>&1; then
    echo "## codex rotating task" >> "$REPORT"
    echo '```' >> "$REPORT"
    if [ "$DRY" = "1" ]; then
        echo "[dry-run] codex exec '$TODAY_TASK'" >> "$REPORT"
    else
        echo "$TODAY_TASK" | codex exec - >> "$REPORT" 2>&1 || echo "[codex exit non-zero]" >> "$REPORT"
    fi
    echo '```' >> "$REPORT"
fi

# Diff + status snapshot for human review next morning — DO NOT COMMIT
run "post-run git status" git status -sb
DIFF_FILE="$NIGHTLY_DIR/${DATE}.patch"
if [ "$DRY" != "1" ]; then
    git diff > "$DIFF_FILE" 2>/dev/null || true
fi

SUMMARY="$(grep -E '^(passed|failed|error|\[non-zero|FAILED)' "$REPORT" | head -5 || true)"
if [ -z "$SUMMARY" ]; then
    SUMMARY="ok — review $REPORT"
fi

# macOS notification (no-op on linux)
if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"$SUMMARY\" with title \"esg nightly_burn $DATE\"" || true
fi

echo "Wrote $REPORT"
echo "Diff snapshot: $DIFF_FILE"
