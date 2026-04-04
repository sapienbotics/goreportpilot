'use client'

import { useState, useRef, useCallback } from 'react'
import { Upload, X, Download, FileText, Check, AlertCircle, ChevronDown, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import api from '@/lib/api'

export interface CSVMetric {
  name: string
  current_value: number
  previous_value: number | null
  unit: string
  change: number | null
}

export interface ParsedCSV {
  sourceName: string
  fileName: string
  metrics: CSVMetric[]
}

interface Props {
  onAdd: (csv: ParsedCSV) => void
  onClose: () => void
}

const MAX_FILE_SIZE = 1 * 1024 * 1024 // 1 MB

const CSV_TEMPLATES = [
  { label: 'LinkedIn Ads',  name: 'linkedin_ads' },
  { label: 'TikTok Ads',    name: 'tiktok_ads' },
  { label: 'Mailchimp',     name: 'mailchimp' },
  { label: 'Shopify',       name: 'shopify' },
  { label: 'Generic',       name: 'generic' },
]

export default function CSVUploadForReport({ onAdd, onClose }: Props) {
  const [file,          setFile]          = useState<File | null>(null)
  const [parsing,       setParsing]       = useState(false)
  const [parsed,        setParsed]        = useState<{ source_name: string; metrics: CSVMetric[] } | null>(null)
  const [sourceName,    setSourceName]    = useState('')
  const [error,         setError]         = useState<string | null>(null)
  const [dragging,      setDragging]      = useState(false)
  const [templateMenu,  setTemplateMenu]  = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  function validateFile(f: File): string | null {
    if (!f.name.toLowerCase().endsWith('.csv')) return 'Only .csv files are accepted.'
    if (f.size > MAX_FILE_SIZE) return 'File must be smaller than 1 MB.'
    return null
  }

  async function parseFile(f: File) {
    const err = validateFile(f)
    if (err) { setError(err); return }

    setFile(f)
    setError(null)
    setParsing(true)
    setParsed(null)

    try {
      const form = new FormData()
      form.append('file', f)
      const res = await api.post<{ source_name: string; metrics: CSVMetric[] }>(
        '/api/connections/csv-parse',
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
      setParsed(res.data)
      setSourceName(res.data.source_name)
    } catch (e: unknown) {
      // Extract the most specific error message available from the response.
      // Priority: backend detail → backend message → HTTP status hint → network error → fallback.
      const err = e as {
        response?: { status?: number; data?: { detail?: string; message?: string } }
        message?: string
        code?: string
      }
      let detail: string
      if (err?.response?.data?.detail) {
        detail = err.response.data.detail
      } else if (err?.response?.data?.message) {
        detail = err.response.data.message
      } else if (err?.response?.status === 413) {
        detail = 'File too large. Please upload a file smaller than 1 MB.'
      } else if (err?.response?.status === 415) {
        detail = 'Unsupported file type. Please upload a .csv file.'
      } else if (err?.response?.status === 422) {
        detail = 'Invalid file or request format. Please check the file and try again.'
      } else if (err?.code === 'ERR_NETWORK' || err?.message?.toLowerCase().includes('network')) {
        detail = 'Network error — could not reach the server. Please check your connection and try again.'
      } else {
        detail = 'Failed to parse CSV. Please check the file format and try again.'
      }
      setError(detail)
      setFile(null)
    } finally {
      setParsing(false)
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) parseFile(f)
    e.target.value = ''
  }

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f) parseFile(f)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function handleReset() {
    setFile(null); setParsed(null); setSourceName(''); setError(null)
  }

  function handleAdd() {
    if (!parsed || !sourceName.trim() || !file) return
    onAdd({
      sourceName: sourceName.trim(),
      fileName:   file.name,
      metrics:    parsed.metrics,
    })
    onClose()
  }

  const formatChange = (c: number | null) => {
    if (c === null) return '—'
    return `${c > 0 ? '+' : ''}${c.toFixed(1)}%`
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="relative flex w-full max-w-xl flex-col gap-0 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-indigo-600" />
            <h2 className="text-base font-semibold text-slate-900">Add CSV Data Source</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex flex-col gap-4 overflow-y-auto px-5 py-5 max-h-[70vh]">
          <p className="text-sm text-slate-500">
            Upload metrics for platforms not directly integrated — LinkedIn Ads, TikTok, Shopify, Mailchimp, etc. The data will be included in this report only.
          </p>

          {/* Drop zone */}
          {!parsed && !parsing && (
            <div
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                'flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors',
                dragging
                  ? 'border-indigo-500 bg-indigo-50'
                  : 'border-slate-300 bg-slate-50 hover:border-indigo-400 hover:bg-indigo-50/50'
              )}
            >
              <Upload className={cn('h-8 w-8 transition-colors', dragging ? 'text-indigo-600' : 'text-slate-400')} />
              <div>
                <p className="text-sm font-medium text-slate-700">
                  {dragging ? 'Drop your CSV here' : 'Drag & drop your CSV file'}
                </p>
                <p className="mt-1 text-xs text-slate-500">or click to browse — max 1 MB</p>
              </div>
              <input ref={fileInputRef} type="file" accept=".csv" onChange={handleFileInput} className="hidden" />
            </div>
          )}

          {/* Parsing spinner */}
          {parsing && (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
              Parsing file…
            </div>
          )}

          {/* Preview */}
          {parsed && !parsing && (
            <>
              {/* Source name */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-slate-700">Source Name</label>
                <input
                  type="text"
                  value={sourceName}
                  onChange={(e) => setSourceName(e.target.value)}
                  placeholder="e.g. LinkedIn Ads Q1"
                  className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 transition-colors"
                />
              </div>

              {/* Metrics preview table */}
              <div className="rounded-lg border border-slate-200 overflow-hidden">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200">
                      <th className="text-left px-3 py-2 font-semibold text-slate-500">Metric</th>
                      <th className="text-right px-3 py-2 font-semibold text-slate-500">Value</th>
                      <th className="text-right px-3 py-2 font-semibold text-slate-500">Change</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {parsed.metrics.map((m, i) => (
                      <tr key={i} className="hover:bg-slate-50">
                        <td className="px-3 py-2 text-slate-700 font-medium">{m.name}</td>
                        <td className="px-3 py-2 text-slate-700 text-right">
                          {m.unit && !['%', '$', '€', '£', '₹'].includes(m.unit)
                            ? `${m.current_value.toLocaleString()} ${m.unit}`
                            : ['%'].includes(m.unit)
                            ? `${m.current_value}%`
                            : m.current_value.toLocaleString()}
                        </td>
                        <td className={cn(
                          'px-3 py-2 text-right font-medium',
                          m.change === null ? 'text-slate-400'
                            : m.change > 0   ? 'text-emerald-600'
                            : m.change < 0   ? 'text-rose-500'
                            : 'text-slate-400'
                        )}>
                          {formatChange(m.change)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="px-3 py-1.5 bg-slate-50 border-t border-slate-200 text-[11px] text-slate-400">
                  {parsed.metrics.length} metric{parsed.metrics.length !== 1 ? 's' : ''} · {file?.name}
                </div>
              </div>

              {/* File info + reset */}
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-rose-500 transition-colors self-start"
              >
                <X className="h-3.5 w-3.5" /> Remove file, upload a different one
              </button>

              {/* Success indicator */}
              <div className="flex items-center gap-1.5 text-xs text-emerald-600">
                <Check className="h-3.5 w-3.5" /> File parsed successfully
              </div>
            </>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 rounded-md border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm text-rose-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-200 px-5 py-4">
          {/* Template downloads */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setTemplateMenu((v) => !v)}
              className="flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-600 shadow-sm hover:bg-slate-50 transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              Download Templates
              <ChevronDown className="h-3.5 w-3.5" />
            </button>
            {templateMenu && (
              <div
                className="absolute bottom-full left-0 mb-1.5 w-48 rounded-md border border-slate-200 bg-white py-1 shadow-md z-10"
                onMouseLeave={() => setTemplateMenu(false)}
              >
                {CSV_TEMPLATES.map((t) => (
                  <a
                    key={t.name}
                    href={`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/connections/csv-templates/${t.name}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block px-3 py-2 text-xs text-slate-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
                    onClick={() => setTemplateMenu(false)}
                  >
                    {t.label}
                  </a>
                ))}
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="rounded-md px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={!parsed || !sourceName.trim()}
              className={cn(
                'flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium text-white shadow-sm',
                'bg-indigo-600 hover:bg-indigo-700 transition-colors',
                (!parsed || !sourceName.trim()) && 'cursor-not-allowed opacity-50'
              )}
            >
              <Check className="h-4 w-4" />
              Add to Report
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
