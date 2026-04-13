#!/usr/bin/env bash
# Untrack files listed in .guard/local-only-files.txt while keeping local copies.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

LIST_FILE=".guard/local-only-files.txt"
if [ ! -f "$LIST_FILE" ]; then
  echo "[untrack] list not found: $LIST_FILE"
  exit 1
fi

removed=0
while IFS= read -r path; do
  [ -z "$path" ] && continue
  case "$path" in
    \#*) continue ;;
  esac

  if git ls-files --error-unmatch "$path" >/dev/null 2>&1; then
    git rm --cached -- "$path"
    removed=$((removed + 1))
  fi
done < "$LIST_FILE"

echo "[untrack] done, removed_from_index=$removed"
