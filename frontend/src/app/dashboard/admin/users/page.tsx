'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Search, Loader2 } from 'lucide-react'
import { adminApi } from '@/lib/api'
import { DataTable, Pagination, type Column } from '@/components/admin/DataTable'
import { StatusBadge } from '@/components/admin/StatusBadge'

interface UserRow {
  id: string
  email: string
  full_name: string
  agency_name: string
  plan: string
  subscription_status: string
  client_count: number
  report_count: number
  created_at: string
  is_admin: boolean
  is_disabled: boolean
}

export default function AdminUsersPage() {
  const router = useRouter()
  const [users, setUsers] = useState<UserRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [planFilter, setPlanFilter] = useState('')

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('page', String(page))
      params.set('limit', '25')
      if (search) params.set('search', search)
      if (planFilter) params.set('plan', planFilter)
      const data = await adminApi.getUsers(params.toString())
      setUsers(data.users || [])
      setTotal(data.total || 0)
    } catch { /* silent */ }
    finally { setLoading(false) }
  }, [page, search, planFilter])

  useEffect(() => { fetchUsers() }, [fetchUsers])

  type Row = Record<string, unknown>
  const columns: Column<Row>[] = [
    { key: 'email', label: 'Email', render: (r) => (
      <span className="font-medium text-slate-900">{String(r.email ?? '')}</span>
    )},
    { key: 'full_name', label: 'Name' },
    { key: 'agency_name', label: 'Agency' },
    { key: 'plan', label: 'Plan', render: (r) => <StatusBadge status={String(r.plan ?? '')} /> },
    { key: 'subscription_status', label: 'Status', render: (r) => (
      <div className="flex items-center gap-1">
        <StatusBadge status={String(r.subscription_status ?? '')} />
        {Boolean(r.is_disabled) && <StatusBadge status="disabled" />}
        {Boolean(r.is_admin) && <span className="text-[10px] font-bold text-rose-500 uppercase">Admin</span>}
      </div>
    )},
    { key: 'client_count', label: 'Clients' },
    { key: 'report_count', label: 'Reports' },
    { key: 'created_at', label: 'Signed Up', render: (r) => (
      <span className="text-xs">{r.created_at ? new Date(String(r.created_at)).toLocaleDateString() : '—'}</span>
    )},
  ]

  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>
        Users
      </h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by email, name, or agency..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className="w-full rounded-lg border border-slate-200 pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-200"
          />
        </div>
        <select
          value={planFilter}
          onChange={(e) => { setPlanFilter(e.target.value); setPage(1) }}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
        >
          <option value="">All Plans</option>
          <option value="free">Free</option>
          <option value="starter">Starter</option>
          <option value="pro">Pro</option>
          <option value="agency">Agency</option>
        </select>
        {loading && <Loader2 className="h-4 w-4 animate-spin text-slate-400" />}
      </div>

      <DataTable
        columns={columns}
        data={users as unknown as Row[]}
        loading={loading}
        onRowClick={(row) => router.push(`/dashboard/admin/users/${String(row.id)}`)}
        emptyMessage="No users found."
      />

      <Pagination page={page} total={total} limit={25} onPageChange={setPage} />
    </div>
  )
}
