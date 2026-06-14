#!/usr/bin/env bash
# guard_lib.sh — shared content/structure guards for the commit and push gates.
#
# Both scripts/security_check.sh (pre-commit, staged scope) and
# scripts/review_push_guard.sh (pre-push, range scope) source this file so the
# two gates enforce ONE rule set instead of two copies that silently drift.
#
# Caller contract (set before calling any guard_* function):
#   GUARD_SCOPE      diff selector passed straight to `git diff`,
#                    e.g. "--cached"  or  "origin/main..HEAD"
#   GUARD_MODE_ARGS  array of flags for the external sub-guards,
#                    e.g. ("--staged")  or  ("--range" "origin/main..HEAD")
#   GUARD_FAILED     integer initialised to 0; blocking checks set it to 1.
#                    Warn-only checks (⚠️) never touch it.

# Added (+) lines in scope, minus the +++ header. Extra args become pathspecs.
_guard_added() {
  git diff "$GUARD_SCOPE" "$@" | grep -E '^\+' | grep -vE '^\+\+\+' || true
}

_guard_names() {
  git diff "$GUARD_SCOPE" --name-only || true
}

# --- blocking checks -------------------------------------------------------

guard_sensitive_filenames() {
  local patterns=(
    '\.env$' '\.env\.local$' '\.env\.production$'
    '.*_key$' '.*_secret$' '.*token.*'
    'credentials\.json' 'secrets\.json'
    '\.omx/' '\.codex/' '\.claude/'
    'PERSONAL_' 'PRIVATE_' '_PRIVATE\.' '_PERSONAL\.'
  )
  local names hits p
  names="$(_guard_names)"
  for p in "${patterns[@]}"; do
    hits="$(printf '%s\n' "$names" | grep -E "$p" || true)"
    if [ -n "$hits" ]; then
      echo "❌ sensitive file in changes: $hits"
      GUARD_FAILED=1
    fi
  done
}

guard_local_only() {
  local list=".guard/local-only-files.txt"
  [ -f "$list" ] || return 0
  local names f status
  names="$(_guard_names)"
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    case "$f" in \#*) continue ;; esac
    printf '%s\n' "$names" | grep -Fxq "$f" || continue
    # Deleting a local-only file is allowed; A/M/R/C/T/U/X/B are not.
    status="$(git diff "$GUARD_SCOPE" --name-status -- "$f" | awk 'NR==1{print $1}')"
    if [ -n "$status" ] && [ "$status" != "D" ]; then
      echo "❌ local-only file changed (status=$status): $f"
      GUARD_FAILED=1
    fi
  done < "$list"
}

guard_api_key() {
  local hits
  hits="$(_guard_added -- '*.py' '*.toml' '*.yaml' '*.yml' '*.json' '*.sh' \
    | grep -iE "(api[_-]?key|secret[_-]?key|openai[_-]?key|anthropic[_-]?key)[[:space:]]*=[[:space:]]*['\"][a-zA-Z0-9_-]{20,}" || true)"
  if [ -n "$hits" ]; then
    echo "❌ possible hard-coded API key (code/config/script):"
    printf '%s\n' "$hits" | head -5
    GUARD_FAILED=1
  fi
}

guard_relay_endpoints() {
  local hits
  hits="$(_guard_added | grep -E '(relay\.nf\.video|api\.longcat\.chat|ark\.cn-beijing\.volces\.com)' || true)"
  if [ -n "$hits" ]; then
    echo "❌ relay/third-party API endpoint not allowed on GitHub:"
    printf '%s\n' "$hits" | head -5
    GUARD_FAILED=1
  fi
}

guard_openai_base_url() {
  local hits
  hits="$(_guard_added \
    | grep -E 'OPENAI_BASE_URL[[:space:]]*=[[:space:]]*https?://' \
    | grep -vE 'OPENAI_BASE_URL[[:space:]]*=[[:space:]]*https://api\.openai\.com/v1' || true)"
  if [ -n "$hits" ]; then
    echo "❌ OPENAI_BASE_URL must be the official endpoint or omitted:"
    printf '%s\n' "$hits" | head -5
    GUARD_FAILED=1
  fi
}

guard_prose() {
  local patterns=("现在你可以睡觉" "祝你好梦" "联系方式" "明天醒来后")
  local p hits
  for p in "${patterns[@]}"; do
    hits="$(_guard_added -- '*.md' '*.txt' | grep -F "$p" || true)"
    if [ -n "$hits" ]; then
      echo "❌ non-engineering prose blocked: $p"
      GUARD_FAILED=1
    fi
  done
}

guard_email() {
  local re="[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
  local hits
  hits="$(_guard_added | grep -E "$re" | grep -v "example@" || true)"
  if [ -n "$hits" ]; then
    echo "❌ email address detected (use an issue link or example@):"
    printf '%s\n' "$hits" | head -3
    GUARD_FAILED=1
  fi
}

# --- warn-only checks (never block) ---------------------------------------

guard_internal_ip() {
  local hits
  hits="$(_guard_added | grep -E '(192\.168\.[0-9]{1,3}\.[0-9]{1,3}|10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3})' || true)"
  if [ -n "$hits" ]; then
    echo "⚠️  internal IP address found — confirm whether it needs redacting:"
    printf '%s\n' "$hits" | head -3
  fi
}

guard_abs_path() {
  local hits
  hits="$(_guard_added | grep -E '/Users/[^/]+/' | grep -v "$HOME/" || true)"
  if [ -n "$hits" ]; then
    echo "⚠️  absolute path of another user found:"
    printf '%s\n' "$hits" | head -3
  fi
}

# --- external sub-guards (fail-closed, quiet on success) ------------------
# A missing/failing sub-guard blocks rather than silently passing.

guard_subguards() {
  local out; out="$(mktemp)"
  if ! scripts/review_file_zones.sh "${GUARD_MODE_ARGS[@]}" --block-local >"$out" 2>&1; then
    echo "❌ file-zone audit failed (unclassified or local-only change)"; cat "$out"; GUARD_FAILED=1
  fi
  if ! scripts/secret_guard.sh "${GUARD_MODE_ARGS[@]}" >"$out" 2>&1; then
    echo "❌ secret guard failed"; cat "$out"; GUARD_FAILED=1
  fi
  if ! scripts/local_boundary_guard.sh "${GUARD_MODE_ARGS[@]}" --skip-zone-review >"$out" 2>&1; then
    echo "❌ local boundary guard failed"; cat "$out"; GUARD_FAILED=1
  fi
  rm -f "$out"
}

# Run every shared content check in one call.
guard_content_all() {
  guard_sensitive_filenames
  guard_local_only
  guard_api_key
  guard_relay_endpoints
  guard_openai_base_url
  guard_prose
  guard_email
  guard_internal_ip
  guard_abs_path
}
