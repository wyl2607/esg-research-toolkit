# Company + Year 双下拉选择器 (F1)

**Status**: draft (design) · **Owner**: frontend · **Depth**: 2026-04-18

## Goal

在所有 company-centric 页面（CompanyProfile / Frameworks / Benchmark / Taxonomy 等）把现在"单一 company:year combo（`BASF|2024`）"的下拉改成 **two-step picker**：

1. **Company** — 始终列出所有历史上出现过的公司名（即使某年没数据也可见）。
2. **Year** — 在选中公司后显示，区分 **已导入** 与 **未导入** 两类年份，让用户一眼看到"这家公司在数据库里有/没有哪几年"。

## Pain Point

现状的 `{name}|{year}` combo 下拉让 recruiter 无法区分「这家公司 2022 年度没披露」和「我们还没抓取」——只能看到数据库里"有"的年份。和 Bloomberg ESG / MSCI 的"选好公司就默认最新年"的风格无区别，浪费了本项目的差异点（**gap-driven, 我们允许用户发起补抓**）。

## User Stories

- (U1) 作为用户，我在 CompanyProfile 页面选 BASF，马上能看到 `2020–2024` 五个年份，已导入的年高亮，未导入的年用虚线+“未入库”标签。
- (U2) 点击**已导入**的年 → 直接加载页面数据。
- (U3) 点击**未入库**的年 → 触发一条 pending 行为（见下方 Decision）。
- (U4) 语言切换不影响已选公司/年。

## Decision Points

| # | 决策 | 选项 | 默认 |
| - | --- | --- | --- |
| D1 | 未入库年份的行为 | (a) 置灰禁用 / (b) 跳 Upload / (c) 触发 auto-fetch | **(b) 跳 Upload 预填 company+year** |
| D2 | "可选年份"来源 | (a) 硬编码 `currentYear-5..currentYear` / (b) 按行业自动推断 / (c) 后端返回推荐列表 | (a) 先固化成 currentYear-5..currentYear-1 |
| D3 | 下拉组件 | 两个独立 Select / 一个 Combobox | 两个 Select（Company → Year），`aria-controls` 关联 |

> D1=b 原因：auto-fetch 涉及版权和数据合规（见 `auto_disclosure_fetch.md`），不宜默认触发；跳 Upload 让用户显式上传 PDF 或粘贴 URL，链路清晰、demo 友好。

## API Surface

前端现有 `listCompanies()` 返回 `{ company_name, report_year }[]`。改造：

```ts
// 新增 GET /companies  —— 改为带年份列表聚合（保留旧接口做向后兼容）
interface CompanyWithYears {
  company_name: string
  sector?: string | null
  imported_years: number[]       // 数据库中已存在
  suggested_years: number[]      // currentYear-5 .. currentYear-1
}
```

后端改动范围：`report_parser/api.py`（或 `companies/api.py`）添加 `/companies/v2` 端点；旧 `/companies` 保持不变，先灰度前端切新路径。

## UI Sketch

```
[Company ▼ BASF SE                 ]
          └─ 19 公司，按字母排序

[Year ▼  2024 ✓                    ]
         ├─ 2024  ✓ imported (active)
         ├─ 2023  ✓ imported
         ├─ 2022  · not imported — click to upload
         ├─ 2021  · not imported
         └─ 2020  · not imported
```

- **已导入**：实心 text-slate-800 + `CheckIcon`
- **未导入**：text-slate-400 + dashed border，右侧 `Upload ↗` icon

## Rollout

1. 先在 CompanyProfile 单点实装并加 Playwright smoke。
2. 跑通后把同一 `<CompanyYearPicker>` 抽成 `frontend/src/components/CompanyYearPicker.tsx`。
3. 迁移 Frameworks / Benchmark / Taxonomy 四个页面。

## Done Criteria

- [ ] `/api/companies/v2` 返回 `imported_years` + `suggested_years`
- [ ] `CompanyYearPicker` 组件替换 4 个页面里的 combo Select
- [ ] 点击未导入年份跳转 `/upload?company=X&year=Y`
- [ ] Playwright smoke：已导入年和未导入年的点击路径分别有 assertion
- [ ] zh/en/de 三语本地化 key 完整

## 非目标

- 不做行业维度过滤。
- 不在本次改后端数据库 schema。
- 不实现 auto-fetch（见独立 doc）。
