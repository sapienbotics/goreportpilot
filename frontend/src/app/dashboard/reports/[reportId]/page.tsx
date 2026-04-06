'use client'

// Report preview page — full AI narrative, KPIs, inline editing, regenerate, and send.

import { useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft, Download, FileText, TrendingUp, TrendingDown,
  Minus, Loader2,
  Pencil, RefreshCw, Check, X as XIcon, Send, Mail, Share2,
} from 'lucide-react'
import { reportsApi, downloadFileWithAuth } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import type { Report } from '@/types'
import ShareReportDialog from '@/components/reports/ShareReportDialog'
import ViewAnalytics from '@/components/reports/ViewAnalytics'

// ── Currency symbol lookup ──────────────────────────────────────────────────
const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$',   EUR: '€',   GBP: '£',   INR: '₹',
  AUD: 'A$',  CAD: 'C$',  JPY: '¥',   CNY: '¥',
  BRL: 'R$',  MXN: 'Mex$', SGD: 'S$', HKD: 'HK$',
  CHF: 'CHF ',SEK: 'kr',  NOK: 'kr',  DKK: 'kr',
  ZAR: 'R',   AED: 'AED ',SAR: 'SAR ',MYR: 'RM',
}

function getCurrencySymbol(code?: string | null): string {
  if (!code) return '$'
  return CURRENCY_SYMBOLS[code.toUpperCase()] ?? code + ' '
}

