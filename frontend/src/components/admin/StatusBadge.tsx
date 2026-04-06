'use client'

const statusColors: Record<string, string> = {
  active:    'bg-emerald-50 text-emerald-700 border-emerald-200',
  trialing:  'bg-blue-50 text-blue-700 border-blue-200',
  past_due:  'bg-amber-50 text-amber-700 border-amber-200',
  cancelled: 'bg-slate-100 text-slate-500 border-slate-200',
  canceled:  'bg-slate-100 text-slate-500 border-slate-200',
  expired:   'bg-rose-50 text-rose-600 border-rose-200',
  error:     'bg-rose-50 text-rose-600 border-rose-200',
  errored:   'bg-rose-50 text-rose-600 border-rose-200',
  revoked:   'bg-rose-50 text-rose-600 border-rose-200',
  failed:    'bg-rose-50 text-rose-600 border-rose-200',
  pending:   'bg-amber-50 text-amber-700 border-amber-200',
  in_progress: 'bg-blue-50 text-blue-700 border-blue-200',
  completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  rejected:  'bg-slate-100 text-slate-500 border-slate-200',
  draft:     'bg-slate-100 text-slate-500 border-slate-200',
  sent:      'bg-indigo-50 text-indigo-700 border-indigo-200',
  none:      'bg-slate-50 text-slate-400 border-slate-200',
  free:      'bg-slate-50 text-slate-400 border-slate-200',
  starter:   'bg-blue-50 text-blue-700 border-blue-200',
  pro:       'bg-indigo-50 text-indigo-700 border-indigo-200',
  agency:    'bg-purple-50 text-purple-700 border-purple-200',
}

export function StatusBadge({ status }: { status: string }) {
  const cls = statusColors[status?.toLowerCase()] || 'bg-slate-100 text-slate-500 border-slate-200'
  return (
    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-semibold ${cls}`}>
      {status?.replace(/_/g, ' ') || 'unknown'}
    </span>
  )
}
