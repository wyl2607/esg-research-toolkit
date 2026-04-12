#!/usr/bin/env bash
# backup.sh - backup ESG Toolkit data

set -euo pipefail

BACKUP_DIR="/opt/esg-backups"
DATE="$(date +%Y%m%d_%H%M%S)"
DB_PATH="/opt/esg-data/esg_toolkit.db"
TARGET="${BACKUP_DIR}/esg_toolkit_${DATE}.db"

mkdir -p "$BACKUP_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup..."

cp "$DB_PATH" "$TARGET"

# Keep only recent 7 days backups.
find "$BACKUP_DIR" -name "*.db" -mtime +7 -delete

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup complete: $TARGET"
