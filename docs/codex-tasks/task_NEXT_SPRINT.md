# 下一冲刺执行索引（Task 19–26）

**版本目标**: v0.3.0 — 全球三地 ESG 对比 + UI 升级  
**更新时间**: 2026-04-13  
**执行方式**: 逐条喂给 Codex loop，或按优先级分批

---

## 任务一览

| # | 文件 | 内容 | 优先级 | 依赖 | 预估时间 |
|---|------|------|--------|------|---------|
| 19 | `task_19_us_esg_standard.md` | 美国 SEC + GRI + SASB 框架评分 | P0 | 无 | 45–60 min |
| 20 | `task_20_three_region_comparison.md` | 三地对比引擎 + `/compare/regional` API | P0 | Task 19 | 40–50 min |
| 21 | `task_21_comparison_page.md` | RegionalPage 前端（雷达图 + 监管矩阵） | P0 | Task 20 | 50–60 min |
| 22 | `task_22_ui_ux_polish.md` | 全站 UI 打磨（骨架屏/Toast/动画/移动端） | P1 | 无 | 45–60 min |
| 23 | `task_23_dashboard_analytics.md` | Dashboard 升级（趋势图/排行/覆盖率） | P1 | Task 22 | 40–50 min |
| 24 | `task_24_pdf_cjk_charts.md` | PDF CJK 字体 + 排放柱状图嵌入 | P1 | 无 | 35–45 min |
| 25 | `task_25_company_profile.md` | 企业画像详情页（历年趋势 + 六框架） | P1 | Task 19 | 45–55 min |
| 26 | `task_26_api_perf_cache.md` | API TTL 缓存层 | P2 | 无 | 30 min |

**总预估**: 5.5–7 小时（Codex 可并行处理无依赖任务）

---

## 执行依赖图

```
Task 19 (US ESG)
    ├── Task 20 (Regional Compare API)
    │       └── Task 21 (RegionalPage 前端)
    └── Task 25 (Company Profile)

Task 22 (UI Polish)
    └── Task 23 (Dashboard Analytics)

Task 24 (PDF CJK)   ← 独立，随时可做
Task 26 (Cache)     ← 独立，随时可做
```

---

## Codex 执行命令

### 批次 A（P0 核心功能，按序执行）

```bash
# Task 19
codex "读取 docs/codex-tasks/task_19_us_esg_standard.md，
严格按照步骤实现 SEC Climate + GRI Universal + SASB 三个 ESG 框架评分器，
完成后运行 pytest tests/ -v 确认全通过，然后提交。
遇到失败最多自愈 3 次再停止。"

# Task 20（Task 19 完成后）
codex "读取 docs/codex-tasks/task_20_three_region_comparison.md，
实现三地对比引擎和 /frameworks/compare/regional API 端点，
完成后验证端点返回 200，提交。"

# Task 21（Task 20 完成后）
codex "读取 docs/codex-tasks/task_21_comparison_page.md，
实现 RegionalPage.tsx 前端页面，npm run build 通过后提交。"
```

### 批次 B（P1 可并行，与批次 A 同时开）

```bash
# Task 22
codex "读取 docs/codex-tasks/task_22_ui_ux_polish.md，
按步骤实现全站 UI 打磨，npm run build 通过后提交。"

# Task 24（独立）
codex "读取 docs/codex-tasks/task_24_pdf_cjk_charts.md，
实现 PDF CJK 字体支持和排放柱状图，验证 PDF > 20KB，提交。"
```

### 批次 C（批次 B 完成后）

```bash
# Task 23（Task 22 完成后）
codex "读取 docs/codex-tasks/task_23_dashboard_analytics.md，
新增 /report/dashboard/stats API 和 Dashboard 趋势图，提交。"

# Task 25（Task 19 完成后）
codex "读取 docs/codex-tasks/task_25_company_profile.md，
实现企业画像 Profile API 和 CompanyProfilePage，提交。"

# Task 26（随时）
codex "读取 docs/codex-tasks/task_26_api_perf_cache.md，
为框架评分端点加 TTL 缓存，提交。"
```

---

## 全局自愈指令（每条 Codex 任务均适用）

```
每个 Step 完成后立即运行验证命令。
若失败：
1. 读错误信息
2. 定位原因（import 路径？字段名？类型不匹配？）
3. 修复
4. 重新验证
5. 最多重试 3 次，第 3 次仍失败则停止并说明卡点

每个任务最终必须：
- pytest tests/ -v 全部通过（如有后端改动）
- npm run build 无 TS 报错（如有前端改动）
- git commit 已完成
```

---

## v0.3.0 完成标准

- [ ] 6 个 ESG 框架（EU Taxonomy + CSRC + CSRD + SEC + GRI + SASB）全部可用
- [ ] `/frameworks/compare/regional` 返回三地分组 + 维度矩阵
- [ ] 前端新增 RegionalPage（`/regional`）
- [ ] 前端新增 CompanyProfilePage（`/companies/:name`）
- [ ] Dashboard 有趋势图 + 覆盖率条形
- [ ] PDF 中文不乱码，包含柱状图
- [ ] 全站骨架屏 + Toast 错误提示
- [ ] `pytest tests/ -v` 全部通过
- [ ] `npm run build` 无 TS 报错
