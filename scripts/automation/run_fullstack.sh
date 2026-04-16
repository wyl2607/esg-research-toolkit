#!/usr/bin/env bash
# run_fullstack.sh — 一键启动后端 + 前端，做健康检查
#
# Usage:
#   scripts/automation/run_fullstack.sh           # 前台运行（Ctrl+C 退出）
#   scripts/automation/run_fullstack.sh --detach  # 后台运行，写入 PID 文件
#   scripts/automation/run_fullstack.sh --stop    # 停止后台实例
#   scripts/automation/run_fullstack.sh --status  # 查看当前状态
#
# 输出：
#   scripts/automation/logs/backend.log
#   scripts/automation/logs/frontend.log
#   scripts/automation/logs/fullstack.pids

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

LOG_DIR="$PROJECT_ROOT/scripts/automation/logs"
PID_FILE="$LOG_DIR/fullstack.pids"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
BACKEND_PORT=8000
FRONTEND_PORT=5173

mkdir -p "$LOG_DIR"

# ---------- helpers ----------
color() { printf '\033[%sm%s\033[0m' "$1" "$2"; }
info()  { echo "$(color 36 '[fullstack]') $*"; }
warn()  { echo "$(color 33 '[fullstack]') $*" >&2; }
error() { echo "$(color 31 '[fullstack]') $*" >&2; }

port_in_use() {
    lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

wait_for_port() {
    local port=$1 name=$2 timeout=${3:-60}
    local elapsed=0
    while ! port_in_use "$port"; do
        sleep 1
        elapsed=$((elapsed + 1))
        if [ $elapsed -ge "$timeout" ]; then
            error "$name did not open port $port within ${timeout}s"
            return 1
        fi
    done
    info "$name is listening on :$port"
}

health_check_backend() {
    local url="http://localhost:${BACKEND_PORT}/health"
    local response
    response=$(curl -sS --max-time 5 "$url" 2>&1 || true)
    if echo "$response" | grep -q '"status":"ok"'; then
        info "backend /health OK"
        return 0
    fi
    error "backend /health failed: $response"
    return 1
}

health_check_frontend() {
    local url="http://localhost:${FRONTEND_PORT}/"
    local status
    status=$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000")
    if [ "$status" = "200" ]; then
        info "frontend / returns 200"
        return 0
    fi
    error "frontend returned HTTP $status"
    return 1
}

# ---------- commands ----------
cmd_status() {
    if [ -f "$PID_FILE" ]; then
        echo "pid file: $PID_FILE"
        cat "$PID_FILE"
    else
        echo "no pid file"
    fi
    echo "---"
    echo "backend :$BACKEND_PORT $(port_in_use $BACKEND_PORT && echo RUNNING || echo DOWN)"
    echo "frontend :$FRONTEND_PORT $(port_in_use $FRONTEND_PORT && echo RUNNING || echo DOWN)"
    health_check_backend 2>/dev/null || true
    health_check_frontend 2>/dev/null || true
}

cmd_stop() {
    if [ ! -f "$PID_FILE" ]; then
        warn "no pid file; attempting port-based kill"
        for port in $BACKEND_PORT $FRONTEND_PORT; do
            pid=$(lsof -ti:$port 2>/dev/null || true)
            [ -n "$pid" ] && kill $pid 2>/dev/null && info "killed pid $pid on :$port" || true
        done
        return 0
    fi
    while IFS='=' read -r name pid; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" && info "stopped $name (pid $pid)"
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
}

start_backend() {
    if port_in_use $BACKEND_PORT; then
        info "backend already running on :$BACKEND_PORT"
        return 0
    fi
    info "starting backend (uvicorn) → $BACKEND_LOG"
    if [ ! -f ".venv/bin/uvicorn" ]; then
        error ".venv/bin/uvicorn not found — run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
        return 1
    fi
    nohup .venv/bin/uvicorn main:app \
        --host 0.0.0.0 --port $BACKEND_PORT \
        > "$BACKEND_LOG" 2>&1 &
    echo "backend=$!" >> "$PID_FILE"
    wait_for_port $BACKEND_PORT backend 45
    sleep 2
    health_check_backend
}

start_frontend() {
    if port_in_use $FRONTEND_PORT; then
        info "frontend already running on :$FRONTEND_PORT"
        return 0
    fi
    if [ ! -d "frontend/node_modules" ]; then
        info "installing frontend deps..."
        (cd frontend && npm install)
    fi
    info "starting frontend (vite) → $FRONTEND_LOG"
    nohup bash -c "cd frontend && npm run dev -- --host 0.0.0.0 --port $FRONTEND_PORT" \
        > "$FRONTEND_LOG" 2>&1 &
    echo "frontend=$!" >> "$PID_FILE"
    wait_for_port $FRONTEND_PORT frontend 60
    sleep 2
    health_check_frontend
}

cmd_start() {
    local detach=${1:-0}
    > "$PID_FILE"
    start_backend
    start_frontend
    echo ""
    info "✅ full stack ready"
    info "   backend   http://localhost:$BACKEND_PORT"
    info "   frontend  http://localhost:$FRONTEND_PORT"
    info "   logs      $LOG_DIR/"
    if [ "$detach" = "1" ]; then
        info "(detached) use 'scripts/automation/run_fullstack.sh --stop' to stop"
        return 0
    fi
    info "tailing logs (Ctrl+C to stop)..."
    trap 'cmd_stop; exit 0' INT TERM
    tail -f "$BACKEND_LOG" "$FRONTEND_LOG"
}

# ---------- dispatch ----------
case "${1:-}" in
    --stop|stop)     cmd_stop ;;
    --status|status) cmd_status ;;
    --detach|detach) cmd_start 1 ;;
    *)               cmd_start 0 ;;
esac
