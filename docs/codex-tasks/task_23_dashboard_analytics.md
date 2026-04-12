# Task 23: Dashboard 分析看板升级

**目标**: 把 Dashboard 从静态汇总卡片升级为动态分析看板——趋势图、行业基准对比、Top/Bottom 排行、指标热力图。

**前置条件**: Task 22 完成（UI 基础已统一）  
**优先级**: P1  
**预计时间**: 40–50 分钟

---

## Step 1 — 后端新增 Dashboard 统计 API

在 `report_parser/api.py` 新增端点：

```python
@router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    返回 Dashboard 所需的聚合统计数据：
    - 公司数量、平均 Taxonomy 对齐度、平均可再生能源占比
    - 按年份分组的上传趋势
    - Scope 1 排放 Top 5 / Bottom 5
    - 各指标覆盖率（有多少公司填写了该字段）
    """
    records = list_reports(db, skip=0, limit=10000)
    
    if not records:
        return {
            "total_companies": 0,
            "avg_taxonomy_aligned": 0,
            "avg_renewable_pct": 0,
            "yearly_trend": [],
            "top_emitters": [],
            "bottom_emitters": [],
            "coverage_rates": {},
        }
    
    import statistics
    
    # 年度趋势
    from collections import defaultdict
    yearly: dict[int, int] = defaultdict(int)
    for r in records:
        yearly[r.report_year] += 1
    yearly_trend = [{"year": y, "count": c} for y, c in sorted(yearly.items())]
    
    # 平均值（只统计非 None）
    tax_vals = [r.taxonomy_aligned_revenue_pct for r in records if r.taxonomy_aligned_revenue_pct]
    ren_vals  = [r.renewable_energy_pct for r in records if r.renewable_energy_pct]
    
    # 排放排行
    emitters = [(r.company_name, r.report_year, r.scope1_co2e_tonnes)
                for r in records if r.scope1_co2e_tonnes]
    emitters.sort(key=lambda x: x[2], reverse=True)
    
    # 字段覆盖率
    fields = ["scope1_co2e_tonnes","scope2_co2e_tonnes","scope3_co2e_tonnes",
              "energy_consumption_mwh","renewable_energy_pct","water_usage_m3",
              "waste_recycled_pct","taxonomy_aligned_revenue_pct","female_pct"]
    coverage = {
        f: round(sum(1 for r in records if getattr(r, f) is not None) / len(records) * 100, 1)
        for f in fields
    }
    
    return {
        "total_companies": len(records),
        "avg_taxonomy_aligned": round(statistics.mean(tax_vals), 1) if tax_vals else 0,
        "avg_renewable_pct": round(statistics.mean(ren_vals), 1) if ren_vals else 0,
        "yearly_trend": yearly_trend,
        "top_emitters": [{"company": e[0], "year": e[1], "scope1": e[2]} for e in emitters[:5]],
        "bottom_emitters": [{"company": e[0], "year": e[1], "scope1": e[2]} for e in emitters[-5:][::-1]],
        "coverage_rates": coverage,
    }
```

**验证**:
```bash
source .venv/bin/activate
uvicorn main:app --port 8000 &
sleep 2
curl -sf http://localhost:8000/report/dashboard/stats | python3 -m json.tool
kill %1
```

---

## Step 2 — 前端 Dashboard 重构

重构 `frontend/src/pages/DashboardPage.tsx`，布局如下：

```
┌─────────────┬─────────────┬─────────────┐
│ 公司数量     │ 平均 Taxonomy│ 平均可再生能源│  ← MetricCard ×3
└─────────────┴─────────────┴─────────────┘

┌───────────────────┬────────────────────┐
│  年度上传趋势      │  排放 Top 5 排行   │
│  (BarChart)       │  (HorizontalBar)   │
└───────────────────┴────────────────────┘

┌──────────────────────────────────────────┐
│  指标覆盖率热力图                         │
│  (Progress bar grid × 9 字段)            │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  最近分析（表格，可点击跳转 Taxonomy 页）  │
└──────────────────────────────────────────┘
```

关键代码片段：

```tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
         Cell } from 'recharts'
import { getDashboardStats } from '@/lib/api'

// 覆盖率热力图
const CoverageBar = ({ label, pct }: { label: string; pct: number }) => (
  <div className="flex items-center gap-3 text-sm">
    <span className="w-36 text-slate-600 shrink-0">{label}</span>
    <div className="flex-1 bg-slate-100 rounded-full h-2">
      <div
        className={`h-2 rounded-full transition-all ${
          pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-400' : 'bg-red-400'
        }`}
        style={{ width: `${pct}%` }}
      />
    </div>
    <span className="w-10 text-right font-medium text-slate-700">{pct}%</span>
  </div>
)
```

---

## Step 3 — 前端 API 扩展

在 `frontend/src/lib/api.ts` 增加：

```typescript
export interface DashboardStats {
  total_companies: number
  avg_taxonomy_aligned: number
  avg_renewable_pct: number
  yearly_trend: Array<{ year: number; count: number }>
  top_emitters: Array<{ company: string; year: number; scope1: number }>
  bottom_emitters: Array<{ company: string; year: number; scope1: number }>
  coverage_rates: Record<string, number>
}

export const getDashboardStats = (): Promise<DashboardStats> =>
  apiFetch('/report/dashboard/stats')
```

---

## Step 4 — i18n 补充

在三语 JSON 的 `"dashboard"` 节增加：
```json
"yearlyTrend": "Yearly Upload Trend",
"topEmitters": "Top 5 Emitters (Scope 1)",
"coverageRates": "Data Coverage Rates",
"uploads": "Uploads"
```

---

## Step 5 — 测试 + 提交

```bash
pytest tests/ -v -q && \
cd frontend && npm run build 2>&1 | tail -5 && \
cd .. && git add . && git commit -m "feat: Dashboard 升级——年度趋势图、排放排行、指标覆盖率热力图

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 完成标准

- [ ] GET `/report/dashboard/stats` 返回 200 + 完整 JSON
- [ ] DashboardPage 展示年度趋势 BarChart
- [ ] DashboardPage 展示 Top 5 排放排行
- [ ] DashboardPage 展示 9 字段覆盖率条形
- [ ] `npm run build` 无 TS 报错
