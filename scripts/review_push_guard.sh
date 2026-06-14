#!/usr/bin/env bash
# Push-time review guard: scan outgoing commits with the SAME rule set as the
# pre-commit gate (scripts/guard_lib.sh), plus push-only structural guards.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"
# shellcheck source=scripts/guard_lib.sh
source scripts/guard_lib.sh

# NB: keep @{u} out of the ${1:-...} default — its '}' would close the expansion early.
BASE_REF="${1:-}"
[ -z "$BASE_REF" ] && BASE_REF='@{u}'
if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
  echo "[guard] base ref not found: $BASE_REF"
  echo "[guard] tip: pass an explicit base, e.g. scripts/review_push_guard.sh origin/main"
  exit 2
fi

RANGE="$BASE_REF..HEAD"
if [ -z "$(git diff --name-only "$RANGE")" ]; then
  echo "[guard] no outgoing changes"
  exit 0
fi
echo "[guard] scanning range: $RANGE"

GUARD_SCOPE="$RANGE"
GUARD_MODE_ARGS=("--range" "$RANGE")
GUARD_FAILED=0

# Push-only structural guard: worktree convergence (repo-wide, heavier).
# CONVERGE_WORKTREE_GUARD=0 临时关闭。
if [ "${CONVERGE_WORKTREE_GUARD:-1}" = "1" ] && [ -x scripts/automation/converge_worktrees.sh ]; then
  out="$(mktemp)"
  if ! scripts/automation/converge_worktrees.sh --assert-no-lanes --assert-no-lane-artifacts >"$out" 2>&1; then
    echo "[guard][FAIL] worktree converge guard failed"; cat "$out"; GUARD_FAILED=1
  fi
  rm -f "$out"
fi

guard_subguards
guard_content_all

# Push-only structural guard: SSoT consistency (docs/policies/project-consistency-rules.md §1).
# CONSISTENCY_GUARD=0 临时关闭（不建议）。
if [ "${CONSISTENCY_GUARD:-1}" = "1" ] && [ -x scripts/consistency_check.sh ]; then
  out="$(mktemp)"
  if ! scripts/consistency_check.sh >"$out" 2>&1; then
    echo "[guard][FAIL] SSoT consistency_check.sh reported violations"; cat "$out"; GUARD_FAILED=1
  fi
  rm -f "$out"
fi

if [ "$GUARD_FAILED" -ne 0 ]; then
  echo "[guard] push review failed"
  exit 1
fi

echo "[guard] push review passed"
exit 0
