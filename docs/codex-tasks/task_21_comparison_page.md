# Task 21: 前端三地对比页面（ComparisonPage 升级）

**目标**: 将现有 `/compare`（公司横向对比）升级，并新增 `/frameworks/regional` 页面，实现 EU/CN/US 三地监管框架可视化对比。

**前置条件**: Task 19 + Task 20 完成  
**优先级**: P0  
**预计时间**: 50–60 分钟

---

## 背景

当前 `ComparePage.tsx` 是 4 家公司并排比较简单指标。  
本任务在此基础上：
1. **升级 ComparePage**：加入三地 ESG 得分对比雷达图
2. **新增 RegionalPage**（`/regional`）：展示三地监管框架横向对比，维度交叉矩阵，合规优先级

---

## Step 1 — 新建 `frontend/src/pages/RegionalPage.tsx`

```tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { listCompanies, getRegionalComparison } from '@/lib/api'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Legend } from 'recharts'
import { Globe, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react'

const REGION_COLORS = { EU: '#6366f1', CN: '#ef4444', US: '#22c55e', 'Global/US': '#f59e0b' }
const READINESS_COLOR = { Leading: 'green', High: 'blue', Medium: 'yellow', Low: 'red' } as const

export function RegionalPage() {
  const { t } = useTranslation()
  const [selected, setSelected] = useState('')
  const { data: companies = [] } = useQuery({ queryKey: ['companies'], queryFn: listCompanies })
  const [companyName, companyYear] = selected ? selected.split('|') : [null, null]

  const { data: report, isLoading } = useQuery({
    queryKey: ['regional', companyName, companyYear],
    queryFn: () => getRegionalComparison(companyName!, Number(companyYear)),
    enabled: !!companyName && !!companyYear,
  })

  // 构造雷达图数据（按维度名聚合三地得分）
  const radarData = report?.cross_matrix.map(m => ({
    dimension: m.dimension_name,
    EU: m.eu_score ? Math.round(m.eu_score * 100) : 0,
    CN: m.cn_score ? Math.round(m.cn_score * 100) : 0,
    US: m.us_score ? Math.round(m.us_score * 100) : 0,
  })) ?? []

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Globe className="text-indigo-500" size={28} />
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{t('regional.title')}</h1>
          <p className="text-slate-500 text-sm">{t('regional.subtitle')}</p>
        </div>
      </div>

      {/* Company selector */}
      <Select value={selected} onValueChange={setSelected}>
        <SelectTrigger className="w-72">
          <SelectValue placeholder={t('common.selectCompany')} />
        </SelectTrigger>
        <SelectContent>
          {companies.map(c => (
            <SelectItem key={`${c.company_name}|${c.report_year}`} value={`${c.company_name}|${c.report_year}`}>
              {c.company_name} ({c.report_year})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {isLoading && <p className="text-slate-400">{t('common.loading')}</p>}

      {report && (
        <div className="space-y-6">
          {/* Overall readiness banner */}
          <Card className={`border-l-4 ${report.overall_readiness === 'Leading' ? 'border-green-500' : report.overall_readiness === 'High' ? 'border-blue-500' : report.overall_readiness === 'Medium' ? 'border-yellow-500' : 'border-red-500'}`}>
            <CardContent className="pt-4 flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">{t('regional.overallReadiness')}</p>
                <p className="text-2xl font-bold text-slate-900">{report.overall_readiness}</p>
              </div>
              <div className="text-right text-sm text-slate-500">
                {report.company_name} · {report.report_year}
              </div>
            </CardContent>
          </Card>

          {/* Regional score cards */}
          <div className="grid grid-cols-3 gap-4">
            {report.regional_groups.map(g => (
              <Card key={g.region}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: REGION_COLORS[g.region as keyof typeof REGION_COLORS] ?? '#94a3b8' }} />
                    {g.region}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold text-slate-900">{g.avg_grade}</p>
                  <p className="text-lg text-slate-600">{Math.round(g.avg_score * 100)}%</p>
                  <p className="text-xs text-slate-400 mt-1">↑ {g.strongest_area}</p>
                  <p className="text-xs text-red-400">↓ {g.weakest_area}</p>
                  <div className="mt-2 space-y-1">
                    {g.frameworks.map(f => (
                      <div key={f.framework_id} className="flex justify-between text-xs">
                        <span className="text-slate-600 truncate mr-2">{f.framework_name}</span>
                        <span className="font-medium">{f.grade}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-6">
            {/* Radar chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t('regional.dimensionRadar')}</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <RadarChart data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 11 }} />
                    <Radar name="EU" dataKey="EU" stroke="#6366f1" fill="#6366f1" fillOpacity={0.2} />
                    <Radar name="CN" dataKey="CN" stroke="#ef4444" fill="#ef4444" fillOpacity={0.2} />
                    <Radar name="US" dataKey="US" stroke="#22c55e" fill="#22c55e" fillOpacity={0.2} />
                    <Legend />
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Key insights */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp size={16} className="text-indigo-500" />
                  {t('regional.keyInsights')}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {report.key_insights.map((insight, i) => (
                  <div key={i} className="flex gap-2 text-sm">
                    <CheckCircle size={14} className="text-green-500 mt-0.5 shrink-0" />
                    <span className="text-slate-600">{insight}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Cross matrix table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('regional.crossMatrix')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-slate-500">
                      <th className="text-left py-2 pr-4 font-medium">{t('regional.dimension')}</th>
                      <th className="text-left py-2 pr-4 font-medium text-indigo-600">🇪🇺 EU</th>
                      <th className="text-left py-2 pr-4 font-medium text-red-600">🇨🇳 CN</th>
                      <th className="text-left py-2 pr-4 font-medium text-green-600">🇺🇸 US</th>
                      <th className="text-left py-2 font-medium">{t('regional.gapAnalysis')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.cross_matrix.map((row, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-3 pr-4 font-medium text-slate-800">{row.dimension_name}</td>
                        <td className="py-3 pr-4 text-slate-600 text-xs max-w-[160px]">{row.eu_requirement}</td>
                        <td className="py-3 pr-4 text-slate-600 text-xs max-w-[160px]">{row.cn_requirement}</td>
                        <td className="py-3 pr-4 text-slate-600 text-xs max-w-[160px]">{row.us_requirement}</td>
                        <td className="py-3 text-xs text-slate-500">{row.gap_analysis}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Compliance priority */}
          {report.compliance_priority.length > 0 && (
            <Card className="border-orange-200 bg-orange-50">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2 text-orange-700">
                  <AlertTriangle size={16} />
                  {t('regional.compliancePriority')}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {report.compliance_priority.map((item, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-orange-800">
                    <span className="font-bold shrink-0">{i + 1}.</span>
                    <span>{item}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {!selected && (
        <p className="text-slate-400 text-center py-12">{t('regional.selectPrompt')}</p>
      )}
    </div>
  )
}
```

