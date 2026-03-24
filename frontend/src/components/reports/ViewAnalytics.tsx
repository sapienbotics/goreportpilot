'use client'

// ViewAnalytics — displays share link view counts and time-on-page stats for a report.

import { useEffect, useState } from 'react'
import { BarChart2, Eye, Clock, TrendingUp, Loader2, ChevronDown, ChevronUp } from 'lucide-react'
import { shareApi } from '@/lib/api'

interface ViewEvent {
  viewed_at: string
  duration_seconds?: number | null
  ip_country?: string | null
}

interface AnalyticsData {
  total_views: number
  unique_views?: number | null
  avg_duration_seconds?: number | null
  share_links: Array<{
    share_hash: string
    share_url: string
    views: number
    last_viewed_at?: string | null
    view_events?: ViewEvent[]
  }>
}

interface Props {
  reportId: string
}

function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || seconds <= 0) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return s > 0 ? `${m}m ${s}s` : `${m}m`
}

function formatDate(d: string): string {
  try {
    return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return d
  }
}

export default function ViewAnalytics({ reportId }: Props) {
  const [data,      setData]      = useState<AnalyticsData | null>(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState<string | null>(null)
  const [expanded,  setExpanded]  = useState(false)
  const [loaded,    setLoaded]    = useState(false)

  // Lazy-load analytics only when user expands the section
  useEffect(() => {
    if (!expanded || loaded) return

    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const result = await shareApi.getAnalytics(reportId)
        setData(result)
        setLoaded(true)
      } catch {
        setError('Could not load analytics.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [expanded, loaded, reportId])

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      {/* Collapsible header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <BarChart2 className="h-4 w-4 text-indigo-500" />
          <span className="text-sm font-semibold text-slate-700">View Analytics</span>
          {data && (
            <span className="ml-1 text-xs text-slate-400">
              {data.total_views} view{data.total_views !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        {expanded
          ? <ChevronUp className="h-4 w-4 text-slate-400" />
          : <ChevronDown className="h-4 w-4 text-slate-400" />}
      </button>

      {expanded && (
        <div className="border-t border-slate-100 px-5 py-4 space-y-4">

          {loading && (
            <div className="flex justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-slate-300" />
            </div>
          )}

          {error && (
            <p className="text-sm text-slate-400 text-center py-2">{error}</p>
          )}

          {data && !loading && (
            <>
              {/* Summary stats */}
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3 text-center">
                  <div className="flex items-center justify-center gap-1.5 text-indigo-500 mb-1">
                    <Eye className="h-4 w-4" />
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Total Views</span>
                  </div>
                  <p className="text-2xl font-bold text-slate-900">{data.total_views}</p>
                </div>

                {data.unique_views != null && (
                  <div className="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1.5 text-emerald-500 mb-1">
                      <TrendingUp className="h-4 w-4" />
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Unique</span>
                    </div>
                    <p className="text-2xl font-bold text-slate-900">{data.unique_views}</p>
                  </div>
                )}

                {data.avg_duration_seconds != null && (
                  <div className="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1.5 text-amber-500 mb-1">
                      <Clock className="h-4 w-4" />
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Avg. Time</span>
                    </div>
                    <p className="text-2xl font-bold text-slate-900">{formatDuration(data.avg_duration_seconds)}</p>
                  </div>
                )}
              </div>

              {/* Per-link breakdown */}
              {data.share_links && data.share_links.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">By Share Link</p>
                  {data.share_links.map((link) => (
                    <div key={link.share_hash} className="rounded-lg border border-slate-100 bg-slate-50 px-4 py-3">
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <p className="text-xs font-mono text-slate-500 truncate max-w-xs">{link.share_url}</p>
                        <div className="flex items-center gap-3 shrink-0">
                          <span className="inline-flex items-center gap-1 text-xs text-slate-600">
                            <Eye className="h-3.5 w-3.5 text-indigo-400" />
                            {link.views} view{link.views !== 1 ? 's' : ''}
                          </span>
                          {link.last_viewed_at && (
                            <span className="text-xs text-slate-400">
                              Last: {formatDate(link.last_viewed_at)}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Recent view events */}
                      {link.view_events && link.view_events.length > 0 && (
                        <ul className="mt-2 space-y-1 border-t border-slate-200 pt-2">
                          {link.view_events.slice(0, 5).map((evt, i) => (
                            <li key={i} className="flex items-center justify-between text-[11px] text-slate-400">
                              <span>{formatDate(evt.viewed_at)}</span>
                              <div className="flex items-center gap-3">
                                {evt.ip_country && <span>{evt.ip_country}</span>}
                                {evt.duration_seconds != null && (
                                  <span className="flex items-center gap-1">
                                    <Clock className="h-3 w-3" />
                                    {formatDuration(evt.duration_seconds)}
                                  </span>
                                )}
                              </div>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {data.total_views === 0 && (
                <p className="text-sm text-slate-400 text-center py-2">
                  No views yet. Share the report to start tracking.
                </p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
