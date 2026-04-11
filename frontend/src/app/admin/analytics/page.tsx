'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Users, FileText, CreditCard, Link2, TrendingUp, Globe2,
  Loader2, RefreshCw, DollarSign,
} from 'lucide-react'
import { adminApi } from '@/lib/api'

type PlanKey = 'trial' | 'starter' | 'pro' | 'agency'
type PlatformKey = 'ga4' | 'meta_ads' | 'google_ads' | 'search_console' | 'csv'
type SortKey = 'reports' | 'clients' | 'email' | 'name' | 'plan'

interface DailyPoint {
  date: string
  count: number
}

interface TopUser {
  email: string
  name: string
  plan: string
  clients: number
  reports_generated: number
  last_active: string
}

interface Subscriptions {
  trial: number
  trial_expired: number
  starter: number
  pro: number
  agency: number
  total_paying: number
  mrr_inr: number
  mrr_usd: number
}

interface Connections {
  ga4: number
  meta_ads: number
  google_ads: number
  search_console: number
  csv: number
  total: number
}

interface Analytics {
  total_users: number
  active_users_7d: number
  active_users_30d: number
  new_users_today: number
  new_users_7d: number
  new_users_30d: number
  signups_daily: DailyPoint[]
  subscriptions: Subscriptions
  total_reports: number
  reports_today: number
  reports_7d: number
  reports_30d: number
  reports_daily: DailyPoint[]
  connections: Connections
  users_by_country: Array<{ country: string; count: number }>
  top_users: TopUser[]
  funnel: { signed_up: number; connected_source: number; generated_report: number; paid: number }
  generated_at: string
}

const REFRESH_INTERVAL_MS = 5 * 60 * 1000

