#!/usr/bin/env bash
#
# Phase 2 of the design-system rollout: migrate each top-level page to the
# locked primitives (PageContainer / PageHeader / Panel / FormCard / StatCard /
# NoticeBanner / FilterBar).
#
# Executes one page at a time via `codex exec` with gpt-5.3 high reasoning
# effort, then runs lint + build as a gate. If the gate fails, the page is
# reverted so you can diff & retry instead of stacking broken commits.
#
# Usage:
#   bash scripts/dev_tasks/06_ui_page_migration.sh                    # migrate next pending page
#   bash scripts/dev_tasks/06_ui_page_migration.sh UploadPage         # migrate a specific page
#   bash scripts/dev_tasks/06_ui_page_migration.sh --list             # show progress
#   bash scripts/dev_tasks/06_ui_page_migration.sh --all              # sequential full run
#   bash scripts/dev_tasks/06_ui_page_migration.sh --dry-run UploadPage  # print prompt, no codex call
#
# Env:
#   OPENAI_API_KEY   required for real runs (not --dry-run / --list)
#   CODEX_MODEL      override model (default: gpt-5.3)
#   CODEX_EFFORT     override reasoning effort (default: high)
#
# Exit codes:
#   0 success / nothing to do
#   1 user error (bad arg, missing env)
#   2 codex failed
#   3 post-migration gate (lint/build) failed — page reverted

set -euo pipefail

cd "$(dirname "$0")/../.."
ROOT="$(pwd)"

PAGES=(
  UploadPage
  TaxonomyPage
  LcoePage
  CompaniesPage
  CompanyProfilePage
  ComparePage
  BenchmarkPage
  FrameworksPage
  RegionalPage
  ManualCaseBuilderPage
  CoverageFieldPage
  DashboardPage
)

STATE_DIR="scripts/automation/state/ui_migration"
mkdir -p "$STATE_DIR"

MODEL="${CODEX_MODEL:-gpt-5.3}"
EFFORT="${CODEX_EFFORT:-high}"

cmd_list() {
  echo "Page migration progress:"
  for p in "${PAGES[@]}"; do
    if [ -f "$STATE_DIR/$p.done" ]; then
      echo "  [x] $p  ($(cat "$STATE_DIR/$p.done"))"
    else
      echo "  [ ] $p"
    fi
  done
}

