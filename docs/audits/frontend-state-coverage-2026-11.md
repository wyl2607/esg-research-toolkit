# 前端空/错误状态覆盖清单（2026-11）

## 目的与范围

本清单只记录事实，供后续决定是否补齐状态 UI，本卡不改任何页面代码。

- 范围：`frontend/src/pages/` 下 15 个页面入口（`*.tsx`，不含 `company-profile/`、`compare/`、`manual-case/` 子目录内的工具函数）。
- 共享组件：`frontend/src/components/QueryStateCard.tsx`。
- 判定口径：「使用 QueryStateCard」指页面文件（或其直接子组件）实际渲染了该组件；`BenchmarkPage` 虽未使用该组件，但用 `Skeleton`/`NoticeBanner`/内联文本实现了等价状态。
- `loading`/`error`/`empty` 证据列均给出 `文件:行号`；标注「未处理」表示该状态下没有对应分支。

## 汇总

- 15 个页面中 11 个引用 `QueryStateCard`：Companies、CompanyProfile、Compare、CoverageField、Dashboard、Frameworks、ManualCaseBuilder、PendingDisclosures、Regional、Taxonomy、Upload。
- 未引用 `QueryStateCard` 的 4 个：Benchmark（内联状态）、Lcoe（状态在子组件）、Saf（内联状态）、DesignPreview（静态页，无数据请求）。
- 明确的空状态缺口：CoverageField、Lcoe、Saf、Dashboard（loading 与 empty 冲突）、Frameworks/Regional/Taxonomy（report 结果为空时）、Upload（四个次要查询）、Benchmark（公司筛选查询）。

| # | 页面 | 是否用 react-query | 是否用 QueryStateCard | loading 证据 | error 证据 | empty 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 1 | BenchmarkPage | 是（useQuery 215/228/234，useMutation 240） | 否（内联 Skeleton/NoticeBanner） | BenchmarkPage.tsx:87、BenchmarkPage.tsx:159、BenchmarkPage.tsx:375 | BenchmarkPage.tsx:93、BenchmarkPage.tsx:165、BenchmarkPage.tsx:393 | BenchmarkPage.tsx:99、BenchmarkPage.tsx:171 | 主面板三态齐全；`companiesCoverageQuery` 仅错误 308，缺 loading/empty |
| 2 | CompaniesPage | 是（useQuery 116，useMutation 121） | 是（import 8） | CompaniesPage.tsx:266 | CompaniesPage.tsx:191、CompaniesPage.tsx:198 | CompaniesPage.tsx:272 | 三态齐全 |
| 3 | CompanyProfilePage | 是（useQuery 81） | 是（import 9） | CompanyProfilePage.tsx:319 | CompanyProfilePage.tsx:329 | CompanyProfilePage.tsx:341 | 三态齐全 |
| 4 | ComparePage | 是（useQuery 39） | 是（import 9） | ComparePage.tsx:84 | ComparePage.tsx:74 | ComparePage.tsx:92 | 三态齐全 |
| 5 | CoverageFieldPage | 是（useQuery 50） | 是（import 7） | CoverageFieldPage.tsx:139 | CoverageFieldPage.tsx:145 | 未处理（无 `rows.length === 0` 分支，表格直接渲染于 CoverageFieldPage.tsx:152/176） | 缺空状态 |
| 6 | DashboardPage | 是（useQuery 81/86） | 是（import 4） | DashboardPage.tsx:118、DashboardPage.tsx:308 | DashboardPage.tsx:205、DashboardPage.tsx:301 | DashboardPage.tsx:280、DashboardPage.tsx:314 | coverage 的 empty 在 280 未等 `statsLoading` 结束，加载中会误显示「无数据」 |
| 7 | DesignPreviewPage | 否（静态展示页） | 否 | N/A（无请求） | N/A（无请求） | N/A（无请求） | 开发预览页，无数据依赖，无需状态处理 |
| 8 | FrameworksPage | 是（useQuery 348/353） | 是（import 7） | FrameworksPage.tsx:387、FrameworksPage.tsx:419 | FrameworksPage.tsx:373 | FrameworksPage.tsx:410、FrameworksPage.tsx:444 | report 存在但 `frameworks` 为空时无空状态（渲染分支 FrameworksPage.tsx:428） |
| 9 | LcoePage | 是（useQuery 42，useMutation 34/35） | 否（子组件 LcoeInputForm 使用，LcoeInputForm.tsx:98/104） | LcoePage.tsx:102、LcoePage.tsx:107（子组件渲染 LcoeInputForm.tsx:97、LcoeInputForm.tsx:269） | LcoePage.tsx:103、LcoePage.tsx:108-109（子组件渲染 LcoeInputForm.tsx:103、LcoeInputForm.tsx:272） | 未处理（benchmarks 为空对象时无提示，预设区直接为空） | 缺 benchmarks 空状态 |
| 10 | ManualCaseBuilderPage | 是（useQuery 35，useMutation 60） | 是（import 9） | ManualCaseBuilderPage.tsx:155 | ManualCaseBuilderPage.tsx:161、ManualCaseBuilderPage.tsx:141（子组件保存错误 ManualCaseFormPanel.tsx:219） | ManualCaseBuilderPage.tsx:169 | 三态齐全 |
| 11 | PendingDisclosuresPage | 是（useQuery 37/42，useMutation 66/79） | 是（import 18） | PendingDisclosuresPage.tsx:116 | PendingDisclosuresPage.tsx:124、PendingDisclosuresPage.tsx:132 | PendingDisclosuresPage.tsx:140 | 三态齐全 |
| 12 | RegionalPage | 是（useQuery 36/46） | 是（import 16） | RegionalPage.tsx:115、RegionalPage.tsx:147 | RegionalPage.tsx:98 | RegionalPage.tsx:138、RegionalPage.tsx:156 | 选中年度但 report 为空时无空状态（渲染分支 RegionalPage.tsx:165） |
| 13 | SafPage | 是（useQuery 131，useMutation 129） | 否（内联文本） | SafPage.tsx:199、SafPage.tsx:272 | SafPage.tsx:278（仅 mutation；benchmarks 错误未处理） | SafPage.tsx:287（仅结果区） | benchmarks 缺 error/empty；mutation 错误直接 `String(...)` 未本地化 |
| 14 | TaxonomyPage | 是（useQuery 34/44/52） | 是（import 6） | TaxonomyPage.tsx:112、TaxonomyPage.tsx:145、TaxonomyPage.tsx:212 | TaxonomyPage.tsx:98、TaxonomyPage.tsx:151 | TaxonomyPage.tsx:135、TaxonomyPage.tsx:159 | report 存在但内容为空时无空状态（渲染分支 TaxonomyPage.tsx:221） |
| 15 | UploadPage | 是（useQuery 90/102/115/128/143，useMutation 72/81/159/176/191） | 是（import 22） | UploadPage.tsx:454、UploadPage.tsx:477 | UploadPage.tsx:463、UploadPage.tsx:486 | 未处理（上传结果/空队列无独立空状态） | `pendingDisclosures`/`laneStats`/`companyCoverage`/`existingReport` 四个查询在主流程无 loading/error/empty UI（仅 DEV 面板 359-377） |

