#!/usr/bin/env bash
# Install and verify git guard hooks on coco build host.

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/setup_coco_guards_$(date +%Y%m%d_%H%M%S).log"

CONFIG_FILE="$HOME/.esg-deploy-config"
COCO_TARGET=""
REMOTE_DIR=""
MAX_RETRIES=3
DRY_RUN=0

usage() {
  cat <<USAGE
Usage:
  $SCRIPT_NAME [options]

Options:
  --config <path>             Config file (default: ~/.esg-deploy-config)
  --target <user@host>        Override coco target (default: COCO_USER@COCO_HOST from config)
  --remote-dir <path>         Override remote project dir (default: COCO_BUILD_DIR from config)
  --max-retries <n>           Retry count for each step (default: 3)
  --dry-run                   Print actions only
  -h, --help                  Show help

Config keys:
  COCO_USER, COCO_HOST, COCO_BUILD_DIR
USAGE
}

ts() {
  date '+%Y-%m-%d %H:%M:%S %z'
}

log() {
  printf '[%s] %s\n' "$(ts)" "$1" | tee -a "$LOG_FILE"
}

fail() {
  log "ERROR: $1"
  exit 1
}

require_bin() {
  local bin="$1"
  command -v "$bin" >/dev/null 2>&1 || fail "missing required command: $bin"
}

retry_cmd() {
  local label="$1"
  shift
  local attempt=1
  local rc=0
  while [ "$attempt" -le "$MAX_RETRIES" ]; do
    log "STEP=$label attempt=$attempt/$MAX_RETRIES cmd=$(printf '%q ' "$@")"
    if [ "$DRY_RUN" -eq 1 ]; then
      log "STEP=$label dry-run skip"
      return 0
    fi
    if "$@" >>"$LOG_FILE" 2>&1; then
      rc=0
    else
      rc=$?
    fi
    if [ "$rc" -eq 0 ]; then
      log "STEP=$label status=SUCCESS"
      return 0
    fi
    log "STEP=$label status=FAILED rc=$rc"
    attempt=$((attempt + 1))
    sleep 1
  done
  return "$rc"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --config)
      CONFIG_FILE="${2:-}"
      shift 2
      ;;
    --target)
      COCO_TARGET="${2:-}"
      shift 2
      ;;
    --remote-dir)
      REMOTE_DIR="${2:-}"
      shift 2
      ;;
    --max-retries)
      MAX_RETRIES="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
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

require_bin bash
require_bin ssh
require_bin rsync

if [ -f "$CONFIG_FILE" ]; then
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
else
  log "WARN: config file not found: $CONFIG_FILE"
fi

if [ -z "$COCO_TARGET" ]; then
  if [ -n "${COCO_USER:-}" ] && [ -n "${COCO_HOST:-}" ]; then
    COCO_TARGET="${COCO_USER}@${COCO_HOST}"
  fi
fi

if [ -z "$REMOTE_DIR" ] && [ -n "${COCO_BUILD_DIR:-}" ]; then
  REMOTE_DIR="$COCO_BUILD_DIR"
fi

[ -n "$COCO_TARGET" ] || fail "missing coco target (set --target or COCO_USER/COCO_HOST)"
[ -n "$REMOTE_DIR" ] || fail "missing remote dir (set --remote-dir or COCO_BUILD_DIR)"
case "$REMOTE_DIR" in
  /*) ;;
  *) fail "REMOTE_DIR must be absolute path, got: $REMOTE_DIR" ;;
esac

log "START $SCRIPT_NAME"
log "LOG_FILE=$LOG_FILE"
log "TARGET=$COCO_TARGET REMOTE_DIR=$REMOTE_DIR MAX_RETRIES=$MAX_RETRIES DRY_RUN=$DRY_RUN"

retry_cmd "preflight-coco" \
  bash "$PROJECT_DIR/scripts/preflight_safe_exec.sh" \
  --target "$COCO_TARGET" \
  --remote-dir "$REMOTE_DIR" \
  --preflight-only \
  || fail "preflight failed for coco target"

retry_cmd "prepare-remote-dirs" \
  ssh "$COCO_TARGET" \
  "set -eu; mkdir -p '$REMOTE_DIR' '$REMOTE_DIR/scripts' '$REMOTE_DIR/.guard'; test -d '$REMOTE_DIR/.git'" \
  || fail "remote directory is missing .git; initialize repo on coco first"

retry_cmd "sync-guard-files" \
  rsync -az \
  "$PROJECT_DIR/.guard/local-only-files.txt" \
  "$PROJECT_DIR/.guard/local-prefixes.txt" \
  "$PROJECT_DIR/.guard/public-prefixes.txt" \
  "$PROJECT_DIR/.guard/ZONE_POLICY.md" \
  "$COCO_TARGET:$REMOTE_DIR/.guard/" \
  || fail "failed to sync .guard policy files to coco"

retry_cmd "sync-guard-scripts" \
  rsync -az \
  "$PROJECT_DIR/scripts/install_git_guards.sh" \
  "$PROJECT_DIR/scripts/security_check.sh" \
  "$PROJECT_DIR/scripts/review_file_zones.sh" \
  "$PROJECT_DIR/scripts/review_push_guard.sh" \
  "$COCO_TARGET:$REMOTE_DIR/scripts/" \
  || fail "failed to sync guard scripts to coco"

retry_cmd "install-hooks" \
  ssh "$COCO_TARGET" \
  "set -eu; cd '$REMOTE_DIR'; chmod +x scripts/install_git_guards.sh scripts/security_check.sh scripts/review_file_zones.sh scripts/review_push_guard.sh; bash scripts/install_git_guards.sh" \
  || fail "failed to install hooks on coco"

retry_cmd "verify-hooks" \
  ssh "$COCO_TARGET" \
  "set -eu; test -x '$REMOTE_DIR/.git/hooks/pre-commit'; test -x '$REMOTE_DIR/.git/hooks/pre-push'; ls -l '$REMOTE_DIR/.git/hooks/pre-commit' '$REMOTE_DIR/.git/hooks/pre-push'" \
  || fail "hook verification failed on coco"

log "DONE: coco guards installed and verified"
log "END"
