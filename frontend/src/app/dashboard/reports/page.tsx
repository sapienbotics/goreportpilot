'use client'

// All reports page — lists every report generated across all clients.

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { FileText, Calendar, Building2, ChevronRight, Download, Search, X as XIcon, MessageSquare } from 'lucide-react'
import { toast } from 'sonner'
import { reportsApi, commentsApi, downloadFileWithAuth } from '@/lib/api'
import type { Report } from '@/types'

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    ready:     'bg-emerald-50 text-emerald-700',
    generating:'bg-amber-50 text-amber-700',
    error:     'bg-rose-50 text-rose-600',
  }
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${styles[status] ?? 'bg-slate-100 text-slate-500'}`}>
      {status}
    </span>
  )
}

export default function ReportsPage() {
  const [reports, setReports]   = useState<Report[]>([])
  const [loading, setLoading]   = useState(true)
  const [error,   setError]     = useState<string | null>(null)
  const [dlId,    setDlId]      = useState<string | null>(null)
  const [unreadByReport, setUnreadByReport] = useState<Record<string, number>>({})

  // Filters
  const [filterSearch,  setFilterSearch]  = useState('')
  const [filterStatus,  setFilterStatus]  = useState('')
  const [filterClient,  setFilterClient]  = useState('')
  const [filterDateFrom, setFilterDateFrom] = useState('')
  const [filterDateTo,   setFilterDateTo]   = useState('')

  const clientOptions = useMemo(() => {
    const names = Array.from(new Set(reports.map(r => r.client_name).filter(Boolean))) as string[]
    return names.sort()
  }, [reports])

  const filtered = useMemo(() => {
    return reports.filter(r => {
      if (filterSearch  && !r.title.toLowerCase().includes(filterSearch.toLowerCase())) return false
      if (filterStatus  && r.status !== filterStatus) return false
      if (filterClient  && r.client_name !== filterClient) return false
      if (filterDateFrom && r.period_end < filterDateFrom) return false
      if (filterDateTo   && r.period_start > filterDateTo)  return false
      return true
    })
  }, [reports, filterSearch, filterStatus, filterClient, filterDateFrom, filterDateTo])

  const hasFilters = filterSearch || filterStatus || filterClient || filterDateFrom || filterDateTo
  const clearFilters = () => {
    setFilterSearch(''); setFilterStatus(''); setFilterClient('')
    setFilterDateFrom(''); setFilterDateTo('')
  }

  useEffect(() => {
    const fetch = async () => {
      try {
        const { reports: data } = await reportsApi.listAll()
        setReports(data)
      } catch {
        setError('Failed to load reports.')
      } finally {
        setLoading(false)
      }
    }
    fetch()
    commentsApi.unread()
      .then((res) => {
        const map: Record<string, number> = {}
        for (const row of res.by_report) map[row.report_id] = row.unresolved_count
        setUnreadByReport(map)
      })
      .catch(() => { /* non-fatal */ })
  }, [])

  const handleDownloadPdf = async (report: Report, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDlId(report.id)
    try {
      await downloadFileWithAuth(`/api/reports/${report.id}/download/pdf`, `${report.title}.pdf`)
    } catch {
      toast.error('Download failed. Please try again.')
    } finally {
      setDlId(null)
    }
  }

  // ── Loading ────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto space-y-3">
        <div className="h-8 w-48 rounded bg-slate-100 animate-pulse" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 rounded-xl bg-slate-100 animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1
          className="text-2xl font-bold text-slate-900"
          style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
        >
          All Reports
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          {filtered.length !== reports.length
            ? `${filtered.length} of ${reports.length} report${reports.length !== 1 ? 's' : ''}`
            : `${reports.length} report${reports.length !== 1 ? 's' : ''} generated`}
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {/* Empty state */}
      {reports.length === 0 && !error && (
        <div className="rounded-xl border border-slate-100 bg-white p-12 text-center shadow-sm">
          <FileText className="mx-auto h-10 w-10 text-slate-200 mb-4" />
          <p className="text-slate-500 font-medium">No reports generated yet.</p>
          <p className="text-slate-400 text-sm mt-1">
            Go to a client page to generate your first report.
          </p>
          <Link
            href="/dashboard/clients"
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors"
          >
            View Clients
          </Link>
        </div>
      )}

      {/* Filter bar */}
      {reports.length > 0 && (
        <div className="mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-3">
          <div className="flex flex-wrap gap-2">
            {/* Search */}
            <div className="relative flex-1 min-w-[180px]">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
              <input
                type="text"
                value={filterSearch}
                onChange={e => setFilterSearch(e.target.value)}
                placeholder="Search reports…"
                className="w-full rounded-md border border-slate-200 bg-white pl-8 pr-3 py-1.5 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            {/* Status */}
            <select
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value)}
              className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All statuses</option>
              <option value="draft">Draft</option>
              <option value="approved">Approved</option>
              <option value="generating">Generating</option>
              <option value="sent">Sent</option>
              <option value="failed">Failed</option>
            </select>
            {/* Client */}
            {clientOptions.length > 0 && (
              <select
                value={filterClient}
                onChange={e => setFilterClient(e.target.value)}
                className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All clients</option>
                {clientOptions.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            )}
            {/* Clear */}
            {hasFilters && (
              <button
                onClick={clearFilters}
                className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-500 hover:bg-slate-50 transition-colors"
              >
                <XIcon className="h-3 w-3" />
                Clear filters
              </button>
            )}
          </div>
          {/* Date range */}
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-xs text-slate-400">Period:</span>
            <input
              type="date"
              value={filterDateFrom}
              onChange={e => setFilterDateFrom(e.target.value)}
              className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <span className="text-xs text-slate-400">to</span>
            <input
              type="date"
              value={filterDateTo}
              onChange={e => setFilterDateTo(e.target.value)}
              className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
      )}

      {/* Reports table */}
      {reports.length > 0 && (
        <div className="rounded-xl border border-slate-100 bg-white shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/70">
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wide">
                  Report
                </th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wide hidden sm:table-cell">
                  Client
                </th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wide hidden md:table-cell">
                  Period
                </th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wide">
                  Status
                </th>
                <th className="py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wide text-right">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-10 text-center">
                    <p className="text-sm text-slate-400">No reports match your filters.</p>
                    <button onClick={clearFilters} className="mt-1.5 text-xs text-indigo-600 hover:underline">
                      Clear filters
                    </button>
                  </td>
                </tr>
              )}
              {filtered.map((report) => {
                const unread = unreadByReport[report.id] ?? 0
                return (
                <tr
                  key={report.id}
                  className="hover:bg-slate-50/60 transition-colors group"
                >
                  {/* Report title */}
                  <td className="py-3.5 px-4">
                    <Link
                      href={`/dashboard/reports/${report.id}`}
                      className="flex items-center gap-2.5"
                    >
                      <FileText className="h-4 w-4 text-indigo-400 shrink-0" />
                      <span className="font-medium text-slate-800 group-hover:text-indigo-700 transition-colors line-clamp-1">
                        {report.title}
                      </span>
                      {unread > 0 && (
                        <span
                          className="inline-flex items-center gap-1 rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-[11px] font-semibold text-rose-600 shrink-0"
                          title={`${unread} unresolved comment${unread === 1 ? '' : 's'}`}
                        >
                          <MessageSquare className="h-3 w-3" />
                          {unread}
                        </span>
                      )}
                    </Link>
                  </td>

                  {/* Client name */}
                  <td className="py-3.5 px-4 text-slate-500 hidden sm:table-cell">
                    {report.client_name ? (
                      <span className="flex items-center gap-1.5">
                        <Building2 className="h-3.5 w-3.5 text-slate-300" />
                        {report.client_name}
                      </span>
                    ) : (
                      <span className="text-slate-300">—</span>
                    )}
                  </td>

                  {/* Period */}
                  <td className="py-3.5 px-4 text-slate-400 hidden md:table-cell">
                    <span className="flex items-center gap-1.5">
                      <Calendar className="h-3.5 w-3.5 text-slate-300" />
                      {report.period_start} → {report.period_end}
                    </span>
                  </td>

                  {/* Status */}
                  <td className="py-3.5 px-4">
                    <StatusBadge status={report.status} />
                  </td>

                  {/* Actions */}
                  <td className="py-3.5 px-4">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={(e) => handleDownloadPdf(report, e)}
                        disabled={dlId === report.id}
                        title="Download PDF"
                        className="rounded-md p-1.5 text-slate-400 hover:text-indigo-700 hover:bg-indigo-50 transition-colors disabled:opacity-40"
                      >
                        <Download className="h-4 w-4" />
                      </button>
                      <Link
                        href={`/dashboard/reports/${report.id}`}
                        className="rounded-md p-1.5 text-slate-400 hover:text-indigo-700 hover:bg-indigo-50 transition-colors"
                        title="View report"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Link>
                    </div>
                  </td>
                </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
