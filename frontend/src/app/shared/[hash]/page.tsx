'use client'

// Public shared report view page — no authentication required
// Shows report narrative, KPIs, and branding
// URL: /shared/{hash}

import { useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import { TrendingUp, TrendingDown, Minus, Loader2, Lock } from 'lucide-react'
import {
  CommentsProvider,
  CommentsDrawer,
  CommentButton,
  FloatingCommentFAB,
} from '@/components/shared/CommentsPanel'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SharedReportData {
  report_title: string
  client_name: string
  period_start: string
  period_end: string
  agency_name?: string | null
  agency_logo_url?: string | null
  narrative: Record<string, string | string[]>
  data_summary: Record<string, number | null>
  meta_currency?: string | null
}

interface SharedLinkMeta {
  requires_password: boolean
  is_active: boolean
  expired: boolean
  report_title?: string
  client_name?: string
}

// ---------------------------------------------------------------------------
// Currency helpers
// ---------------------------------------------------------------------------

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$',   EUR: '€',   GBP: '£',   INR: '₹',
  AUD: 'A$',  CAD: 'C$',  JPY: '¥',   CNY: '¥',
  BRL: 'R$',  MXN: 'Mex$', SGD: 'S$', HKD: 'HK$',
  CHF: 'CHF ', SEK: 'kr',  NOK: 'kr',  DKK: 'kr',
  ZAR: 'R',   AED: 'AED ', SAR: 'SAR ', MYR: 'RM',
}

function getCurrencySymbol(code?: string | null): string {
  if (!code) return '$'
  return CURRENCY_SYMBOLS[code.toUpperCase()] ?? code + ' '
}

// ---------------------------------------------------------------------------
// KPI config
// ---------------------------------------------------------------------------

interface KpiConfig {
  key: string
  label: string
  format: (v: number) => string
  invertPolarity?: boolean
}

function buildKpiConfigs(currencySymbol: string): KpiConfig[] {
  return [
    { key: 'sessions',    label: 'Sessions',    format: (v) => v.toLocaleString() },
    { key: 'users',       label: 'Users',       format: (v) => v.toLocaleString() },
    { key: 'conversions', label: 'Conversions', format: (v) => v.toLocaleString() },
    { key: 'spend',       label: 'Ad Spend',    format: (v) => `${currencySymbol}${v.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}` },
    { key: 'roas',        label: 'ROAS',        format: (v) => `${v.toFixed(1)}x` },
    { key: 'cost_per_conversion', label: 'Cost / Conv.', format: (v) => `${currencySymbol}${v.toFixed(2)}`, invertPolarity: true },
  ]
}

function getChange(summary: Record<string, number | null>, key: string): number | null {
  if (key === 'sessions')    return summary['sessions_change']    ?? null
  if (key === 'users')       return summary['users_change']       ?? null
  if (key === 'conversions') return summary['conversions_change'] ?? null
  if (key === 'spend')       return summary['spend_change']       ?? null
  return null
}

// ---------------------------------------------------------------------------
// Small shared sub-components
// ---------------------------------------------------------------------------