---

## Step 2 — 注册路由

修改 `frontend/src/App.tsx`，加入：
```tsx
import { RegionalPage } from './pages/RegionalPage'
// 在 <Routes> 内加入：
<Route path="/regional" element={<RegionalPage />} />
```

修改 `frontend/src/components/Sidebar.tsx`，在 links 数组加入：
```tsx
{ to: '/regional', label: t('nav.regional'), icon: Map },
// import Map from 'lucide-react'
```

---

## Step 3 — 更新 i18n

在 `frontend/src/i18n/locales/en.json` 的 `"nav"` 节增加：
```json
"regional": "Regional Analysis"
```

在 `"regional"` 节增加（三语）：
```json
"regional": {
  "title": "Three-Region ESG Comparison",
  "subtitle": "EU · China · US regulatory framework alignment",
  "overallReadiness": "Overall Compliance Readiness",
  "dimensionRadar": "Dimension Scores by Region",
  "keyInsights": "Key Insights",
  "crossMatrix": "Regulatory Requirement Matrix",
  "dimension": "Dimension",
  "gapAnalysis": "Gap Analysis",
  "compliancePriority": "Compliance Priority Actions",
  "selectPrompt": "Select a company to view three-region ESG comparison."
}
```

中文（`zh.json`）：
```json
"regional": "区域对比"
```
```json
"regional": {
  "title": "三地 ESG 框架对比",
  "subtitle": "欧盟 · 中国 · 美国监管框架合规度分析",
  "overallReadiness": "综合合规准备度",
  "dimensionRadar": "各区域维度得分雷达",
  "keyInsights": "核心洞察",
  "crossMatrix": "监管要求对比矩阵",
  "dimension": "维度",
  "gapAnalysis": "差距分析",
  "compliancePriority": "合规优先行动",
  "selectPrompt": "选择企业以查看三地 ESG 框架对比分析"
}
```

德文（`de.json`）：
```json
"regional": "Regionalvergleich"
```
```json
"regional": {
  "title": "Drei-Regionen ESG-Vergleich",
  "subtitle": "EU · China · US regulatorischer Rahmenvergleich",
  "overallReadiness": "Gesamte Compliance-Bereitschaft",
  "dimensionRadar": "Dimensionswerte nach Region",
  "keyInsights": "Wichtige Erkenntnisse",
  "crossMatrix": "Regulatorische Anforderungsmatrix",
  "dimension": "Dimension",
  "gapAnalysis": "Lückenanalyse",
  "compliancePriority": "Compliance-Prioritäten",
  "selectPrompt": "Unternehmen auswählen für Drei-Regionen-ESG-Vergleich"
}
```

---

## Step 4 — 编译验证

```bash
cd frontend && npm run build 2>&1 | tail -5
# 期望：✓ built in XXXms，无 error TS
```

---

## Step 5 — 提交

```bash
git add frontend/
git commit -m "feat: 三地 ESG 对比页面（RegionalPage）—— EU/CN/US 雷达图 + 监管矩阵 + 合规优先级

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 完成标准

- [ ] `RegionalPage.tsx` 存在
- [ ] `/regional` 路由可访问
- [ ] Sidebar 出现"区域对比"导航项
- [ ] 三语 i18n 键全部存在
- [ ] `npm run build` 无 TS 报错
