'use client'

// Dashboard home — real metrics from /api/dashboard/stats

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Users, FileText, Clock, Send, Plus, AlertCircle, CheckCircle2, Activity } from 'lucide-react'
import api from '@/lib/api'
import { Skeleton } from '@/components/ui/skeleton'

interface DashboardStats {
  total_clients: number
  client_limit: number
  reports_this_month: number
  reports_all_time: number
  reports_due_this_week: {
    client_name: string
    frequency: string
    next_run_at: string
    template: string
  }[]
  connection_health: Record<string, { connected: number; healthy: number; issues: number }>
  recent_activity: {
    type: string
    description: string
    time: string
  }[]
}

const PLATFORM_LABELS: Record<string, string> = {
  ga4: 'Google Analytics',
  meta_ads: 'Meta Ads',
  google_ads: 'Google Ads',
}

function MetricCard({
  label,
  value,
  sub,
  icon: Icon,
  colorBg,
  colorText,
}: {
  label: string
  value: string | number
  sub?: string
  icon: React.ElementType
  colorBg: string
  colorText: string
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 flex flex-col gap-3">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${colorBg}`}>
        <Icon className={`h-[18px] w-[18px] ${colorText}`} />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-900">{value}</p>
        <p className="text-sm text-slate-500 mt-0.5">{label}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

function MetricCardSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 flex flex-col gap-3">
      <Skeleton className="w-9 h-9 rounded-lg" />
      <div className="space-y-1">
        <Skeleton className="h-8 w-16" />
        <Skeleton className="h-4 w-28" />
      </div>
    </div>
  )
}

function formatNextRun(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
  } catch {
    return iso
  }
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get('/api/dashboard/stats')
      .then((res) => setStats(res.data))
      .catch(() => setError('Failed to load dashboard stats.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>
          Dashboard
        </h1>
        <div className="flex gap-2">
          <Link
            href="/dashboard/clients"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Client
          </Link>
          <Link
            href="/dashboard/clients"
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-700 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-800 transition-colors"
          >
            <FileText className="h-3.5 w-3.5" />
            Generate Report
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {/* Metric cards — 2 cols on mobile, 4 on desktop */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <MetricCardSkeleton key={i} />)
        ) : stats ? (
          <>
            <MetricCard
              label="Total Clients"
              value={stats.total_clients}
              sub={`${stats.total_clients} / ${stats.client_limit} on plan`}
              icon={Users}
              colorBg="bg-indigo-50"
              colorText="text-indigo-600"
            />
            <MetricCard
              label="Reports Due This Week"
              value={stats.reports_due_this_week.length}
              icon={Clock}
              colorBg="bg-amber-50"
              colorText="text-amber-600"
            />
            <MetricCard
              label="Reports This Month"
              value={stats.reports_this_month}
              icon={Send}
              colorBg="bg-emerald-50"
              colorText="text-emerald-600"
            />
            <MetricCard
              label="Reports All Time"
              value={stats.reports_all_time}
              icon={FileText}
              colorBg="bg-slate-100"
              colorText="text-slate-600"
            />
          </>
        ) : null}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Reports due this week */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Reports Due This Week</h2>
          {loading ? (
            <div className="space-y-3">
              {[1, 2].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : stats?.reports_due_this_week.length === 0 ? (
            <p className="text-sm text-slate-400 py-4 text-center">No reports due this week.</p>
          ) : (
            <div className="divide-y divide-slate-50">
              {stats?.reports_due_this_week.map((r, i) => (
                <div key={i} className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0">
                  <div>
                    <p className="text-sm font-medium text-slate-800">{r.client_name}</p>
                    <p className="text-xs text-slate-400 capitalize">{r.frequency} · {r.template}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">Due {formatNextRun(r.next_run_at)}</span>
                    <Link
                      href="/dashboard/clients"
                      className="text-xs text-indigo-600 font-medium hover:underline"
                    >
                      View
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Connection health */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-700">Connection Health</h2>
            <Link href="/dashboard/integrations" className="text-xs text-indigo-600 hover:underline">
              Manage →
            </Link>
          </div>
          {loading ? (
            <div className="space-y-3">
              {[1, 2].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : !stats || Object.keys(stats.connection_health).length === 0 ? (
            <div className="py-4 text-center">
              <p className="text-sm text-slate-400 mb-2">No platform connections yet.</p>
              <Link href="/dashboard/integrations" className="text-xs text-indigo-600 hover:underline">
                View integrations →
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-slate-50">
              {Object.entries(stats.connection_health).map(([platform, h]) => (
                <Link
                  key={platform}
                  href="/dashboard/integrations"
                  className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0 hover:bg-slate-50 -mx-2 px-2 rounded transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {h.issues > 0 ? (
                      <AlertCircle className="h-4 w-4 text-amber-500 shrink-0" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                    )}
                    <span className="text-sm text-slate-700">
                      {PLATFORM_LABELS[platform] ?? platform}
                      <span className="text-slate-400 ml-1">({h.connected})</span>
                    </span>
                  </div>
                  <span className={`text-xs font-medium ${h.issues > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                    {h.issues > 0 ? `${h.issues} issue${h.issues > 1 ? 's' : ''} — Fix →` : 'All healthy'}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent activity */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
          <Activity className="h-4 w-4 text-slate-400" />
          Recent Activity
        </h2>
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-5 w-3/4" />)}
          </div>
        ) : !stats || stats.recent_activity.length === 0 ? (
          <p className="text-sm text-slate-400 py-2">No recent activity yet. Add a client to get started.</p>
        ) : (
          <ul className="space-y-2.5">
            {stats.recent_activity.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                <span className="mt-2 w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
                <span>
                  {item.description}
                  {item.time && (
                    <span className="text-slate-400 ml-1.5">— {item.time}</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
