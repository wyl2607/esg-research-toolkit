#!/usr/bin/env bash
# PR readiness sanity check. This does not push; it reviews outgoing files
# against secret, local-boundary, and existing repo consistency guards.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

BASE_REF="${1:-origin/main}"

if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
  echo "[pr][FAIL] base ref not found: $BASE_REF"
  echo "[pr] usage: scripts/pr_sanity_check.sh origin/main"
  exit 2
fi

RANGE="$BASE_REF..HEAD"

echo "[pr] base_ref=$BASE_REF"
echo "[pr] branch=$(git branch --show-current 2>/dev/null || true)"
echo "[pr] head=$(git rev-parse --short HEAD)"

echo
echo "[pr] status"
git status --short --branch

echo
echo "[pr] outgoing commits"
git log --oneline "$RANGE" --stat | sed -n '1,80p'

echo
echo "[pr] diff stat"
git diff --stat "$RANGE"

echo
echo "[pr] changed files"
git diff --name-only "$RANGE"

echo
scripts/secret_guard.sh --range "$RANGE"
scripts/local_boundary_guard.sh --range "$RANGE"

if [ -x scripts/consistency_check.sh ]; then
  scripts/consistency_check.sh
fi

echo "[pr] sanity check passed"
