#!/usr/bin/env bash
# setup_vps.sh — First-time setup on USA VPS
# Run once: bash <(curl -s https://raw.githubusercontent.com/wyl2607/esg-research-toolkit/main/scripts/setup_vps.sh)
set -euo pipefail

REPO_URL="https://github.com/wyl2607/esg-research-toolkit.git"
REPO_DIR="/opt/esg-research-toolkit"

echo "=== ESG Toolkit — First-time VPS Setup ==="

# 1. Install dependencies
apt-get update -qq
apt-get install -y -qq git docker.io docker-compose-v2 nodejs npm nginx certbot python3-certbot-nginx curl

# 2. Enable Docker
systemctl enable --now docker

# 3. Clone repo
if [ -d "$REPO_DIR" ]; then
    echo "Repo already exists, pulling..."
    cd "$REPO_DIR" && git pull
else
    git clone "$REPO_URL" "$REPO_DIR"
fi

# 4. Create .env.prod template
if [ ! -f "$REPO_DIR/.env.prod" ]; then
    cat > "$REPO_DIR/.env.prod" << 'ENV'
OPENAI_API_KEY=sk-YOUR-KEY-HERE
OPENAI_MODEL=gpt-5.3-codex
DATABASE_URL=sqlite:///./data/esg_toolkit.db
ENV
    echo "NOTICE: .env.prod 不再预置任何中转/自定义 URL 端点，默认使用官方 OpenAI API。"
    echo "IMPORTANT: Edit $REPO_DIR/.env.prod and add your API key!"
fi

echo "=== Setup complete. Next step: ==="
echo "1. Edit: nano $REPO_DIR/.env.prod"
echo "2. Run:  bash $REPO_DIR/scripts/deploy.sh"