export default function AdminAnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastFetch, setLastFetch] = useState<Date | null>(null)
  const [sortKey, setSortKey] = useState<SortKey>('reports')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const fetchData = useCallback(async (background = false) => {
    if (background) setRefreshing(true)
    else setLoading(true)
    setError(null)
    try {
      const payload = await adminApi.getAnalytics()
      setData(payload)
      setLastFetch(new Date())
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Failed to load analytics'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    fetchData(false)
    const id = setInterval(() => fetchData(true), REFRESH_INTERVAL_MS)
    return () => clearInterval(id)
  }, [fetchData])

  const sortedTopUsers = useMemo(() => {
    if (!data) return []
    const copy = [...data.top_users]
    copy.sort((a, b) => {
      let cmp = 0
      switch (sortKey) {
        case 'reports': cmp = a.reports_generated - b.reports_generated; break
        case 'clients': cmp = a.clients - b.clients; break
        case 'email':   cmp = a.email.localeCompare(b.email); break
        case 'name':    cmp = a.name.localeCompare(b.name); break
        case 'plan':    cmp = a.plan.localeCompare(b.plan); break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
    return copy
  }, [data, sortKey, sortDir])

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
        {error || 'No analytics data available.'}
      </div>
    )
  }

  const conversionRate =
    data.funnel.signed_up > 0
      ? Math.round((data.funnel.paid / data.funnel.signed_up) * 100)
      : 0

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1
            className="text-2xl font-bold text-slate-900"
            style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
          >
            Site Analytics
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Live metrics from our database — no third-party tracking.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400">
            {lastFetch
              ? `Last updated ${relativeTime(lastFetch)}`
              : 'Loading…'}
          </span>
          <button
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors disabled:opacity-60"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700">
          {error}
        </div>
      )}

      <div className="grid gap-4 grid-cols-2 md:grid-cols-3 xl:grid-cols-6">
        <StatCard
          icon={Users}
          label="Total Users"
          value={data.total_users}
          subtitle={`${data.new_users_7d} new this week`}
        />
        <StatCard
          icon={TrendingUp}
          label="Active Users (7d)"
          value={data.active_users_7d}
          subtitle={`of ${data.total_users} total`}
        />
        <StatCard
          icon={FileText}
          label="Reports Generated"
          value={data.total_reports}
          subtitle={`${data.reports_today} today`}
        />
        <StatCard
          icon={CreditCard}
          label="Paying Customers"
          value={data.subscriptions.total_paying}
          subtitle={`MRR ₹${formatNumber(data.subscriptions.mrr_inr)} / $${formatNumber(data.subscriptions.mrr_usd)}`}
        />
        <StatCard
          icon={DollarSign}
          label="Conversion Rate"
          value={`${conversionRate}%`}
          subtitle="signup → paid"
        />
        <StatCard
          icon={Link2}
          label="Platform Connections"
          value={data.connections.total}
          subtitle={`${data.connections.ga4 + data.connections.meta_ads + data.connections.google_ads + data.connections.search_console} OAuth + ${data.connections.csv} CSV`}
        />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <TrendCard
          title="User Signups — Last 30 Days"
          data={data.signups_daily}
          color="#6366F1"
        />
        <TrendCard
          title="Reports Generated — Last 30 Days"
          data={data.reports_daily}
          color="#047857"
        />
      </div>

      <Card title="Subscription Breakdown">
        <div className="grid gap-6 md:grid-cols-[1fr_auto] items-center">
          <div className="space-y-2">
            <HorizontalBarRow label="Trial"         count={data.subscriptions.trial}         total={data.total_users} colorClass="bg-slate-400" />
            <HorizontalBarRow label="Trial Expired" count={data.subscriptions.trial_expired} total={data.total_users} colorClass="bg-rose-500" />
            <HorizontalBarRow label="Starter"       count={data.subscriptions.starter}       total={data.total_users} colorClass="bg-sky-500" />
            <HorizontalBarRow label="Pro"           count={data.subscriptions.pro}           total={data.total_users} colorClass="bg-indigo-600" />
            <HorizontalBarRow label="Agency"        count={data.subscriptions.agency}        total={data.total_users} colorClass="bg-violet-600" />
          </div>
          <div className="rounded-lg bg-slate-50 border border-slate-200 p-4 text-center min-w-[180px]">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Monthly Recurring Revenue
            </p>
            <p className="mt-2 text-2xl font-bold text-slate-900">
              ₹{formatNumber(data.subscriptions.mrr_inr)}
            </p>
            <p className="text-sm text-slate-500">
              / ${formatNumber(data.subscriptions.mrr_usd)}
            </p>
            <p className="mt-2 text-xs text-slate-400">
              {data.subscriptions.total_paying} paying customers
            </p>
          </div>
        </div>
      </Card>

      <Card title="Conversion Funnel">
        <FunnelChart
          stages={[
            { label: 'Signed Up',        count: data.funnel.signed_up },
            { label: 'Connected Source', count: data.funnel.connected_source },
            { label: 'Generated Report', count: data.funnel.generated_report },
            { label: 'Paid',             count: data.funnel.paid },
          ]}
        />
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card title="Users by Country" icon={Globe2}>
          <CountryList countries={data.users_by_country.slice(0, 10)} total={data.total_users} />
        </Card>
        <Card title="Platform Connections" icon={Link2}>
          <ConnectionBreakdown connections={data.connections} />
        </Card>
      </div>

      <Card title="Top 10 Most Active Users">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left">
                <SortableTh label="Email"    k="email"   sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Name"     k="name"    sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Plan"     k="plan"    sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Clients"  k="clients" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} align="right" />
                <SortableTh label="Reports"  k="reports" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} align="right" />
                <th className="py-3 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Last Active</th>
              </tr>
            </thead>
            <tbody>
              {sortedTopUsers.map((u) => (
                <tr key={u.email} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/50">
                  <td className="py-3 px-3 text-slate-700 font-medium">{u.email}</td>
                  <td className="py-3 px-3 text-slate-500">{u.name || '—'}</td>
                  <td className="py-3 px-3">
                    <PlanBadge plan={u.plan} />
                  </td>
                  <td className="py-3 px-3 text-right text-slate-700 tabular-nums">{u.clients}</td>
                  <td className="py-3 px-3 text-right text-slate-700 tabular-nums">{u.reports_generated}</td>
                  <td className="py-3 px-3 text-slate-500 text-xs">{u.last_active}</td>
                </tr>
              ))}
              {sortedTopUsers.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-6 px-3 text-center text-sm text-slate-400">
                    No user activity yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  subtitle,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string | number
  subtitle: string
}) {
  return (
    <div className="rounded-xl bg-white border border-slate-100 p-4 shadow-sm">
      <div className="flex items-center gap-2 text-slate-500">
        <Icon className="h-4 w-4" />
        <span className="text-xs font-semibold uppercase tracking-wider">{label}</span>
      </div>
      <p className="mt-2 text-3xl font-bold text-slate-900 tabular-nums">
        {typeof value === 'number' ? formatNumber(value) : value}
      </p>
      <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
    </div>
  )
}

