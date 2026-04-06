'use client'

import { useEffect, useState } from 'react'
import { Loader2, DollarSign, CreditCard, TrendingUp } from 'lucide-react'
import { adminApi } from '@/lib/api'
import { StatsCard } from '@/components/admin/StatsCard'
import { DataTable, type Column } from '@/components/admin/DataTable'
import { StatusBadge } from '@/components/admin/StatusBadge'

export default function AdminSubscriptionsPage() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [revenue, setRevenue] = useState<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [subs, setSubs] = useState<any[]>([])
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [payments, setPayments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([adminApi.getRevenue(), adminApi.getSubscriptions(), adminApi.getPayments('status=failed')])
      .then(([r, s, p]) => { setRevenue(r); setSubs(s.subscriptions || []); setPayments(p.payments || []) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-slate-300" /></div>

  const subCols: Column<Record<string, unknown>>[] = [
    { key: 'user_email', label: 'User', render: (r) => <span className="font-medium">{String(r.user_email ?? '')}</span> },
    { key: 'user_name', label: 'Name' },
    { key: 'plan', label: 'Plan', render: (r) => <StatusBadge status={String(r.plan ?? '')} /> },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={String(r.status ?? '')} /> },
    { key: 'billing_cycle', label: 'Cycle' },
    { key: 'created_at', label: 'Created', render: (r) => <span className="text-xs">{r.created_at ? new Date(String(r.created_at)).toLocaleDateString() : ''}</span> },
  ]

  const failedCols: Column<Record<string, unknown>>[] = [
    { key: 'user_email', label: 'User' },
    { key: 'amount', label: 'Amount', render: (r) => <span>{'\u20b9'}{String(r.amount ?? 0)}</span> },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={String(r.status ?? '')} /> },
    { key: 'created_at', label: 'Date', render: (r) => <span className="text-xs">{r.created_at ? new Date(String(r.created_at)).toLocaleDateString() : ''}</span> },
  ]

  const dist = revenue?.plan_distribution || {}

  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>Subscriptions</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard label="MRR" value={`\u20b9${(revenue?.mrr ?? 0).toLocaleString()}`} icon={DollarSign} color="emerald" />
        <StatsCard label="Active" value={revenue?.active_count ?? 0} icon={CreditCard} color="emerald" />
        <StatsCard label="Trialing" value={revenue?.trialing_count ?? 0} icon={TrendingUp} color="indigo" />
        <StatsCard label="Total Revenue" value={`\u20b9${(revenue?.total_revenue ?? 0).toLocaleString()}`} icon={DollarSign} color="indigo" />
      </div>

      {/* Plan distribution */}
      {Object.keys(dist).length > 0 && (
        <div className="flex gap-3 flex-wrap">
          {Object.entries(dist).map(([plan, count]) => (
            <div key={plan} className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm">
              <StatusBadge status={plan} /> <span className="ml-1 font-semibold">{String(count)}</span>
            </div>
          ))}
        </div>
      )}

      <h2 className="text-lg font-semibold text-slate-900">All Subscriptions</h2>
      <DataTable columns={subCols} data={subs} emptyMessage="No subscriptions" />

      {payments.length > 0 && (
        <>
          <h2 className="text-lg font-semibold text-rose-700">Failed Payments</h2>
          <DataTable columns={failedCols} data={payments} emptyMessage="No failed payments" />
        </>
      )}
    </div>
  )
}
