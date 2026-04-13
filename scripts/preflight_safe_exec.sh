#!/usr/bin/env bash
# preflight_safe_exec.sh
# Unified preflight + self-heal execution template for remote deployment tasks.

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/preflight_exec_$(date +%Y%m%d_%H%M%S).log"

TARGET_HOST=""
REMOTE_DIR=""
EXPECTED_DOMAIN=""
EXPECTED_IP=""
MAX_RETRIES=3
PREFLIGHT_ONLY=0

declare -a EXEC_CMDS

usage() {
  cat <<USAGE
Usage:
  $SCRIPT_NAME --target <user@host> [options]

Required:
  --target <user@host>        Remote SSH target

Optional:
  --remote-dir <path>         Remote project directory to verify
  --domain <fqdn>             Domain used for host-header checks
  --expected-ip <ip>          Expected DNS A record (warning-only if mismatch)
  --max-retries <n>           Retry count for each exec command (default: 3)
  --exec <cmd>                Remote command to execute (can be repeated)
  --preflight-only            Run checks only, do not execute commands
  -h, --help                  Show help

Template tips:
  1) Use explicit target (user@ip), avoid local SSH aliases.
  2) Use {{COMPOSE}} placeholder in --exec commands.
     It auto-resolves to "docker compose" or "docker-compose".

Example:
  $SCRIPT_NAME \
    --target root@<vps-host-or-ip> \
    --remote-dir /opt/esg-research-toolkit \
    --domain esg.meichen.beauty \
    --expected-ip <expected-public-ip> \
    --exec "cd /opt/esg-research-toolkit && {{COMPOSE}} -f docker-compose.prod.yml ps"
USAGE
}

ts() {
  date '+%Y-%m-%d %H:%M:%S %z'
}

log() {
  printf '[%s] %s\n' "$(ts)" "$1" | tee -a "$LOG_FILE"
}

require_bin() {
  local bin="$1"
  command -v "$bin" >/dev/null 2>&1 || {
    log "ERROR: missing required command: $bin"
    exit 2
  }
}

is_alias_host() {
  local host_part="$1"
  case "$host_part" in
    *.*|*:* ) return 1 ;;
    * ) return 0 ;;
  esac
}

classify_failure() {
  local content="$1"
  case "$content" in
    *"Operation not permitted"* ) echo "SSH_BLOCKED_OR_SANDBOX" ;;
    *"Could not resolve hostname"*|*"Temporary failure in name resolution"* ) echo "HOSTNAME_RESOLUTION_FAILURE" ;;
    *"Permission denied"* ) echo "AUTH_OR_PERMISSION_DENIED" ;;
    *"unknown shorthand flag: 'f' in -f"* ) echo "DOCKER_COMPOSE_VARIANT_MISMATCH" ;;
    *"Illegal option -o pipefail"* ) echo "REMOTE_SHELL_NOT_BASH" ;;
    *"404 Not Found"* ) echo "HOST_HEADER_OR_ROUTE_MISMATCH" ;;
    *"parse error: Invalid numeric literal"* ) echo "NON_JSON_RESPONSE_TO_JQ" ;;
    * ) echo "UNKNOWN" ;;
  esac
}

run_ssh() {
  local cmd="$1"
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$TARGET_HOST" "$cmd"
}

PREFLIGHT_OK=1
COMPOSE_CMD=""

preflight_target_shape() {
  if [[ "$TARGET_HOST" != *"@"* ]]; then
    log "ERROR: --target must be in user@host format"
    PREFLIGHT_OK=0
    return
  fi
  local host_part="${TARGET_HOST#*@}"
  if is_alias_host "$host_part"; then
    log "WARN: target host looks like SSH alias ($host_part). Prefer explicit IP/FQDN to avoid resolver drift."
  else
    log "OK: target host uses explicit address ($host_part)"
  fi
}

preflight_ssh_connectivity() {
  log "PREFLIGHT: ssh connectivity"
  local out rc
  out="$(run_ssh "echo __SSH_OK__ && hostname && id -un" 2>&1)"
  rc=$?
  printf '%s\n' "$out" >> "$LOG_FILE"
  if [ $rc -ne 0 ] || ! printf '%s' "$out" | grep -q "__SSH_OK__"; then
    log "ERROR: ssh connectivity failed (reason=$(classify_failure "$out"))"
    PREFLIGHT_OK=0
    return
  fi
  log "OK: ssh connectivity"
}

preflight_remote_dir() {
  [ -z "$REMOTE_DIR" ] && return 0
  log "PREFLIGHT: remote directory exists ($REMOTE_DIR)"
  if run_ssh "test -d '$REMOTE_DIR'" >> "$LOG_FILE" 2>&1; then
    log "OK: remote directory exists"
  else
    log "ERROR: remote directory missing"
    PREFLIGHT_OK=0
  fi
}

preflight_compose_variant() {
  log "PREFLIGHT: detect docker compose variant"
  local out rc
  out="$(run_ssh "if docker compose version >/dev/null 2>&1; then echo 'docker compose'; elif docker-compose version >/dev/null 2>&1; then echo 'docker-compose'; else echo 'missing'; fi" 2>&1)"
  rc=$?
  printf '%s\n' "$out" >> "$LOG_FILE"
  if [ $rc -ne 0 ] || [ "$out" = "missing" ]; then
    log "ERROR: docker compose command not found on remote"
    PREFLIGHT_OK=0
    return
  fi
  COMPOSE_CMD="$out"
  log "OK: compose command = $COMPOSE_CMD"
}

