'use client'

import { useEffect, useState } from 'react'
import { Loader2, Link2 } from 'lucide-react'
import { adminApi } from '@/lib/api'
import { StatsCard } from '@/components/admin/StatsCard'
import { DataTable, type Column } from '@/components/admin/DataTable'
import { StatusBadge } from '@/components/admin/StatusBadge'

export default function AdminConnectionsPage() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [conns, setConns] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [platformFilter, setPlatformFilter] = useState('')

  useEffect(() => {
    const params = platformFilter ? `platform=${platformFilter}` : undefined
    adminApi.getConnections(params)
      .then((d) => setConns(d.connections || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [platformFilter])

  const active = conns.filter((c) => c.status === 'active').length
  const expired = conns.filter((c) => c.status === 'expired').length
  const errored = conns.filter((c) => c.status === 'errored' || c.status === 'error').length

  const columns: Column<Record<string, unknown>>[] = [
    { key: 'user_email', label: 'User', render: (r) => <span className="text-xs">{String(r.user_email ?? '')}</span> },
    { key: 'client_name', label: 'Client' },
    { key: 'platform', label: 'Platform', render: (r) => <StatusBadge status={String(r.platform ?? '')} /> },
    { key: 'account_name', label: 'Account' },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={String(r.status ?? '')} /> },
    { key: 'token_expires_at', label: 'Token Expires', render: (r) => {
      if (!r.token_expires_at) return <span className="text-xs text-slate-400">—</span>
      const d = new Date(String(r.token_expires_at))
      const isExpired = d < new Date()
      return <span className={`text-xs ${isExpired ? 'text-rose-600 font-semibold' : 'text-slate-600'}`}>{d.toLocaleDateString()}</span>
    }},
    { key: 'updated_at', label: 'Updated', render: (r) => <span className="text-xs">{r.updated_at ? new Date(String(r.updated_at)).toLocaleDateString() : ''}</span> },
  ]

  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>Connections</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard label="Total" value={conns.length} icon={Link2} color="indigo" />
        <StatsCard label="Active" value={active} icon={Link2} color="emerald" />
        <StatsCard label="Expired" value={expired} icon={Link2} color="rose" />
        <StatsCard label="Errored" value={errored} icon={Link2} color="amber" />
      </div>

      <div className="flex gap-3">
        <select
          value={platformFilter}
          onChange={(e) => setPlatformFilter(e.target.value)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
        >
          <option value="">All Platforms</option>
          <option value="ga4">GA4</option>
          <option value="meta_ads">Meta Ads</option>
          <option value="google_ads">Google Ads</option>
          <option value="search_console">Search Console</option>
        </select>
        {loading && <Loader2 className="h-4 w-4 animate-spin text-slate-400 self-center" />}
      </div>

      <DataTable columns={columns} data={conns} loading={loading} emptyMessage="No connections" />
    </div>
  )
}
