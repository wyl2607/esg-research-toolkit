import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface MetricCardProps {
  label: string
  value: string | number
  sub?: string
  color?: 'default' | 'green' | 'red' | 'blue'
}

export function MetricCard({
  label,
  value,
  sub,
  color = 'default',
}: MetricCardProps) {
  const valueColor = {
    default: 'text-slate-900',
    green: 'text-green-600',
    red: 'text-red-600',
    blue: 'text-indigo-600',
  }[color]

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-slate-500">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${valueColor}`}>{value}</div>
        {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
      </CardContent>
    </Card>
  )
}
