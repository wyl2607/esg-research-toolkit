#!/usr/bin/env bash
#
# Overnight loop: migrate every pending page one by one, auto-commit each
# successful migration, stop immediately on any failure so a human can
# inspect without stacking broken commits.
#
# Usage (from project root):
#   set -a; source .env; set +a
#   CODEX_MODEL=gpt-5.3-codex bash scripts/dev_tasks/07_ui_page_migration_loop.sh
#
# Env knobs (all optional):
#   CODEX_MODEL        default gpt-5.3-codex
#   CODEX_EFFORT       default high
#   MAX_PAGES          hard cap per run (default 99 — effectively all)
#   COOLDOWN_SECONDS   gap between pages (default 10) — gives API quota breathing room
#
# Exit codes:
#   0  all pending pages migrated (or MAX_PAGES reached)
#   1  setup error (missing key, wrong dir, etc.)
#   2  codex or gate failure on a page — loop stopped, page already reverted
#      by 06_ui_page_migration.sh snapshot, nothing to clean up

set -euo pipefail

cd "$(dirname "$0")/../.."

LOG_DIR="scripts/automation/logs/ui_migration"
mkdir -p "$LOG_DIR"
TS=$(date +"%Y%m%d_%H%M%S")
LOG="$LOG_DIR/loop_${TS}.log"

MAX_PAGES="${MAX_PAGES:-99}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-10}"

log() { echo "[$(date +"%H:%M:%S")] $*" | tee -a "$LOG"; }

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "❌ OPENAI_API_KEY not set — run: set -a; source .env; set +a" >&2
  exit 1
fi

# Block if working tree is dirty — otherwise auto-commits sweep up unrelated stuff.
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "❌ working tree dirty. Commit or stash first." >&2
  git status -s >&2
  exit 1
fi

# Collect pending list up front (the per-page script reports only one at a time).
STATE_DIR="scripts/automation/state/ui_migration"
PAGES=(
  TaxonomyPage
  LcoePage
  CompanyProfilePage
  ComparePage
  BenchmarkPage
  FrameworksPage
  RegionalPage
  ManualCaseBuilderPage
  CoverageFieldPage
  DashboardPage
)

PENDING=()
for p in "${PAGES[@]}"; do
  [ -f "$STATE_DIR/$p.done" ] || PENDING+=("$p")
done

if [ ${#PENDING[@]} -eq 0 ]; then
  log "✅ nothing pending. All pages already migrated."
  exit 0
fi

log "=== Overnight UI migration loop ==="
log "log file: $LOG"
log "pending:  ${PENDING[*]}"
log "cap:      $MAX_PAGES"
log "cooldown: ${COOLDOWN_SECONDS}s"
log ""

count=0
for page in "${PENDING[@]}"; do
  if [ "$count" -ge "$MAX_PAGES" ]; then
    log "reached MAX_PAGES=$MAX_PAGES — stopping"
    break
  fi

  log "--- [$((count+1))/${#PENDING[@]}] $page ---"

  if ! bash scripts/dev_tasks/06_ui_page_migration.sh "$page" >>"$LOG" 2>&1; then
    log "❌ $page failed (codex or gate). Page auto-reverted by 06 script."
    log "Inspect: tail -120 $LOG"
    exit 2
  fi

  # Gate already ran inside 06 — so the migrated file is lint+build clean.
  # Safety: confirm only the expected files changed.
  changed=$(git status --porcelain)
  expected_file="frontend/src/pages/${page}.tsx"
  if ! grep -q "$expected_file" <<<"$changed"; then
    log "❌ $page: migration succeeded but $expected_file not in changeset — aborting"
    log "$changed"
    exit 2
  fi

  # Flag any file outside the allowlist — if codex touched something else, stop.
  unexpected=$(echo "$changed" | awk '{print $2}' | grep -vE "^(${expected_file//\//\\/}|scripts/automation/state/ui_migration/|scripts/dev_tasks/07_ui_page_migration_loop\\.sh)" || true)
  if [ -n "$unexpected" ]; then
    log "❌ $page: unexpected files changed:"
    log "$unexpected"
    log "Leaving working tree for human review — NOT committing."
    exit 2
  fi

  git add "$expected_file" "scripts/automation/state/ui_migration/${page}.done" \
          "scripts/automation/state/ui_migration/${page}.pre.tsx" 2>/dev/null || true

  if git diff --cached --quiet; then
    log "⚠  $page: nothing staged after git add — skipping commit"
  else
    git commit -m "ui(${page,,}): migrate $page to design primitives

Automated migration via scripts/dev_tasks/06_ui_page_migration.sh
Model: ${CODEX_MODEL:-gpt-5.3-codex}, effort: ${CODEX_EFFORT:-high}
Gate:  frontend lint + build passed." >>"$LOG" 2>&1
    log "✅ $page migrated + committed ($(git rev-parse --short HEAD))"
  fi

  count=$((count+1))

  if [ "$count" -lt "${#PENDING[@]}" ] && [ "$count" -lt "$MAX_PAGES" ]; then
    log "cooldown ${COOLDOWN_SECONDS}s"
    sleep "$COOLDOWN_SECONDS"
  fi
done

log ""
log "=== Loop complete: $count page(s) migrated ==="
bash scripts/dev_tasks/06_ui_page_migration.sh --list | tee -a "$LOG"
