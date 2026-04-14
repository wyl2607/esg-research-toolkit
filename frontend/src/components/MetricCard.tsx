import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface MetricCardProps {
  label: string
  value: string | number
  sub?: string
  unit?: string
  color?: 'default' | 'green' | 'red' | 'blue'
}

export function MetricCard({
  label,
  value,
  sub,
  unit,
  color = 'default',
}: MetricCardProps) {
  const valueColor = {
    default: 'text-slate-900',
    green: 'text-green-600',
    red: 'text-red-600',
    blue: 'text-indigo-600',
  }[color]
  
  // Generate unique ID for aria-labelledby
  const titleId = `metric-title-${label.replace(/\s+/g, '-').toLowerCase()}`

  return (
    <Card className="surface-card h-full" role="region" aria-labelledby={titleId}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-3">
          <CardTitle 
            id={titleId}
            className="text-sm font-medium leading-5 text-slate-600"
          >
            {label}
          </CardTitle>
          {unit ? <span className="metric-unit shrink-0">{unit}</span> : null}
        </div>
      </CardHeader>
      <CardContent>
        <div
          className={`numeric-mono text-[1.85rem] font-semibold leading-none ${valueColor}`}
        >
          {value}
        </div>
        {sub && <p className="mt-2 text-xs leading-5 text-slate-500">{sub}</p>}
      </CardContent>
    </Card>
  )
}
