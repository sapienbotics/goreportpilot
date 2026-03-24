import { cn } from '@/lib/utils'

interface CSVMetric {
  name: string
  current_value: number | null
  previous_value: number | null
  change: number | null
  unit: string
}

interface Props {
  metrics: CSVMetric[]
  sourceName: string
}

function formatValue(value: number | null, unit: string): string {
  if (value === null) return '—'
  if (unit === '%') return `${value.toFixed(2)}%`
  if (unit === 'currency') return `$${value.toLocaleString()}`
  return value.toLocaleString()
}

function formatChange(change: number | null, unit: string): string {
  if (change === null) return '—'
  const sign = change >= 0 ? '+' : ''
  if (unit === '%') return `${sign}${change.toFixed(2)}%`
  if (unit === 'currency') return `${sign}$${Math.abs(change).toLocaleString()}`
  return `${sign}${change.toLocaleString()}`
}

export default function CSVPreviewTable({ metrics, sourceName }: Props) {
  const DISPLAY_LIMIT = 10
  const visible = metrics.slice(0, DISPLAY_LIMIT)
  const overflow = metrics.length - DISPLAY_LIMIT

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-700">
          Preview —{' '}
          <span className="font-semibold text-indigo-700">{sourceName}</span>
        </p>
        <p className="text-xs text-slate-500">
          {metrics.length} metric{metrics.length !== 1 ? 's' : ''} detected
        </p>
      </div>

      <div className="overflow-hidden rounded-md border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                Metric
              </th>
              <th className="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                Current
              </th>
              <th className="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                Previous
              </th>
              <th className="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                Change
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100 bg-white">
            {visible.map((metric, idx) => {
              const isPositive = metric.change !== null && metric.change > 0
              const isNegative = metric.change !== null && metric.change < 0
              const isNeutral = metric.change === null || metric.change === 0

              return (
                <tr key={idx} className="hover:bg-slate-50 transition-colors duration-100">
                  <td className="px-3 py-2 font-medium text-slate-800">{metric.name}</td>
                  <td className="px-3 py-2 text-right text-slate-700">
                    {formatValue(metric.current_value, metric.unit)}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-500">
                    {formatValue(metric.previous_value, metric.unit)}
                  </td>
                  <td
                    className={cn(
                      'px-3 py-2 text-right font-medium tabular-nums',
                      isPositive && 'text-emerald-600',
                      isNegative && 'text-rose-600',
                      isNeutral && 'text-slate-400'
                    )}
                  >
                    {isPositive && (
                      <span className="mr-0.5" aria-hidden="true">
                        ▲
                      </span>
                    )}
                    {isNegative && (
                      <span className="mr-0.5" aria-hidden="true">
                        ▼
                      </span>
                    )}
                    {formatChange(metric.change, metric.unit)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        {overflow > 0 && (
          <div className="border-t border-slate-100 bg-slate-50 px-3 py-2 text-center text-xs text-slate-500">
            …and{' '}
            <span className="font-semibold text-slate-700">{overflow}</span> more metric
            {overflow !== 1 ? 's' : ''}
          </div>
        )}
      </div>
    </div>
  )
}
