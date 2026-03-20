'use client'

// Report preview page — shows full AI narrative, KPIs, and download buttons.

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft, Download, FileText, TrendingUp, TrendingDown,
  Minus, CheckCircle, AlertTriangle, ChevronRight, Loader2,
} from 'lucide-react'
import { reportsApi, downloadFileWithAuth } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Report } from '@/types'

// ── KPI display config ──────────────────────────────────────────────────────
interface KpiConfig {
  key: string
  label: string
  format: (v: number) => string
  /** If true, a positive change is bad (e.g. CPA) */
  invertPolarity?: boolean
}

const KPI_CONFIGS: KpiConfig[] = [
  { key: 'sessions',    label: 'Sessions',    format: (v) => v.toLocaleString() },
  { key: 'users',       label: 'Users',       format: (v) => v.toLocaleString() },
  { key: 'conversions', label: 'Conversions', format: (v) => v.toLocaleString() },
  { key: 'spend',       label: 'Ad Spend',    format: (v) => `$${v.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}` },
  { key: 'roas',        label: 'ROAS',        format: (v) => `${v.toFixed(1)}x` },
  { key: 'cost_per_conversion', label: 'Cost / Conv.', format: (v) => `$${v.toFixed(2)}`, invertPolarity: true },
]

const CHANGE_KEYS: Record<string, string> = {
  sessions:    'sessions_change',
  users:       'users_change',
  conversions: 'conversions_change',
  spend:       'spend_change',
  roas:        'roas',   // derive below
  cost_per_conversion: 'cost_per_conversion', // derive below
}

function getChange(
  summary: Record<string, number | null>,
  key: string,
): number | null {
  // Direct change fields
  if (key === 'sessions')    return summary['sessions_change']    ?? null
  if (key === 'users')       return summary['users_change']       ?? null
  if (key === 'conversions') return summary['conversions_change'] ?? null
  if (key === 'spend')       return summary['spend_change']       ?? null
  return null   // ROAS and CPA don't have pre-computed change in data_summary
}

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
      {neutral ? <Minus className="h-3 w-3" /> :
       positive ? <TrendingUp className="h-3 w-3" /> :
                  <TrendingDown className="h-3 w-3" />}
      {change > 0 ? '+' : ''}{change.toFixed(1)}%
    </span>
  )
}

// ── Shared helper — normalise str | string[] → string[] ─────────────────────
// GPT-4o returns paragraph fields as strings and bullet fields as arrays;
// handle both so neither component crashes regardless of AI output format.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toLines(content: any): string[] {
  if (Array.isArray(content)) return content.map(String).filter((l) => l.trim())
  if (typeof content === 'string') return content.split('\n').filter((l) => l.trim())
  return []
}

// ── Narrative section ───────────────────────────────────────────────────────
function NarrativeSection({ title, content, icon }: {
  title: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  content: any
  icon?: React.ReactNode
}) {
  const paragraphs = toLines(content)
  if (paragraphs.length === 0) return null
  return (
    <div>
      <h3 className="text-base font-semibold text-slate-800 flex items-center gap-2 mb-3">
        {icon}
        {title}
      </h3>
      <div className="space-y-2">
        {paragraphs.map((p, i) => (
          <p key={i} className="text-sm text-slate-600 leading-relaxed">
            {p}
          </p>
        ))}
      </div>
    </div>
  )
}

// ── Bullet-list section (wins / concerns / next steps) ──────────────────────
function BulletSection({ title, content, color }: {
  title: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  content: any
  color: 'emerald' | 'amber' | 'indigo'
}) {
  const lines = toLines(content)
  if (lines.length === 0) return null

  const dotClass = {
    emerald: 'text-emerald-500',
    amber:   'text-amber-500',
    indigo:  'text-indigo-500',
  }[color]

  return (
    <div>
      <h3 className="text-base font-semibold text-slate-800 mb-3">{title}</h3>
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
    </div>
  )
}

