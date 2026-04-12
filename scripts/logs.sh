#!/usr/bin/env bash
# logs.sh - quick ESG Toolkit log view

set -euo pipefail

echo "=== Docker Container Logs ==="
docker-compose -f /opt/esg-research-toolkit/docker-compose.prod.yml logs --tail=50

echo
echo "=== Nginx Access Log (last 20) ==="
tail -20 /var/log/nginx/access.log 2>/dev/null || echo "access.log not found"

echo
echo "=== Nginx Error Log (last 20) ==="
tail -20 /var/log/nginx/error.log 2>/dev/null || echo "error.log not found"
