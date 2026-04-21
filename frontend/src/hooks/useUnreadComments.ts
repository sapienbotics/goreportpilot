'use client'

// Shared unread-comment counts for the agency dashboard.
//
// One provider mounted at the dashboard root owns a single poll loop
// (30s interval + refetch on tab-visibility + explicit refetch()).
// Every badge renderer (Sidebar, Clients list, All Reports, client
// detail's Reports tab) subscribes via useUnreadComments() so they
// all update in lock-step.

import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { commentsApi } from '@/lib/api'

const POLL_INTERVAL_MS = 30_000

interface UnreadCommentsValue {
  total:        number
  byReport:     Record<string, number>
  byClient:     Record<string, number>
  loading:      boolean
  refetch:      () => Promise<void>
  /** ISO timestamp of the most recent successful fetch — handy for debugging. */
  lastFetchedAt: string | null
}

const DEFAULT_VALUE: UnreadCommentsValue = {
  total:        0,
  byReport:     {},
  byClient:     {},
  loading:      false,
  refetch:      async () => { /* no-op when provider is absent */ },
  lastFetchedAt: null,
}

const UnreadCommentsContext = createContext<UnreadCommentsValue>(DEFAULT_VALUE)

export function useUnreadComments(): UnreadCommentsValue {
  return useContext(UnreadCommentsContext)
}

interface ProviderProps {
  children: React.ReactNode
}

export function UnreadCommentsProvider({ children }: ProviderProps) {
  const [total,    setTotal]    = useState(0)
  const [byReport, setByReport] = useState<Record<string, number>>({})
  const [byClient, setByClient] = useState<Record<string, number>>({})
  const [loading,  setLoading]  = useState(true)
  const [lastFetchedAt, setLastFetchedAt] = useState<string | null>(null)

  // An in-flight guard prevents overlapping requests when focus/visibility
  // events fire in rapid succession (common on desktop window-switching).
  const inFlightRef = useRef(false)

  const refetch = useCallback(async () => {
    if (inFlightRef.current) return
    inFlightRef.current = true
    try {
      const res = await commentsApi.unread()
      const rep: Record<string, number> = {}
      for (const row of res.by_report) rep[row.report_id] = row.unresolved_count
      const cli: Record<string, number> = {}
      for (const row of res.by_client) cli[row.client_id] = row.unresolved_count
      setTotal(res.total)
      setByReport(rep)
      setByClient(cli)
      setLastFetchedAt(new Date().toISOString())
    } catch {
      // Silent — an auth hiccup or transient failure shouldn't nuke badges.
    } finally {
      setLoading(false)
      inFlightRef.current = false
    }
  }, [])

  // Poll loop + mount fetch.
  useEffect(() => {
    refetch()
    const id = window.setInterval(refetch, POLL_INTERVAL_MS)
    return () => window.clearInterval(id)
  }, [refetch])

  // Refetch immediately when the user returns to the tab so returning
  // from the shared-link preview shows fresh counts without waiting for
  // the next poll tick.
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible') void refetch()
    }
    const onFocus = () => { void refetch() }
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('focus', onFocus)
    return () => {
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('focus', onFocus)
    }
  }, [refetch])

  const value: UnreadCommentsValue = useMemo(
    () => ({ total, byReport, byClient, loading, refetch, lastFetchedAt }),
    [total, byReport, byClient, loading, refetch, lastFetchedAt],
  )

  return createElement(UnreadCommentsContext.Provider, { value }, children)
}