// ── KPI display config ──────────────────────────────────────────────────────
interface KpiConfig {
  key: string
  label: string
  format: (v: number) => string
  /** If true, a positive change is bad (e.g. CPA) */
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

// ── Editable narrative card ──────────────────────────────────────────────────
// Wraps a narrative section with Edit / Save / Cancel / Regenerate controls.
function EditableNarrativeCard({
  sectionKey,
  title,
  content,
  cardClassName,
  titleClassName,
  children,
  onSave,
  onRegenerate,
  saving,
  regenerating,
}: {
  sectionKey: string
  title: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  content: any
  cardClassName?: string
  titleClassName?: string
  children: React.ReactNode
  onSave: (sectionKey: string, text: string) => Promise<void>
  onRegenerate: (sectionKey: string) => Promise<void>
  saving: boolean
  regenerating: boolean
}) {
  const rawText = Array.isArray(content)
    ? content.join('\n')
    : typeof content === 'string' ? content : ''

  const [editing, setEditing]   = useState(false)
  const [editText, setEditText] = useState(rawText)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Keep editText in sync when parent content changes (e.g. after regenerate)
  useEffect(() => {
    if (!editing) setEditText(rawText)
  }, [rawText, editing])

  const handleEdit = () => {
    setEditText(rawText)
    setEditing(true)
    setTimeout(() => textareaRef.current?.focus(), 50)
  }

  const handleCancel = () => {
    setEditText(rawText)
    setEditing(false)
  }

  const handleSave = async () => {
    await onSave(sectionKey, editText)
    setEditing(false)
  }

  return (
    <Card className={cardClassName}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <CardTitle className={`text-base ${titleClassName ?? 'text-slate-700'}`}>
            {title}
          </CardTitle>
          <div className="flex items-center gap-1.5">
            {editing ? (
              <>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="inline-flex items-center gap-1 rounded-md bg-indigo-700 px-2.5 py-1 text-xs font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-60"
                >
                  {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                  Save
                </button>
                <button
                  onClick={handleCancel}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50 transition-colors"
                >
                  <XIcon className="h-3 w-3" /> Cancel
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={handleEdit}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1 text-xs text-slate-500 hover:bg-slate-50 transition-colors"
                >
                  <Pencil className="h-3 w-3" /> Edit
                </button>
                <button
                  onClick={() => onRegenerate(sectionKey)}
                  disabled={regenerating}
                  title="Re-run AI for this section"
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1 text-xs text-slate-500 hover:bg-slate-50 transition-colors disabled:opacity-60"
                >
                  {regenerating
                    ? <Loader2 className="h-3 w-3 animate-spin" />
                    : <RefreshCw className="h-3 w-3" />}
                  Regenerate
                </button>
              </>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {editing ? (
          <Textarea
            ref={textareaRef}
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            rows={8}
            className="text-sm text-slate-700 leading-relaxed font-mono resize-y"
          />
        ) : (
          children
        )}
      </CardContent>
    </Card>
  )
}

// ── Narrative section (read-only inner content) ──────────────────────────────
function NarrativeSection({ content }: {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  content: any
}) {
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

// ── Bullet-list section (wins / concerns / next steps) ──────────────────────
function BulletSection({ content, color }: {
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

// ── Send Report dialog ───────────────────────────────────────────────────────
function SendReportDialog({
  report,
  onClose,
}: {
  report: Report
  onClose: () => void
}) {
  const [toEmails, setToEmails]     = useState(report.client_id ? '' : '')  // pre-fill if available
  const [subject, setSubject]       = useState(report.title)
  const [attachment, setAttachment] = useState<'both' | 'pdf' | 'pptx'>('both')
  const [sending, setSending]       = useState(false)
  const [sent, setSent]             = useState(false)
  const [sendError, setSendError]   = useState<string | null>(null)

  const handleSend = async () => {
    const emails = toEmails.split(',').map((e) => e.trim()).filter(Boolean)
    if (emails.length === 0) {
      setSendError('Please enter at least one recipient email.')
      return
    }
    setSending(true)
    setSendError(null)
    try {
      await reportsApi.send(report.id, {
        to_emails:  emails,
        subject:    subject || report.title,
        attachment,
      })
      setSent(true)
    } catch (err: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const resp = (err as any)?.response
      if (resp?.status === 410) {
        setSendError('Report files have expired. Close this dialog and click "Regenerate Report" first.')
      } else {
        const msg = err instanceof Error ? err.message : 'Failed to send email.'
        setSendError(msg)
      }
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-xl bg-white shadow-2xl border border-slate-200 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Mail className="h-5 w-5 text-indigo-600" />
            Send to Client
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
            <XIcon className="h-5 w-5" />
          </button>
        </div>

        {sent ? (
          <div className="text-center py-6 space-y-2">
            <div className="text-4xl">✅</div>
            <p className="font-semibold text-slate-800">Email sent!</p>
            <p className="text-sm text-slate-500">
              The report has been delivered to {toEmails}.
            </p>
            <button
              onClick={onClose}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors"
            >
              Done
            </button>
          </div>
        ) : (
          <>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">
                  To (comma-separated)
                </label>
                <Input
                  type="text"
                  value={toEmails}
                  onChange={(e) => setToEmails(e.target.value)}
                  placeholder="client@example.com, contact@example.com"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">
                  Subject
                </label>
                <Input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">
                  Attachment
                </label>
                <div className="flex gap-2">
                  {(['both', 'pdf', 'pptx'] as const).map((opt) => (
                    <button
                      key={opt}
                      onClick={() => setAttachment(opt)}
                      className={`flex-1 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                        attachment === opt
                          ? 'bg-indigo-700 border-indigo-700 text-white'
                          : 'border-slate-200 text-slate-600 hover:border-indigo-300'
                      }`}
                    >
                      {opt === 'both' ? 'PDF + PPTX' : opt.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>

              {sendError && (
                <p className="text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                  {sendError}
                </p>
              )}
            </div>

            <div className="flex gap-2 pt-1">
              <button
                onClick={handleSend}
                disabled={sending}
                className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-60"
              >
                {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                {sending ? 'Sending…' : 'Send Report'}
              </button>
              <button
                onClick={onClose}
                className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ── Main page component ─────────────────────────────────────────────────────
export default function ReportDetailPage() {
  const params  = useParams<{ reportId: string }>()
  const reportId = params.reportId

  const [report,          setReport]        = useState<Report | null>(null)
  const [loading,         setLoading]       = useState(true)
  const [error,           setError]         = useState<string | null>(null)
  const [dlPptx,          setDlPptx]        = useState(false)
  const [dlPdf,           setDlPdf]         = useState(false)
  const [savingSection,   setSavingSection]  = useState<string | null>(null)
  const [regenSection,    setRegenSection]   = useState<string | null>(null)
  const [showSendDialog,  setShowSendDialog] = useState(false)
  const [showShare,       setShowShare]      = useState(false)
  const [filesExpired,    setFilesExpired]   = useState(false)
  const [regenerating,    setRegenerating]   = useState(false)

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

  const handleSaveEdit = async (sectionKey: string, text: string) => {
    if (!report) return
    setSavingSection(sectionKey)
    try {
      const updated = await reportsApi.update(report.id, { [sectionKey]: text })
      setReport(updated)
    } catch {
      setError('Failed to save edit. Please try again.')
    } finally {
      setSavingSection(null)
    }
  }

  const handleRegenerate = async (sectionKey: string) => {
    if (!report) return
    setRegenSection(sectionKey)
    try {
      const updated = await reportsApi.regenerateSection(report.id, sectionKey)
      setReport(updated)
    } catch {
      setError('Failed to regenerate section. Please try again.')
    } finally {
      setRegenSection(null)
    }
  }

  const isFilesExpiredError = (err: unknown): boolean => {
    if (err && typeof err === 'object' && 'response' in err) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const resp = (err as any).response
      if (resp?.status === 410) return true
      const detail = resp?.data?.detail
      if (typeof detail === 'object' && detail?.code === 'FILES_EXPIRED') return true
    }
    return false
  }

  const handleDownloadPptx = async () => {
    if (!report) return
    setDlPptx(true)
    try {
      await downloadFileWithAuth(
        `/api/reports/${reportId}/download/pptx`,
        `${report.title}.pptx`,
      )
    } catch (err) {
      if (isFilesExpiredError(err)) {
        setFilesExpired(true)
      } else {
        alert('Download failed. Please try again.')
      }
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
    } catch (err) {
      if (isFilesExpiredError(err)) {
        setFilesExpired(true)
      } else {
        alert('Download failed. Please try again.')
      }
    } finally {
      setDlPdf(false)
    }
  }

  const handleRegenerateReport = async () => {
    if (!report) return
    setRegenerating(true)
    setFilesExpired(false)
    setError(null)
    try {
      const updated = await reportsApi.regenerate(report.id)
      setReport(updated)
    } catch {
      setError('Failed to regenerate report. Please try again.')
    } finally {
      setRegenerating(false)
    }
  }

  // ── States ──────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto space-y-4">
        <div className="h-8 w-64 rounded bg-slate-100 animate-pulse" />
        <div className="h-40 rounded-xl bg-slate-100 animate-pulse" />
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <div key={i} className="h-28 rounded-xl bg-slate-100 animate-pulse" />)}
        </div>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error ?? 'Report not found.'}
        </div>
      </div>
    )
  }

  const summary = report.data_summary ?? {}
  // Merge user_edits over ai_narrative so manual edits take priority in the UI
  const baseNarrative = report.narrative ?? {}
  const userEdits     = report.user_edits ?? {}
  const narrative     = { ...baseNarrative, ...Object.fromEntries(
    Object.entries(userEdits).filter(([, v]) => v)
  )}
  const KPI_CONFIGS = buildKpiConfigs(getCurrencySymbol(report.meta_currency))

  return (
    <div className="max-w-7xl mx-auto space-y-6">

      {/* ── Send dialog (rendered at top level so it overlays everything) ── */}
      {showSendDialog && (
        <SendReportDialog
          report={report}
          onClose={() => setShowSendDialog(false)}
        />
      )}

      {/* ── Share dialog ──────────────────────────────────────────────────── */}
      {showShare && (
        <ShareReportDialog reportId={report.id} onClose={() => setShowShare(false)} />
      )}

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
                report.status === 'sent'
                  ? 'bg-indigo-50 text-indigo-700'
                  : report.status === 'draft' || report.status === 'approved'
                  ? 'bg-emerald-50 text-emerald-700'
                  : 'bg-slate-100 text-slate-500'
              }`}
            >
              {report.status}
            </span>
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 shrink-0 flex-wrap">
          <button
            onClick={() => setShowSendDialog(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-100 transition-colors"
          >
            <Send className="h-4 w-4" />
            Send to Client
          </button>
          <button
            onClick={() => setShowShare(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <Share2 className="h-4 w-4" />
            Share
          </button>
          <button
            onClick={handleDownloadPptx}
            disabled={dlPptx}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-60"
          >
            {dlPptx ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            PPTX
          </button>
          {report.pdf_url !== null && report.pdf_url !== undefined ? (
            <button
              onClick={handleDownloadPdf}
              disabled={dlPdf}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors disabled:opacity-60"
            >
              {dlPdf ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
              PDF
            </button>
          ) : (
            <span
              title="PDF not available — this report language requires LibreOffice for PDF rendering. Download PPTX instead."
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-400 cursor-not-allowed select-none"
            >
              <FileText className="h-4 w-4" />
              PDF unavailable
            </span>
          )}
        </div>
      </div>

      {filesExpired && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-5 py-4 flex items-center justify-between gap-4 flex-wrap">
          <div>
            <p className="text-sm font-semibold text-amber-800">Report files have expired</p>
            <p className="text-xs text-amber-600 mt-0.5">
              Report files are removed when the server redeploys. Click &ldquo;Regenerate Report&rdquo; to create fresh files.
            </p>
          </div>
          <button
            onClick={handleRegenerateReport}
            disabled={regenerating}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-60 shrink-0"
          >
            {regenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            {regenerating ? 'Regenerating…' : 'Regenerate Report'}
          </button>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

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
      <EditableNarrativeCard
        sectionKey="executive_summary"
        title="Executive Summary"
        content={narrative['executive_summary']}
        titleClassName="text-indigo-700"
        onSave={handleSaveEdit}
        onRegenerate={handleRegenerate}
        saving={savingSection === 'executive_summary'}
        regenerating={regenSection === 'executive_summary'}
      >
        <NarrativeSection content={narrative['executive_summary']} />
      </EditableNarrativeCard>

      {/* ── Website & Paid Advertising ────────────────────────────────────── */}
      <div className="grid md:grid-cols-2 gap-4">
        <EditableNarrativeCard
          sectionKey="website_performance"
          title="Website Performance"
          content={narrative['website_performance']}
          onSave={handleSaveEdit}
          onRegenerate={handleRegenerate}
          saving={savingSection === 'website_performance'}
          regenerating={regenSection === 'website_performance'}
        >
          <NarrativeSection content={narrative['website_performance']} />
        </EditableNarrativeCard>

        <EditableNarrativeCard
          sectionKey="paid_advertising"
          title="Paid Advertising"
          content={narrative['paid_advertising']}
          onSave={handleSaveEdit}
          onRegenerate={handleRegenerate}
          saving={savingSection === 'paid_advertising'}
          regenerating={regenSection === 'paid_advertising'}
        >
          <NarrativeSection content={narrative['paid_advertising']} />
        </EditableNarrativeCard>
      </div>

      {/* ── Wins / Concerns / Next Steps ──────────────────────────────────── */}
      <div className="grid md:grid-cols-3 gap-4">
        <EditableNarrativeCard
          sectionKey="key_wins"
          title="Key Wins"
          content={narrative['key_wins']}
          cardClassName="border-emerald-100"
          titleClassName="text-emerald-700"
          onSave={handleSaveEdit}
          onRegenerate={handleRegenerate}
          saving={savingSection === 'key_wins'}
          regenerating={regenSection === 'key_wins'}
        >
          <BulletSection content={narrative['key_wins']} color="emerald" />
        </EditableNarrativeCard>

        <EditableNarrativeCard
          sectionKey="concerns"
          title="Concerns"
          content={narrative['concerns']}
          cardClassName="border-amber-100"
          titleClassName="text-amber-700"
          onSave={handleSaveEdit}
          onRegenerate={handleRegenerate}
          saving={savingSection === 'concerns'}
          regenerating={regenSection === 'concerns'}
        >
          <BulletSection content={narrative['concerns']} color="amber" />
        </EditableNarrativeCard>

        <EditableNarrativeCard
          sectionKey="next_steps"
          title="Next Steps"
          content={narrative['next_steps']}
          titleClassName="text-indigo-700"
          onSave={handleSaveEdit}
          onRegenerate={handleRegenerate}
          saving={savingSection === 'next_steps'}
          regenerating={regenSection === 'next_steps'}
        >
          <BulletSection content={narrative['next_steps']} color="indigo" />
        </EditableNarrativeCard>
      </div>

      {/* ── View Analytics ─────────────────────────────────────────────────── */}
      <ViewAnalytics reportId={report.id} />

    </div>
  )
}
