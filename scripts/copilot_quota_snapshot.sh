#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

OUT_DIR="${OUT_DIR:-.local/peer-reviews/copilot-usage}"
LATEST_JSON="${LATEST_JSON:-$OUT_DIR/latest.json}"
HISTORY_NDJSON="${HISTORY_NDJSON:-$OUT_DIR/history.ndjson}"
COPILOT_QUOTA_TERMINAL_DUMP="${COPILOT_QUOTA_TERMINAL_DUMP:-}"

mkdir -p "$OUT_DIR"

has_rg=0
if command -v rg >/dev/null 2>&1; then
  has_rg=1
fi

terminal_dump="$COPILOT_QUOTA_TERMINAL_DUMP"
if [ -z "$terminal_dump" ]; then
  if ! command -v osascript >/dev/null 2>&1; then
    echo "[copilot-quota] FAIL: osascript not found (macOS required)"
    exit 2
  fi
  terminal_dump="$(osascript -e 'tell application "Terminal" to contents of selected tab of front window' 2>/dev/null || true)"
fi

if [ -z "$terminal_dump" ]; then
  echo "[copilot-quota] FAIL: could not read Terminal tab content"
  echo "[copilot-quota] tip: keep your Copilot CLI terminal tab in front and rerun"
  exit 1
fi

if [ "$has_rg" -eq 1 ]; then
  remaining="$(printf '%s\n' "$terminal_dump" | rg -o 'Remaining reqs\.\:\s*[0-9]+%' | tail -n 1 | rg -o '[0-9]+%' || true)"
else
  remaining="$(printf '%s\n' "$terminal_dump" | grep -Eo 'Remaining reqs\.\:\s*[0-9]+%' | tail -n 1 | grep -Eo '[0-9]+%' || true)"
fi

if [ -z "$remaining" ]; then
  echo "[copilot-quota] FAIL: 'Remaining reqs.' not found in active Terminal tab"
  echo "[copilot-quota] tip: run Copilot CLI in the front tab first, then rerun"
  exit 1
fi
if ! printf '%s\n' "$remaining" | grep -Eq '^[0-9]+%$'; then
  echo "[copilot-quota] FAIL: extracted remaining quota has invalid format: $remaining"
  exit 1
fi

timestamp="$(date '+%Y-%m-%dT%H:%M:%S%z')"
cat > "$LATEST_JSON" <<EOF
{
  "timestamp": "$timestamp",
  "remaining_reqs_pct": "$remaining",
  "source": "terminal_front_tab"
}
EOF

printf '{"timestamp":"%s","remaining_reqs_pct":"%s","source":"terminal_front_tab"}\n' \
  "$timestamp" "$remaining" >> "$HISTORY_NDJSON"

echo "[copilot-quota] remaining reqs: $remaining"
echo "[copilot-quota] latest: $LATEST_JSON"
