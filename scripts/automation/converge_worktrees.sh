#!/usr/bin/env bash
# converge_worktrees.sh — lane worktree 收敛/去重复工具
#
# 目标：
# 1) 输出 lane 与 main 的差异体检（ahead/behind、脏改动、唯一提交）
# 2) 可选清理重型产物（node_modules / dist / test artifacts）
# 3) 可选回收 worktree，并按需删除本地/远程 lane 分支
#
# 默认是 dry-run：只打印计划，不做破坏性动作。
# 真执行必须显式加 --apply。
#
# 示例：
#   # 仅体检（自动发现所有附加 worktree）
#   scripts/automation/converge_worktrees.sh
#
#   # 体检 + 仅清理产物（dry-run）
#   scripts/automation/converge_worktrees.sh --clean-artifacts
#
#   # 真执行：清理产物 + 回收 lane worktree（不删分支）
#   scripts/automation/converge_worktrees.sh --apply --clean-artifacts --remove-worktrees
#
#   # 真执行：回收 worktree + 删除对应本地/远程分支
#   scripts/automation/converge_worktrees.sh --apply --remove-worktrees --delete-local-branches --delete-remote-branches

set -euo pipefail

PROJECT_ROOT_DEFAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO_PATH="$PROJECT_ROOT_DEFAULT"
MAIN_BRANCH="main"
APPLY=0
FORCE=0
REMOVE_WORKTREES=0
CLEAN_ARTIFACTS=0
CLEAN_LANE_VENV_COPIES=0
DELETE_LOCAL_BRANCHES=0
DELETE_REMOTE_BRANCHES=0
INCLUDE_REPO_ROOT=1

LANES=()
EXPLICIT_BRANCHES=()

ARTIFACT_PATHS=(
  "frontend/node_modules"
  "frontend/dist"
  "frontend/playwright-report"
  "frontend/test-results"
  "frontend/health-reports/latest"
)

color() { printf '\033[%sm%s\033[0m' "$1" "$2"; }
info()  { echo "$(color 36 '[converge]') $*"; }
warn()  { echo "$(color 33 '[converge]') $*" >&2; }
error() { echo "$(color 31 '[converge]') $*" >&2; }

usage() {
  cat <<USAGE
Usage: scripts/automation/converge_worktrees.sh [options]

Options:
  --repo <path>                    Git 主仓路径（默认：脚本所在项目根）
  --main <branch>                  主分支名（默认：main）
  --lane <path>                    指定 lane 路径，可重复；不传则自动发现

  --clean-artifacts                清理重型前端产物（node_modules/dist/test artifacts）
  --clean-lane-venv-copies         若 lane 下 .venv 是目录（非软链），也纳入清理
  --remove-worktrees               回收 lane worktree（保留分支，除非另开删除分支开关）
  --delete-local-branches          删除 lane 对应本地分支（默认安全模式，仅删已并入 main）
  --delete-remote-branches         删除 lane 对应远程分支（origin/<branch>）

  --no-repo-root                   清理产物时不处理主仓，只处理 lane
  --force                          强制模式：允许 dirty worktree remove / 强制删除未并入分支
  --apply                          真执行；默认 dry-run 仅输出计划
  -h, --help                       显示帮助

Safe defaults:
  - 默认只体检，不改动任何文件/分支
  - 破坏性动作都需要 --apply
USAGE
}

