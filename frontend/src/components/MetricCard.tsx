import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface MetricCardProps {
  label: string
  value: string | number
  sub?: string
  color?: 'default' | 'green' | 'red' | 'blue' | 'orange'
}

export function MetricCard({
  label,
  value,
  sub,
  color = 'default',
}: MetricCardProps) {
  const styles = {
    default: {
      card: 'bg-white border-slate-200',
      value: 'text-slate-900',
    },
    green: {
      card: 'bg-green-50 border-green-200',
      value: 'text-green-700',
    },
    blue: {
      card: 'bg-blue-50 border-blue-200',
      value: 'text-blue-700',
    },
    orange: {
      card: 'bg-orange-50 border-orange-200',
      value: 'text-orange-700',
    },
    red: {
      card: 'bg-red-50 border-red-200',
      value: 'text-red-700',
    },
  }[color]

  return (
    <Card className={styles.card}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-slate-500">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${styles.value}`}>{value}</div>
        {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
      </CardContent>
    </Card>
  )
}
