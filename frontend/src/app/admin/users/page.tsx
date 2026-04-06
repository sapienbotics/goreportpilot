'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Search, Loader2, ChevronUp, ChevronDown } from 'lucide-react'
import { adminApi } from '@/lib/api'
import { DataTable, Pagination, type Column } from '@/components/admin/DataTable'
import { StatusBadge } from '@/components/admin/StatusBadge'

type Row = Record<string, unknown>

export default function AdminUsersPage() {
  const router = useRouter()
  const [users, setUsers] = useState<Row[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [planFilter, setPlanFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('page', String(page))
      params.set('limit', '25')
      params.set('sort_by', sortBy)
      params.set('sort_order', sortOrder)
      if (search) params.set('search', search)
      if (planFilter) params.set('plan', planFilter)
      if (statusFilter) params.set('status', statusFilter)
      const data = await adminApi.getUsers(params.toString())
      setUsers(data.users || [])
      setTotal(data.total || 0)
    } catch { /* silent */ }
    finally { setLoading(false) }
  }, [page, search, planFilter, statusFilter, sortBy, sortOrder])

  useEffect(() => { fetchUsers() }, [fetchUsers])

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(key)
      setSortOrder('desc')
    }
    setPage(1)
  }

  const SortIcon = ({ col }: { col: string }) => {
    if (sortBy !== col) return null
    return sortOrder === 'asc' ? <ChevronUp className="h-3 w-3 inline ml-0.5" /> : <ChevronDown className="h-3 w-3 inline ml-0.5" />
  }

  const columns: Column<Row>[] = [
    { key: 'email', label: 'Email', render: (r) => (
      <div>
        <span className="font-medium text-slate-900">{String(r.email ?? '')}</span>
        {Boolean(r.name) && <p className="text-xs text-slate-400">{String(r.name)}</p>}
      </div>
    )},
    { key: 'agency_name', label: 'Agency', render: (r) => (
      <span className="font-medium">{String(r.agency_name ?? '') || '\u2014'}</span>
    )},
    { key: 'plan', label: 'Plan', render: (r) => <StatusBadge status={String(r.plan ?? 'free')} /> },
    { key: 'subscription_status', label: 'Status', render: (r) => (
      <div className="flex items-center gap-1 flex-wrap">
        <StatusBadge status={String(r.subscription_status ?? 'none')} />
        {Boolean(r.is_disabled) && <StatusBadge status="disabled" />}
        {Boolean(r.is_admin) && <span className="text-[10px] font-bold text-rose-500 uppercase">Admin</span>}
      </div>
    )},
    { key: 'client_count', label: 'Clients' },
    { key: 'report_count', label: 'Reports' },
    { key: 'created_at', label: 'Signed Up', render: (r) => (
      <span className="text-xs">{r.created_at ? new Date(String(r.created_at)).toLocaleDateString() : '\u2014'}</span>
    )},
  ]

  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>Users</h1>

      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text" placeholder="Search email, name, or agency..."
            value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className="w-full rounded-lg border border-slate-200 pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-200"
          />
        </div>
        <select value={planFilter} onChange={(e) => { setPlanFilter(e.target.value); setPage(1) }}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
          <option value="">All Plans</option>
          <option value="free">Free</option>
          <option value="starter">Starter</option>
          <option value="pro">Pro</option>
          <option value="agency">Agency</option>
        </select>
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          <option value="trialing">Trialing</option>
          <option value="active">Active</option>
          <option value="past_due">Past Due</option>
          <option value="cancelled">Cancelled</option>
          <option value="none">No Subscription</option>
        </select>

        {/* Sort buttons */}
        <div className="flex gap-1 text-xs text-slate-500">
          {[
            { key: 'created_at', label: 'Date' },
            { key: 'email', label: 'Email' },
            { key: 'report_count', label: 'Reports' },
          ].map(({ key, label }) => (
            <button key={key} onClick={() => handleSort(key)}
              className={`px-2 py-1 rounded border text-xs ${sortBy === key ? 'bg-indigo-50 border-indigo-200 text-indigo-700' : 'border-slate-200'}`}>
              {label}<SortIcon col={key} />
            </button>
          ))}
        </div>

        {loading && <Loader2 className="h-4 w-4 animate-spin text-slate-400" />}
      </div>

      <DataTable
        columns={columns} data={users} loading={loading}
        onRowClick={(row) => router.push(`/admin/users/${String(row.id)}`)}
        emptyMessage="No users found."
      />
      <Pagination page={page} total={total} limit={25} onPageChange={setPage} />
    </div>
  )
}
