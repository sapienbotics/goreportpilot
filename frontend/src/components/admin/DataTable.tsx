'use client'

import { Loader2 } from 'lucide-react'

export interface Column<T> {
  key: string
  label: string
  render?: (row: T) => React.ReactNode
  className?: string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  loading?: boolean
  emptyMessage?: string
  onRowClick?: (row: T) => void
  keyField?: string
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  loading = false,
  emptyMessage = 'No data found.',
  onRowClick,
  keyField = 'id',
}: DataTableProps<T>) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <p className="text-center text-sm text-slate-400 py-12">{emptyMessage}</p>
    )
  }

  return (
    <div className="overflow-x-auto -mx-4 sm:mx-0 rounded-lg border border-slate-200">
      <table className="min-w-[640px] w-full text-sm">
        <thead className="bg-slate-50 border-b border-slate-200">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-400 ${col.className ?? ''}`}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {data.map((row, i) => (
            <tr
              key={(row[keyField] as string) ?? i}
              className={`bg-white hover:bg-slate-50 transition-colors ${onRowClick ? 'cursor-pointer' : ''}`}
              onClick={() => onRowClick?.(row)}
            >
              {columns.map((col) => (
                <td key={col.key} className={`px-4 py-3 text-slate-700 whitespace-nowrap ${col.className ?? ''}`}>
                  {col.render ? col.render(row) : String(row[col.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// Simple pagination controls
export function Pagination({
  page,
  total,
  limit,
  onPageChange,
}: {
  page: number
  total: number
  limit: number
  onPageChange: (page: number) => void
}) {
  const totalPages = Math.max(1, Math.ceil(total / limit))
  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-2 pt-4 text-sm">
      <span className="text-slate-400 text-xs sm:text-sm">
        {Math.min((page - 1) * limit + 1, total)}–{Math.min(page * limit, total)} of {total}
      </span>
      <div className="flex gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="rounded-md border border-slate-200 px-3 py-2 min-h-[44px] sm:min-h-0 sm:py-1.5 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Prev
        </button>
        <span className="flex items-center px-2 text-slate-500">
          {page}/{totalPages}
        </span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="rounded-md border border-slate-200 px-3 py-2 min-h-[44px] sm:min-h-0 sm:py-1.5 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Next
        </button>
      </div>
    </div>
  )
}
