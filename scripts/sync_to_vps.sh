#!/usr/bin/env bash
#
# sync_to_vps.sh — push the latest verified export to the demo VPS.
#
# Workflow:
#   1. Run scripts/export_verified.py locally → writes to data/exports/<timestamp>/
#   2. rsync that directory to <VPS_HOST>:<VPS_PATH>/exports/<timestamp>/
#   3. SSH into VPS, run import + benchmark recompute
#
# Usage:
#   ./scripts/sync_to_vps.sh $VPS_USER@$VPS_HOST /opt/esg-toolkit
#
# Prerequisites on VPS:
#   - python venv at /opt/esg-toolkit/.venv with backend deps installed
#   - scripts/import_verified.py present (mirror of repo)
#   - uvicorn running, /benchmarks/recompute reachable on 127.0.0.1:8000
#
# Safety:
#   - never auto-runs; you call it explicitly when you've reviewed the export
#   - dry-run: SYNC_DRY_RUN=1 ./scripts/sync_to_vps.sh ...

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <user@host> <remote_path>" >&2
    echo "Example: $0 deploy@1.2.3.4 /opt/esg-toolkit" >&2
    exit 64
fi

VPS_HOST="$1"
VPS_PATH="$2"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
EXPORT_ROOT="${ROOT}/data/exports"
DRY_RUN="${SYNC_DRY_RUN:-0}"

echo "→ exporting verified rows…"
"$PYTHON" "${ROOT}/scripts/export_verified.py" --out "${EXPORT_ROOT}"

LATEST="$(ls -1 "${EXPORT_ROOT}" | sort | tail -n 1)"
if [ -z "${LATEST}" ]; then
    echo "ERROR: no export directory found under ${EXPORT_ROOT}" >&2
    exit 1
fi
LOCAL_DIR="${EXPORT_ROOT}/${LATEST}"
REMOTE_DIR="${VPS_PATH}/exports/${LATEST}"

echo "→ local export:  ${LOCAL_DIR}"
echo "→ remote target: ${VPS_HOST}:${REMOTE_DIR}"

if [ "${DRY_RUN}" = "1" ]; then
    echo "DRY RUN — skipping rsync + ssh"
    cat "${LOCAL_DIR}/manifest.json"
    exit 0
fi

ssh "${VPS_HOST}" "mkdir -p '${REMOTE_DIR}'"
rsync -avz --checksum "${LOCAL_DIR}/" "${VPS_HOST}:${REMOTE_DIR}/"

echo "→ triggering remote import + benchmark recompute…"
ssh "${VPS_HOST}" bash -s <<EOF
set -euo pipefail
cd "${VPS_PATH}"
.venv/bin/python scripts/import_verified.py "${REMOTE_DIR}"
curl -sf -X POST http://127.0.0.1:8000/benchmarks/recompute || echo "WARN: recompute call failed"
echo "Remote import complete."
EOF

echo "✅ sync done."
