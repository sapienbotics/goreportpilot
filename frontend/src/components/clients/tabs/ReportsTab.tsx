'use client'
import { useEffect, useState, useMemo } from 'react'
import Link from 'next/link'
import {
  FileText, Sparkles, Calendar, ChevronRight, Settings2,
  Check, Loader2, Image as ImageIcon, Search, X as XIcon, Upload, Lock,
  MessageSquare,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { usePlanFeatures } from '@/hooks/usePlanFeatures'
import RichTextEditor from '@/components/clients/RichTextEditor'
import CSVUploadForReport, { type ParsedCSV } from '@/components/reports/CSVUploadForReport'
import { commentsApi } from '@/lib/api'
import type { Report, ReportConfig } from '@/types'

type TemplateValue = 'full' | 'summary' | 'brief'

interface Props {
  clientId: string
  reports: Report[]
  reportsLoading: boolean
  periodStart: string
  periodEnd: string
  setPeriodStart: (v: string) => void
  setPeriodEnd: (v: string) => void
  selectedTemplate: TemplateValue
  setSelectedTemplate: (v: TemplateValue) => void
  generating: boolean
  genError: string | null
  reportConfig: ReportConfig
  setReportConfig: React.Dispatch<React.SetStateAction<ReportConfig>>
  savingConfig: boolean
  configSaved: boolean
  customImgInputRef: React.RefObject<HTMLInputElement>
  customImgUploading: boolean
  csvFiles: ParsedCSV[]
  setCsvFiles: React.Dispatch<React.SetStateAction<ParsedCSV[]>>
  handleGenerate: () => void
  handleSaveConfig: () => void
  handleCustomSectionImageUpload: (e: React.ChangeEvent<HTMLInputElement>) => void
}

export default function ReportsTab({
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  clientId, reports, reportsLoading,
  periodStart, periodEnd, setPeriodStart, setPeriodEnd,
  selectedTemplate, setSelectedTemplate,
  generating, genError,
  reportConfig, setReportConfig,
  savingConfig, configSaved,
  customImgInputRef, customImgUploading,
  csvFiles, setCsvFiles,
  handleGenerate, handleSaveConfig, handleCustomSectionImageUpload,
}: Props) {
  const { status: subStatus, trialReportsUsed, trialReportsLimit } = usePlanFeatures()
  const isExpired = subStatus === 'expired' || subStatus === 'cancelled'
  const isTrialing = subStatus === 'trialing'
  const trialLimitReached = isTrialing && trialReportsUsed >= trialReportsLimit
  const [showCsvUpload, setShowCsvUpload] = useState(false)

  function removeCsv(index: number) {
    setCsvFiles(prev => prev.filter((_, i) => i !== index))
  }
  const [historySearch,     setHistorySearch]     = useState('')
  const [historyStatus,     setHistoryStatus]     = useState<'all' | 'draft' | 'approved' | 'generating' | 'sent' | 'failed'>('all')
  const [historyDateFrom,   setHistoryDateFrom]   = useState('')
  const [historyDateTo,     setHistoryDateTo]     = useState('')

  // Unread-comment counts per report — loaded once, merged into each row.
  const [unreadByReport, setUnreadByReport] = useState<Record<string, number>>({})
  useEffect(() => {
    commentsApi.unread()
      .then((res) => {
        const map: Record<string, number> = {}
        for (const row of res.by_report) map[row.report_id] = row.unresolved_count
        setUnreadByReport(map)
      })
      .catch(() => { /* non-fatal */ })
  }, [])

  const filteredReports = useMemo(() => {
    return reports.filter(r => {
      if (historySearch && !r.title.toLowerCase().includes(historySearch.toLowerCase())) return false
      if (historyStatus !== 'all' && r.status !== historyStatus) return false
      if (historyDateFrom && r.period_end < historyDateFrom) return false
      if (historyDateTo   && r.period_start > historyDateTo)  return false
      return true
    })
  }, [reports, historySearch, historyStatus, historyDateFrom, historyDateTo])

  const clearFilters = () => {
    setHistorySearch('')
    setHistoryStatus('all')
    setHistoryDateFrom('')
    setHistoryDateTo('')
  }

  const hasFilters = historySearch || historyStatus !== 'all' || historyDateFrom || historyDateTo

  return (
    <div className="space-y-6">
      {/* Generate Report */}
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
              <p className="text-sm text-slate-400 max-w-xs">AI is pulling data and writing your narrative insights. This takes 15–30 seconds.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Detail level */}
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-2">Detail level</label>
                <div className="flex flex-wrap gap-2">
                  {([
                    { value: 'full' as const, label: 'Full Report', desc: '8 slides · complete analysis' },
                    { value: 'summary' as const, label: 'Summary', desc: '4 slides · KPIs + highlights' },
                    { value: 'brief' as const, label: 'One-Page Brief', desc: '2 slides · numbers + summary' },
                  ]).map(opt => (
                    <button key={opt.value} onClick={() => setSelectedTemplate(opt.value)}
                      className={`flex flex-col items-start px-4 py-2.5 rounded-lg border text-left transition-colors ${selectedTemplate === opt.value ? 'bg-indigo-700 border-indigo-700 text-white' : 'bg-white border-slate-200 text-slate-700 hover:border-indigo-300 hover:bg-indigo-50'}`}>
                      <span className="text-sm font-semibold">{opt.label}</span>
                      <span className={`text-xs mt-0.5 ${selectedTemplate === opt.value ? 'text-indigo-200' : 'text-slate-400'}`}>{opt.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Visual style moved to Design tab — theme is per-client now. */}

              {/* Date range */}
              <div className="flex flex-wrap gap-4">
                <div className="flex-1 min-w-[160px]">
                  <label className="block text-xs font-medium text-slate-500 mb-1.5">Period start</label>
                  <Input type="date" value={periodStart} onChange={e => setPeriodStart(e.target.value)} />
                </div>
                <div className="flex-1 min-w-[160px]">
                  <label className="block text-xs font-medium text-slate-500 mb-1.5">Period end</label>
                  <Input type="date" value={periodEnd} onChange={e => setPeriodEnd(e.target.value)} />
                </div>
              </div>

              {/* CSV Data Sources */}
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                  Additional Data Sources <span className="normal-case font-normal">(optional)</span>
                </label>
                <p className="text-xs text-slate-400 mb-2">
                  Upload CSVs for platforms not directly integrated — LinkedIn Ads, TikTok, Shopify, Mailchimp, etc.
                </p>
                {csvFiles.length > 0 && (
                  <ul className="mb-2 space-y-1.5">
                    {csvFiles.map((csv, i) => (
                      <li key={i} className="flex items-center justify-between rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText className="h-3.5 w-3.5 text-indigo-500 shrink-0" />
                          <span className="text-sm font-medium text-slate-800 truncate">{csv.sourceName}</span>
                          <span className="text-xs text-slate-400 shrink-0">{csv.metrics.length} metrics</span>
                        </div>
                        <button
                          onClick={() => removeCsv(i)}
                          className="ml-2 text-slate-400 hover:text-rose-500 transition-colors"
                          title="Remove"
                        >
                          <XIcon className="h-3.5 w-3.5" />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                <button
                  type="button"
                  onClick={() => setShowCsvUpload(true)}
                  className="flex items-center justify-center gap-2 w-full rounded-lg border border-dashed border-slate-300 px-3 py-2 text-sm text-slate-500 hover:border-indigo-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                >
                  <Upload className="h-4 w-4" />
                  {csvFiles.length === 0 ? 'Add CSV Data Source' : 'Add Another CSV'}
                </button>
              </div>

              {genError && <p className="text-sm text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">{genError}</p>}

              {isExpired ? (
                <div className="rounded-lg bg-rose-50 border border-rose-200 px-4 py-3 text-sm text-rose-700 flex items-center gap-2">
                  <Lock className="h-4 w-4 shrink-0" />
                  Trial expired — <a href="/dashboard/billing" className="font-semibold underline hover:text-rose-800">upgrade to generate reports</a>
                </div>
              ) : trialLimitReached ? (
                <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-700 flex items-center gap-2">
                  <Lock className="h-4 w-4 shrink-0" />
                  You&apos;ve used all {trialReportsLimit} trial reports — <a href="/dashboard/billing" className="font-semibold underline hover:text-amber-800">upgrade for unlimited reports</a>
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <button onClick={handleGenerate} disabled={!periodStart || !periodEnd}
                    className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-50">
                    <Sparkles className="h-4 w-4" />
                    Generate Report with AI
                  </button>
                  {isTrialing && (
                    <span className="text-xs text-slate-400">
                      {trialReportsUsed}/{trialReportsLimit} trial reports used
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Report Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700 flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-slate-400" />
            Report Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Default detail level for scheduled reports</label>
            <select value={reportConfig.template}
              onChange={e => setReportConfig(c => ({ ...c, template: e.target.value as ReportConfig['template'] }))}
              className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="full">Full Report — 8 slides, complete analysis</option>
              <option value="summary">Summary — 4 slides, KPIs + highlights</option>
              <option value="brief">One-Page Brief — 2 slides, numbers + summary</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Sections</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {(Object.keys(reportConfig.sections) as Array<keyof ReportConfig['sections']>).map(key => (
                <label key={key} className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={reportConfig.sections[key]}
                    onChange={e => setReportConfig(c => ({ ...c, sections: { ...c.sections, [key]: e.target.checked } }))}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                  <span className="text-sm text-slate-700 capitalize">{key.replace(/_/g, ' ')}</span>
                </label>
              ))}
            </div>
          </div>

          {reportConfig.sections.custom_section && (
            <div className="space-y-3 rounded-lg border border-indigo-100 bg-indigo-50 p-4">
              <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide">Custom Section</p>
              <Input value={reportConfig.custom_section_title}
                onChange={e => setReportConfig(c => ({ ...c, custom_section_title: e.target.value }))}
                placeholder="Section title…" />
              <RichTextEditor value={reportConfig.custom_section_text}
                onChange={val => setReportConfig(c => ({ ...c, custom_section_text: val }))}
                placeholder="Write your custom commentary — use **bold**, ## headings, - bullets, 1. numbered lists…"
                rows={6} />
              <div className="flex items-center gap-3">
                {reportConfig.custom_section_image_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={reportConfig.custom_section_image_url} alt="Custom section" className="h-16 w-24 object-cover rounded-md border border-indigo-200" />
                )}
                <div>
                  <button type="button" onClick={() => customImgInputRef.current?.click()} disabled={customImgUploading}
                    className="inline-flex items-center gap-1.5 rounded-md border border-indigo-200 bg-white px-3 py-1.5 text-xs text-indigo-700 hover:bg-indigo-50 transition-colors disabled:opacity-60">
                    {customImgUploading ? <Loader2 className="h-3 w-3 animate-spin" /> : <ImageIcon className="h-3 w-3" />}
                    {customImgUploading ? 'Uploading…' : reportConfig.custom_section_image_url ? 'Replace image' : 'Add image'}
                  </button>
                  {reportConfig.custom_section_image_url && (
                    <button type="button" onClick={() => setReportConfig(c => ({ ...c, custom_section_image_url: undefined }))}
                      className="ml-2 text-xs text-rose-500 hover:text-rose-700">Remove</button>
                  )}
                  <p className="mt-1 text-[11px] text-slate-400">PNG / JPEG / WebP · max 5 MB · shown on slide right</p>
                </div>
                <input ref={customImgInputRef} type="file" accept="image/png,image/jpeg,image/webp"
                  onChange={handleCustomSectionImageUpload} className="hidden" />
              </div>
            </div>
          )}

          <div className="flex items-center gap-3">
            <button onClick={handleSaveConfig} disabled={savingConfig}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-60">
              {savingConfig ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              {savingConfig ? 'Saving…' : 'Save Configuration'}
            </button>
            {configSaved && <span className="text-sm text-emerald-600 font-medium">✓ Saved</span>}
          </div>
        </CardContent>
      </Card>

      {/* Report History */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700 flex items-center gap-2">
            <FileText className="h-4 w-4 text-slate-400" />
            Report History
            {reports.length > 0 && (
              <span className="ml-1 text-xs font-normal text-slate-400">({reports.length})</span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {/* Filter bar */}
          {!reportsLoading && reports.length > 0 && (
            <div className="mb-4 space-y-2">
              <div className="flex flex-wrap gap-2">
                {/* Search */}
                <div className="relative flex-1 min-w-[160px]">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                  <input
                    type="text"
                    value={historySearch}
                    onChange={e => setHistorySearch(e.target.value)}
                    placeholder="Search reports…"
                    className="w-full rounded-md border border-slate-200 bg-white pl-8 pr-3 py-1.5 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                {/* Status filter */}
                <select
                  value={historyStatus}
                  onChange={e => setHistoryStatus(e.target.value as typeof historyStatus)}
                  className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="all">All statuses</option>
                  <option value="draft">Draft</option>
                  <option value="approved">Approved</option>
                  <option value="generating">Generating</option>
                  <option value="sent">Sent</option>
                  <option value="failed">Failed</option>
                </select>
                {/* Clear */}
                {hasFilters && (
                  <button
                    onClick={clearFilters}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-500 hover:bg-slate-50 transition-colors"
                  >
                    <XIcon className="h-3 w-3" />
                    Clear
                  </button>
                )}
              </div>
              {/* Date range row */}
              <div className="flex flex-wrap gap-2 items-center">
                <span className="text-xs text-slate-400">Period:</span>
                <input
                  type="date"
                  value={historyDateFrom}
                  onChange={e => setHistoryDateFrom(e.target.value)}
                  className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <span className="text-xs text-slate-400">to</span>
                <input
                  type="date"
                  value={historyDateTo}
                  onChange={e => setHistoryDateTo(e.target.value)}
                  className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
          )}

          {reportsLoading ? (
            <div className="space-y-2">
              {[1,2].map(i => <div key={i} className="h-12 rounded-lg bg-slate-100 animate-pulse" />)}
            </div>
          ) : reports.length === 0 ? (
            <p className="text-sm text-slate-400 py-2">No reports generated yet. Use the form above to generate your first report.</p>
          ) : filteredReports.length === 0 ? (
            <div className="py-6 text-center">
              <p className="text-sm text-slate-400">No reports match your filters.</p>
              <button onClick={clearFilters} className="mt-2 text-xs text-indigo-600 hover:underline">Clear filters</button>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {filteredReports.map(report => {
                const unread = unreadByReport[report.id] ?? 0
                return (
                  <li key={report.id}>
                    <Link href={`/dashboard/reports/${report.id}`} className="flex items-center justify-between py-3 hover:bg-slate-50 -mx-2 px-2 rounded-lg transition-colors group">
                      <div className="flex items-start gap-3">
                        <FileText className="h-4 w-4 text-indigo-400 mt-0.5 shrink-0" />
                        <div>
                          <p className="text-sm font-medium text-slate-800 group-hover:text-indigo-700 transition-colors">{report.title}</p>
                          <p className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                            <Calendar className="h-3 w-3" />
                            {report.period_start} → {report.period_end}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {unread > 0 && (
                          <span
                            className="inline-flex items-center gap-1 rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-[11px] font-semibold text-rose-600"
                            title={`${unread} unresolved comment${unread === 1 ? '' : 's'}`}
                          >
                            <MessageSquare className="h-3 w-3" />
                            {unread}
                          </span>
                        )}
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          report.status === 'draft' || report.status === 'approved'
                            ? 'bg-emerald-50 text-emerald-700'
                            : report.status === 'generating'
                            ? 'bg-amber-50 text-amber-700'
                            : report.status === 'failed'
                            ? 'bg-rose-50 text-rose-600'
                            : 'bg-slate-100 text-slate-500'
                        }`}>
                          {report.status}
                        </span>
                        <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-slate-500 transition-colors" />
                      </div>
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* CSV Upload Modal */}
      {showCsvUpload && (
        <CSVUploadForReport
          onAdd={(csv) => setCsvFiles(prev => [...prev, csv])}
          onClose={() => setShowCsvUpload(false)}
        />
      )}
    </div>
  )
}
