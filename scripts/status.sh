#!/usr/bin/env bash
# status.sh - show ESG Toolkit runtime status

set -euo pipefail

echo "=== ESG Research Toolkit Status ==="
echo "Time: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo

echo "--- Docker Container ---"
docker ps --filter name=esg-research-toolkit --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo

echo "--- Resource Usage ---"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
echo

echo "--- Disk Usage ---"
df -h /opt/esg-data /opt/esg-reports | tail -2
echo

echo "--- Deploy Fingerprint ---"
if [ -f /opt/esg-research-toolkit/.deploy-fingerprint.json ]; then
  cat /opt/esg-research-toolkit/.deploy-fingerprint.json
else
  echo "No deploy fingerprint found"
fi
echo

echo "--- Recent Requests (last 10) ---"
tail -10 /var/log/nginx/esg-access.log 2>/dev/null || echo "No esg-access log yet"
echo

echo "--- Health Check ---"
if curl -sf http://127.0.0.1:8001/health >/dev/null; then
  echo "OK: API healthy"
else
  echo "FAIL: API unhealthy"
fi