// ── Main page component ─────────────────────────────────────────────────────
export default function ReportDetailPage() {
  const params  = useParams<{ reportId: string }>()
  const reportId = params.reportId

  const [report,   setReport]  = useState<Report | null>(null)
  const [loading,  setLoading] = useState(true)
  const [error,    setError]   = useState<string | null>(null)
  const [dlPptx,   setDlPptx]  = useState(false)
  const [dlPdf,    setDlPdf]   = useState(false)

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await reportsApi.get(reportId)
        setReport(data)
      } catch {
        setError('Report not found or failed to load.')
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [reportId])

  const handleDownloadPptx = async () => {
    if (!report) return
    setDlPptx(true)
    try {
      await downloadFileWithAuth(
        `/api/reports/${reportId}/download/pptx`,
        `${report.title}.pptx`,
      )
    } catch {
      alert('Download failed. Please try again.')
    } finally {
      setDlPptx(false)
    }
  }

  const handleDownloadPdf = async () => {
    if (!report) return
    setDlPdf(true)
    try {
      await downloadFileWithAuth(
        `/api/reports/${reportId}/download/pdf`,
        `${report.title}.pdf`,
      )
    } catch {
      alert('Download failed. Please try again.')
    } finally {
      setDlPdf(false)
    }
  }

  // ── States ──────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-4">
        <div className="h-8 w-64 rounded bg-slate-100 animate-pulse" />
        <div className="h-40 rounded-xl bg-slate-100 animate-pulse" />
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <div key={i} className="h-28 rounded-xl bg-slate-100 animate-pulse" />)}
        </div>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error ?? 'Report not found.'}
        </div>
      </div>
    )
  }

  const summary = report.data_summary ?? {}
  const narrative = report.narrative ?? {}

  return (
    <div className="max-w-4xl mx-auto space-y-6">

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <Link
            href={`/dashboard/clients/${report.client_id}`}
            className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-600 transition-colors mb-2"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            {report.client_name ?? 'Back to client'}
          </Link>
          <h1
            className="text-2xl font-bold text-slate-900"
            style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
          >
            {report.title}
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            {report.period_start} → {report.period_end}
            <span
              className={`ml-3 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                report.status === 'draft' || report.status === 'approved'
                  ? 'bg-emerald-50 text-emerald-700'
                  : 'bg-slate-100 text-slate-500'
              }`}
            >
              {report.status}
            </span>
          </p>
        </div>

        {/* Download buttons */}
        <div className="flex gap-2 shrink-0">
          <button
            onClick={handleDownloadPptx}
            disabled={dlPptx}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-60"
          >
            {dlPptx ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Download PPTX
          </button>
          <button
            onClick={handleDownloadPdf}
            disabled={dlPdf}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors disabled:opacity-60"
          >
            {dlPdf ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
            Download PDF
          </button>
        </div>
      </div>

      {/* ── KPI scorecard ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {KPI_CONFIGS.map(({ key, label, format, invertPolarity }) => {
          const rawVal = summary[key]
          const value  = rawVal != null ? format(rawVal) : '—'
          const change = getChange(summary as Record<string, number | null>, key)

          return (
            <div
              key={key}
              className="rounded-xl bg-white border border-slate-100 p-4 shadow-sm"
            >
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">{label}</p>
              <p className="text-xl font-bold text-slate-900 mt-1 leading-tight">{value}</p>
              <div className="mt-1">
                <ChangeTag change={change} invert={invertPolarity} />
              </div>
            </div>
          )
        })}
      </div>

      {/* ── Executive Summary ─────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-indigo-700">Executive Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <NarrativeSection
            title=""
            content={narrative['executive_summary']}
          />
        </CardContent>
      </Card>

      {/* ── Website & Paid Advertising ────────────────────────────────────── */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base text-slate-700">Website Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <NarrativeSection title="" content={narrative['website_performance']} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base text-slate-700">Paid Advertising</CardTitle>
          </CardHeader>
          <CardContent>
            <NarrativeSection title="" content={narrative['paid_advertising']} />
          </CardContent>
        </Card>
      </div>

      {/* ── Wins / Concerns / Next Steps ──────────────────────────────────── */}
      <div className="grid md:grid-cols-3 gap-4">
        <Card className="border-emerald-100">
          <CardHeader>
            <CardTitle className="text-base text-emerald-700 flex items-center gap-2">
              <CheckCircle className="h-4 w-4" /> Key Wins
            </CardTitle>
          </CardHeader>
          <CardContent>
            <BulletSection title="" content={narrative['key_wins']} color="emerald" />
          </CardContent>
        </Card>

        <Card className="border-amber-100">
          <CardHeader>
            <CardTitle className="text-base text-amber-700 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" /> Concerns
            </CardTitle>
          </CardHeader>
          <CardContent>
            <BulletSection title="" content={narrative['concerns']} color="amber" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base text-indigo-700 flex items-center gap-2">
              <ChevronRight className="h-4 w-4" /> Next Steps
            </CardTitle>
          </CardHeader>
          <CardContent>
            <BulletSection title="" content={narrative['next_steps']} color="indigo" />
          </CardContent>
        </Card>
      </div>

    </div>
  )
}
