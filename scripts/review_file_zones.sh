#!/usr/bin/env bash
# File-zone reviewer: classify changed files as public/local/unclassified.
# - unclassified => fail
# - local changes (A/M/R/C/...) can be blocked with --block-local

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

MODE=""
RANGE=""
BLOCK_LOCAL=0

usage() {
  cat <<USAGE
Usage:
  scripts/review_file_zones.sh --staged [--block-local]
  scripts/review_file_zones.sh --range <git-range> [--block-local]

Examples:
  scripts/review_file_zones.sh --staged --block-local
  scripts/review_file_zones.sh --range origin/main..HEAD --block-local
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --staged)
      MODE="staged"
      shift
      ;;
    --range)
      MODE="range"
      RANGE="${2:-}"
      shift 2
      ;;
    --block-local)
      BLOCK_LOCAL=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [ -z "$MODE" ]; then
  usage
  exit 2
fi

LOCAL_ONLY_LIST=".guard/local-only-files.txt"
LOCAL_PREFIXES=".guard/local-prefixes.txt"
PUBLIC_PREFIXES=".guard/public-prefixes.txt"

for f in "$LOCAL_ONLY_LIST" "$LOCAL_PREFIXES" "$PUBLIC_PREFIXES"; do
  if [ ! -f "$f" ]; then
    echo "[zone][FAIL] missing policy file: $f"
    exit 2
  fi
done

get_changes() {
  if [ "$MODE" = "staged" ]; then
    git diff --cached --name-status
  else
    git diff --name-status "$RANGE"
  fi
}

is_exact_in_file() {
  local needle="$1"
  local list_file="$2"
  while IFS= read -r item || [ -n "$item" ]; do
    item="${item%$'\r'}"
    [ -z "$item" ] && continue
    case "$item" in
      \#*) continue ;;
    esac
    if [ "$item" = "$needle" ]; then
      return 0
    fi
  done < "$list_file"
  return 1
}

match_prefix() {
  local path="$1"
  local list_file="$2"
  while IFS= read -r prefix || [ -n "$prefix" ]; do
    prefix="${prefix%$'\r'}"
    [ -z "$prefix" ] && continue
    case "$prefix" in
      \#*) continue ;;
    esac
    case "$path" in
      "$prefix"*) return 0 ;;
    esac
  done < "$list_file"
  return 1
}

classify_path() {
  local path="$1"
  if is_exact_in_file "$path" "$LOCAL_ONLY_LIST"; then
    echo "local"
    return
  fi
  if match_prefix "$path" "$LOCAL_PREFIXES"; then
    echo "local"
    return
  fi
  if match_prefix "$path" "$PUBLIC_PREFIXES"; then
    echo "public"
    return
  fi
  echo "unclassified"
}

fails=0
lines="$(get_changes || true)"

if [ -z "$lines" ]; then
  echo "[zone] no changes to review"
  exit 0
fi

echo "[zone] review mode=$MODE block_local=$BLOCK_LOCAL"

while IFS= read -r line; do
  [ -z "$line" ] && continue
  status="$(printf '%s' "$line" | awk '{print $1}')"
  path=""
  case "$status" in
    R*|C*)
      path="$(printf '%s' "$line" | awk '{print $3}')"
      ;;
    *)
      path="$(printf '%s' "$line" | awk '{print $2}')"
      ;;
  esac
  [ -n "$path" ] || continue

  zone="$(classify_path "$path")"
  echo "[zone] status=$status zone=$zone path=$path"

  if [ "$zone" = "unclassified" ]; then
    echo "[zone][FAIL] unclassified file: $path"
    fails=1
    continue
  fi

  if [ "$BLOCK_LOCAL" -eq 1 ] && [ "$zone" = "local" ]; then
    case "$status" in
      D*)
        # deleting local-only file is allowed
        ;;
      *)
        echo "[zone][FAIL] local-only file change blocked: status=$status path=$path"
        fails=1
        ;;
    esac
  fi
done <<< "$lines"

if [ "$fails" -ne 0 ]; then
  echo "[zone] review failed"
  exit 1
fi

echo "[zone] review passed"
exit 0
