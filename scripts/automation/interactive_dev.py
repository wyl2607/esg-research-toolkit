"""interactive_dev.py — 交互式开发助手

把项目里常用的"找 bug / 查状态 / 触发流程"操作做成菜单，不用再记命令。
每次执行会把选项和输出追加到 scripts/automation/logs/interactive_log.md，
方便日后作为 Claude/Codex 的 context。

Usage:
    .venv/bin/python scripts/automation/interactive_dev.py
    .venv/bin/python scripts/automation/interactive_dev.py --pick db_summary  # 无交互直接跑
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

LOG = ROOT / "scripts" / "automation" / "logs" / "interactive_log.md"
BACKEND_URL = os.environ.get("API_BASE", "http://localhost:8000")


def log_entry(action: str, output: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().isoformat(timespec="seconds")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"\n## {ts} · {action}\n\n```\n{output.strip()}\n```\n")


def run(cmd: list[str], cwd: Path | None = None) -> str:
    print(f"$ {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd, cwd=cwd or ROOT,
            capture_output=True, text=True, timeout=300,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        print(out)
        return out
    except subprocess.TimeoutExpired as exc:
        return f"TIMEOUT: {exc}"
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: {exc}"


# -------------------- actions --------------------

def act_db_summary() -> str:
    import sqlite3
    from collections import defaultdict

    db_path = ROOT / "data" / "esg_toolkit.db"
    if not db_path.exists():
        return f"DB not found: {db_path}"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    out: list[str] = []

    cur.execute("SELECT company_name, report_year FROM company_reports "
                "ORDER BY company_name, report_year")
    rows = cur.fetchall()
    out.append(f"Total company_reports rows: {len(rows)}")
    by_c: dict[str, list[int]] = defaultdict(list)
    for name, yr in rows:
        by_c[name].append(yr)
    out.append("")
    out.append("Per company (years):")
    multi_year = 0
    for name in sorted(by_c):
        years = sorted(set(by_c[name]))
        marker = " ⭐" if len(years) >= 2 else ""
        if len(years) >= 2:
            multi_year += 1
        out.append(f"  {name}: {years}{marker}")
    out.append("")
    out.append(f"Companies with ≥2 years of data: {multi_year}")

    try:
        cur.execute("SELECT COUNT(*) FROM extraction_runs")
        out.append(f"extraction_runs rows: {cur.fetchone()[0]}")
    except sqlite3.OperationalError:
        out.append("extraction_runs table not present")

    try:
        cur.execute("SELECT COUNT(*) FROM framework_results")
        out.append(f"framework_results rows: {cur.fetchone()[0]}")
    except sqlite3.OperationalError:
        pass

    conn.close()
    return "\n".join(out)


def act_api_health() -> str:
    import urllib.request

    out: list[str] = []
    endpoints = [
        "/health",
        "/report/companies",
        "/frameworks/list",
        "/techno/benchmarks",
    ]
    for ep in endpoints:
        url = BACKEND_URL + ep
        try:
            with urllib.request.urlopen(url, timeout=8) as resp:
                code = resp.status
                body = resp.read(200).decode("utf-8", errors="replace")
            out.append(f"  {code}  {ep}  → {body[:120]}{'…' if len(body) >= 200 else ''}")
        except Exception as exc:  # noqa: BLE001
            out.append(f"  ERR  {ep}  → {exc}")
    return "\n".join(out)


def act_trend_peek() -> str:
    """Pick companies with ≥2 years and show their /history payload."""
    import urllib.parse
    import urllib.request
    import sqlite3
    from collections import defaultdict

    db_path = ROOT / "data" / "esg_toolkit.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT company_name, report_year FROM company_reports "
                "ORDER BY company_name, report_year")
    by_c: dict[str, list[int]] = defaultdict(list)
    for name, yr in cur.fetchall():
        by_c[name].append(yr)
    conn.close()

    multi = [n for n, ys in by_c.items() if len(set(ys)) >= 2]
    if not multi:
        return "No companies with ≥2 years yet — seed still running?"
    out: list[str] = [f"Companies with multi-year data: {len(multi)}"]
    for name in multi[:5]:
        url = f"{BACKEND_URL}/report/companies/{urllib.parse.quote(name)}/history"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            trend = data.get("trend", [])
            years = [t.get("year") for t in trend]
            out.append(f"  {name}: {len(trend)} trend points, years={years}")
        except Exception as exc:  # noqa: BLE001
            out.append(f"  {name}: ERR {exc}")
    return "\n".join(out)


def act_pytest_fast() -> str:
    return run([".venv/bin/pytest", "-q", "-x", "--timeout=30"])


def act_pytest_full() -> str:
    env = os.environ.copy()
    env.setdefault("OPENAI_API_KEY", "dummy")
    proc = subprocess.run(
        [".venv/bin/pytest", "-q"], cwd=ROOT, env=env,
        capture_output=True, text=True, timeout=600,
    )
    return (proc.stdout + proc.stderr).strip()


def act_frontend_lint() -> str:
    return run(["npm", "run", "lint"], cwd=ROOT / "frontend")


def act_frontend_build() -> str:
    return run(["npm", "run", "build"], cwd=ROOT / "frontend")


def act_frontend_smoke() -> str:
    return run(["npm", "run", "test:smoke"], cwd=ROOT / "frontend")


def act_git_status() -> str:
    return run(["git", "status", "-sb"]) + "\n" + run(["git", "log", "--oneline", "-10"])


def act_seed_status() -> str:
    out: list[str] = []
    log = ROOT / "scripts" / "automation" / "logs" / "seed_run.log"
    if log.exists():
        txt = log.read_text(encoding="utf-8", errors="replace")
        out.append(f"seed_run.log: {log.stat().st_size} bytes")
        lines = txt.strip().splitlines()
        out.append("--- last 20 lines ---")
        out.extend(lines[-20:])
    else:
        out.append("no seed_run.log yet")
    try:
        ps = subprocess.run(["ps", "aux"], capture_output=True, text=True).stdout
        running = [l for l in ps.splitlines() if "seed_german" in l and "grep" not in l]
        out.append("--- running processes ---")
        out.extend(running or ["(no seed process running)"])
    except Exception:  # noqa: BLE001
        pass
    return "\n".join(out)


def act_benchmarks_recompute() -> str:
    import urllib.request
    try:
        req = urllib.request.Request(f"{BACKEND_URL}/benchmarks/recompute", method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return f"{resp.status} {resp.read().decode('utf-8')[:500]}"
    except Exception as exc:  # noqa: BLE001
        return f"ERR: {exc}"


def act_open_browser() -> str:
    url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    return run(["open", url])


def act_ui_screenshots() -> str:
    return run([
        sys.executable, str(ROOT / "scripts" / "automation" / "ui_autopolish.py"),
        "--screenshot-only",
    ])


# -------------------- menu --------------------

MENU = [
    ("db_summary",           "Database summary (companies, years, rows)",          act_db_summary),
    ("api_health",           "API health sweep (/health + endpoints)",             act_api_health),
    ("trend_peek",           "Peek multi-year trend data via API",                 act_trend_peek),
    ("seed_status",          "Seed script status (log tail + process)",            act_seed_status),
    ("benchmarks_recompute", "Trigger POST /benchmarks/recompute",                 act_benchmarks_recompute),
    ("pytest_fast",          "Run pytest -q -x (fail fast)",                       act_pytest_fast),
    ("pytest_full",          "Run full pytest suite",                              act_pytest_full),
    ("frontend_lint",        "npm run lint (frontend)",                            act_frontend_lint),
    ("frontend_build",       "npm run build (frontend)",                           act_frontend_build),
    ("frontend_smoke",       "npm run test:smoke (frontend Playwright)",           act_frontend_smoke),
    ("ui_screenshots",       "Take UI screenshots (no LLM)",                       act_ui_screenshots),
    ("git_status",           "git status + last 10 commits",                       act_git_status),
    ("open_browser",         "Open frontend in browser",                           act_open_browser),
]


def render_menu() -> None:
    print("")
    print("━" * 70)
    print("  ESG Toolkit · Interactive Dev Helper")
    print("━" * 70)
    for i, (key, label, _) in enumerate(MENU, 1):
        print(f"  {i:>2}. {label:<50} [{key}]")
    print(f"   q. quit")
    print("")


def interactive_loop() -> None:
    while True:
        render_menu()
        choice = input("  pick > ").strip().lower()
        if choice in ("q", "quit", "exit", ""):
            print("bye")
            return
        action = None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(MENU):
                action = MENU[idx]
        else:
            for item in MENU:
                if item[0] == choice:
                    action = item
                    break
        if not action:
            print(f"  unknown: {choice}")
            continue
        key, label, fn = action
        print(f"\n━━ {label} ━━")
        try:
            output = fn() or "(no output)"
        except Exception as exc:  # noqa: BLE001
            output = f"EXCEPTION: {exc}"
        print(output)
        log_entry(label, output)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pick", help="Run a single action by key (non-interactive)")
    p.add_argument("--list", action="store_true", help="List available actions and exit")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.list:
        for key, label, _ in MENU:
            print(f"  {key:<25} {label}")
        return 0
    if args.pick:
        for key, label, fn in MENU:
            if key == args.pick:
                print(f"━━ {label} ━━")
                out = fn() or "(no output)"
                print(out)
                log_entry(label, out)
                return 0
        print(f"unknown action: {args.pick}", file=sys.stderr)
        return 2
    try:
        interactive_loop()
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nbye")
        return 0


if __name__ == "__main__":
    sys.exit(main())
