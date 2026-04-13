#!/usr/bin/env bash
# Write deployment fingerprint JSON for traceability.

set -euo pipefail

REPO_DIR=""
ENV_NAME=""
SOURCE_NAME="manual"
TARGET_FILE=""
IMAGE_NAME=""

usage() {
  cat <<USAGE
Usage:
  scripts/write_deploy_fingerprint.sh --env <name> [options]

Required:
  --env <name>                 Deployment environment label (e.g. coco-test, vps-prod)

Optional:
  --repo-dir <path>            Repo path (default: git toplevel)
  --source <name>              Source trigger label (default: manual)
  --target <path>              Output JSON file (default: <repo>/.deploy-fingerprint.json)
  --image <image>              Explicit image name/tag (default: auto-detect running container)
  -h, --help                   Show help
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --repo-dir)
      REPO_DIR="${2:-}"
      shift 2
      ;;
    --env)
      ENV_NAME="${2:-}"
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

if [ -z "$ENV_NAME" ]; then
  echo "ERROR: --env is required" >&2
  exit 2
fi

if [ -z "$REPO_DIR" ]; then
  REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi

if [ -z "$TARGET_FILE" ]; then
  TARGET_FILE="$REPO_DIR/.deploy-fingerprint.json"
fi

if [ ! -d "$REPO_DIR/.git" ]; then
  echo "ERROR: repo dir is not a git repo: $REPO_DIR" >&2
  exit 2
fi

GIT_SHA="$(git -C "$REPO_DIR" rev-parse HEAD)"
GIT_BRANCH="$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)"
GIT_TAG="$(git -C "$REPO_DIR" describe --tags --exact-match 2>/dev/null || true)"
DEPLOYED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DEPLOYED_BY="$(whoami)@$(hostname)"

if [ -z "$IMAGE_NAME" ] && command -v docker >/dev/null 2>&1; then
  IMAGE_NAME="$(docker ps --filter name=esg-research-toolkit --format '{{.Image}}' 2>/dev/null | head -n1 || true)"
fi

ENV_NAME="$ENV_NAME" \
GIT_SHA="$GIT_SHA" \
GIT_BRANCH="$GIT_BRANCH" \
GIT_TAG="$GIT_TAG" \
DEPLOYED_AT="$DEPLOYED_AT" \
DEPLOYED_BY="$DEPLOYED_BY" \
SOURCE_NAME="$SOURCE_NAME" \
IMAGE_NAME="$IMAGE_NAME" \
TARGET_FILE="$TARGET_FILE" \
python3 - <<'PY'
import json
import os
from pathlib import Path

payload = {
  "environment": os.environ["ENV_NAME"],
  "git_sha": os.environ["GIT_SHA"],
  "git_branch": os.environ["GIT_BRANCH"],
  "git_tag": os.environ["GIT_TAG"],
  "deployed_at_utc": os.environ["DEPLOYED_AT"],
  "deployed_by": os.environ["DEPLOYED_BY"],
  "source": os.environ["SOURCE_NAME"],
  "image": os.environ["IMAGE_NAME"],
}

target = Path(os.environ["TARGET_FILE"])
target.parent.mkdir(parents=True, exist_ok=True)
tmp = target.with_suffix(target.suffix + ".tmp")
tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
tmp.replace(target)
print(target)
PY

echo "Fingerprint written: $TARGET_FILE"
