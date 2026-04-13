#!/usr/bin/env bash
# Unified local -> coco -> (optional) deploy pipeline with preflight/retry/logging.

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/release_pipeline_$(date +%Y%m%d_%H%M%S).log"

CONFIG_FILE="$HOME/.esg-deploy-config"
BRANCH=""
MAX_RETRIES=3
SKIP_LOCAL_CHECKS=0
SKIP_COCO=0
SETUP_COCO_GUARDS=1
COCO_BUILD=1
DEPLOY_COCO=0
DEPLOY_VPS=0
NO_PUSH=0
DRY_RUN=0

COCO_TARGET=""
COCO_DIR=""
VPS_TARGET=""
VPS_DIR=""
DEPLOY_DOMAIN="${DEPLOY_DOMAIN:-}"
EXPECTED_PUBLIC_IP="${EXPECTED_PUBLIC_IP:-}"
LOCAL_HEAD_SHA=""

usage() {
  cat <<USAGE
Usage:
  $SCRIPT_NAME [options]

Core:
  --branch <name>             Git branch to push (default: current branch)
  --config <path>             Config file (default: ~/.esg-deploy-config)
  --max-retries <n>           Retry count per step (default: 3)
  --no-push                   Skip git push
  --dry-run                   Print actions only

Stage control:
  --skip-local-checks         Skip local security/review checks
  --skip-coco                 Skip coco sync/test stages
  --skip-coco-guards          Skip running setup_coco_guards.sh
  --skip-coco-build           Skip coco parallel build step
  --deploy-coco               Run docker compose up on coco after build
  --deploy-vps                Run remote deploy commands on VPS after coco stage

Help:
  -h, --help                  Show help

Config keys used:
  COCO_USER, COCO_HOST, COCO_BUILD_DIR
  VPS_USER, VPS_HOST, VPS_DEPLOY_DIR
  DEPLOY_DOMAIN, EXPECTED_PUBLIC_IP (optional)
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

sync_remote_scripts() {
  local label="$1"
  local target="$2"
  local remote_dir="$3"
  shift 3

  [ "$#" -gt 0 ] || return 0

  local local_paths=()
  local remote_checks=""
  local rel_path=""
  local base_name=""
  for rel_path in "$@"; do
    [ -f "$PROJECT_DIR/$rel_path" ] || fail "missing local sync file: $rel_path"
    local_paths+=("$PROJECT_DIR/$rel_path")
    base_name="$(basename "$rel_path")"
    remote_checks="$remote_checks test -x '$remote_dir/scripts/$base_name';"
  done

  retry_cmd "${label}-prepare" \
    ssh "$target" \
    "set -eu; mkdir -p '$remote_dir/scripts'" \
    || fail "failed to prepare remote script dir for $label"

  retry_cmd "${label}-rsync" \
    rsync -az "${local_paths[@]}" "$target:$remote_dir/scripts/" \
    || fail "failed to sync helper scripts for $label"

  retry_cmd "${label}-verify" \
    ssh "$target" \
    "set -eu; chmod +x '$remote_dir/scripts/'*.sh; $remote_checks" \
    || fail "failed to verify synced helper scripts for $label"
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
    --branch)
      BRANCH="${2:-}"
      shift 2
      ;;
    --config)
      CONFIG_FILE="${2:-}"
      shift 2
      ;;
    --max-retries)
      MAX_RETRIES="${2:-}"
      shift 2
      ;;
    --skip-local-checks)
      SKIP_LOCAL_CHECKS=1
      shift
      ;;
    --skip-coco)
      SKIP_COCO=1
      shift
      ;;
    --skip-coco-guards)
      SETUP_COCO_GUARDS=0
      shift
      ;;
    --skip-coco-build)
      COCO_BUILD=0
      shift
      ;;
    --deploy-coco)
      DEPLOY_COCO=1
      shift
      ;;
    --deploy-vps)
      DEPLOY_VPS=1
      shift
      ;;
    --no-push)
      NO_PUSH=1
      shift
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

cd "$PROJECT_DIR"

require_bin bash
require_bin git
require_bin ssh
require_bin rsync

if [ -f "$CONFIG_FILE" ]; then
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
else
  log "WARN: config file not found: $CONFIG_FILE"
fi

if [ -z "$BRANCH" ]; then
  BRANCH="$(git rev-parse --abbrev-ref HEAD)"
fi

