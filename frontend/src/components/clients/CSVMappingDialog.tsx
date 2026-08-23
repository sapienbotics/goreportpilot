'use client'

/**
 * Universal CSV/XLSX upload with AI column mapping.
 *
 * Three states: drop zone -> mapping confirmation -> done.
 *
 * The rule the whole screen is built around: a mapping the AI is not confident
 * about is never accepted silently. Low-confidence rows are highlighted, and
 * Confirm stays disabled until every one of them has been resolved. The user
 * also sees the first rows parsed exactly as they will be read, so a wrong
 * locale reading ("1.234" as 1.234 rather than 1,234) is caught here rather
 * than in a client's report.
 */

import { useCallback, useMemo, useRef, useState } from 'react'
import {
  AlertCircle, AlertTriangle, Check, FileSpreadsheet, HelpCircle,
  Loader2, Sparkles, Upload, X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  csvIngestApi,
  type CSVAnalyzeResponse,
  type CSVSourcePayload,
  type ColumnMapping,
  type ColumnMappingProposal,
  type MappingDirection,
  type MappingUnit,
} from '@/lib/api'

interface Props {
  clientId: string
  onAdd: (source: CSVSourcePayload, fileName: string) => void
  onClose: () => void
}

const MAX_FILE_MB = 10
const ACCEPTED = ['.csv', '.tsv', '.xlsx', '.xlsm']

const UNITS: { value: MappingUnit; label: string }[] = [
  { value: 'number',   label: 'Number' },
  { value: 'currency', label: 'Currency' },
  { value: 'percent',  label: 'Percent' },
  { value: 'ratio',    label: 'Ratio' },
  { value: 'duration', label: 'Duration' },
]

function errorMessage(e: unknown, fallback: string): string {
  const err = e as {
    response?: { status?: number; data?: { detail?: string } }
    code?: string
  }
  if (err?.response?.data?.detail) return err.response.data.detail
  if (err?.response?.status === 413) return `That file is larger than ${MAX_FILE_MB} MB.`
  if (err?.code === 'ERR_NETWORK') return 'Could not reach the server. Check your connection and try again.'
  return fallback
}

