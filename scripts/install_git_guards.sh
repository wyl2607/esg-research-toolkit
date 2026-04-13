#!/usr/bin/env bash
# Install local git hooks for commit/push guardrails.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS_DIR="$PROJECT_DIR/.git/hooks"
mkdir -p "$HOOKS_DIR"

cat > "$HOOKS_DIR/pre-commit" <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
scripts/security_check.sh
HOOK

cat > "$HOOKS_DIR/pre-push" <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
scripts/review_push_guard.sh origin/main
HOOK

chmod +x "$HOOKS_DIR/pre-commit" "$HOOKS_DIR/pre-push"

echo "Installed hooks:"
echo "- .git/hooks/pre-commit -> scripts/security_check.sh"
echo "- .git/hooks/pre-push   -> scripts/review_push_guard.sh origin/main"