function Card({
  title,
  icon: Icon,
  children,
}: {
  title: string
  icon?: React.ComponentType<{ className?: string }>
  children: React.ReactNode
}) {
  return (
    <div className="rounded-xl bg-white border border-slate-100 p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        {Icon && <Icon className="h-4 w-4 text-slate-400" />}
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">{title}</h2>
      </div>
      {children}
    </div>
  )
}

function TrendCard({ title, data, color }: { title: string; data: DailyPoint[]; color: string }) {
  const max = Math.max(1, ...data.map(d => d.count))
  return (
    <Card title={title}>
      <div className="flex items-end gap-[2px] h-32">
        {data.map((d) => {
          const h = (d.count / max) * 100
          return (
            <div
              key={d.date}
              className="flex-1 flex flex-col justify-end group relative"
              title={`${d.date}: ${d.count}`}
            >
              <div
                className="w-full rounded-t-sm transition-opacity group-hover:opacity-80"
                style={{ height: `${h}%`, backgroundColor: color, minHeight: d.count > 0 ? 2 : 0 }}
              />
            </div>
          )
        })}
      </div>
      <div className="flex justify-between mt-2 text-[10px] text-slate-400">
        <span>{data[0]?.date}</span>
        <span>{data[data.length - 1]?.date}</span>
      </div>
    </Card>
  )
}

/**
 * Shared horizontal bar row used by the subscription, country, and
 * connection breakdowns. Renders a labelled progress bar with both the
 * raw count and the percentage-of-total. Callers pass either a
 * ``count`` + ``total`` pair (percentage is computed) or a pre-computed
 * ``pct``. The track height and color class are both customisable so
 * each consumer can keep its visual weight.
 */