next_pending() {
  for p in "${PAGES[@]}"; do
    if [ ! -f "$STATE_DIR/$p.done" ]; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

build_prompt() {
  local page="$1"
  local file="frontend/src/pages/${page}.tsx"
  if [ ! -f "$file" ]; then
    echo "ERROR: $file not found" >&2
    exit 1
  fi

  cat <<PROMPT
You are migrating ONE React page to the new design system. Be surgical.
Do NOT touch any other file. Do NOT add comments or docstrings.
Do NOT change business logic, data flow, i18n keys, hooks, or network calls.

Target file: ${file}

# Locked design primitives (already in repo — import from these paths)

\`\`\`ts
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { Panel, FormCard, StatCard } from '@/components/layout/Panel'
import { NoticeBanner } from '@/components/NoticeBanner'
import { FilterBar } from '@/components/FilterBar'
\`\`\`

## PageContainer
- Props: \`width?: 'default' | 'narrow' | 'wide'\` (default 'default').
- Always wrap the page's top-level JSX in <PageContainer>. Remove manual
  \`max-w-*\` / \`mx-auto\` / \`space-y-*\` wrappers that replicate its job.

## PageHeader
- Props: \`title\` (string), \`subtitle?\` (string), \`actions?\` (ReactNode), \`kpis?\` ({label,value,hint?}[]) — max 4 KPIs.
- Replace ad-hoc page headers (h1/h2 + description + action buttons + KPI tiles).
- Do NOT pass a 'kicker' — kickers have been dropped from the design system.

## Panel / FormCard / StatCard
- Panel: default content surface (p-6 rounded-2xl border bg-white). Use to replace \`.surface-card\`, \`.editorial-panel\`, or inline \`rounded-* border bg-white shadow\` wrappers.
- FormCard: denser (p-5) for forms / filter groups.
- StatCard: denser (p-4) for small metric/stat tiles.
- Never stack two of these inside each other.

## NoticeBanner
- Props: \`tone: 'info'|'warning'|'success'|'mode'\`, \`title?\`, \`children\`.
- Replace every hand-rolled colored alert/banner/notice box.

## FilterBar (compound)
- <FilterBar> row wrapper, <FilterBar.Field label htmlFor> for each control, <FilterBar.Actions> for right-aligned buttons.
- Replace bespoke filter rows (grids of selects + search + action buttons at top of list pages).
- Two supported compositions (pick whichever fits, do NOT invent a third):
  - A · fields + primary action — multiple <FilterBar.Field> then <FilterBar.Actions> with 1 primary button (used on heavy list/analytics pages).
  - B · search-only compact — 1–2 <FilterBar.Field> and NO <FilterBar.Actions> (used on light list pages).

# Reference composition for list-style pages (Companies / Compare / Benchmarks / Frameworks)

\`\`\`tsx
<PageContainer>
  <PageHeader
    title={t('...')}
    subtitle={t('...')}
    actions={<Button variant="primary">...</Button>}
    kpis={[{label,value,hint}, ...]}  // up to 4
  />
  <FilterBar>
    <FilterBar.Field label="..." htmlFor="..."><Select/Input/></FilterBar.Field>
    ...
    <FilterBar.Actions><Button>Apply</Button></FilterBar.Actions>  {/* only if page has a primary action */}
  </FilterBar>
  <Panel>
    {/* main table / grid / list */}
  </Panel>
</PageContainer>
\`\`\`

# Rules

1. Keep all existing functionality, props, state, effects, queries, i18n keys.
2. Remove now-dead Tailwind classes that duplicate primitive styling.
3. Prefer primitive defaults over overriding them with className.
4. If the page already uses a primitive in part, normalize the rest consistently.
5. If something genuinely does not fit any primitive, leave it and keep its existing styling — do NOT invent new variants.
6. Do not touch tests, stories, other pages, routing, or backend files.
7. Output: write the edited file in place. No summary, no markdown.

# Before you start

Read the current file fully. Read any primitive you plan to use. Then edit.

Go.
PROMPT
}

cmd_migrate() {
  local page="$1"
  local file="frontend/src/pages/${page}.tsx"

  if [ -f "$STATE_DIR/$page.done" ]; then
    echo "⏭  $page already migrated ($(cat "$STATE_DIR/$page.done")) — delete $STATE_DIR/$page.done to redo"
    return 0
  fi
  if [ ! -f "$file" ]; then
    echo "❌ $file not found"; exit 1
  fi

  echo "=== Migrating $page ==="
  echo "  model:  $MODEL"
  echo "  effort: $EFFORT"
  echo ""

  # Safety snapshot so we can revert on gate failure.
  local snap="$STATE_DIR/$page.pre.tsx"
  cp "$file" "$snap"

  local prompt
  prompt="$(build_prompt "$page")"

  if [ "${DRY_RUN:-0}" = "1" ]; then
    echo "----- PROMPT -----"
    echo "$prompt"
    echo "------------------"
    return 0
  fi

  if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "❌ OPENAI_API_KEY not set" >&2
    exit 1
  fi

  # Run codex. --dangerously-bypass keeps it non-interactive; we've snapshotted.
  if ! codex exec \
        -m "$MODEL" \
        -c "model_reasoning_effort=\"$EFFORT\"" \
        --skip-git-repo-check \
        --dangerously-bypass-approvals-and-sandbox \
        "$prompt"; then
    echo "❌ codex exec failed for $page — restoring snapshot"
    mv "$snap" "$file"
    exit 2
  fi

  echo ""
  echo "--- Gate: lint + build ---"
  pushd frontend >/dev/null
  if ! npm run lint --silent; then
    echo "❌ lint failed — reverting $page"
    popd >/dev/null
    mv "$snap" "$file"
    exit 3
  fi
  if ! npm run build --silent; then
    echo "❌ build failed — reverting $page"
    popd >/dev/null
    mv "$snap" "$file"
    exit 3
  fi
  popd >/dev/null

  rm -f "$snap"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$STATE_DIR/$page.done"
  echo "✅ $page migrated. Review diff:"
  echo "   git diff -- $file"
  echo ""
  echo "When satisfied: git add $file && git commit -m \"ui: migrate $page to design primitives\""
}

# --- arg parsing ---
case "${1:-}" in
  --list|-l)
    cmd_list
    ;;
  --dry-run)
    shift
    DRY_RUN=1
    target="${1:-$(next_pending || true)}"
    [ -z "$target" ] && { echo "nothing pending"; exit 0; }
    cmd_migrate "$target"
    ;;
  --all)
    while target="$(next_pending)"; do
      cmd_migrate "$target"
    done
    cmd_list
    ;;
  "")
    target="$(next_pending || true)"
    [ -z "$target" ] && { echo "✅ all pages migrated"; cmd_list; exit 0; }
    cmd_migrate "$target"
    ;;
  *)
    cmd_migrate "$1"
    ;;
esac
