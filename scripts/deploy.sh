#!/usr/bin/env bash
# deploy.sh — One-shot deploy for ESG Research Toolkit on USA VPS.
# Callers must fetch and checkout the intended revision before running.
set -euo pipefail

REPO_DIR="/opt/esg-research-toolkit"
DATA_DIR="/opt/esg-data"
REPORTS_DIR="/opt/esg-reports"
NGINX_CONF="/etc/nginx/sites-available/esg.conf"
FINGERPRINT_FILE="$REPO_DIR/.deploy-fingerprint.json"

detect_compose() {
    if docker compose version >/dev/null 2>&1; then
        echo "docker compose"
    elif command -v docker-compose >/dev/null 2>&1; then
        echo "docker-compose"
    else
        echo ""
    fi
}

COMPOSE_CMD="$(detect_compose)"
if [ -z "$COMPOSE_CMD" ]; then
    echo "ERROR: neither 'docker compose' nor 'docker-compose' is available"
    exit 1
fi

echo "=== ESG Toolkit Deploy ==="

# 1. Verify deployed revision. The workflow checks out the exact SHA before
# calling this script; do not pull main here or deployments lose traceability.
cd "$REPO_DIR"
git rev-parse HEAD

# 2. Build frontend
echo "→ Building frontend..."
cd "$REPO_DIR/frontend"
npm install --silent
npm run build

# 3. Ensure data dirs exist
mkdir -p "$DATA_DIR" "$REPORTS_DIR"

# 4. Check .env.prod exists
if [ ! -f "$REPO_DIR/.env.prod" ]; then
    echo "ERROR: $REPO_DIR/.env.prod not found!"
    echo "Create it with: OPENAI_API_KEY, OPENAI_MODEL (OPENAI_BASE_URL optional, defaults to official OpenAI endpoint)"
    exit 1
fi

# 5. Write deploy fingerprint before Compose sees the file bind mount.
echo "→ Writing deploy fingerprint..."
bash "$REPO_DIR/scripts/write_deploy_fingerprint.sh" \
  --repo-dir "$REPO_DIR" \
  --env "vps-prod" \
  --source "deploy.sh" \
  --image "pending-compose-build" \
  --target "$FINGERPRINT_FILE" >/dev/null
echo " Fingerprint: $FINGERPRINT_FILE"

# 6. Build first, then swap containers. Build-before-down keeps the old
# container serving if the build fails (2026-06-11 incident: down-then-build
# with a full disk left the site 502 for hours). No --no-cache: cached layers
# avoid the containerd snapshot blowup that filled the 39G disk.
echo "→ Building API image..."
cd "$REPO_DIR"
$COMPOSE_CMD -f docker-compose.prod.yml build

echo "→ Restarting API container..."
$COMPOSE_CMD -f docker-compose.prod.yml down --remove-orphans || true
$COMPOSE_CMD -f docker-compose.prod.yml up -d

# 7. Install nginx config (first deploy only)
if [ ! -f "$NGINX_CONF" ]; then
    echo "→ Installing nginx config..."
    cp "$REPO_DIR/nginx/esg.conf" "$NGINX_CONF"
    ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/esg.conf
    nginx -t && systemctl reload nginx
    echo "→ Getting SSL certificate..."
    certbot --nginx -d esg.meichen.beauty --non-interactive --agree-tos \
        -m admin@meichen.beauty --redirect || echo "WARN: certbot failed, HTTP only"
else
    nginx -t && systemctl reload nginx
fi

# 8. Smoke check. /health stays green even when the DB schema has drifted
# (2026-06-10 incident: stamped-but-unmigrated SQLite 500'd every core route),
# so also hit endpoints that actually query the main tables.
echo "→ Smoke check..."
for i in $(seq 1 10); do
    if curl -sf http://localhost:8001/health >/dev/null; then
        break
    fi
    if [ "$i" = "10" ]; then
        echo "ERROR: API health check failed"
        exit 1
    fi
    echo " waiting... ($i/10)"
    sleep 3
done
for endpoint in /health /health/deploy /report/companies /disclosures/pending; do
    if ! curl -sf "http://localhost:8001$endpoint" >/dev/null; then
        echo "ERROR: smoke check failed on $endpoint"
        exit 1
    fi
    echo " OK $endpoint"
done

# 9. Reclaim disk: drop dangling images left by the rebuild.
echo "→ Pruning dangling images..."
docker image prune -f

echo "=== Deploy complete ==="
echo "URL: https://esg.meichen.beauty"
