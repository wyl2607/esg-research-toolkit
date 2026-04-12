import {
  Radar,
  RadarChart as ReRadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

interface RadarChartProps {
  data: Record<string, number>
}

const LABEL_MAP: Record<string, string> = {
  climate_mitigation: 'Climate Mitigation',
  climate_adaptation: 'Climate Adaptation',
  water: 'Water',
  circular_economy: 'Circular Economy',
  pollution_prevention: 'Pollution Prevention',
  biodiversity: 'Biodiversity',
}

export function TaxonomyRadarChart({ data }: RadarChartProps) {
  const chartData = Object.entries(data).map(([key, value]) => ({
    subject: LABEL_MAP[key] ?? key,
    score: Math.round(value * 100),
    fullMark: 100,
  }))

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ReRadarChart data={chartData}>
        <PolarGrid />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 12 }} />
        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
        <Radar
          name="Score"
          dataKey="score"
          stroke="#6366f1"
          fill="#6366f1"
          fillOpacity={0.3}
        />
        <Tooltip formatter={(v) => `${v}%`} />
      </ReRadarChart>
    </ResponsiveContainer>
  )
}
