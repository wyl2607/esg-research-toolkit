#!/usr/bin/env bash
# Guard the local/GitHub boundary by checking ignored local paths, tracked
# local-only paths, and optional staged/outgoing file-zone classifications.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

MODE="tracked"
RANGE=""
CHECK_ZONES=1

usage() {
  cat <<USAGE
Usage:
  scripts/local_boundary_guard.sh [--tracked]
  scripts/local_boundary_guard.sh --staged
  scripts/local_boundary_guard.sh --range <git-range>
  scripts/local_boundary_guard.sh --range <git-range> --skip-zone-review
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --tracked)
      MODE="tracked"
      shift
      ;;
    --staged)
      MODE="staged"
      shift
      ;;
    --range)
      MODE="range"
      RANGE="${2:-}"
      shift 2
      ;;
    --skip-zone-review)
      CHECK_ZONES=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[boundary][FAIL] unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

fail=0

required_ignored=(
  ".local/probe"
  ".omx/state/probe"
  ".codex/probe"
  ".claude/probe"
  ".env"
  "credentials.json"
  "secrets.json"
  "runtime/perf/probe.log"
  "scripts/__pycache__/probe.pyc"
)

for path in "${required_ignored[@]}"; do
  if ! git check-ignore -q "$path"; then
    echo "[boundary][FAIL] expected ignored path is not ignored: $path"
    fail=1
  fi
done

tracked_local="$(git ls-files | rg '(^\.local/|^\.omx/|^\.codex/|^\.claude/|^\.cursor/|^\.gemini/|^dev-local/|^runtime/|^logs/|^reports/|(^|/)\.DS_Store$|__pycache__/|\.pyc$)' || true)"
if [ -n "$tracked_local" ]; then
  echo "[boundary][FAIL] tracked local-only/cache paths detected"
  printf '%s\n' "$tracked_local"
  fail=1
fi

case "$MODE" in
  tracked)
    ;;
  staged)
    if [ "$CHECK_ZONES" -eq 1 ] && ! scripts/review_file_zones.sh --staged --block-local; then
      fail=1
    fi
    ;;
  range)
    if [ -z "$RANGE" ]; then
      echo "[boundary][FAIL] --range requires a git range" >&2
      exit 2
    fi
    if [ "$CHECK_ZONES" -eq 1 ] && ! scripts/review_file_zones.sh --range "$RANGE" --block-local; then
      fail=1
    fi
    ;;
esac

if [ "$fail" -ne 0 ]; then
  echo "[boundary] guard failed"
  exit 1
fi

echo "[boundary] guard passed mode=$MODE"
