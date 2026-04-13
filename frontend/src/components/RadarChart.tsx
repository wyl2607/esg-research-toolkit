import {
  Radar,
  RadarChart as ReRadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { useTranslation } from 'react-i18next'

interface RadarChartProps {
  data: Record<string, number>
}

const LABEL_MAP: Record<string, string> = {
  climate_mitigation: 'taxonomy.objectives.climateMitigation',
  climate_adaptation: 'taxonomy.objectives.climateAdaptation',
  water: 'taxonomy.objectives.water',
  circular_economy: 'taxonomy.objectives.circularEconomy',
  pollution_prevention: 'taxonomy.objectives.pollutionPrevention',
  biodiversity: 'taxonomy.objectives.biodiversity',
}

export function TaxonomyRadarChart({ data }: RadarChartProps) {
  const { t } = useTranslation()
  const chartData = Object.entries(data).map(([key, value]) => ({
    subject: LABEL_MAP[key] ? t(LABEL_MAP[key]) : key,
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
          name={t('common.score')}
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
