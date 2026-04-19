'use client'

// Connection Health Widget — Phase 2.
// Shows aggregate counts (healthy / warning / broken / expiring_soon) plus
// the top 3 problem connections with reconnect CTAs.
//
// Fetches from GET /api/dashboard/connection-health.

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  RefreshCw,
} from 'lucide-react'
import api from '@/lib/api'
import { Skeleton } from '@/components/ui/skeleton'

interface HealthSummary {
  total: number
  healthy: number
  warning: number
  broken: number
  expiring_soon: number
}

interface PlatformBucket {
  connected: number
  healthy: number
  warning: number
  broken: number
  expiring_soon: number
}

interface HealthIssue {
  connection_id: string
  client_id: string
  client_name: string
  platform: string
  account_name: string
  health_status: 'broken' | 'expiring_soon' | 'warning' | 'healthy'
  last_error_message: string | null
  last_health_check_at: string | null
  token_expires_at: string | null
}

interface ConnectionHealthResponse {
  summary: HealthSummary
  by_platform: Record<string, PlatformBucket>
  issues: HealthIssue[]
}

const PLATFORM_LABELS: Record<string, string> = {
  ga4: 'Google Analytics',
  meta_ads: 'Meta Ads',
  google_ads: 'Google Ads',
  search_console: 'Search Console',
}

const STATUS_MESSAGE: Record<HealthIssue['health_status'], string> = {
  broken: 'Connection broken — reconnect required',
  expiring_soon: 'Token expires soon — reconnect',
  warning: 'Returned zero data — check tracking',
  healthy: '',
}

function statusBadge(status: HealthIssue['health_status']) {
  if (status === 'broken') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700">
        <AlertCircle className="h-3 w-3" /> Broken
      </span>
    )
  }
  if (status === 'expiring_soon') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
        <Clock className="h-3 w-3" /> Expiring
      </span>
    )
  }
  if (status === 'warning') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-yellow-50 px-2 py-0.5 text-xs font-medium text-yellow-700">
        <AlertTriangle className="h-3 w-3" /> Warning
      </span>
    )
  }
  return null
}

interface Props {
  className?: string
  title?: string
}

export default function ConnectionHealthWidget({ className, title = 'Connection Health' }: Props) {
  const [data, setData] = useState<ConnectionHealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchHealth = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    try {
      const res = await api.get<ConnectionHealthResponse>('/api/dashboard/connection-health')
      setData(res.data)
      setError(null)
    } catch {
      setError('Failed to load connection health.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchHealth()
  }, [])

  const hasIssues = !!data && data.summary.total > 0 && data.summary.healthy !== data.summary.total

  return (
    <div className={`bg-white rounded-xl border border-slate-200 p-5 ${className ?? ''}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
          {data && data.summary.total > 0 && (
            <span className="text-xs text-slate-400">· {data.summary.total} total</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => fetchHealth(true)}
            disabled={refreshing || loading}
            className="text-xs text-slate-400 hover:text-slate-700 inline-flex items-center gap-1 disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={`h-3 w-3 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <Link href="/dashboard/integrations" className="text-xs text-indigo-600 hover:underline">
            Manage →
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          <div className="grid grid-cols-4 gap-2">
            {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-12" />)}
          </div>
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      ) : error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
          {error}
        </div>
      ) : !data || data.summary.total === 0 ? (
        <div className="py-4 text-center">
          <p className="text-sm text-slate-400 mb-2">No platform connections yet.</p>
          <Link href="/dashboard/integrations" className="text-xs text-indigo-600 hover:underline">
            View integrations →
          </Link>
        </div>
      ) : (
        <>
          {/* Aggregate counts */}
          <div className="grid grid-cols-4 gap-2 mb-4">
            <CountTile label="Healthy" value={data.summary.healthy} tone="emerald" icon={CheckCircle2} />
            <CountTile label="Expiring" value={data.summary.expiring_soon} tone="amber" icon={Clock} />
            <CountTile label="Warning" value={data.summary.warning} tone="yellow" icon={AlertTriangle} />
            <CountTile label="Broken" value={data.summary.broken} tone="rose" icon={AlertCircle} />
          </div>

          {/* Top issues */}
          {data.issues.length > 0 ? (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                Needs attention
              </p>
              <ul className="divide-y divide-slate-100">
                {data.issues.map((issue) => (
                  <li key={issue.connection_id} className="py-2.5 first:pt-0">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-medium text-slate-800 truncate">
                            {issue.client_name}
                          </span>
                          <span className="text-xs text-slate-400">
                            · {PLATFORM_LABELS[issue.platform] ?? issue.platform}
                          </span>
                          {statusBadge(issue.health_status)}
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {STATUS_MESSAGE[issue.health_status]}
                          {issue.last_error_message && issue.health_status === 'broken' && (
                            <span className="text-slate-400 ml-1">
                              — {issue.last_error_message.slice(0, 80)}
                            </span>
                          )}
                        </p>
                      </div>
                      <Link
                        href="/dashboard/integrations"
                        className="inline-flex items-center gap-1 rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100 shrink-0"
                      >
                        Reconnect
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    </div>
                  </li>
                ))}
              </ul>
              {hasIssues && data.issues.length >= 3 && (
                <Link
                  href="/dashboard/integrations"
                  className="mt-3 block text-center text-xs text-indigo-600 hover:underline"
                >
                  View all connections →
                </Link>
              )}
            </div>
          ) : (
            <p className="text-sm text-emerald-600 text-center py-2">
              ✓ All connections healthy
            </p>
          )}
        </>
      )}
    </div>
  )
}

function CountTile({
  label,
  value,
  tone,
  icon: Icon,
}: {
  label: string
  value: number
  tone: 'emerald' | 'amber' | 'yellow' | 'rose'
  icon: React.ElementType
}) {
  const TONES: Record<string, { bg: string; text: string }> = {
    emerald: { bg: 'bg-emerald-50', text: 'text-emerald-700' },
    amber: { bg: 'bg-amber-50', text: 'text-amber-700' },
    yellow: { bg: 'bg-yellow-50', text: 'text-yellow-700' },
    rose: { bg: 'bg-rose-50', text: 'text-rose-700' },
  }
  const t = TONES[tone]
  return (
    <div className={`${t.bg} rounded-lg px-2 py-2 flex flex-col items-center`}>
      <Icon className={`h-4 w-4 ${t.text}`} />
      <p className={`text-lg font-bold ${t.text} mt-0.5`}>{value}</p>
      <p className={`text-[10px] uppercase tracking-wide ${t.text}`}>{label}</p>
    </div>
  )
}
