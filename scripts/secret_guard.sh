#!/usr/bin/env bash
# Fail if tracked files or candidate diffs include obvious secret/private paths
# or newly added hardcoded credential values.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

MODE="tracked"
RANGE=""

usage() {
  cat <<USAGE
Usage:
  scripts/secret_guard.sh [--tracked]
  scripts/secret_guard.sh --staged
  scripts/secret_guard.sh --range <git-range>
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
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[secret][FAIL] unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [ "$MODE" = "range" ] && [ -z "$RANGE" ]; then
  echo "[secret][FAIL] --range requires a git range" >&2
  exit 2
fi

path_pattern='(^|/)\.env($|\.)|\.pem$|\.key$|\.p12$|credentials(\.|/|$)|secrets(\.|/|$)|api_keys(\.|/|$)|config\.private\.|(^|/)cookies?(\.|/|$)|(^|/)tokens?(\.|/|$)'
fail=0

case "$MODE" in
  tracked)
    paths="$(git ls-files)"
    ;;
  staged)
    paths="$(git diff --cached --name-only)"
    ;;
  range)
    paths="$(git diff --name-only "$RANGE")"
    ;;
esac

matches="$(printf '%s\n' "$paths" | rg -n "$path_pattern" || true)"
if [ -n "$matches" ]; then
  allowed="$(printf '%s\n' "$matches" | rg '^[0-9]+:\.env\.example$' || true)"
  blocked="$(printf '%s\n' "$matches" | rg -v '^[0-9]+:\.env\.example$' || true)"
  if [ -n "$blocked" ]; then
    echo "[secret][FAIL] secret/private path candidates detected"
    printf '%s\n' "$blocked"
    fail=1
  fi
  if [ -n "$allowed" ]; then
    echo "[secret] allowed example path(s)"
    printf '%s\n' "$allowed"
  fi
fi

scan_diff() {
  case "$MODE" in
    tracked)
      return 0
      ;;
    staged)
      git diff --cached -- '*.py' '*.toml' '*.yaml' '*.yml' '*.json' '*.sh' '*.ts' '*.tsx' '*.js' '*.jsx'
      ;;
    range)
      git diff "$RANGE" -- '*.py' '*.toml' '*.yaml' '*.yml' '*.json' '*.sh' '*.ts' '*.tsx' '*.js' '*.jsx'
      ;;
  esac
}

if [ "$MODE" != "tracked" ]; then
  if scan_diff | rg '^\+' | rg -v '^\+\+\+' | rg -i "(api[_-]?key|secret[_-]?key|openai[_-]?key|anthropic[_-]?key|token)\s*[:=]\s*['\"][A-Za-z0-9_./+=:-]{20,}" >/tmp/secret_guard_hits.out 2>/dev/null; then
    echo "[secret][FAIL] hardcoded credential-like value added"
    sed -n '1,8p' /tmp/secret_guard_hits.out
    fail=1
  fi

  if scan_diff | rg '^\+' | rg -v '^\+\+\+' | rg "(relay\.nf\.video|api\.longcat\.chat|ark\.cn-beijing\.volces\.com)" >/tmp/secret_guard_endpoints.out 2>/dev/null; then
    echo "[secret][FAIL] private relay/third-party endpoint added"
    sed -n '1,8p' /tmp/secret_guard_endpoints.out
    fail=1
  fi
fi

if [ "$fail" -ne 0 ]; then
  echo "[secret] guard failed"
  exit 1
fi

echo "[secret] guard passed mode=$MODE"