ensure_repo() {
  if [ ! -d "$REPO_PATH/.git" ]; then
    error "repo path is not a git repository: $REPO_PATH"
    exit 1
  fi
}

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --repo)
        REPO_PATH="$2"
        shift 2
        ;;
      --main)
        MAIN_BRANCH="$2"
        shift 2
        ;;
      --lane)
        LANES+=("$2")
        shift 2
        ;;
      --clean-artifacts)
        CLEAN_ARTIFACTS=1
        shift
        ;;
      --clean-lane-venv-copies)
        CLEAN_LANE_VENV_COPIES=1
        shift
        ;;
      --remove-worktrees)
        REMOVE_WORKTREES=1
        shift
        ;;
      --delete-local-branches)
        DELETE_LOCAL_BRANCHES=1
        shift
        ;;
      --delete-remote-branches)
        DELETE_REMOTE_BRANCHES=1
        shift
        ;;
      --branch)
        EXPLICIT_BRANCHES+=("$2")
        shift 2
        ;;
      --no-repo-root)
        INCLUDE_REPO_ROOT=0
        shift
        ;;
      --force)
        FORCE=1
        shift
        ;;
      --apply)
        APPLY=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        error "unknown option: $1"
        usage
        exit 2
        ;;
    esac
  done
}

collect_auto_lanes() {
  local current_path=""

  while IFS= read -r line; do
    case "$line" in
      worktree\ *)
        current_path="${line#worktree }"
        ;;
      "")
        if [ -n "$current_path" ]; then
          local abs_path
          abs_path="$(cd "$current_path" 2>/dev/null && pwd || true)"
          if [ -n "$abs_path" ]; then
            if [ "$abs_path" != "$REPO_PATH" ]; then
              LANES+=("$abs_path")
            fi
          fi
        fi
        current_path=""
        ;;
    esac
  done < <(git -C "$REPO_PATH" worktree list --porcelain)
}

uniq_lanes() {
  if [ "${LANES[0]+x}" != "x" ]; then
    return
  fi

  local tmp=()
  local seen="|"
  local lane
  for lane in "${LANES[@]-}"; do
    [ -z "$lane" ] && continue
    local abs_lane
    abs_lane="$(cd "$lane" 2>/dev/null && pwd || true)"
    if [ -z "$abs_lane" ]; then
      warn "skip missing lane path: $lane"
      continue
    fi
    if [ "$abs_lane" = "$REPO_PATH" ]; then
      continue
    fi
    if [[ "$seen" == *"|$abs_lane|"* ]]; then
      continue
    fi
    seen+="$abs_lane|"
    tmp+=("$abs_lane")
  done
  LANES=("${tmp[@]}")
}

branch_for_lane() {
  local lane="$1"
  git -C "$REPO_PATH" worktree list --porcelain | awk -v target="$lane" '
    $1=="worktree" {w=$2}
    $1=="branch" && w==target {sub("refs/heads/", "", $2); print $2; exit}
  '
}

head_for_lane() {
  local lane="$1"
  git -C "$REPO_PATH" worktree list --porcelain | awk -v target="$lane" '
    $1=="worktree" {w=$2}
    $1=="HEAD" && w==target {print $2; exit}
  '
}

is_branch_ancestor_of_main() {
  local branch="$1"
  if git -C "$REPO_PATH" merge-base --is-ancestor "$branch" "$MAIN_BRANCH"; then
    return 0
  fi
  return 1
}

run_or_echo() {
  if [ "$APPLY" -eq 1 ]; then
    "$@"
  else
    echo "[dry-run] $*"
  fi
}

