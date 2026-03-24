'use client'

import { useState, useRef, useCallback } from 'react'
import { Upload, X, Download, FileText, Check, AlertCircle, ChevronDown } from 'lucide-react'
import { Card } from '@/components/ui/card'
import CSVPreviewTable from './CSVPreviewTable'
import { cn } from '@/lib/utils'
import api from '@/lib/api'

interface CSVMetric {
  name: string
  current_value: number | null
  previous_value: number | null
  change: number | null
  unit: string
}

interface PreviewData {
  source_name: string
  metrics: CSVMetric[]
}

interface Props {
  clientId: string
  onSuccess: (connection: { source_name: string; metric_count: number }) => void
  onClose: () => void
}

const MAX_FILE_SIZE = 1 * 1024 * 1024 // 1 MB

const CSV_TEMPLATES = [
  { label: 'LinkedIn Ads', name: 'linkedin_ads' },
  { label: 'TikTok Ads', name: 'tiktok_ads' },
  { label: 'Mailchimp', name: 'mailchimp' },
  { label: 'Shopify', name: 'shopify' },
  { label: 'Generic', name: 'generic' },
]

export default function CSVUploadDialog({ clientId, onSuccess, onClose }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [previewing, setPreviewing] = useState(false)
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [sourceName, setSourceName] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [templateMenuOpen, setTemplateMenuOpen] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  function validateFile(f: File): string | null {
    if (!f.name.endsWith('.csv')) return 'Only .csv files are accepted.'
    if (f.size > MAX_FILE_SIZE) return 'File must be smaller than 1 MB.'
    return null
  }

  async function parseFile(f: File) {
    const validationError = validateFile(f)
    if (validationError) {
      setError(validationError)
      return
    }

    setFile(f)
    setError(null)
    setPreviewing(true)
    setPreviewData(null)

    try {
      const form = new FormData()
      form.append('file', f)
      form.append('client_id', clientId)

      const res = await api.post<PreviewData>('/api/connections/csv-preview', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setPreviewData(res.data)
      setSourceName(res.data.source_name)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to parse CSV. Please check the file format.'
      setError(msg)
      setFile(null)
    } finally {
      setPreviewing(false)
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

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragging(true)
  }

  const handleDragLeave = () => setDragging(false)

  async function handleUpload() {
    if (!file || !previewData) return
    setUploading(true)
    setError(null)

    try {
      const form = new FormData()
      form.append('file', file)
      form.append('client_id', clientId)
      form.append('source_name', sourceName)

      await api.post('/api/connections/csv-upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      setSuccess(true)
      onSuccess({ source_name: sourceName, metric_count: previewData.metrics.length })
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Upload failed. Please try again.'
      setError(msg)
    } finally {
      setUploading(false)
    }
  }

  function handleReset() {
    setFile(null)
    setPreviewData(null)
    setSourceName('')
    setError(null)
    setSuccess(false)
    setPreviewing(false)
  }

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <Card className="relative flex w-full max-w-xl flex-col gap-0 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-indigo-600" />
            <h2 className="text-base font-semibold text-slate-900">Upload CSV Data</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex flex-col gap-4 overflow-y-auto px-5 py-5 max-h-[70vh]">
          {/* Success state */}
          {success ? (
            <div className="flex flex-col items-center gap-3 py-8">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50">
                <Check className="h-7 w-7 text-emerald-600" />
              </div>
              <p className="text-base font-semibold text-slate-900">Connected successfully!</p>
              <p className="text-sm text-slate-500">
                <span className="font-medium text-slate-700">{sourceName}</span> has been added as a
                data source.
              </p>
              <button
                onClick={onClose}
                className="mt-2 rounded-md bg-indigo-600 px-5 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 transition-colors"
              >
                Done
              </button>
            </div>
          ) : (
            <>
              {/* Drop zone */}
              {!previewData && (
                <div
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onClick={() => fileInputRef.current?.click()}
                  className={cn(
                    'flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors duration-150',
                    dragging
                      ? 'border-indigo-500 bg-indigo-50'
                      : 'border-slate-300 bg-slate-50 hover:border-indigo-400 hover:bg-indigo-50/50'
                  )}
                >
                  <Upload
                    className={cn(
                      'h-8 w-8 transition-colors',
                      dragging ? 'text-indigo-600' : 'text-slate-400'
                    )}
                  />
                  <div>
                    <p className="text-sm font-medium text-slate-700">
                      {dragging ? 'Drop your CSV here' : 'Drag & drop your CSV file'}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">or click to browse — max 1 MB</p>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv"
                    onChange={handleFileInput}
                    className="hidden"
                  />
                </div>
              )}

              {/* Parsing spinner */}
              {previewing && (
                <div className="flex items-center justify-center gap-2 py-4 text-sm text-slate-500">
                  <svg
                    className="h-4 w-4 animate-spin text-indigo-600"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8v8H4z"
                    />
                  </svg>
                  Parsing file…
                </div>
              )}

              {/* Preview */}
              {previewData && !previewing && (
                <>
                  <CSVPreviewTable metrics={previewData.metrics} sourceName={sourceName} />

                  {/* Source name input */}
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

                  {/* File info + reset */}
                  <div className="flex items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
                    <FileText className="h-3.5 w-3.5 shrink-0 text-indigo-500" />
                    <span className="truncate font-medium text-slate-700">{file?.name}</span>
                    <span className="ml-auto shrink-0">
                      {((file?.size ?? 0) / 1024).toFixed(1)} KB
                    </span>
                    <button
                      onClick={handleReset}
                      className="ml-1 shrink-0 text-slate-400 hover:text-rose-500 focus:outline-none transition-colors"
                      title="Remove file"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
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
            </>
          )}
        </div>

        {/* Footer */}
        {!success && (
          <div className="flex items-center justify-between border-t border-slate-200 px-5 py-4">
            {/* Download templates dropdown */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setTemplateMenuOpen((v) => !v)}
                className="flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-600 shadow-sm hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 transition-colors"
              >
                <Download className="h-3.5 w-3.5" />
                Download Templates
                <ChevronDown className="h-3.5 w-3.5" />
              </button>

              {templateMenuOpen && (
                <div
                  className="absolute bottom-full left-0 mb-1.5 w-48 rounded-md border border-slate-200 bg-white py-1 shadow-md"
                  onMouseLeave={() => setTemplateMenuOpen(false)}
                >
                  {CSV_TEMPLATES.map((t) => (
                    <a
                      key={t.name}
                      href={`/api/connections/csv-templates/${t.name}`}
                      download
                      className="block px-3 py-2 text-xs text-slate-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
                      onClick={() => setTemplateMenuOpen(false)}
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
                className="rounded-md px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={!previewData || uploading || !sourceName.trim()}
                className={cn(
                  'flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium text-white shadow-sm',
                  'bg-indigo-600 hover:bg-indigo-700',
                  'focus:outline-none focus:ring-2 focus:ring-indigo-500/40',
                  'transition-colors duration-150',
                  (!previewData || uploading || !sourceName.trim()) &&
                    'cursor-not-allowed opacity-50'
                )}
              >
                {uploading && (
                  <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                )}
                {uploading ? 'Uploading…' : 'Upload & Connect'}
              </button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
