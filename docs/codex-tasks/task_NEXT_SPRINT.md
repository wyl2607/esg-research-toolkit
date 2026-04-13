# 下一冲刺执行索引（Career-first / Product-first）

**版本目标**: v0.4.0-alpha — 高可信度分析引擎作品  
**更新时间**: 2026-04-13  
**执行方式**: 先打穿数据、版本、证据、趋势，再做展示层与轻量产品化

> 总路线图见 [CAREER_PRODUCT_ROADMAP.md](../CAREER_PRODUCT_ROADMAP.md)

---

## 优先级原则

当前冲刺不以“功能越多越好”为目标，而以“求职展示价值 + 产品壁垒”最大化为目标。

执行顺序固定为：

1. 历史趋势 + 证据追溯 + 规则版本化
2. 公司画像页 + 可展示案例 + 英文说明
3. 跨法规映射和差异解释
4. 行业 benchmark / peer compare
5. API、导出、顾问交付能力
6. 登录、付费、权限、运营后台

---

## 任务一览（当前推荐顺序）

| # | 文件 | 内容 | 优先级 | 依赖 | 预估时间 |
|---|------|------|--------|------|---------|
| 27 | `task_27_analysis_engine_foundation.md` | 数据/版本/证据/趋势基础层 | P0 | 无 | 2–3 天 |
| 25 | `task_25_company_profile.md` | 企业画像详情页（趋势 + 六框架 + 展示主页面） | P0 | Task 27 | 1–2 天 |
| 23 | `task_23_dashboard_analytics.md` | Dashboard 升级（趋势图/覆盖率/排行） | P1 | Task 27 | 0.5–1 天 |
| 20 | `task_20_three_region_comparison.md` | 三地对比引擎 + 监管差距矩阵 | P1 | Task 27 | 0.5–1 天 |
| 21 | `task_21_comparison_page.md` | RegionalPage 前端（雷达图 + 监管矩阵） | P1 | Task 20 | 0.5–1 天 |
| 19 | `task_19_us_esg_standard.md` | 美国 SEC + GRI + SASB 框架评分 | P1 | 无 | 0.5–1 天 |
| 24 | `task_24_pdf_cjk_charts.md` | PDF CJK 字体 + 排放柱状图嵌入 | P2 | 无 | 0.5 天 |
| 26 | `task_26_api_perf_cache.md` | API TTL 缓存层 | P2 | Task 27 | 0.5 天 |
| TBA | case-study packaging | 英文案例、截图、招聘展示物料 | P0 | Task 25 | 0.5–1 天 |

**总预估**: 3–5 周可形成强作品；12 周可形成轻量产品雏形

---

## 执行依赖图

```
Task 27 (Analysis Foundation)
    ├── Task 25 (Company Profile)
    │       └── case-study packaging
    ├── Task 23 (Dashboard Analytics)
    ├── Task 20 (Regional Compare API)
    │       └── Task 21 (RegionalPage 前端)
    └── Task 26 (Cache / reuse)

Task 19 (US ESG) can run before or alongside Task 20 if needed
Task 24 (PDF CJK) remains independent and lower priority
```

---

## Codex 执行命令

### 批次 A（最高优先，先做壁垒）

```bash
# Task 27
codex "读取 docs/CAREER_PRODUCT_ROADMAP.md 和 docs/codex-tasks/task_27_analysis_engine_foundation.md，
优先实现 reporting period、evidence metadata、framework version persistence 和 history/profile API。
完成后运行 pytest 与前端构建验证，再提交。"

# Task 25（Task 27 后）
codex "读取 docs/codex-tasks/task_25_company_profile.md，
在新的 history/evidence 基础上实现企业画像详情页，把它做成作品集主页面。
完成后运行 npm run build 和相关测试，再提交。"
```

### 批次 B（第二优先，增强展示和解释）

```bash
# Task 23
codex "读取 docs/codex-tasks/task_23_dashboard_analytics.md，
优先补强趋势、覆盖率和招聘展示价值，不做与主线无关的装饰。"

# Task 20
codex "读取 docs/codex-tasks/task_20_three_region_comparison.md，
实现三地监管对比与差距矩阵，要求输出可解释、可扩展、能服务后续案例分析。 "
```

### 批次 C（第三优先，扩展差异化）

```bash
# Task 21
codex "读取 docs/codex-tasks/task_21_comparison_page.md，
将三地监管矩阵做成高可信度展示页面，保留 evidence / explanation 扩展位。"

# Task 19
codex "读取 docs/codex-tasks/task_19_us_esg_standard.md，
补齐美国侧框架，为跨法规映射和跨地区比较提供支撑。"

# Task 26
codex "读取 docs/codex-tasks/task_26_api_perf_cache.md，
为 history/profile/framework 结果加缓存与复用能力，避免重复计算。"

# Task 24（低优先独立）
codex "读取 docs/codex-tasks/task_24_pdf_cjk_charts.md，
在主线完成后补 PDF 展示质量，用于咨询式交付和导出。"
```

---

## 当前阶段不要优先做

- 登录系统
- 支付
- 权限体系
- 客户后台
- 复杂运营页面
- 泛化过度的企业工作流

这些功能放到分析引擎和展示价值成熟之后再做。

---

## 全局自愈指令（每条 Codex 任务均适用）

1. 每个 Step 完成后立即运行验证命令。
2. 若失败，先读错误信息，再定位原因，再修复。
3. 最多重试 3 次；第 3 次仍失败则停止并写明卡点。
4. 涉及后端改动时，必须跑 `pytest`。
5. 涉及前端改动时，必须跑 `npm run build`。
6. 若改动触及主线展示能力，优先补最关键测试而不是堆次要功能。

---

## v0.4.0-alpha 完成标准

- [ ] 项目具备明确的 reporting period / evidence / framework version 基础层
- [ ] 企业画像页可作为作品集主展示页面
- [ ] 至少 2 个真实公司案例可以完成趋势和解释展示
- [ ] 英文说明可以支撑求职演示
- [ ] 核心 API 与前端构建验证通过
- [ ] 新功能明显服务于“高可信度分析引擎作品”目标
