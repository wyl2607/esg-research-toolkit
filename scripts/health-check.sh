#!/usr/bin/env bash
# health-check.sh - ESG Toolkit health checks

set -euo pipefail

API_URL="http://127.0.0.1:8001/health"
FRONTEND_URL="http://127.0.0.1/"
FRONTEND_HOST="esg.meichen.beauty"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting health check..."

if ! docker ps --format '{{.Names}}' | grep -q '^esg-research-toolkit_api_1$'; then
  echo "ERROR: Docker container not running"
  exit 1
fi

if ! curl -sf "$API_URL" >/dev/null; then
  echo "ERROR: API health check failed"
  exit 1
fi

if ! curl -sf -H "Host: ${FRONTEND_HOST}" "$FRONTEND_URL" >/dev/null; then
  echo "ERROR: Frontend not accessible"
  exit 1
fi

DISK_USAGE="$(df /opt/esg-data | awk 'NR==2 {gsub(/%/, "", $5); print $5}')"
if [ "${DISK_USAGE:-0}" -gt 80 ]; then
  echo "WARN: Disk usage at ${DISK_USAGE}%"
fi

echo "OK: All checks passed"
