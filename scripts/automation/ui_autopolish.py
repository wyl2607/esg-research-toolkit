"""ui_autopolish.py — UI 美学自优化脚本

工作流程：
1. Playwright 访问前端关键页面，多视口（desktop/mobile）截图
2. 将截图 + 页面 DOM 摘要发给视觉 LLM，请求"设计师级"美学评审
3. 生成结构化 critique 报告（markdown + JSON），每条包含：
   - 页面 / 区域 / 严重性 / 问题描述 / 建议修改（可落地的 CSS / Tailwind / 组件改动）
4. 可选：把 critique 追加到 docs/exec-plans/ui_autopolish_tasks.md 作为后续 Codex / Claude 执行清单

使用方式：
  # 准备：前端需要运行在 http://localhost:5173（可通过 --frontend-url 覆盖）
  .venv/bin/python scripts/automation/ui_autopolish.py                # 截图 + critique + 生成 tasks
  .venv/bin/python scripts/automation/ui_autopolish.py --screenshot-only
  .venv/bin/python scripts/automation/ui_autopolish.py --pages /,/companies,/taxonomy
  .venv/bin/python scripts/automation/ui_autopolish.py --iterations 3  # 迭代多轮，每轮应用建议后重拍

环境变量：
  VISION_MODEL        默认读取 $OPENAI_MODEL；推荐 gpt-4o / gpt-4.1
  OPENAI_API_KEY      必填
  OPENAI_BASE_URL     可选（第三方中转站）
  FRONTEND_URL        默认 http://localhost:5173

输出：
  scripts/automation/screenshots/<timestamp>/<page_slug>_<viewport>.png
  scripts/automation/ui_reports/<timestamp>/critique.md
  scripts/automation/ui_reports/<timestamp>/critique.json
  docs/exec-plans/ui_autopolish_tasks.md  （追加模式）
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import datetime as dt
import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from core.config import settings  # noqa: E402

DEFAULT_PAGES = [
    "/",
    "/upload",
    "/companies",
    "/taxonomy",
    "/frameworks",
    "/compare",
    "/benchmarks",
]
DEFAULT_VIEWPORTS = [
    ("desktop", 1440, 900),
    ("mobile", 390, 844),
]

CRITIC_SYSTEM_PROMPT = """You are a senior product designer and frontend engineer reviewing the
ESG regulatory intelligence platform's UI. Your job is to produce ACTIONABLE,
SPECIFIC critiques that a developer can implement with Tailwind CSS + React.

Evaluate each screenshot on:
1. Visual hierarchy — clarity of primary action, readable scanning order
2. Spacing & rhythm — consistent padding, breathing room, density
3. Typography — font-size ladder, line-height, contrast of weight
4. Color system — contrast ratios, semantic use, accessibility (WCAG AA)
5. Component polish — borders, shadows, rounded corners, interactive states
6. Data density — charts, tables, cards legibility at the given viewport
7. Storytelling — does the page communicate what this product does?

For each issue you find, produce JSON with:
- severity: "critical" | "high" | "medium" | "low"
- area: short human-readable region ("Header", "KPI card", "Trend chart", etc)
- issue: what is wrong (one sentence)
- recommendation: concrete code-level fix (Tailwind class change, spacing value,
  color token, component prop)
- effort: "xs" (1-line CSS), "s" (single component), "m" (multi-component), "l" (redesign)