export default function CSVMappingDialog({ clientId, onAdd, onClose }: Props) {
  const [file,       setFile]       = useState<File | null>(null)
  const [analysis,   setAnalysis]   = useState<CSVAnalyzeResponse | null>(null)
  const [mapping,    setMapping]    = useState<ColumnMappingProposal | null>(null)
  const [resolved,   setResolved]   = useState<Set<string>>(new Set())
  const [answered,   setAnswered]   = useState<Set<string>>(new Set())
  const [sourceName, setSourceName] = useState('')
  const [saveAs,     setSaveAs]     = useState('')
  const [busy,       setBusy]       = useState<'analyzing' | 'committing' | null>(null)
  const [error,      setError]      = useState<string | null>(null)
  const [dragging,   setDragging]   = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const threshold = analysis?.confidence_threshold ?? 0.8

  // Confirm is blocked while any low-confidence mapping is untouched or any
  // ambiguity is unanswered. This mirrors the same check on the server.
  //
  // Deduped by column name: a column can be both below-threshold AND carry
  // an open ambiguity (the common case — the ambiguity is usually *why* the
  // model's confidence was low), and counting it twice made the footer say
  // "2 columns need your confirmation" for a single column with two
  // overlapping reasons. canConfirm was never affected by this — it only
  // checked blockers.length === 0 — so this was a display-only miscount.
  // NOTE: the comparison is `<=`, matching ColumnMapping.needs_confirmation in
  // backend/services/csv_ingest/schema.py. It must stay in step with it: the
  // backend rejects a commit containing any column it considers unconfirmed,
  // so if this said `<` while the backend said `<=`, a column at exactly the
  // threshold would leave Confirm enabled and then fail the request with a 422
  // the user cannot act on. 0.80 is a value GPT-4.1 emits often.
  const blockers = useMemo(() => {
    if (!mapping) return [] as string[]
    const out = new Set<string>()
    for (const column of mapping.columns) {
      if (column.confidence <= threshold && !resolved.has(column.source_column)) {
        out.add(column.source_column)
      }
    }
    for (const ambiguity of mapping.ambiguities) {
      if (!answered.has(ambiguity.column)) out.add(ambiguity.column)
    }
    return Array.from(out)
  }, [mapping, resolved, answered, threshold])

  const canConfirm = !!mapping && mapping.columns.length > 0 && blockers.length === 0

  function validate(f: File): string | null {
    const lower = f.name.toLowerCase()
    if (!ACCEPTED.some((ext) => lower.endsWith(ext))) {
      return `Upload a ${ACCEPTED.join(', ')} file. Most platforms offer one of these under Export.`
    }
    if (f.size > MAX_FILE_MB * 1024 * 1024) {
      return `That file is ${(f.size / 1024 / 1024).toFixed(1)} MB. The limit is ${MAX_FILE_MB} MB — try a shorter date range.`
    }
    return null
  }

  const analyze = useCallback(async (f: File, sheet?: string) => {
    const invalid = validate(f)
    if (invalid) { setError(invalid); return }

    setFile(f)
    setError(null)
    setBusy('analyzing')
    try {
      const result = await csvIngestApi.analyze(f, clientId, sheet)
      setAnalysis(result)
      setMapping(result.mapping)
      setSourceName(result.mapping.source_label || f.name.replace(/\.[^.]+$/, ''))
      // A replayed saved mapping was already confirmed once — don't make the
      // user re-confirm the same file layout every month.
      const preResolved = result.mapping.origin === 'ai'
        ? new Set<string>()
        : new Set(result.mapping.columns.map((c) => c.source_column))
      setResolved(preResolved)
      setAnswered(new Set())
      if (result.saved_mapping_name) setSaveAs(result.saved_mapping_name)
    } catch (e: unknown) {
      setError(errorMessage(e, 'We could not read that file. Try re-exporting it as CSV.'))
      setFile(null)
    } finally {
      setBusy(null)
    }
  }, [clientId])

  function updateColumn(sourceColumn: string, patch: Partial<ColumnMapping>) {
    if (!mapping) return
    setMapping({
      ...mapping,
      columns: mapping.columns.map((c) =>
        c.source_column === sourceColumn ? { ...c, ...patch } : c,
      ),
    })
    setResolved((prev) => new Set(prev).add(sourceColumn))
  }

  function removeColumn(sourceColumn: string) {
    if (!mapping) return
    setMapping({
      ...mapping,
      columns: mapping.columns.filter((c) => c.source_column !== sourceColumn),
    })
    setResolved((prev) => {
      const next = new Set(prev)
      next.delete(sourceColumn)
      return next
    })
  }

  function addColumn(columnName: string) {
    if (!mapping || mapping.columns.some((c) => c.source_column === columnName)) return
    setMapping({
      ...mapping,
      columns: [
        ...mapping.columns,
        {
          source_column: columnName,
          target_metric: columnName.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, ''),
          label: columnName,
          unit: 'number',
          direction: 'higher_is_better',
          confidence: 1,           // the user chose it, so it is not a guess
          reasoning: 'Added manually',
        },
      ],
    })
    setResolved((prev) => new Set(prev).add(columnName))
  }

  async function confirm() {
    if (!mapping || !analysis || !file) return
    setBusy('committing')
    setError(null)
    try {
      // Anything the user touched is theirs now, so it carries full confidence.
      //
      // Ambiguities the user has already answered (via a candidate button or
      // "Leave it out") are dropped here before anything is saved. Without
      // this, a saved mapping kept the ORIGINAL unresolved ambiguity forever —
      // updateColumn() already wrote the chosen target_metric into `columns`,
      // but the ambiguity entry itself was only tracked in `answered`, which
      // is local React state that's never sent to the server. Reusing the
      // saved mapping replayed the stale ambiguity and asked the same
      // question again on every future upload, even though the column's
      // resolved answer was sitting right there in `columns`.
      //
      // This is a plain filter over `answered` membership, so it handles any
      // number of ambiguities of any kind without special-casing: whichever
      // ones the user resolved in this session are gone from what gets
      // persisted; anything still open (e.g. the user clicked Confirm on a
      // mapping with zero ambiguities to begin with) is left untouched.
      const finalMapping: ColumnMappingProposal = {
        ...mapping,
        columns: mapping.columns.map((c) =>
          resolved.has(c.source_column) ? { ...c, confidence: 1 } : c,
        ),
        ambiguities: mapping.ambiguities.filter((a) => !answered.has(a.column)),
      }
      const { source } = await csvIngestApi.commit({
        analysis_id: analysis.analysis_id,
        client_id:   clientId,
        mapping:     finalMapping,
        source_name: sourceName.trim(),
        save_as:     saveAs.trim(),
      })
      onAdd(source, file.name)
      onClose()
    } catch (e: unknown) {
      setError(errorMessage(e, 'Could not apply that mapping. Adjust it and try again.'))
    } finally {
      setBusy(null)
    }
  }

  const unmappedColumns = analysis
    ? analysis.columns.filter(
        (c) =>
          c.type === 'number' &&
          !mapping?.columns.some((m) => m.source_column === c.column) &&
          c.column !== mapping?.date_column?.name,
      )
    : []

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="relative flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-indigo-600" />
            <h2 className="text-base font-semibold text-slate-900">Import data from a file</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex flex-col gap-4 overflow-y-auto px-5 py-5">
          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
              <p className="text-sm text-rose-800">{error}</p>
            </div>
          )}

          {/* ── Step 1: drop zone ─────────────────────────────────────────── */}
          {!analysis && busy !== 'analyzing' && (
            <>
              <p className="text-sm text-slate-500">
                Any export, any layout — LinkedIn Ads, TikTok, Semrush, a spreadsheet you
                keep by hand. We work out what the columns mean and show you before anything
                is used.
              </p>
              <div
                onDrop={(e) => {
                  e.preventDefault()
                  setDragging(false)
                  const f = e.dataTransfer.files?.[0]
                  if (f) analyze(f)
                }}
                onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  'flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-6 py-12 text-center transition-colors',
                  dragging
                    ? 'border-indigo-500 bg-indigo-50'
                    : 'border-slate-300 bg-slate-50 hover:border-indigo-400 hover:bg-indigo-50/50',
                )}
              >
                <Upload className={cn('h-8 w-8 transition-colors', dragging ? 'text-indigo-600' : 'text-slate-400')} />
                <div>
                  <p className="text-sm font-medium text-slate-700">
                    {dragging ? 'Drop it here' : 'Drag & drop a CSV or Excel file'}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    or click to browse — .csv, .tsv, .xlsx, up to {MAX_FILE_MB} MB
                  </p>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED.join(',')}
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (f) analyze(f)
                    e.target.value = ''
                  }}
                  className="hidden"
                />
              </div>
            </>
          )}

          {busy === 'analyzing' && (
            <div className="flex flex-col items-center justify-center gap-3 py-12 text-sm text-slate-500">
              <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
              Reading {file?.name} and working out what the columns mean…
            </div>
          )}

          {/* ── Step 2: confirmation ──────────────────────────────────────── */}
          {analysis && mapping && busy !== 'analyzing' && (
            <>
              {/* Provenance */}
              <div className="flex flex-wrap items-center gap-2 text-xs">
                {mapping.origin === 'ai' ? (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-1 font-medium text-indigo-700">
                    <Sparkles className="h-3 w-3" /> Mapped automatically — check it below
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 font-medium text-emerald-700">
                    <Check className="h-3 w-3" />
                    {analysis.saved_mapping_name
                      ? `Reused your saved mapping "${analysis.saved_mapping_name}"`
                      : 'Reused a saved mapping'}
                  </span>
                )}
                <span className="text-slate-500">
                  {analysis.row_count.toLocaleString()} rows · {analysis.columns.length} columns
                  {analysis.sheets.length > 1 && ` · sheet "${analysis.active_sheet}"`}
                </span>
              </div>

              {/* Sheet switcher */}
              {analysis.sheets.length > 1 && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-medium text-slate-600">Sheet:</span>
                  {analysis.sheets.map((sheet) => (
                    <button
                      key={sheet}
                      onClick={() => file && analyze(file, sheet)}
                      className={cn(
                        'rounded-md border px-2.5 py-1 text-xs transition-colors',
                        sheet === analysis.active_sheet
                          ? 'border-indigo-300 bg-indigo-50 font-medium text-indigo-700'
                          : 'border-slate-200 text-slate-600 hover:bg-slate-50',
                      )}
                    >
                      {sheet}
                    </button>
                  ))}
                </div>
              )}

              {/* Structural notes */}
              {analysis.warnings.length > 0 && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5">
                  <ul className="space-y-1 text-xs text-amber-900">
                    {analysis.warnings.map((warning, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                        {warning}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Ambiguities — questions, asked before anything is assumed */}
              {mapping.ambiguities.map((ambiguity) => (
                <div
                  key={ambiguity.column}
                  className={cn(
                    'rounded-lg border px-3 py-3',
                    answered.has(ambiguity.column)
                      ? 'border-slate-200 bg-slate-50'
                      : 'border-indigo-300 bg-indigo-50',
                  )}
                >
                  <div className="flex items-start gap-2">
                    <HelpCircle className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-slate-800">{ambiguity.question}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {(ambiguity.candidates.length ? ambiguity.candidates : ['Got it']).map((candidate) => (
                          <button
                            key={candidate}
                            onClick={() => {
                              setAnswered((prev) => new Set(prev).add(ambiguity.column))
                              const target = mapping.columns.find((c) => c.source_column === ambiguity.column)
                              if (target && ambiguity.candidates.length) {
                                updateColumn(ambiguity.column, {
                                  target_metric: candidate.toLowerCase().replace(/[^a-z0-9]+/g, '_'),
                                  label: candidate.replace(/_/g, ' '),
                                })
                              }
                            }}
                            className="rounded-md border border-indigo-300 bg-white px-2.5 py-1 text-xs font-medium text-indigo-700 transition-colors hover:bg-indigo-100"
                          >
                            {candidate}
                          </button>
                        ))}
                        <button
                          onClick={() => {
                            setAnswered((prev) => new Set(prev).add(ambiguity.column))
                            removeColumn(ambiguity.column)
                          }}
                          className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-600 transition-colors hover:bg-slate-50"
                        >
                          Leave it out
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Mapping table */}
              <div className="overflow-hidden rounded-lg border border-slate-200">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">Your column</th>
                      <th className="px-3 py-2 text-left font-medium">Report label</th>
                      <th className="px-3 py-2 text-left font-medium">Format</th>
                      <th className="px-3 py-2 text-left font-medium">Confidence</th>
                      <th className="px-3 py-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {mapping.date_column && (
                      <tr className="bg-slate-50/60">
                        <td className="px-3 py-2 font-mono text-xs text-slate-700">
                          {mapping.date_column.name}
                        </td>
                        <td className="px-3 py-2 text-slate-500" colSpan={2}>
                          Date column — used for the trend chart
                        </td>
                        <td className="px-3 py-2 text-xs text-slate-500">
                          {mapping.date_column.format ?? 'auto'}
                        </td>
                        <td />
                      </tr>
                    )}
                    {mapping.columns.map((column) => {
                      // `<=` for the same reason as `blockers` above — a row
                      // that blocks Confirm must also be highlighted as the
                      // reason why.
                      const needsAttention =
                        column.confidence <= threshold && !resolved.has(column.source_column)
                      return (
                        <tr
                          key={column.source_column}
                          className={needsAttention ? 'bg-amber-50/70' : undefined}
                        >
                          <td className="px-3 py-2 align-middle">
                            <span className="font-mono text-xs text-slate-700">
                              {column.source_column}
                            </span>
                            {column.reasoning && (
                              <p className="mt-0.5 text-[11px] text-slate-400">{column.reasoning}</p>
                            )}
                          </td>
                          <td className="px-3 py-2">
                            <input
                              value={column.label}
                              onChange={(e) =>
                                updateColumn(column.source_column, { label: e.target.value })
                              }
                              className="w-full rounded-md border border-slate-200 px-2 py-1 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                            />
                          </td>
                          <td className="px-3 py-2">
                            <select
                              value={column.unit}
                              onChange={(e) =>
                                updateColumn(column.source_column, {
                                  unit: e.target.value as MappingUnit,
                                })
                              }
                              className="rounded-md border border-slate-200 px-2 py-1 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                            >
                              {UNITS.map((unit) => (
                                <option key={unit.value} value={unit.value}>{unit.label}</option>
                              ))}
                            </select>
                            <select
                              value={column.direction}
                              onChange={(e) =>
                                updateColumn(column.source_column, {
                                  direction: e.target.value as MappingDirection,
                                })
                              }
                              className="ml-1.5 rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-600 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                            >
                              <option value="higher_is_better">Higher is better</option>
                              <option value="lower_is_better">Lower is better</option>
                            </select>
                          </td>
                          <td className="px-3 py-2">
                            <ConfidenceBadge
                              value={column.confidence}
                              threshold={threshold}
                              resolved={resolved.has(column.source_column)}
                            />
                          </td>
                          <td className="px-3 py-2 text-right">
                            <button
                              onClick={() => removeColumn(column.source_column)}
                              className="rounded p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-rose-600"
                              aria-label={`Remove ${column.source_column}`}
                            >
                              <X className="h-3.5 w-3.5" />
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                    {mapping.columns.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-3 py-6 text-center text-sm text-slate-500">
                          No columns selected yet. Add the ones you want from the list below.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Columns we left out — one click to include */}
              {unmappedColumns.length > 0 && (
                <div>
                  <p className="mb-1.5 text-xs font-medium text-slate-600">
                    Not included — click to add:
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {unmappedColumns.map((column) => (
                      <button
                        key={column.column}
                        onClick={() => addColumn(column.column)}
                        className="rounded-md border border-slate-200 bg-white px-2 py-1 font-mono text-xs text-slate-600 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
                        title={`e.g. ${column.samples.slice(0, 3).join(', ')}`}
                      >
                        + {column.column}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Parse preview — the locale sanity check */}
              {analysis.preview.length > 0 && mapping.columns.length > 0 && (
                <details className="rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2">
                  <summary className="cursor-pointer text-xs font-medium text-slate-600">
                    Check how the first rows are read
                  </summary>
                  <div className="mt-2 overflow-x-auto">
                    <table className="w-full text-xs">
                      <tbody className="divide-y divide-slate-200">
                        {analysis.preview.map((row, i) => (
                          <tr key={i}>
                            {Object.entries(row).map(([column, cell]) => (
                              <td key={column} className="px-2 py-1 whitespace-nowrap">
                                <span className="text-slate-400">{cell.raw || '—'}</span>
                                <span className="mx-1 text-slate-300">→</span>
                                <span
                                  className={cn(
                                    'font-medium',
                                    cell.parsed === null ? 'text-rose-500' : 'text-slate-700',
                                  )}
                                >
                                  {cell.parsed === null ? 'unreadable' : String(cell.parsed)}
                                </span>
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              )}

              {/* Naming + reuse */}
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium text-slate-700">
                    Source name
                  </label>
                  <input
                    value={sourceName}
                    onChange={(e) => setSourceName(e.target.value)}
                    placeholder="LinkedIn Ads"
                    className="rounded-md border border-slate-200 px-2.5 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                  />
                  <p className="text-[11px] text-slate-400">Shown as the slide heading.</p>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium text-slate-700">
                    Save this mapping <span className="font-normal text-slate-400">(optional)</span>
                  </label>
                  <input
                    value={saveAs}
                    onChange={(e) => setSaveAs(e.target.value)}
                    placeholder="Monthly LinkedIn export"
                    className="rounded-md border border-slate-200 px-2.5 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                  />
                  <p className="text-[11px] text-slate-400">
                    Next month&rsquo;s upload of the same export becomes one click.
                  </p>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        {analysis && (
          <div className="flex items-center justify-between gap-3 border-t border-slate-200 bg-slate-50 px-5 py-3">
            <p className="text-xs text-slate-500">
              {blockers.length > 0
                ? `${blockers.length} ${blockers.length === 1 ? 'column needs' : 'columns need'} your confirmation before this can be used.`
                : `${mapping?.columns.length ?? 0} metrics ready.`}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={onClose}
                className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 transition-colors hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={confirm}
                disabled={!canConfirm || busy === 'committing'}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                  canConfirm && busy !== 'committing'
                    ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                    : 'cursor-not-allowed bg-slate-200 text-slate-400',
                )}
              >
                {busy === 'committing' ? (
                  <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Importing…</>
                ) : (
                  <><Check className="h-3.5 w-3.5" /> Use this data</>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ConfidenceBadge({
  value, threshold, resolved,
}: { value: number; threshold: number; resolved: boolean }) {
  if (resolved) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
        <Check className="h-3 w-3" /> Confirmed
      </span>
    )
  }
  if (value >= 0.95) {
    return (
      <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
        High
      </span>
    )
  }
  if (value >= threshold) {
    return (
      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
        Medium
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800">
      <AlertTriangle className="h-3 w-3" /> Check this
    </span>
  )
}
