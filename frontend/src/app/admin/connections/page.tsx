'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2, Link2 } from 'lucide-react'
import { adminApi } from '@/lib/api'
import { StatsCard } from '@/components/admin/StatsCard'
import { DataTable, type Column } from '@/components/admin/DataTable'
import { StatusBadge } from '@/components/admin/StatusBadge'

export default function AdminConnectionsPage() {
  const router = useRouter()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [conns, setConns] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [platformFilter, setPlatformFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams()
    if (platformFilter) params.set('platform', platformFilter)
    if (statusFilter) params.set('status', statusFilter)
    const qs = params.toString()
    adminApi.getConnections(qs || undefined)
      .then((d) => setConns(d.connections || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [platformFilter, statusFilter])

  const active = conns.filter((c) => c.effective_status === 'active').length
  const expiringSoon = conns.filter((c) => c.effective_status === 'expiring_soon').length
  const expired = conns.filter((c) => c.effective_status === 'expired').length
  const errored = conns.filter((c) => c.effective_status === 'error' || c.effective_status === 'errored').length
  const revoked = conns.filter((c) => c.effective_status === 'revoked').length

  const columns: Column<Record<string, unknown>>[] = [
    { key: 'user_email', label: 'User', render: (r) => <span className="text-xs">{String(r.user_email ?? '')}</span> },
    { key: 'client_name', label: 'Client' },
    { key: 'platform', label: 'Platform', render: (r) => <StatusBadge status={String(r.platform ?? '')} /> },
    { key: 'account_name', label: 'Account' },
    { key: 'effective_status', label: 'Status', render: (r) => <StatusBadge status={String(r.effective_status ?? r.status ?? '')} /> },
    { key: 'token_expires_at', label: 'Token Expires', render: (r) => {
      if (!r.token_expires_at) return <span className="text-xs text-slate-400">{'\u2014'}</span>
      const d = new Date(String(r.token_expires_at))
      const isExpired = d < new Date()
      return <span className={`text-xs ${isExpired ? 'text-rose-600 font-semibold' : 'text-slate-600'}`}>{d.toLocaleDateString()}</span>
    }},
    { key: 'updated_at', label: 'Updated', render: (r) => <span className="text-xs">{r.updated_at ? new Date(String(r.updated_at)).toLocaleDateString() : ''}</span> },
  ]

  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>Connections</h1>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatsCard label="Active" value={`${active} of ${conns.length}`} icon={Link2} color="emerald" />
        <StatsCard label="Expiring Soon" value={expiringSoon} icon={Link2} color="amber" />
        <StatsCard label="Expired" value={`${expired} of ${conns.length}`} icon={Link2} color="rose" />
        <StatsCard label="Errored" value={errored} icon={Link2} color="rose" />
        <StatsCard label="Revoked" value={revoked} icon={Link2} color="slate" />
      </div>

      <div className="flex gap-3 flex-wrap">
        <select value={platformFilter} onChange={(e) => setPlatformFilter(e.target.value)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
          <option value="">All Platforms</option>
          <option value="ga4">GA4</option>
          <option value="meta_ads">Meta Ads</option>
          <option value="google_ads">Google Ads</option>
          <option value="search_console">Search Console</option>
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="expiring_soon">Expiring Soon</option>
          <option value="expired">Expired</option>
          <option value="error">Error</option>
          <option value="revoked">Revoked</option>
        </select>
        {loading && <Loader2 className="h-4 w-4 animate-spin text-slate-400 self-center" />}
      </div>

      <DataTable
        columns={columns}
        data={conns}
        loading={loading}
        emptyMessage="No connections found."
        onRowClick={(row) => row.user_id && router.push(`/admin/users/${String(row.user_id)}`)}
      />
    </div>
  )
}
