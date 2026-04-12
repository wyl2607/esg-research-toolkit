import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listCompanies, getFrameworkComparison } from '@/lib/api'
import type { FrameworkScoreResult, DimensionScore } from '@/lib/types'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from 'recharts'

// ── Grade badge ────────────────────────────────────────────────────────────

function GradeBadge({ grade }: { grade: string }) {
  const colors: Record<string, string> = {
    A: 'bg-green-100 text-green-800 border-green-300',
    B: 'bg-blue-100 text-blue-800 border-blue-300',
    C: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    D: 'bg-orange-100 text-orange-800 border-orange-300',
    F: 'bg-red-100 text-red-800 border-red-300',
  }
  return (
    <span className={`inline-flex items-center justify-center w-10 h-10 rounded-full border-2 font-bold text-lg ${colors[grade] ?? colors.F}`}>
      {grade}
    </span>
  )
}

// ── Score bar ──────────────────────────────────────────────────────────────

function ScoreBar({ value, max = 1 }: { value: number; max?: number }) {
  const pct = Math.round((value / max) * 100)
  const color = pct >= 80 ? 'bg-green-500' : pct >= 60 ? 'bg-blue-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-slate-100 rounded-full h-2">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-500 w-8 text-right">{pct}%</span>
    </div>
  )
}

// ── Framework card ─────────────────────────────────────────────────────────

const FRAMEWORK_COLORS: Record<string, string> = {
  eu_taxonomy: '#6366f1',
  csrc_2023:   '#f59e0b',
  csrd:        '#10b981',
}

function FrameworkCard({ fw }: { fw: FrameworkScoreResult }) {
  const [expanded, setExpanded] = useState(false)
  const color = FRAMEWORK_COLORS[fw.framework_id] ?? '#6366f1'
  const radarData = fw.dimensions.map((d: DimensionScore) => ({
    subject: d.name.split(' ')[0],
    score: Math.round(d.score * 100),
  }))

  return (
    <div className="border rounded-xl p-5 bg-white shadow-sm space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-3 h-3 rounded-full inline-block" style={{ background: color }} />
            <h3 className="font-semibold text-slate-800">{fw.framework}</h3>
          </div>
          <p className="text-xs text-slate-400">覆盖率 {fw.coverage_pct}%</p>
        </div>
        <GradeBadge grade={fw.grade} />
      </div>

      {/* Total score bar */}
      <div>
        <p className="text-xs text-slate-500 mb-1">综合得分</p>
        <ScoreBar value={fw.total_score} />
      </div>

      {/* Radar */}
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10 }} />
            <Radar dataKey="score" fill={color} fillOpacity={0.25} stroke={color} strokeWidth={2} />
            <Tooltip formatter={(v) => [`${v}%`, '']} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Dimensions */}
      <div className="space-y-2">
        {fw.dimensions.map((d: DimensionScore) => (
          <div key={d.name}>
            <div className="flex justify-between text-xs text-slate-600 mb-0.5">
              <span>{d.name}</span>
              <span>{d.disclosed}/{d.total} 项</span>
            </div>
            <ScoreBar value={d.score} />
          </div>
        ))}
      </div>

      {/* Gaps / Recs toggle */}
      <button
        className="text-xs text-indigo-600 hover:underline"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? '收起' : `查看差距 (${fw.gaps.length}) 和建议 (${fw.recommendations.length})`}
      </button>

      {expanded && (
        <div className="space-y-3 pt-2 border-t">
          {fw.gaps.length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-700 mb-1">差距</p>
              <ul className="space-y-1">
                {fw.gaps.map((g, i) => (
                  <li key={i} className="flex gap-2 text-xs text-slate-600">
                    <Badge variant="outline" className="shrink-0 text-[10px] px-1">缺失</Badge>
                    {g}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {fw.recommendations.length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-700 mb-1">建议</p>
              <ul className="space-y-1">
                {fw.recommendations.map((r, i) => (
                  <li key={i} className="text-xs text-slate-600">• {r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────

export function FrameworksPage() {
  const [selected, setSelected] = useState('')

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const [companyName, companyYear] = selected ? selected.split('|') : [null, null]

  const { data: report, isLoading } = useQuery({
    queryKey: ['frameworks', companyName, companyYear],
    queryFn: () => getFrameworkComparison(companyName!, Number(companyYear)),
    enabled: !!companyName && !!companyYear,
  })

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Multi-Framework ESG</h1>
        <p className="text-sm text-slate-500 mt-1">
          同时对比 EU Taxonomy 2020 · 中国证监会 CSRC 2023 · EU CSRD/ESRS 三大框架
        </p>
      </div>

      <Select value={selected} onValueChange={setSelected}>
        <SelectTrigger className="w-72">
          <SelectValue placeholder="选择公司和年份…" />
        </SelectTrigger>
        <SelectContent>
          {companies.map((c) => (
            <SelectItem
              key={`${c.company_name}|${c.report_year}`}
              value={`${c.company_name}|${c.report_year}`}
            >
              {c.company_name} ({c.report_year})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {isLoading && <p className="text-slate-400">正在计算三框架得分…</p>}

      {report && (
        <div className="space-y-4">
          {/* Summary banner */}
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg px-5 py-3 text-sm text-indigo-800">
            {report.summary}
          </div>

          {/* Three framework cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {report.frameworks.map((fw) => (
              <FrameworkCard key={fw.framework_id} fw={fw} />
            ))}
          </div>
        </div>
      )}

      {!selected && (
        <p className="text-slate-400 text-center py-12">
          选择一家公司，查看三大 ESG 框架下的合规评分与差距分析。
        </p>
      )}
    </div>
  )
}
