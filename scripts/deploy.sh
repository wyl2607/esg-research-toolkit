#!/usr/bin/env bash
# deploy.sh — One-shot deploy for ESG Research Toolkit on USA VPS
# Run on VPS: bash /opt/esg-research-toolkit/scripts/deploy.sh
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

# 1. Pull latest code
cd "$REPO_DIR"
git pull origin main

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

# 5. Rebuild and restart Docker container
echo "→ Restarting API container..."
cd "$REPO_DIR"
$COMPOSE_CMD -f docker-compose.prod.yml down --remove-orphans || true
$COMPOSE_CMD -f docker-compose.prod.yml build --no-cache
$COMPOSE_CMD -f docker-compose.prod.yml up -d

# 6. Install nginx config (first deploy only)
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

# 7. Health check
echo "→ Health check..."
sleep 3
curl -sf http://localhost:8001/health && echo " API OK" || echo " WARN: API not responding yet"

# 8. Write deploy fingerprint (git sha/tag/time/source)
echo "→ Writing deploy fingerprint..."
bash "$REPO_DIR/scripts/write_deploy_fingerprint.sh" \
  --repo-dir "$REPO_DIR" \
  --env "vps-prod" \
  --source "deploy.sh" \
  --target "$FINGERPRINT_FILE" >/dev/null
echo " Fingerprint: $FINGERPRINT_FILE"

echo "=== Deploy complete ==="
echo "URL: https://esg.meichen.beauty"
