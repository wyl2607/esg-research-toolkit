# Task 25: 企业 ESG 画像详情页

**目标**: 新增 `/companies/:name/:year` 深度详情页，整合该公司所有维度数据：基础指标 + 六框架得分 + 历年趋势 + 全球同行基准对比。

**前置条件**: Task 19（6 框架）完成  
**优先级**: P1  
**预计时间**: 45–55 分钟

---

## 背景

当前 `CompaniesPage` 只有列表 + 删除，点击没有详情。  
本任务添加独立的 `CompanyProfilePage`，让用户看到一家企业的完整 ESG 画像。

---

## Step 1 — 后端：企业 Profile API

在 `report_parser/api.py` 新增：

```python
@router.get("/companies/{company_name}/profile")
def get_company_profile(
    company_name: str,
    db: Session = Depends(get_db),
):
    """
    返回该企业所有年份报告 + 最新年份的六框架评分
    """
    from sqlalchemy import asc
    records = (
        db.query(CompanyReport)
        .filter(CompanyReport.company_name == company_name,
                CompanyReport.deletion_requested == False)
        .order_by(asc(CompanyReport.report_year))
        .all()
    )
    if not records:
        raise HTTPException(404, f"No reports found for {company_name}")

    # 历年趋势数据
    trend = [
        {
            "year": r.report_year,
            "scope1": r.scope1_co2e_tonnes,
            "scope2": r.scope2_co2e_tonnes,
            "scope3": r.scope3_co2e_tonnes,
            "renewable_pct": r.renewable_energy_pct,
            "taxonomy_aligned": r.taxonomy_aligned_revenue_pct,
            "female_pct": r.female_pct,
        }
        for r in records
    ]

    # 最新年份
    latest = records[-1]
    latest_data = CompanyESGData(
        company_name=latest.company_name,
        report_year=latest.report_year,
        scope1_co2e_tonnes=latest.scope1_co2e_tonnes,
        scope2_co2e_tonnes=latest.scope2_co2e_tonnes,
        scope3_co2e_tonnes=latest.scope3_co2e_tonnes,
        energy_consumption_mwh=latest.energy_consumption_mwh,
        renewable_energy_pct=latest.renewable_energy_pct,
        water_usage_m3=latest.water_usage_m3,
        waste_recycled_pct=latest.waste_recycled_pct,
        total_revenue_eur=latest.total_revenue_eur,
        taxonomy_aligned_revenue_pct=latest.taxonomy_aligned_revenue_pct,
        total_capex_eur=latest.total_capex_eur,
        taxonomy_aligned_capex_pct=latest.taxonomy_aligned_capex_pct,
        total_employees=latest.total_employees,
        female_pct=latest.female_pct,
        primary_activities=json.loads(latest.primary_activities) if latest.primary_activities else [],
    )

    # 六框架评分
    from esg_frameworks.api import _SCORERS
    framework_scores = [scorer(latest_data).model_dump() for scorer in _SCORERS.values()]

    return {
        "company_name": company_name,
        "years_available": [r.report_year for r in records],
        "latest_year": latest.report_year,
        "trend": trend,
        "framework_scores": framework_scores,
        "latest_metrics": latest_data.model_dump(),
    }
```

**验证**:
```bash
curl -sf "http://localhost:8000/report/companies/宁德时代/profile" | python3 -m json.tool | head -30
```

---

## Step 2 — 前端 CompanyProfilePage

新建 `frontend/src/pages/CompanyProfilePage.tsx`：

布局：
```
┌─────────────────────────────────────────┐
│ 🏢 [公司名] · [年份] ← ← 返回列表       │
└─────────────────────────────────────────┘

┌──────────┬──────────┬──────────┬────────┐
│ Scope 1  │ Scope 2  │可再生能源│ 员工数  │  ← MetricCard ×4
└──────────┴──────────┴──────────┴────────┘

┌─────────────────┬───────────────────────┐
│ 六框架评分雷达图  │  历年指标趋势折线图    │
│ (6 个点)        │  (scope1/renewable)   │
└─────────────────┴───────────────────────┘

┌─────────────────────────────────────────┐
│ 框架详情 Accordion（展开各框架维度分解）   │
└─────────────────────────────────────────┘
```

路由：`/companies/:companyName`

关键代码：
```tsx
import { useParams, useNavigate } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const { companyName } = useParams<{ companyName: string }>()
const { data: profile, isLoading } = useQuery({
  queryKey: ['profile', companyName],
  queryFn: () => getCompanyProfile(companyName!),
  enabled: !!companyName,
})

// 历年趋势图
<ResponsiveContainer width="100%" height={220}>
  <LineChart data={profile.trend}>
    <XAxis dataKey="year" />
    <YAxis />
    <Tooltip />
    <Legend />
    <Line type="monotone" dataKey="scope1" stroke="#ef4444" name="Scope 1" dot />
    <Line type="monotone" dataKey="renewable_pct" stroke="#22c55e" name="Renewable %" dot />
  </LineChart>
</ResponsiveContainer>
```

---

## Step 3 — Companies 列表添加点击跳转

在 `CompaniesPage.tsx` 的表格行加入：
```tsx
import { useNavigate } from 'react-router-dom'
const nav = useNavigate()
// onClick:
onClick={() => nav(`/companies/${encodeURIComponent(record.company_name)}`)}
className="cursor-pointer hover:bg-slate-50"
```

---

## Step 4 — 路由注册 + i18n + 构建

`App.tsx`：
```tsx
import { CompanyProfilePage } from './pages/CompanyProfilePage'
<Route path="/companies/:companyName" element={<CompanyProfilePage />} />
```

i18n 三语新增 `"profile"` 节（EN/ZH/DE 各一条）。

```bash
cd frontend && npm run build 2>&1 | tail -5
git add .
git commit -m "feat: 企业 ESG 画像页（历年趋势 + 六框架评分 + 指标总览）

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 完成标准

- [ ] GET `/report/companies/{name}/profile` 返回 200
- [ ] `CompanyProfilePage.tsx` 存在
- [ ] `/companies/:companyName` 路由可访问
- [ ] Companies 列表行点击可跳转
- [ ] 趋势折线图渲染正常
- [ ] `npm run build` 无 TS 报错