report_lane_status() {
  local lane="$1"
  local branch="$2"

  local counts
  counts="$(git -C "$REPO_PATH" rev-list --left-right --count "$MAIN_BRANCH...$branch" 2>/dev/null || echo "? ?")"
  local main_ahead branch_ahead
  read -r main_ahead branch_ahead <<<"$counts"

  local dirty_count
  dirty_count="$(git -C "$lane" status --porcelain | wc -l | tr -d ' ')"

  local merge_base
  merge_base="$(git -C "$REPO_PATH" merge-base "$MAIN_BRANCH" "$branch" 2>/dev/null || echo '-')"
  local head
  head="$(head_for_lane "$lane")"
  if [ -z "$head" ]; then
    head="$(git -C "$lane" rev-parse --short HEAD 2>/dev/null || echo '-')"
  fi

  echo "---"
  echo "lane:   $lane"
  echo "branch: $branch"
  echo "head:   $head"
  echo "main_ahead=$main_ahead branch_ahead=$branch_ahead dirty=$dirty_count"
  echo "merge-base: $merge_base"

  local unique_commits
  unique_commits="$(git -C "$REPO_PATH" log --oneline "$MAIN_BRANCH..$branch" | head -n 5 || true)"
  if [ -n "$unique_commits" ]; then
    echo "unique commits (top 5):"
    echo "$unique_commits" | sed 's/^/  - /'
  else
    echo "unique commits: (none)"
  fi

  if is_branch_ancestor_of_main "$branch"; then
    echo "recommendation: branch is already ancestor of $MAIN_BRANCH (safe to delete local branch)"
  elif [ "$branch_ahead" = "0" ]; then
    echo "recommendation: no unique commits vs $MAIN_BRANCH (safe to remove worktree; branch cleanup optional)"
  else
    echo "recommendation: branch still has unique commits vs $MAIN_BRANCH; keep branch unless explicitly retired"
  fi

  if [ "$dirty_count" != "0" ]; then
    echo "warning: lane has uncommitted changes; cleanup/remove requires commit/stash or --force"
  fi
}

clean_artifacts_under_path() {
  local base="$1"
  local rel

  if [ ! -d "$base" ]; then
    warn "skip artifact clean for missing path: $base"
    return
  fi

  for rel in "${ARTIFACT_PATHS[@]}"; do
    local target="$base/$rel"
    if [ -e "$target" ]; then
      if [ "$APPLY" -eq 1 ]; then
        rm -rf "$target"
        info "removed artifact: $target"
      else
        echo "[dry-run] rm -rf $target"
      fi
    fi
  done

  if [ "$CLEAN_LANE_VENV_COPIES" -eq 1 ]; then
    local venv_path="$base/.venv"
    if [ -d "$venv_path" ] && [ ! -L "$venv_path" ]; then
      if [ "$APPLY" -eq 1 ]; then
        rm -rf "$venv_path"
        info "removed lane venv copy: $venv_path"
      else
        echo "[dry-run] rm -rf $venv_path"
      fi
    fi
  fi
}

remove_lane_worktree() {
  local lane="$1"
  local branch="$2"

  local dirty_count
  dirty_count="$(git -C "$lane" status --porcelain | wc -l | tr -d ' ')"

  if [ "$dirty_count" != "0" ] && [ "$FORCE" -ne 1 ]; then
    warn "skip worktree remove for dirty lane (use --force): $lane"
    return
  fi

  if [ "$APPLY" -eq 1 ]; then
    if [ "$FORCE" -eq 1 ]; then
      git -C "$REPO_PATH" worktree remove --force "$lane"
    else
      git -C "$REPO_PATH" worktree remove "$lane"
    fi
    info "removed worktree: $lane"
  else
    if [ "$FORCE" -eq 1 ]; then
      echo "[dry-run] git -C $REPO_PATH worktree remove --force $lane"
    else
      echo "[dry-run] git -C $REPO_PATH worktree remove $lane"
    fi
  fi

  # 记录分支供后续删除
  if [ -n "$branch" ]; then
    EXPLICIT_BRANCHES+=("$branch")
  fi
}

uniq_branches() {
  if [ "${EXPLICIT_BRANCHES[0]+x}" != "x" ]; then
    return
  fi

  local tmp=()
  local seen="|"
  local b
  for b in "${EXPLICIT_BRANCHES[@]}"; do
    [ -z "$b" ] && continue
    if [[ "$seen" == *"|$b|"* ]]; then
      continue
    fi
    seen+="$b|"
    tmp+=("$b")
  done
  EXPLICIT_BRANCHES=("${tmp[@]}")
}

