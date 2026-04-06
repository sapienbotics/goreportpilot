'use client'

import { useEffect, useState } from 'react'
import { Loader2, FileText, AlertCircle } from 'lucide-react'
import { adminApi } from '@/lib/api'
import { StatsCard } from '@/components/admin/StatsCard'
import { DataTable, type Column } from '@/components/admin/DataTable'
import { StatusBadge } from '@/components/admin/StatusBadge'

export default function AdminReportsPage() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [stats, setStats] = useState<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [reports, setReports] = useState<any[]>([])
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [failed, setFailed] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([adminApi.getReportStats(), adminApi.getReports(), adminApi.getReports('status=failed')])
      .then(([s, r, f]) => {
        setStats(s)
        setReports(r.reports || [])
        setFailed(f.reports || [])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-slate-300" /></div>

  const columns: Column<Record<string, unknown>>[] = [
    { key: 'title', label: 'Title', render: (r) => (
      <span className="font-medium max-w-[250px] block truncate" title={String(r.title ?? '')}>
        {String(r.title ?? '')}
      </span>
    )},
    { key: 'user_email', label: 'User', render: (r) => <span className="text-xs">{String(r.user_email ?? '')}</span> },
    { key: 'client_name', label: 'Client' },
    { key: 'period_start', label: 'Period', render: (r) => <span className="text-xs">{String(r.period_start ?? '')} {'\u2192'} {String(r.period_end ?? '')}</span> },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={String(r.status ?? '')} /> },
    { key: 'created_at', label: 'Created', render: (r) => <span className="text-xs">{r.created_at ? new Date(String(r.created_at)).toLocaleDateString() : ''}</span> },
  ]

  const templateDist = stats?.template_distribution || {}
  const languageDist = stats?.language_distribution || {}

  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>Reports</h1>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatsCard label="Today" value={stats?.today ?? 0} icon={FileText} color="indigo" />
        <StatsCard label="This Week" value={stats?.this_week ?? 0} icon={FileText} color="indigo" />
        <StatsCard label="This Month" value={stats?.this_month ?? 0} icon={FileText} color="emerald" />
        <StatsCard label="All Time" value={stats?.all_time ?? 0} icon={FileText} color="slate" />
        <StatsCard label="Failed" value={stats?.failed ?? 0} icon={AlertCircle} color="rose" />
      </div>

      {/* Template distribution */}
      {Object.keys(templateDist).length > 0 && (
        <div className="flex gap-3 flex-wrap items-center">
          <span className="text-xs font-bold text-slate-400 uppercase">Templates:</span>
          {Object.entries(templateDist).map(([tmpl, count]) => (
            <div key={tmpl} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs">
              <span className="font-medium text-slate-700">{tmpl}</span>: <span className="font-semibold">{String(count)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Language distribution */}
      {Object.keys(languageDist).length > 0 && (
        <div className="flex gap-3 flex-wrap items-center">
          <span className="text-xs font-bold text-slate-400 uppercase">Languages:</span>
          {Object.entries(languageDist).map(([lang, count]) => (
            <div key={lang} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs">
              <span className="font-medium text-slate-700">{lang}</span>: <span className="font-semibold">{String(count)}</span>
            </div>
          ))}
        </div>
      )}

      <h2 className="text-lg font-semibold text-slate-900">Recent Reports</h2>
      <DataTable columns={columns} data={reports} emptyMessage="No reports found." />

      {/* Failed reports */}
      {failed.length > 0 && (
        <>
          <h2 className="text-lg font-semibold text-rose-700">Failed Reports</h2>
          <DataTable columns={columns} data={failed} emptyMessage="No failed reports." />
        </>
      )}
    </div>
  )
}