preflight_shell_compat() {
  log "PREFLIGHT: remote /bin/sh compatibility"
  if run_ssh "sh -c 'set -o pipefail' >/dev/null 2>&1" >> "$LOG_FILE" 2>&1; then
    log "OK: remote sh supports pipefail"
  else
    log "WARN: remote sh may not support pipefail; use POSIX-safe scripts"
  fi
}

preflight_dns() {
  [ -z "$EXPECTED_DOMAIN" ] && return 0
  log "PREFLIGHT: dns lookup ($EXPECTED_DOMAIN)"
  local out
  out="$(run_ssh "nslookup '$EXPECTED_DOMAIN' 2>/dev/null || true")"
  printf '%s\n' "$out" >> "$LOG_FILE"

  local ips
  ips="$(printf '%s\n' "$out" | grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}' | sort -u | tr '\n' ' ' | sed 's/ *$//')"
  if [ -z "$ips" ]; then
    log "WARN: no IPv4 records parsed for $EXPECTED_DOMAIN"
    return
  fi
  log "INFO: dns ipv4 => $ips"

  if [ -n "$EXPECTED_IP" ]; then
    if printf '%s\n' "$ips" | grep -Eq "(^| )${EXPECTED_IP}( |$)"; then
      log "OK: expected IP found in DNS"
    else
      log "WARN: DNS does not include expected IP $EXPECTED_IP (external routing may be in front, e.g. CDN)"
    fi
  fi
}

preflight_host_header() {
  [ -z "$EXPECTED_DOMAIN" ] && return 0
  log "PREFLIGHT: host-header local check"
  local out rc code
  out="$(run_ssh "curl -I -H 'Host: $EXPECTED_DOMAIN' http://127.0.0.1/ | head -n 1" 2>&1)"
  rc=$?
  printf '%s\n' "$out" >> "$LOG_FILE"
  if [ $rc -ne 0 ]; then
    log "WARN: host-header check command failed"
    return
  fi
  code="$(printf '%s\n' "$out" | grep -Eo 'HTTP/[0-9.]+ [0-9]+' | awk '{print $2}' | head -n 1 || true)"
  case "$code" in
    200|301|302)
      log "OK: host-header frontend status=$code"
      ;;
    *)
      log "WARN: host-header frontend unexpected status=$code"
      ;;
  esac
}

safe_exec_one() {
  local raw_cmd="$1"
  local cmd="$raw_cmd"
  if [ -n "$COMPOSE_CMD" ]; then
    cmd="${cmd//\{\{COMPOSE\}\}/$COMPOSE_CMD}"
  fi

  local attempt out rc reason
  for ((attempt=1; attempt<=MAX_RETRIES; attempt++)); do
    log "EXEC attempt=$attempt cmd=$cmd"
    out="$(run_ssh "$cmd" 2>&1)"
    rc=$?
    printf '%s\n' "$out" >> "$LOG_FILE"

    if [ $rc -eq 0 ]; then
      log "EXEC result=SUCCESS attempt=$attempt"
      return 0
    fi

    reason="$(classify_failure "$out")"
    log "EXEC result=FAILED attempt=$attempt rc=$rc reason=$reason"
    sleep 1
  done

  return 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --target)
      TARGET_HOST="${2:-}"
      shift 2
      ;;
    --remote-dir)
      REMOTE_DIR="${2:-}"
      shift 2
      ;;
    --domain)
      EXPECTED_DOMAIN="${2:-}"
      shift 2
      ;;
    --expected-ip)
      EXPECTED_IP="${2:-}"
      shift 2
      ;;
    --max-retries)
      MAX_RETRIES="${2:-}"
      shift 2
      ;;
    --exec)
      EXEC_CMDS+=("${2:-}")
      shift 2
      ;;
    --preflight-only)
      PREFLIGHT_ONLY=1
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

if [ -z "$TARGET_HOST" ]; then
  usage
  exit 2
fi

require_bin ssh
require_bin grep
require_bin awk
require_bin sed
require_bin curl

log "START $SCRIPT_NAME"
log "LOG_FILE=$LOG_FILE"
log "TARGET_HOST=$TARGET_HOST REMOTE_DIR=${REMOTE_DIR:-<none>} DOMAIN=${EXPECTED_DOMAIN:-<none>} EXPECTED_IP=${EXPECTED_IP:-<none>}"

preflight_target_shape
preflight_ssh_connectivity
preflight_remote_dir
preflight_compose_variant
preflight_shell_compat
preflight_dns
preflight_host_header

if [ "$PREFLIGHT_OK" -ne 1 ]; then
  log "PREFLIGHT_STATUS: FAILED"
  exit 1
fi
log "PREFLIGHT_STATUS: SUCCESS"

if [ "$PREFLIGHT_ONLY" -eq 1 ]; then
  log "END (preflight only)"
  exit 0
fi

if [ "${#EXEC_CMDS[@]}" -eq 0 ]; then
  log "WARN: no --exec commands provided"
  log "END"
  exit 0
fi

all_ok=1
for c in "${EXEC_CMDS[@]}"; do
  if ! safe_exec_one "$c"; then
    all_ok=0
  fi
done

if [ "$all_ok" -eq 1 ]; then
  log "EXEC_STATUS: SUCCESS"
  exit 0
fi

log "EXEC_STATUS: FAILED"
exit 1