delete_local_branch() {
  local branch="$1"

  if [ "$branch" = "$MAIN_BRANCH" ]; then
    warn "refuse to delete main branch: $branch"
    return
  fi

  if ! git -C "$REPO_PATH" show-ref --verify --quiet "refs/heads/$branch"; then
    warn "local branch not found, skip: $branch"
    return
  fi

  local current_branch
  current_branch="$(git -C "$REPO_PATH" branch --show-current)"
  if [ "$current_branch" = "$branch" ]; then
    warn "refuse to delete currently checked-out branch: $branch"
    return
  fi

  if is_branch_ancestor_of_main "$branch"; then
    run_or_echo git -C "$REPO_PATH" branch -d "$branch"
    return
  fi

  if [ "$FORCE" -eq 1 ]; then
    run_or_echo git -C "$REPO_PATH" branch -D "$branch"
  else
    warn "branch not fully merged into $MAIN_BRANCH, skip local delete: $branch (use --force to override)"
  fi
}

delete_remote_branch() {
  local branch="$1"

  if [ "$APPLY" -ne 1 ]; then
    echo "[dry-run] git -C $REPO_PATH push origin --delete $branch"
    return
  fi

  git -C "$REPO_PATH" push origin --delete "$branch"
  info "deleted remote branch: origin/$branch"
}

main() {
  parse_args "$@"
  ensure_repo
  REPO_PATH="$(cd "$REPO_PATH" && pwd)"

  if [ "${LANES[0]+x}" != "x" ]; then
    collect_auto_lanes
  fi

  uniq_lanes

  info "repo: $REPO_PATH"
  info "main branch: $MAIN_BRANCH"
  if [ "$APPLY" -eq 1 ]; then
    warn "APPLY mode enabled — destructive actions are live"
  else
    info "dry-run mode (no destructive action will be executed)"
  fi

  if [ "${LANES[0]+x}" != "x" ]; then
    warn "no lane worktree detected"
  fi

  local lane
  for lane in "${LANES[@]-}"; do
    [ -z "$lane" ] && continue
    local branch
    branch="$(branch_for_lane "$lane")"
    if [ -z "$branch" ]; then
      warn "cannot resolve branch for lane: $lane"
      continue
    fi
    report_lane_status "$lane" "$branch"
  done

  if [ "$CLEAN_ARTIFACTS" -eq 1 ]; then
    echo "---"
    info "artifact cleanup plan"
    if [ "$INCLUDE_REPO_ROOT" -eq 1 ]; then
      clean_artifacts_under_path "$REPO_PATH"
    fi
    for lane in "${LANES[@]-}"; do
      [ -z "$lane" ] && continue
      clean_artifacts_under_path "$lane"
    done
  fi

  if [ "$REMOVE_WORKTREES" -eq 1 ]; then
    echo "---"
    info "worktree reclaim plan"
    for lane in "${LANES[@]-}"; do
      [ -z "$lane" ] && continue
      local branch
      branch="$(branch_for_lane "$lane")"
      if [ -z "$branch" ]; then
        warn "skip worktree remove (branch unresolved): $lane"
        continue
      fi
      remove_lane_worktree "$lane" "$branch"
    done
  fi

  uniq_branches

  if [ "$DELETE_LOCAL_BRANCHES" -eq 1 ]; then
    echo "---"
    info "local branch cleanup plan"
    if [ "${EXPLICIT_BRANCHES[0]+x}" != "x" ]; then
      warn "no branch candidates collected; add --branch <name> or combine with --remove-worktrees"
    else
      local branch
      for branch in "${EXPLICIT_BRANCHES[@]}"; do
        delete_local_branch "$branch"
      done
    fi
  fi

  if [ "$DELETE_REMOTE_BRANCHES" -eq 1 ]; then
    echo "---"
    info "remote branch cleanup plan"
    if [ "${EXPLICIT_BRANCHES[0]+x}" != "x" ]; then
      warn "no branch candidates collected; add --branch <name> or combine with --remove-worktrees"
    else
      local branch
      for branch in "${EXPLICIT_BRANCHES[@]}"; do
        delete_remote_branch "$branch"
      done
    fi
  fi

  echo "---"
  info "done"
}

main "$@"
