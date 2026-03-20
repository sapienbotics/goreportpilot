'use client'

// Client detail page — shows client info, generate report, and report history.
// Includes edit-in-place and delete (soft-delete).

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Globe, Mail, Building2, Pencil, Trash2, Check, X as XIcon,
  FileText, Sparkles, Download, ChevronRight, Calendar,
} from 'lucide-react'
import { clientsApi, reportsApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type { Client, Report } from '@/types'

interface Props {
  params: { clientId: string }
}

// ── Helper: first and last day of last month ────────────────────────────────
function lastMonthRange(): { start: string; end: string } {
  const now = new Date()
  const first = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  const last  = new Date(now.getFullYear(), now.getMonth(), 0)
  const fmt   = (d: Date) => d.toISOString().slice(0, 10)
  return { start: fmt(first), end: fmt(last) }
}

export default function ClientDetailPage({ params }: Props) {
  const router = useRouter()
  const { clientId } = params

  const [client, setClient]   = useState<Client | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  // Edit state
  const [editing, setEditing] = useState(false)
  const [saving, setSaving]   = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [editValues, setEditValues] = useState<Partial<Client>>({})

  // Generate report state
  const defaultRange = lastMonthRange()
  const [periodStart, setPeriodStart] = useState(defaultRange.start)
  const [periodEnd,   setPeriodEnd]   = useState(defaultRange.end)
  const [generating,  setGenerating]  = useState(false)
  const [genError,    setGenError]    = useState<string | null>(null)

  // Reports list
  const [reports, setReports]         = useState<Report[]>([])
  const [reportsLoading, setReportsLoading] = useState(true)

  // Fetch client
  useEffect(() => {
    const fetchClient = async () => {
      try {
        const data = await clientsApi.get(clientId)
        setClient(data)
        setEditValues(data)
      } catch {
        setError('Client not found or failed to load.')
      } finally {
        setLoading(false)
      }
    }
    fetchClient()
  }, [clientId])

  // Fetch reports for this client
  useEffect(() => {
    const fetchReports = async () => {
      try {
        const { reports: data } = await reportsApi.listByClient(clientId)
        setReports(data)
      } catch {
        // Reports list failing shouldn't break the page
      } finally {
        setReportsLoading(false)
      }
    }
    fetchReports()
  }, [clientId])

  const handleSave = async () => {
    if (!client) return
    setSaving(true)
    try {
      const updated = await clientsApi.update(client.id, {
        name:                  editValues.name,
        website_url:           editValues.website_url           ?? undefined,
        industry:              editValues.industry              ?? undefined,
        primary_contact_email: editValues.primary_contact_email ?? undefined,
        goals_context:         editValues.goals_context         ?? undefined,
        notes:                 editValues.notes                 ?? undefined,
      })
      setClient(updated)
      setEditing(false)
    } catch {
      setError('Failed to save changes.')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!client) return
    if (!window.confirm(`Delete ${client.name}? This cannot be undone.`)) return
    setDeleting(true)
    try {
      await clientsApi.delete(client.id)
      router.push('/dashboard/clients')
    } catch {
      setError('Failed to delete client.')
      setDeleting(false)
    }
  }

  const handleGenerate = async () => {
    setGenerating(true)
    setGenError(null)
    try {
      const report = await reportsApi.generate({
        client_id:    clientId,
        period_start: periodStart,
        period_end:   periodEnd,
      })
      router.push(`/dashboard/reports/${report.id}`)
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Failed to generate report. Please try again.'
      setGenError(msg)
      setGenerating(false)
    }
  }

  // ── Loading / error states ───────────────────────────────────────────────

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="h-8 w-48 rounded bg-slate-100 animate-pulse" />
        <div className="h-64 rounded-xl bg-slate-100 animate-pulse" />
      </div>
    )
  }

  if (error && !client) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      </div>
    )
  }

  if (!client) return null

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* ── Page header ─────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <h1
            className="text-2xl font-bold text-slate-900"
            style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
          >
            {client.name}
          </h1>
          {client.industry && (
            <p className="mt-1 text-slate-500 text-sm flex items-center gap-1">
              <Building2 className="h-3.5 w-3.5" />
              {client.industry}
            </p>
          )}
        </div>

        <div className="flex gap-2">
          {editing ? (
            <>
              <button
                onClick={() => { setEditing(false); setEditValues(client) }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
              >
                <XIcon className="h-4 w-4" /> Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-800 transition-colors disabled:opacity-60"
              >
                <Check className="h-4 w-4" /> {saving ? 'Saving…' : 'Save'}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setEditing(true)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
              >
                <Pencil className="h-4 w-4" /> Edit
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-white px-3 py-1.5 text-sm text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-60"
              >
                <Trash2 className="h-4 w-4" /> {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {/* ── Client details card ─────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700">Client details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <Field label="Name">
            {editing ? (
              <Input
                value={editValues.name ?? ''}
                onChange={(e) => setEditValues((v) => ({ ...v, name: e.target.value }))}
              />
            ) : (
              <span>{client.name}</span>
            )}
          </Field>

          <Field label="Website">
            {editing ? (
              <Input
                value={editValues.website_url ?? ''}
                onChange={(e) => setEditValues((v) => ({ ...v, website_url: e.target.value }))}
                placeholder="https://example.com"
                type="url"
              />
            ) : client.website_url ? (
              <a
                href={client.website_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-700 hover:underline flex items-center gap-1"
              >
                <Globe className="h-3.5 w-3.5" />
                {client.website_url.replace(/^https?:\/\//, '')}
              </a>
            ) : (
              <span className="text-slate-400">—</span>
            )}
          </Field>

          <Field label="Industry">
            {editing ? (
              <Input
                value={editValues.industry ?? ''}
                onChange={(e) => setEditValues((v) => ({ ...v, industry: e.target.value }))}
                placeholder="e.g. E-commerce"
              />
            ) : (
              <span>{client.industry ?? <span className="text-slate-400">—</span>}</span>
            )}
          </Field>

          <Field label="Contact email">
            {editing ? (
              <Input
                value={editValues.primary_contact_email ?? ''}
                onChange={(e) =>
                  setEditValues((v) => ({ ...v, primary_contact_email: e.target.value }))
                }
                type="email"
                placeholder="jane@example.com"
              />
            ) : client.primary_contact_email ? (
              <a
                href={`mailto:${client.primary_contact_email}`}
                className="text-indigo-700 hover:underline flex items-center gap-1"
              >
                <Mail className="h-3.5 w-3.5" />
                {client.primary_contact_email}
              </a>
            ) : (
              <span className="text-slate-400">—</span>
            )}
          </Field>

          <Field label="Goals & context">
            {editing ? (
              <Textarea
                value={editValues.goals_context ?? ''}
                onChange={(e) => setEditValues((v) => ({ ...v, goals_context: e.target.value }))}
                placeholder="Goals, KPIs, context for AI reports…"
                rows={4}
              />
            ) : (
              <span className="whitespace-pre-wrap">
                {client.goals_context ?? <span className="text-slate-400">—</span>}
              </span>
            )}
          </Field>
        </CardContent>
      </Card>

      {/* ── Generate Report ─────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-600" />
            Generate Report
          </CardTitle>
        </CardHeader>
        <CardContent>
          {generating ? (
            <div className="flex flex-col items-center justify-center py-8 gap-3 text-center">
              <div className="h-10 w-10 rounded-full border-4 border-indigo-200 border-t-indigo-700 animate-spin" />
              <p className="font-semibold text-slate-700">Generating report…</p>
              <p className="text-sm text-slate-400 max-w-xs">
                AI is pulling data and writing your narrative insights. This takes 15–30 seconds.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-4">
                <div className="flex-1 min-w-[160px]">
                  <label className="block text-xs font-medium text-slate-500 mb-1.5">
                    Period start
                  </label>
                  <Input
                    type="date"
                    value={periodStart}
                    onChange={(e) => setPeriodStart(e.target.value)}
                  />
                </div>
                <div className="flex-1 min-w-[160px]">
                  <label className="block text-xs font-medium text-slate-500 mb-1.5">
                    Period end
                  </label>
                  <Input
                    type="date"
                    value={periodEnd}
                    onChange={(e) => setPeriodEnd(e.target.value)}
                  />
                </div>
              </div>

              {genError && (
                <p className="text-sm text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                  {genError}
                </p>
              )}

              <button
                onClick={handleGenerate}
                disabled={!periodStart || !periodEnd}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-50"
              >
                <Sparkles className="h-4 w-4" />
                Generate Report with AI
              </button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Report history ──────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700 flex items-center gap-2">
            <FileText className="h-4 w-4 text-slate-400" />
            Report History
          </CardTitle>
        </CardHeader>
        <CardContent>
          {reportsLoading ? (
            <div className="space-y-2">
              {[1, 2].map((i) => (
                <div key={i} className="h-12 rounded-lg bg-slate-100 animate-pulse" />
              ))}
            </div>
          ) : reports.length === 0 ? (
            <p className="text-sm text-slate-400 py-2">
              No reports generated yet. Use the form above to generate your first report.
            </p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {reports.map((report) => (
                <li key={report.id}>
                  <Link
                    href={`/dashboard/reports/${report.id}`}
                    className="flex items-center justify-between py-3 hover:bg-slate-50 -mx-2 px-2 rounded-lg transition-colors group"
                  >
                    <div className="flex items-start gap-3">
                      <FileText className="h-4 w-4 text-indigo-400 mt-0.5 shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-slate-800 group-hover:text-indigo-700 transition-colors">
                          {report.title}
                        </p>
                        <p className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                          <Calendar className="h-3 w-3" />
                          {report.period_start} → {report.period_end}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          report.status === 'draft' || report.status === 'approved'
                            ? 'bg-emerald-50 text-emerald-700'
                            : 'bg-slate-100 text-slate-500'
                        }`}
                      >
                        {report.status}
                      </span>
                      <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-slate-500 transition-colors" />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-4 items-start">
      <span className="text-sm font-medium text-slate-500 pt-1">{label}</span>
      <div className="col-span-2 text-sm text-slate-800">{children}</div>
    </div>
  )
}