[ -n "$BRANCH" ] || fail "failed to resolve branch"
if [ "$BRANCH" = "HEAD" ]; then
  fail "detached HEAD is not supported; checkout a branch first"
fi

LOCAL_HEAD_SHA="$(git rev-parse HEAD)"
[ -n "$LOCAL_HEAD_SHA" ] || fail "failed to resolve local HEAD sha"

if [ -n "${COCO_USER:-}" ] && [ -n "${COCO_HOST:-}" ]; then
  COCO_TARGET="${COCO_USER}@${COCO_HOST}"
fi
COCO_DIR="${COCO_BUILD_DIR:-}"

if [ -n "${VPS_USER:-}" ] && [ -n "${VPS_HOST:-}" ]; then
  VPS_TARGET="${VPS_USER}@${VPS_HOST}"
fi
VPS_DIR="${VPS_DEPLOY_DIR:-}"

if [ "$SKIP_COCO" -eq 0 ]; then
  [ -n "$COCO_TARGET" ] || fail "missing COCO_USER/COCO_HOST (or set in config)"
  [ -n "$COCO_DIR" ] || fail "missing COCO_BUILD_DIR"
  case "$COCO_DIR" in
    /*) ;;
    *) fail "COCO_BUILD_DIR must be absolute path, got: $COCO_DIR" ;;
  esac
fi

if [ "$DEPLOY_VPS" -eq 1 ]; then
  [ -n "$VPS_TARGET" ] || fail "missing VPS_USER/VPS_HOST (or set in config)"
  [ -n "$VPS_DIR" ] || fail "missing VPS_DEPLOY_DIR"
  case "$VPS_DIR" in
    /*) ;;
    *) fail "VPS_DEPLOY_DIR must be absolute path, got: $VPS_DIR" ;;
  esac
fi

log "START $SCRIPT_NAME"
log "LOG_FILE=$LOG_FILE"
log "BRANCH=$BRANCH MAX_RETRIES=$MAX_RETRIES DRY_RUN=$DRY_RUN"
log "LOCAL_HEAD_SHA=$LOCAL_HEAD_SHA"
log "FLAGS skip_local=$SKIP_LOCAL_CHECKS skip_coco=$SKIP_COCO setup_coco_guards=$SETUP_COCO_GUARDS coco_build=$COCO_BUILD deploy_coco=$DEPLOY_COCO deploy_vps=$DEPLOY_VPS no_push=$NO_PUSH"

if [ "$SKIP_LOCAL_CHECKS" -eq 0 ]; then
  retry_cmd "local-security-check" bash "$PROJECT_DIR/scripts/security_check.sh" \
    || fail "local security check failed"
  retry_cmd "local-push-review" bash "$PROJECT_DIR/scripts/review_push_guard.sh" origin/main \
    || fail "local push review guard failed"
fi

if [ "$NO_PUSH" -eq 0 ]; then
  retry_cmd "git-push" git push -u origin "$BRANCH" \
    || fail "git push failed"
fi

if [ "$SKIP_COCO" -eq 0 ]; then
  retry_cmd "coco-preflight" \
    bash "$PROJECT_DIR/scripts/preflight_safe_exec.sh" \
    --target "$COCO_TARGET" \
    --remote-dir "$COCO_DIR" \
    --preflight-only \
    || fail "coco preflight failed"

  if [ "$SETUP_COCO_GUARDS" -eq 1 ]; then
    retry_cmd "setup-coco-guards" \
      bash "$PROJECT_DIR/scripts/setup_coco_guards.sh" \
      --config "$CONFIG_FILE" \
      --target "$COCO_TARGET" \
      --remote-dir "$COCO_DIR" \
      --max-retries "$MAX_RETRIES" \
      || fail "setup coco guards failed"
  fi

  retry_cmd "sync-to-coco" \
    rsync -az --delete \
    --exclude '.git/' \
    --exclude '.venv/' \
    --exclude 'node_modules/' \
    --exclude 'logs/' \
    --exclude '.omx/' \
    --exclude '.codex/' \
    --exclude '.claude/' \
    --exclude '.cursor/' \
    --exclude '.gemini/' \
    --exclude '.local/' \
    --exclude '.tmp/' \
    --exclude 'tmp/' \
    --exclude 'data/' \
    --exclude 'reports/' \
    --exclude '.env' \
    --exclude '.env.*' \
    "$PROJECT_DIR/" \
    "$COCO_TARGET:$COCO_DIR/" \
    || fail "rsync to coco failed"

  retry_cmd "coco-smoke-check" \
    ssh "$COCO_TARGET" \
    "set -eu; cd '$COCO_DIR'; bash scripts/security_check.sh; test -f docker-compose.prod.yml; test -f frontend/package.json; test -x scripts/review_push_guard.sh" \
    || fail "coco smoke check failed"

  if [ "$COCO_BUILD" -eq 1 ]; then
REMOTE_BUILD_CMD="$(cat <<EOF
set -eu
cd '$COCO_DIR'
mkdir -p logs
(
  docker build -t esg-toolkit:latest . > logs/docker-build.log 2>&1
) &
docker_pid=\$!
(
  cd frontend
  npm ci > ../logs/frontend-npm-ci.log 2>&1
  npm run build > ../logs/frontend-build.log 2>&1
) &
frontend_pid=\$!
wait \$docker_pid
wait \$frontend_pid
EOF
)"
    retry_cmd "coco-parallel-build" \
      ssh "$COCO_TARGET" "$REMOTE_BUILD_CMD" \
      || fail "coco parallel build failed"
  fi

  if [ "$DEPLOY_COCO" -eq 1 ]; then
    retry_cmd "coco-deploy" \
      bash "$PROJECT_DIR/scripts/preflight_safe_exec.sh" \
      --target "$COCO_TARGET" \
      --remote-dir "$COCO_DIR" \
      --exec "cd $COCO_DIR && {{COMPOSE}} -f docker-compose.prod.yml up -d" \
      || fail "coco deploy failed"
  fi
fi

if [ "$DEPLOY_VPS" -eq 1 ]; then
  VPS_PREFLIGHT_ARGS=(
    --target "$VPS_TARGET"
    --remote-dir "$VPS_DIR"
  )
  PREFLIGHT_ARGS=(
    --target "$VPS_TARGET"
    --remote-dir "$VPS_DIR"
  )
  if [ -n "$DEPLOY_DOMAIN" ]; then
    VPS_PREFLIGHT_ARGS+=(--domain "$DEPLOY_DOMAIN")
    PREFLIGHT_ARGS+=(--domain "$DEPLOY_DOMAIN")
  fi
  if [ -n "$EXPECTED_PUBLIC_IP" ]; then
    VPS_PREFLIGHT_ARGS+=(--expected-ip "$EXPECTED_PUBLIC_IP")
    PREFLIGHT_ARGS+=(--expected-ip "$EXPECTED_PUBLIC_IP")
  fi
  PREFLIGHT_ARGS+=(
    --exec "cd $VPS_DIR && {{COMPOSE}} -f docker-compose.prod.yml up -d"
    --exec "curl -fsS http://localhost:8001/health"
  )

  retry_cmd "vps-preflight" \
    bash "$PROJECT_DIR/scripts/preflight_safe_exec.sh" "${VPS_PREFLIGHT_ARGS[@]}" \
    --preflight-only \
    || fail "vps preflight failed"

  retry_cmd "vps-git-sha-align" \
    ssh "$VPS_TARGET" \
    "set -eu; cd '$VPS_DIR'; remote_sha=\$(git rev-parse HEAD); [ \"\$remote_sha\" = '$LOCAL_HEAD_SHA' ]" \
    || fail "vps git sha mismatch (remote != local HEAD). sync/push code first, then deploy"

  sync_remote_scripts "sync-vps-helper-scripts" "$VPS_TARGET" "$VPS_DIR" \
    "scripts/write_deploy_fingerprint.sh"

  retry_cmd "vps-deploy" \
    bash "$PROJECT_DIR/scripts/preflight_safe_exec.sh" "${PREFLIGHT_ARGS[@]}" \
    || fail "vps deploy failed"

  retry_cmd "stamp-vps-fingerprint" \
    bash "$PROJECT_DIR/scripts/stamp_remote_fingerprint.sh" \
    --host "$VPS_TARGET" \
    --repo-dir "$VPS_DIR" \
    --env "vps-prod" \
    --source "release_pipeline.sh" \
    || fail "stamping vps fingerprint failed"

  retry_cmd "verify-vps-fingerprint" \
    ssh "$VPS_TARGET" \
    "set -eu; test -s '$VPS_DIR/.deploy-fingerprint.json'" \
    || fail "vps fingerprint file verification failed"
fi

log "PIPELINE_STATUS=SUCCESS"
log "END"