function HorizontalBarRow({
  label,
  count,
  total,
  colorClass,
  trackClass = 'h-2',
}: {
  label: string
  count: number
  total: number
  colorClass: string
  trackClass?: string
}) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="text-slate-500 tabular-nums">
          {count} <span className="text-slate-400">· {pct}%</span>
        </span>
      </div>
      <div className={`${trackClass} rounded-full bg-slate-100 overflow-hidden`}>
        <div
          className={`h-full rounded-full ${colorClass} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function FunnelChart({ stages }: { stages: Array<{ label: string; count: number }> }) {
  const max = Math.max(1, ...stages.map(s => s.count))
  return (
    <div className="space-y-3">
      {stages.map((stage, i) => {
        const pct = Math.round((stage.count / max) * 100)
        const dropFromPrev =
          i > 0 && stages[i - 1].count > 0
            ? Math.round((stage.count / stages[i - 1].count) * 100)
            : null
        return (
          <div key={stage.label}>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="font-medium text-slate-700">{stage.label}</span>
              <span className="text-slate-500 tabular-nums">
                {stage.count}
                {dropFromPrev !== null && (
                  <span className="ml-2 text-slate-400">{dropFromPrev}% of previous</span>
                )}
              </span>
            </div>
            <div className="h-8 rounded-lg bg-slate-100 overflow-hidden">
              <div
                className="h-full rounded-lg bg-gradient-to-r from-indigo-500 to-indigo-600 transition-all duration-500 flex items-center justify-end pr-3"
                style={{ width: `${pct}%`, minWidth: stage.count > 0 ? '12%' : 0 }}
              >
                <span className="text-xs font-semibold text-white tabular-nums">
                  {stage.count}
                </span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function CountryList({
  countries,
  total,
}: {
  countries: Array<{ country: string; count: number }>
  total: number
}) {
  if (countries.length === 0) {
    return <p className="text-sm text-slate-400 py-2">No country data available.</p>
  }
  return (
    <div className="space-y-2">
      {countries.map((c) => (
        <HorizontalBarRow
          key={c.country}
          label={c.country}
          count={c.count}
          total={total}
          colorClass="bg-indigo-500"
          trackClass="h-1.5"
        />
      ))}
    </div>
  )
}

const PLATFORM_COLORS: Record<PlatformKey, string> = {
  ga4:            'bg-amber-500',
  meta_ads:       'bg-blue-600',
  google_ads:     'bg-emerald-600',
  search_console: 'bg-sky-500',
  csv:            'bg-slate-500',
}
const PLATFORM_LABELS: Record<PlatformKey, string> = {
  ga4:            'Google Analytics',
  meta_ads:       'Meta Ads',
  google_ads:     'Google Ads',
  search_console: 'Search Console',
  csv:            'CSV Upload',
}

function ConnectionBreakdown({ connections }: { connections: Connections }) {
  const platforms: PlatformKey[] = ['ga4', 'meta_ads', 'google_ads', 'search_console', 'csv']
  const total = connections.total || 1
  return (
    <div className="space-y-2">
      {platforms.map((p) => (
        <HorizontalBarRow
          key={p}
          label={PLATFORM_LABELS[p]}
          count={connections[p]}
          total={total}
          colorClass={PLATFORM_COLORS[p]}
        />
      ))}
    </div>
  )
}

const PLAN_BADGE_COLORS: Record<PlanKey, string> = {
  trial:   'bg-slate-100 text-slate-600 border-slate-200',
  starter: 'bg-sky-50 text-sky-700 border-sky-200',
  pro:     'bg-indigo-50 text-indigo-700 border-indigo-200',
  agency:  'bg-violet-50 text-violet-700 border-violet-200',
}

function PlanBadge({ plan }: { plan: string }) {
  // Unknown plans (future tiers, trial_expired, etc.) fall back to the
  // trial style so the UI never renders a borderless badge.
  const style = PLAN_BADGE_COLORS[plan as PlanKey] || PLAN_BADGE_COLORS.trial
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${style}`}
    >
      {plan}
    </span>
  )
}

function SortableTh({
  label,
  k,
  sortKey,
  sortDir,
  onSort,
  align = 'left',
}: {
  label: string
  k: SortKey
  sortKey: SortKey
  sortDir: 'asc' | 'desc'
  onSort: (k: SortKey) => void
  align?: 'left' | 'right'
}) {
  const active = sortKey === k
  return (
    <th
      onClick={() => onSort(k)}
      className={`py-3 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500 cursor-pointer select-none hover:text-slate-700 ${
        align === 'right' ? 'text-right' : 'text-left'
      }`}
    >
      {label}
      {active && <span className="ml-1 text-slate-400">{sortDir === 'asc' ? '↑' : '↓'}</span>}
    </th>
  )
}

function formatNumber(n: number): string {
  return n.toLocaleString('en-US')
}

function relativeTime(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 5) return 'just now'
  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return date.toLocaleString()
}
