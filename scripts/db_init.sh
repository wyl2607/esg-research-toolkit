#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

if [[ ! -f alembic.ini ]]; then
  echo "ERROR: alembic.ini not found under ${REPO_ROOT}" >&2
  exit 1
fi

if [[ -x .venv/bin/alembic ]]; then
  ALEMBIC_CMD=(.venv/bin/alembic)
  PY_CMD=(.venv/bin/python3)
elif command -v alembic >/dev/null 2>&1; then
  ALEMBIC_CMD=(alembic)
  PY_CMD=(python3)
else
  echo "ERROR: Alembic executable not found. Install dependencies or activate .venv." >&2
  exit 1
fi

# Detect pre-Alembic schema left over by the retired runtime helpers.
# If `company_reports` exists but `alembic_version` doesn't, auto-stamp the
# baseline so `upgrade head` doesn't error with "table already exists".
CURRENT_VERSION="$("${ALEMBIC_CMD[@]}" current 2>/dev/null | awk '/^[0-9a-f]{4,}/{print $1; exit}')"

if [[ -z "${CURRENT_VERSION}" ]]; then
  # Check for legacy-helper-created tables via Alembic's engine. If any table
  # exists but alembic_version is absent, stamp baseline first.
  LEGACY_TABLES=$("${ALEMBIC_CMD[@]}" -x check-existing=1 current 2>&1 >/dev/null || true)
  HAS_LEGACY="$("${PY_CMD[@]}" - <<'PYEOF'
from sqlalchemy import create_engine, inspect, text
from core.config import settings
try:
    engine = create_engine(settings.database_url, future=True)
    names = set(inspect(engine).get_table_names())
    has_core = "company_reports" in names
    # Treat empty alembic_version as "not stamped" (a prior failed upgrade can
    # leave the table empty).
    stamped = False
    if "alembic_version" in names:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
            stamped = len(rows) > 0
    print("yes" if has_core and not stamped else "no")
except Exception:
    print("no")
PYEOF
)"
  if [[ "$HAS_LEGACY" == "yes" ]]; then
    echo "Detected legacy schema without alembic_version; stamping 0001_baseline..."
    "${ALEMBIC_CMD[@]}" stamp 0001_baseline
  fi
fi

echo "Applying Alembic migrations to head..."
"${ALEMBIC_CMD[@]}" upgrade head
echo "Database is at Alembic head."