## 未处理项的修复建议（每项一句）

- BenchmarkPage：为 `companiesCoverageQuery` 补 loading（选择器禁用/骨架）与 `data.length === 0` 空提示，或在 picker 上方复用统一状态卡。
- CoverageFieldPage：在 `CoverageFieldPage.tsx:151` 的表格分支前增加 `rows.length === 0` 的 empty `QueryStateCard`，并区分「字段无效」与「已有公司但该字段无值」。
- DashboardPage：把 coverage 的 empty 分支（`DashboardPage.tsx:280`）改为 `!statsLoading && coverageRows.length === 0`，加载中先走 loading。
- FrameworksPage：在 `report && report.frameworks.length === 0` 时渲染 empty `QueryStateCard`，避免出现空网格。
- LcoePage：在 `benchmarks` 已加载但 `Object.keys(benchmarks).length === 0` 时，于预设区显示 empty 状态。
- RegionalPage：为「已选公司+年度、report 为空且非 loading/error」补 empty 状态；`cross_matrix` 为空时也应提示。
- SafPage：从 benchmarks 查询解构 `isError/error` 并渲染错误态；预设为空时显示 empty；mutation 错误改用 `localizeErrorMessage`。
- TaxonomyPage：在 `report` 存在但各项指标/明细为空时补 empty 状态。
- UploadPage：至少用统一 banner 呈现 `pendingDisclosuresQuery`、`laneStatsQuery`、`companyCoverageQuery`、`existingReportQuery` 的 error，并对 pending 列表为空给出状态提示。

## 备注

- `docs/audits/` 已在 `.guard/public-prefixes.txt` 中列为公开前缀，本文件可归类为 public。
- 本清单仅做静态代码阅读，未运行前端或调用后端；行号基于当前 worktree 的 `origin/main`（`360b8eb`）。