Return ONLY valid JSON with this schema:
{
  "overall_impression": "one-paragraph verdict",
  "strengths": ["..."],
  "issues": [{"severity": ..., "area": ..., "issue": ..., "recommendation": ..., "effort": ...}],
  "top_3_quick_wins": ["..."]
}
"""


@dataclass
class ShotMeta:
    page: str
    viewport_name: str
    width: int
    height: int
    path: str
    ts: str


@dataclass
class PageCritique:
    page: str
    viewport: str
    overall_impression: str
    strengths: list[str]
    issues: list[dict]
    top_3_quick_wins: list[str]
    screenshot_path: str


def slugify_page(path: str) -> str:
    s = path.strip("/") or "home"
    return s.replace("/", "_")


async def take_screenshots(
    frontend_url: str,
    pages: list[str],
    viewports: list[tuple[str, int, int]],
    out_dir: Path,
) -> list[ShotMeta]:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise SystemExit(
            "playwright not installed. In the frontend/ folder run:\n"
            "  npx playwright install chromium\n"
            "Or for a Python install: pip install playwright && playwright install chromium"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    shots: list[ShotMeta] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            for vp_name, width, height in viewports:
                ctx = await browser.new_context(viewport={"width": width, "height": height})
                page = await ctx.new_page()
                for url_path in pages:
                    slug = slugify_page(url_path)
                    target = f"{frontend_url.rstrip('/')}{url_path}"
                    out_path = out_dir / f"{slug}_{vp_name}.png"
                    try:
                        await page.goto(target, wait_until="networkidle", timeout=25000)
                        await page.wait_for_timeout(1500)  # let charts settle
                        await page.screenshot(path=str(out_path), full_page=True)
                        shots.append(ShotMeta(
                            page=url_path, viewport_name=vp_name,
                            width=width, height=height,
                            path=str(out_path), ts=ts,
                        ))
                        print(f"  📸 {vp_name:7s} {url_path} → {out_path.name}")
                    except Exception as exc:  # noqa: BLE001
                        print(f"  ⚠️  {vp_name} {url_path}: {exc}")
                await ctx.close()
        finally:
            await browser.close()
    return shots


def _image_to_data_url(path: str) -> str:
    b64 = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def critique_one(shot: ShotMeta, model: str) -> PageCritique:
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    messages = [
        {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Page: {shot.page}  |  Viewport: {shot.viewport_name} "
                        f"({shot.width}x{shot.height})\n"
                        "Return only the JSON specified in the system prompt."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": _image_to_data_url(shot.path)},
                },
            ],
        },
    ]

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2048,
            temperature=0.3,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ LLM call failed for {shot.page} {shot.viewport_name}: {exc}")
        return PageCritique(
            page=shot.page, viewport=shot.viewport_name,
            overall_impression=f"LLM error: {exc}",
            strengths=[], issues=[], top_3_quick_wins=[],
            screenshot_path=shot.path,
        )

    content = (resp.choices[0].message.content or "").strip()
    # Strip code fences
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Try to recover by finding first { and last }
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                parsed = {
                    "overall_impression": content[:500],
                    "strengths": [], "issues": [], "top_3_quick_wins": [],
                }
        else:
            parsed = {
                "overall_impression": content[:500],
                "strengths": [], "issues": [], "top_3_quick_wins": [],
            }

    return PageCritique(
        page=shot.page,
        viewport=shot.viewport_name,
        overall_impression=str(parsed.get("overall_impression", "")),
        strengths=list(parsed.get("strengths", [])),
        issues=list(parsed.get("issues", [])),
        top_3_quick_wins=list(parsed.get("top_3_quick_wins", [])),
        screenshot_path=shot.path,
    )


def render_markdown(critiques: list[PageCritique], out_path: Path) -> None:
    lines = [
        "# UI Autopolish Critique Report",
        f"Generated: {dt.datetime.now().isoformat(timespec='seconds')}",
        "",
        f"Pages reviewed: {len({c.page for c in critiques})}  |  "
        f"Total screenshots: {len(critiques)}",
        "",
    ]

    # Aggregate quick wins
    all_quick_wins: list[str] = []
    for c in critiques:
        all_quick_wins.extend(c.top_3_quick_wins)
    if all_quick_wins:
        lines.append("## 🏆 Top Quick Wins (aggregated)")
        lines.append("")
        for w in all_quick_wins[:15]:
            lines.append(f"- {w}")
        lines.append("")

    # Per-page sections
    for c in critiques:
        lines.append(f"## {c.page} — {c.viewport}")
        lines.append("")
        lines.append(f"![screenshot]({Path(c.screenshot_path).name})")
        lines.append("")
        if c.overall_impression:
            lines.append(f"**Impression.** {c.overall_impression}")
            lines.append("")
        if c.strengths:
            lines.append("**Strengths**")
            for s in c.strengths:
                lines.append(f"- ✅ {s}")
            lines.append("")
        if c.issues:
            lines.append("**Issues**")
            lines.append("")
            lines.append("| Severity | Area | Issue | Recommendation | Effort |")
            lines.append("|---|---|---|---|---|")
            sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            issues_sorted = sorted(
                c.issues, key=lambda i: sev_order.get(str(i.get("severity", "low")).lower(), 9)
            )
            for i in issues_sorted:
                sev = i.get("severity", "?")
                area = str(i.get("area", "?")).replace("|", "\\|")
                issue = str(i.get("issue", "?")).replace("|", "\\|")[:200]
                rec = str(i.get("recommendation", "?")).replace("|", "\\|")[:250]
                effort = i.get("effort", "?")
                lines.append(f"| {sev} | {area} | {issue} | {rec} | {effort} |")
            lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def render_task_list(critiques: list[PageCritique], out_path: Path) -> None:
    """Append a Codex/Claude-ready task list."""
    ts = dt.datetime.now().isoformat(timespec="seconds")
    header = f"\n\n## Autopolish run {ts}\n"
    buckets: dict[str, list[str]] = {"critical": [], "high": [], "medium": [], "low": []}
    for c in critiques:
        for i in c.issues:
            sev = str(i.get("severity", "low")).lower()
            if sev not in buckets:
                sev = "low"
            bullet = (
                f"- [ ] **[{c.page} · {c.viewport}]** "
                f"({i.get('area', '?')}) {i.get('issue', '?')} → "
                f"{i.get('recommendation', '?')} _(effort: {i.get('effort', '?')})_"
            )
            buckets[sev].append(bullet)

    body = [header]
    for sev in ("critical", "high", "medium", "low"):
        if buckets[sev]:
            body.append(f"\n### {sev.upper()}\n")
            body.extend(buckets[sev])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(body) + "\n")


async def main_async(args: argparse.Namespace) -> int:
    frontend_url = args.frontend_url or os.environ.get("FRONTEND_URL", "http://localhost:5173")
    pages = args.pages.split(",") if args.pages else DEFAULT_PAGES
    pages = [p.strip() if p.strip().startswith("/") else f"/{p.strip()}" for p in pages]

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    shots_dir = ROOT / "scripts" / "automation" / "screenshots" / ts
    reports_dir = ROOT / "scripts" / "automation" / "ui_reports" / ts
    reports_dir.mkdir(parents=True, exist_ok=True)

    print(f"→ taking screenshots → {shots_dir}")
    shots = await take_screenshots(frontend_url, pages, DEFAULT_VIEWPORTS, shots_dir)

    if not shots:
        print("❌ no screenshots captured — is the frontend running?")
        return 1

    if args.screenshot_only:
        print(f"✅ {len(shots)} screenshots saved to {shots_dir}")
        return 0

    model = args.model or os.environ.get("VISION_MODEL") or settings.openai_model
    print(f"→ running critique with model: {model}")

    critiques: list[PageCritique] = []
    for i, shot in enumerate(shots, 1):
        print(f"  [{i}/{len(shots)}] critiquing {shot.page} {shot.viewport_name} ...")
        critiques.append(critique_one(shot, model))

    # Write outputs
    md_path = reports_dir / "critique.md"
    json_path = reports_dir / "critique.json"
    render_markdown(critiques, md_path)
    json_path.write_text(
        json.dumps([asdict(c) for c in critiques], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    # Copy screenshots next to the report for the markdown to render
    for c in critiques:
        try:
            import shutil
            dst = reports_dir / Path(c.screenshot_path).name
            if not dst.exists():
                shutil.copy2(c.screenshot_path, dst)
        except Exception:  # noqa: BLE001
            pass

    tasks_path = ROOT / "docs" / "exec-plans" / "ui_autopolish_tasks.md"
    render_task_list(critiques, tasks_path)

    print("")
    print(f"✅ critique report: {md_path}")
    print(f"✅ structured JSON: {json_path}")
    print(f"✅ appended tasks:   {tasks_path}")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--frontend-url", help="default http://localhost:5173")
    p.add_argument("--pages", help="comma-separated paths, default: " + ",".join(DEFAULT_PAGES))
    p.add_argument("--model", help="vision-capable LLM model (default $VISION_MODEL or $OPENAI_MODEL)")
    p.add_argument("--screenshot-only", action="store_true", help="skip LLM critique")
    p.add_argument("--iterations", type=int, default=1,
                   help="not yet implemented — placeholder for future iterative polish loop")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