function ChangeTag({ change, invert }: { change: number | null; invert?: boolean }) {
  if (change === null) return null
  const positive = invert ? change < 0 : change > 0
  const neutral  = change === 0
  return (
    <span
      className={`inline-flex items-center gap-0.5 text-xs font-semibold ${
        neutral  ? 'text-slate-400' :
        positive ? 'text-emerald-600' :
                   'text-rose-500'
      }`}
    >
      {neutral  ? <Minus className="h-3 w-3" /> :
       positive ? <TrendingUp className="h-3 w-3" /> :
                  <TrendingDown className="h-3 w-3" />}
      {change > 0 ? '+' : ''}{change.toFixed(1)}%
    </span>
  )
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toLines(content: any): string[] {
  if (Array.isArray(content)) return content.map(String).filter((l) => l.trim())
  if (typeof content === 'string') return content.split('\n').filter((l) => l.trim())
  return []
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function NarrativeSection({ content }: { content: any }) {
  const paragraphs = toLines(content)
  if (paragraphs.length === 0) return null
  return (
    <div className="space-y-2">
      {paragraphs.map((p, i) => (
        <p key={i} className="text-sm text-slate-600 leading-relaxed">{p}</p>
      ))}
    </div>
  )
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function BulletSection({ content, color }: { content: any; color: 'emerald' | 'amber' | 'indigo' }) {
  const lines = toLines(content)
  if (lines.length === 0) return null
  const dotClass = { emerald: 'text-emerald-500', amber: 'text-amber-500', indigo: 'text-indigo-500' }[color]
  return (
    <ul className="space-y-2">
      {lines.map((line, i) => (
        <li key={i} className="flex items-start gap-2.5">
          <span className={`mt-0.5 text-base leading-none ${dotClass}`}>•</span>
          <span className="text-sm text-slate-600 leading-relaxed">
            {line.replace(/^[✓⚠•\d.]\s*/, '')}
          </span>
        </li>
      ))}
    </ul>
  )
}

// ---------------------------------------------------------------------------
// Password gate form
// ---------------------------------------------------------------------------

function PasswordGate({
  hash,
  apiBase,
  onUnlock,
}: {
  hash: string
  apiBase: string
  onUnlock: (data: SharedReportData) => void
}) {
  const [password, setPassword] = useState('')
  const [checking, setChecking] = useState(false)
  const [error, setError]       = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!password.trim()) return
    setChecking(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/shared/${hash}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      if (res.status === 401) {
        setError('Incorrect password. Please try again.')
        return
      }
      if (!res.ok) {
        setError('Something went wrong. Please try again.')
        return
      }
      const data: SharedReportData = await res.json()
      onUnlock(data)
    } catch {
      setError('Network error. Please check your connection.')
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-lg border border-slate-200 p-8 space-y-6">
        <div className="text-center space-y-2">
          <div className="mx-auto w-12 h-12 rounded-full bg-indigo-50 flex items-center justify-center">
            <Lock className="h-6 w-6 text-indigo-600" />
          </div>
          <h1 className="text-xl font-bold text-slate-900">Password Required</h1>
          <p className="text-sm text-slate-500">
            This report is password-protected. Enter the password to view it.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
            className="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            autoFocus
          />
          {error && (
            <p className="text-xs text-rose-600 bg-rose-50 border border-rose-100 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={checking || !password.trim()}
            className="w-full flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors disabled:opacity-60"
          >
            {checking ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {checking ? 'Verifying…' : 'View Report'}
          </button>
        </form>

        <p className="text-center text-xs text-slate-400">
          Powered by{' '}
          <a href="https://goreportpilot.com" target="_blank" rel="noopener noreferrer" className="text-indigo-500 hover:underline">
            GoReportPilot
          </a>
        </p>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Expired / inactive state
// ---------------------------------------------------------------------------

function ExpiredView() {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-sm text-center space-y-4">
        <div className="text-5xl">🔗</div>
        <h1 className="text-xl font-bold text-slate-900">Link Expired or Revoked</h1>
        <p className="text-sm text-slate-500">
          This report link has expired or been revoked. Please contact the agency for a new link.
        </p>
        <p className="text-xs text-slate-400">
          Powered by{' '}
          <a href="https://goreportpilot.com" target="_blank" rel="noopener noreferrer" className="text-indigo-500 hover:underline">
            GoReportPilot
          </a>
        </p>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Full report view
// ---------------------------------------------------------------------------

function ReportView({ data }: { data: SharedReportData }) {
  const currencySymbol = getCurrencySymbol(data.meta_currency)
  const KPI_CONFIGS    = buildKpiConfigs(currencySymbol)
  const summary        = data.data_summary ?? {}
  const narrative      = data.narrative    ?? {}

  const formatDate = (d: string) => {
    try { return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) }
    catch { return d }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* ── Branded header ─────────────────────────────────────────────────── */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            {data.agency_logo_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={data.agency_logo_url}
                alt={data.agency_name ?? 'Agency logo'}
                className="h-8 w-auto object-contain flex-shrink-0"
              />
            )}
            <div className="min-w-0">
              {data.agency_name && (
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide truncate">
                  {data.agency_name}
                </p>
              )}
              <p className="text-sm font-bold text-slate-900 truncate">{data.client_name}</p>
            </div>
          </div>
          <p className="text-xs text-slate-400 shrink-0">
            {formatDate(data.period_start)} – {formatDate(data.period_end)}
          </p>
        </div>
      </header>

      {/* ── Report content ─────────────────────────────────────────────────── */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">

        {/* Title */}
        <div>
          <h1
            className="text-2xl font-bold text-slate-900"
            style={{ fontFamily: 'var(--font-plus-jakarta-sans, system-ui)' }}
          >
            {data.report_title}
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            {formatDate(data.period_start)} → {formatDate(data.period_end)}
          </p>
        </div>

        {/* KPI scorecard */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {KPI_CONFIGS.map(({ key, label, format, invertPolarity }) => {
            const rawVal = summary[key]
            const value  = rawVal != null ? format(rawVal) : '—'
            const change = getChange(summary as Record<string, number | null>, key)
            return (
              <div key={key} className="rounded-xl bg-white border border-slate-100 p-4 shadow-sm">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">{label}</p>
                <p className="text-xl font-bold text-slate-900 mt-1 leading-tight">{value}</p>
                <div className="mt-1">
                  <ChangeTag change={change} invert={invertPolarity} />
                </div>
              </div>
            )
          })}
        </div>

        {/* Executive Summary */}
        {narrative['executive_summary'] && (
          <div className="rounded-xl bg-white border border-slate-100 p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-base font-semibold text-indigo-700">Executive Summary</h2>
              <CommentButton sectionKey="executive_summary" sectionLabel="Executive Summary" />
            </div>
            <NarrativeSection content={narrative['executive_summary']} />
          </div>
        )}

        {/* Website & Paid Advertising */}
        <div className="grid md:grid-cols-2 gap-4">
          {narrative['website_performance'] && (
            <div className="rounded-xl bg-white border border-slate-100 p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-base font-semibold text-slate-700">Website Performance</h2>
                <CommentButton sectionKey="website_performance" sectionLabel="Website Performance" />
              </div>
              <NarrativeSection content={narrative['website_performance']} />
            </div>
          )}
          {narrative['paid_advertising'] && (
            <div className="rounded-xl bg-white border border-slate-100 p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-base font-semibold text-slate-700">Paid Advertising</h2>
                <CommentButton sectionKey="paid_advertising" sectionLabel="Paid Advertising" />
              </div>
              <NarrativeSection content={narrative['paid_advertising']} />
            </div>
          )}
        </div>

        {/* Wins / Concerns / Next Steps */}
        <div className="grid md:grid-cols-3 gap-4">
          {narrative['key_wins'] && (
            <div className="rounded-xl bg-white border border-emerald-100 p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-base font-semibold text-emerald-700">Key Wins</h2>
                <CommentButton sectionKey="key_wins" sectionLabel="Key Wins" />
              </div>
              <BulletSection content={narrative['key_wins']} color="emerald" />
            </div>
          )}
          {narrative['concerns'] && (
            <div className="rounded-xl bg-white border border-amber-100 p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-base font-semibold text-amber-700">Concerns</h2>
                <CommentButton sectionKey="concerns" sectionLabel="Concerns" />
              </div>
              <BulletSection content={narrative['concerns']} color="amber" />
            </div>
          )}
          {narrative['next_steps'] && (
            <div className="rounded-xl bg-white border border-indigo-100 p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-base font-semibold text-indigo-700">Next Steps</h2>
                <CommentButton sectionKey="next_steps" sectionLabel="Next Steps" />
              </div>
              <BulletSection content={narrative['next_steps']} color="indigo" />
            </div>
          )}
        </div>
      </main>

      {/* Comments — floating general feedback FAB + slide-in drawer */}
      <FloatingCommentFAB />
      <CommentsDrawer />

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-200 bg-white mt-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-5 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-400">
          <p>Report generated by{' '}
            <a
              href="https://goreportpilot.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-500 hover:underline font-medium"
            >
              GoReportPilot
            </a>
          </p>
          <p>
            {data.client_name} · {formatDate(data.period_start)} – {formatDate(data.period_end)}
          </p>
        </div>
      </footer>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

export default function SharedReportPage() {
  const params  = useParams<{ hash: string }>()
  const hash    = params.hash
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const [linkMeta,   setLinkMeta]   = useState<SharedLinkMeta | null>(null)
  const [reportData, setReportData] = useState<SharedReportData | null>(null)
  const [loading,    setLoading]    = useState(true)
  const [expired,    setExpired]    = useState(false)

  // Sticky flag — we only want ONE view row per page visit. Without this,
  // React double-invokes the effect in Strict Mode and we'd double-count.
  const viewLoggedRef = useRef<boolean>(false)

  // On mount: fetch link metadata (GET /api/shared/{hash})
  useEffect(() => {
    const fetchMeta = async () => {
      try {
        const res = await fetch(`${apiBase}/api/shared/${hash}`)
        if (res.status === 404 || res.status === 410) {
          setExpired(true)
          return
        }
        if (!res.ok) {
          setExpired(true)
          return
        }
        const meta: SharedLinkMeta = await res.json()

        if (!meta.is_active || meta.expired) {
          setExpired(true)
          return
        }

        setLinkMeta(meta)

        // If no password required, also fetch the full report data immediately
        if (!meta.requires_password) {
          const reportRes = await fetch(`${apiBase}/api/shared/${hash}/data`)
          if (reportRes.ok) {
            const data: SharedReportData = await reportRes.json()
            setReportData(data)
          } else {
            setExpired(true)
          }
        }
      } catch {
        setExpired(true)
      } finally {
        setLoading(false)
      }
    }

    fetchMeta()
  }, [hash, apiBase])

  // Log view once report data is available.
  //
  // The backend endpoint expects a JSON body (ViewLogRequest). Prior versions
  // of this page sent no body, which caused FastAPI to 422 and the .catch()
  // swallowed the error — hence View Analytics always read 0.
  //
  // We log exactly once per page visit (viewLoggedRef). The earlier
  // beforeunload/sendBeacon path used text/plain Content-Type (sendBeacon's
  // default for strings) which also failed JSON parsing AND produced a second
  // row per visit — so it's been removed. Duration tracking will return in a
  // future pass once we have a heartbeat / update endpoint.
  useEffect(() => {
    if (!reportData || viewLoggedRef.current) return
    viewLoggedRef.current = true

    const ua = typeof navigator !== 'undefined' ? navigator.userAgent : ''
    const deviceType =
      /Mobi|Android|iPhone|iPod/i.test(ua) ? 'mobile' :
      /iPad|Tablet/i.test(ua)              ? 'tablet' :
                                             'desktop'

    fetch(`${apiBase}/api/shared/${hash}/view`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ device_type: deviceType }),
    }).catch(() => { /* fire-and-forget */ })
  }, [reportData, hash, apiBase])

  // ── Loading skeleton ──────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
          <p className="text-sm text-slate-400">Loading report…</p>
        </div>
      </div>
    )
  }

  // ── Expired / not found ───────────────────────────────────────────────────
  if (expired || !linkMeta) {
    return <ExpiredView />
  }

  // ── Password gate ─────────────────────────────────────────────────────────
  if (linkMeta.requires_password && !reportData) {
    return (
      <PasswordGate
        hash={hash}
        apiBase={apiBase}
        onUnlock={(data) => setReportData(data)}
      />
    )
  }

  // ── Full report ───────────────────────────────────────────────────────────
  if (reportData) {
    return (
      <CommentsProvider shareToken={hash}>
        <ReportView data={reportData} />
      </CommentsProvider>
    )
  }

  // Fallback (should not reach here)
  return <ExpiredView />
}
