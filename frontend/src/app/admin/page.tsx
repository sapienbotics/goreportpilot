'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Users, FileText, CreditCard, BarChart3,
  TrendingUp, AlertCircle, DollarSign,
} from 'lucide-react'
import { adminApi } from '@/lib/api'
import { StatsCard } from '@/components/admin/StatsCard'
import { StatusBadge } from '@/components/admin/StatusBadge'
import { Loader2 } from 'lucide-react'

export default function AdminOverviewPage() {
  const router = useRouter()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [stats, setStats] = useState<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [activity, setActivity] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([adminApi.getStats(), adminApi.getActivity()])
      .then(([s, a]) => { setStats(s); setActivity(a.events || []) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
      </div>
    )
  }

  const activeSubs = stats?.active_subscriptions || {}
  const totalActiveSubs = Object.values(activeSubs as Record<string, number>).reduce((a: number, b: number) => a + b, 0)

  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>
        Admin Overview
      </h1>

      {/* Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard label="Total Users" value={stats?.total_users ?? 0} icon={Users} color="indigo" />
        <StatsCard label="Active (30d)" value={stats?.active_users_30d ?? 0} icon={TrendingUp} color="emerald" />
        <StatsCard label="Total Clients" value={stats?.total_clients ?? 0} icon={BarChart3} color="indigo" />
        <StatsCard label="Reports (Month)" value={stats?.reports_this_month ?? 0} icon={FileText} color="emerald" />
        <StatsCard label="Reports (All)" value={stats?.reports_all_time ?? 0} icon={FileText} color="slate" />
        <StatsCard label="Active Subs" value={totalActiveSubs} icon={CreditCard} color="emerald" />
        <StatsCard label="Failed Payments (30d)" value={stats?.failed_payments_30d ?? 0} icon={AlertCircle} color="rose" />
        <StatsCard label="Revenue" value={`\u20b9${(stats?.total_revenue ?? 0).toLocaleString()}`} icon={DollarSign} color="emerald" />
      </div>

      {/* Recent activity */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-3">Recent Activity</h2>
        <div className="rounded-xl border border-slate-200 bg-white divide-y divide-slate-100">
          {activity.length === 0 && (
            <p className="text-sm text-slate-400 text-center py-8">No recent activity</p>
          )}
          {activity.slice(0, 20).map((evt, i) => (
            <div
              key={i}
              className={`flex items-center gap-4 px-5 py-3 ${evt.user_id ? 'cursor-pointer hover:bg-slate-50' : ''}`}
              onClick={() => evt.user_id && router.push(`/admin/users/${evt.user_id}`)}
            >
              <div className="shrink-0">
                <StatusBadge status={evt.event_type?.replace(/_/g, ' ') ?? 'event'} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-700 truncate">{evt.details}</p>
                <p className="text-xs text-slate-400">{evt.user_email}</p>
              </div>
              <time className="text-xs text-slate-400 shrink-0">
                {evt.timestamp ? new Date(evt.timestamp).toLocaleDateString() : ''}
              </time>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
