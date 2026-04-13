#!/usr/bin/env bash
# Stamp deployment fingerprint on a remote host over SSH.

set -euo pipefail

HOST=""
ENV_NAME=""
REPO_DIR="/opt/esg-research-toolkit"
SOURCE_NAME="remote-manual"
TARGET_FILE=""
IMAGE_NAME=""

usage() {
  cat <<USAGE
Usage:
  scripts/stamp_remote_fingerprint.sh --host <user@host> --env <name> [options]

Required:
  --host <user@host>          SSH target
  --env <name>                Environment label (e.g. coco-test, vps-prod)

Optional:
  --repo-dir <path>           Remote repo dir (default: /opt/esg-research-toolkit)
  --source <name>             Source label (default: remote-manual)
  --target <path>             Remote output file path
  --image <image>             Explicit image value for fingerprint
  -h, --help                  Show help
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --host)
      HOST="${2:-}"
      shift 2
      ;;
    --env)
      ENV_NAME="${2:-}"
      shift 2
      ;;
    --repo-dir)
      REPO_DIR="${2:-}"
      shift 2
      ;;
    --source)
      SOURCE_NAME="${2:-}"
      shift 2
      ;;
    --target)
      TARGET_FILE="${2:-}"
      shift 2
      ;;
    --image)
      IMAGE_NAME="${2:-}"
      shift 2
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

[ -n "$HOST" ] || { echo "ERROR: --host is required" >&2; exit 2; }
[ -n "$ENV_NAME" ] || { echo "ERROR: --env is required" >&2; exit 2; }

REMOTE_CMD=("$REPO_DIR/scripts/write_deploy_fingerprint.sh" "--repo-dir" "$REPO_DIR" "--env" "$ENV_NAME" "--source" "$SOURCE_NAME")
if [ -n "$TARGET_FILE" ]; then
  REMOTE_CMD+=("--target" "$TARGET_FILE")
fi
if [ -n "$IMAGE_NAME" ]; then
  REMOTE_CMD+=("--image" "$IMAGE_NAME")
fi

# shellcheck disable=SC2029
ssh "$HOST" "$(printf '%q ' "${REMOTE_CMD[@]}")"
