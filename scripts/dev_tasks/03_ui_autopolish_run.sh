#!/usr/bin/env bash
#
# First real UI autopolish pass: capture screenshots of every major route in
# desktop + mobile viewports, run the vision-LLM critique, and produce an
# actionable task list ranked by (severity × effort).
#
# Unlike scripts 01/02, this one DOES need network + API key (via
# OPENAI_BASE_URL / OPENAI_API_KEY — the relay URL is fine).
#
# Output:
#   scripts/automation/screenshots/<ts>/*.png
#   scripts/automation/ui_reports/<ts>/critique.md
#   docs/exec-plans/ui_autopolish_tasks.md  (appended)
#
# Usage:
#   bash scripts/dev_tasks/03_ui_autopolish_run.sh            # full run
#   bash scripts/dev_tasks/03_ui_autopolish_run.sh --shots-only  # skip LLM
#
set -euo pipefail

MODE="${1:-}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

cd "$(dirname "$0")/../.."

echo "=== UI Autopolish Run $TIMESTAMP ==="
echo ""

check_http_code() {
  local url="$1"
  local code
  if ! code=$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' "$url" 2>/dev/null); then
    echo "down"
    return 1
  fi
  echo "$code"
}

verify_stack() {
  local backend_ok frontend_ok
  backend_ok=$(check_http_code "http://localhost:8000/health" || true)
  frontend_ok=$(check_http_code "http://localhost:5173/" || true)

  if [ "$backend_ok" = "200" ] && [ "$frontend_ok" = "200" ]; then
    echo "  ✅ Backend :8000 OK, Frontend :5173 OK"
    return 0
  fi

  echo "  ⚠️ stack readiness check failed (backend=$backend_ok frontend=$frontend_ok)"
  return 1
}

# Ensure venv tools exist
if [ ! -x .venv/bin/python ]; then
  echo "❌ .venv/bin/python not found — run 'python3 -m venv .venv && .venv/bin/pip install -r requirements.txt'"
  exit 1
fi

# Ensure Playwright browsers are installed
echo "[1/5] Checking Playwright install..."
if ! .venv/bin/playwright --version >/dev/null 2>&1; then
  echo "  Installing Playwright..."
  .venv/bin/pip install playwright >/dev/null
  .venv/bin/playwright install chromium
fi
echo "  ✅ Playwright ready"
echo ""

# Start fullstack in background
echo "[2/5] Starting full-stack..."
scripts/automation/run_fullstack.sh --detach || true
sleep 3

# Verify it came up. If stale listeners were already present, clear them and retry once.
if ! verify_stack; then
  echo "  ↺ retrying from a clean full-stack restart..."
  scripts/automation/run_fullstack.sh --stop || true
  sleep 1
  scripts/automation/run_fullstack.sh --detach
  sleep 3
  if ! verify_stack; then
    echo "❌ Stack did not come up cleanly after retry"
    scripts/automation/run_fullstack.sh --stop || true
    exit 1
  fi
fi
echo ""

# Run autopolish
if [ "$MODE" = "--shots-only" ]; then
  echo "[3/5] Capturing screenshots only (skipping vision LLM)..."
  .venv/bin/python scripts/automation/ui_autopolish.py --screenshot-only
else
  echo "[3/5] Capturing screenshots + running vision critique..."
  if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "  ⚠️ OPENAI_API_KEY not set in current shell; autopolish will fall back to env from .env if present"
  fi
  .venv/bin/python scripts/automation/ui_autopolish.py || {
    echo "  ⚠️ autopolish had an error — falling back to screenshot-only"
    .venv/bin/python scripts/automation/ui_autopolish.py --screenshot-only
  }
fi
echo ""

# Stop fullstack
echo "[4/5] Stopping full-stack..."
scripts/automation/run_fullstack.sh --stop || true
echo ""

# Locate outputs
echo "[5/5] Locating outputs..."
LATEST_SHOTS=$(ls -td scripts/automation/screenshots/*/ 2>/dev/null | head -1 || echo "")
LATEST_CRITIQUE=$(ls -td scripts/automation/ui_reports/*/ 2>/dev/null | head -1 || echo "")

echo "  Screenshots: ${LATEST_SHOTS:-none}"
echo "  Critique:    ${LATEST_CRITIQUE:-none}"
if [ -f "docs/exec-plans/ui_autopolish_tasks.md" ]; then
  echo "  Task list:   docs/exec-plans/ui_autopolish_tasks.md"
  echo ""
  echo "=== Top 5 tasks (by severity) ==="
  grep -E "^### |severity:" docs/exec-plans/ui_autopolish_tasks.md 2>/dev/null | head -20 || true
fi

echo ""
echo "=== Done ==="
echo ""
echo "Next: paste the 'Top 5 tasks' block back to Claude for review and"
echo "prioritized fix plan. Don't act on the task list without review —"
echo "vision critiques often flag cosmetic issues that are fine as-is."
