#!/usr/bin/env bash
# Repository hygiene audit. Read-only: prints tracked, untracked, ignored,
# large, and policy-sensitive paths without deleting or modifying files.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

BASE_REF="${1:-origin/main}"

echo "[audit] repo=$(basename "$PROJECT_DIR")"
echo "[audit] branch=$(git branch --show-current 2>/dev/null || true)"
echo "[audit] head=$(git rev-parse --short HEAD)"

if git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
  echo "[audit] base_ref=$BASE_REF"
  echo "[audit] ahead_count=$(git rev-list --count "$BASE_REF"..HEAD)"
  echo "[audit] diff_stat"
  git diff --stat "$BASE_REF"...HEAD || true
else
  echo "[audit][WARN] base ref not found: $BASE_REF"
fi

echo
echo "[audit] status"
git status --short --branch

echo
echo "[audit] tracked_count=$(git ls-files | wc -l | tr -d ' ')"
echo "[audit] untracked_not_ignored"
git ls-files --others --exclude-standard

echo
echo "[audit] ignored_sample"
git status --short --ignored | sed -n '1,120p'

echo
echo "[audit] tracked policy-sensitive paths"
git ls-files | rg -n \
  '(^\.local/|^\.omx/|^\.codex/|^\.claude/|^\.cursor/|^\.gemini/|^dev-local/|^runtime/|^logs/|^reports/|^data/|(^|/)\.env($|\.)|\.pem$|\.key$|\.p12$|\.sqlite3?$|\.db$|credentials|secrets|api_keys|config\.private)' \
  || true

echo
echo "[audit] tracked large files >=5MiB"
git ls-files -z | xargs -0 -I{} sh -c '
  [ -f "$1" ] || exit 0
  size=$(wc -c < "$1" | tr -d " ")
  if [ "$size" -ge 5242880 ]; then
    printf "%s\t%s\n" "$size" "$1"
  fi
' sh {} | sort -nr || true

echo
echo "[audit] guard policy files"
for policy in .guard/local-only-files.txt .guard/local-prefixes.txt .guard/public-prefixes.txt .gitignore; do
  if [ -f "$policy" ]; then
    echo "[audit] present $policy"
  else
    echo "[audit][WARN] missing $policy"
  fi
done

echo
echo "[audit] done"
