'use client'

// Agency-side comments widget for the report detail page.
// Fetches /api/comments/report/{reportId}, lets the agency resolve/unresolve,
// and filter between "unresolved" and "all".

import { useCallback, useEffect, useMemo, useState } from 'react'
import { MessageSquare, Loader2, Check, RotateCcw, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { commentsApi, type ReportComment } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

type Filter = 'unresolved' | 'all'

function targetLabel(c: ReportComment): string {
  if (c.slide_number) return `Slide ${c.slide_number}`
  if (c.section_key) return `Section: ${c.section_key.replace(/_/g, ' ')}`
  return 'General feedback'
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export default function CommentsSection({ reportId }: { reportId: string }) {
  const [comments, setComments] = useState<ReportComment[]>([])
  const [loading,  setLoading]  = useState(true)
  const [filter,   setFilter]   = useState<Filter>('unresolved')
  const [busyId,   setBusyId]   = useState<string | null>(null)

  const fetchComments = useCallback(async () => {
    setLoading(true)
    try {
      const res = await commentsApi.listByReport(reportId)
      setComments(res.comments)
    } catch {
      toast.error('Failed to load comments.')
    } finally {
      setLoading(false)
    }
  }, [reportId])

  useEffect(() => {
    fetchComments()
  }, [fetchComments])

  const filtered = useMemo(() => {
    if (filter === 'unresolved') return comments.filter((c) => !c.is_resolved)
    return comments
  }, [comments, filter])

  const unresolvedCount = useMemo(
    () => comments.filter((c) => !c.is_resolved).length,
    [comments],
  )

  const handleResolveToggle = async (c: ReportComment) => {
    setBusyId(c.id)
    try {
      const updated = await commentsApi.resolve(c.id, !c.is_resolved)
      setComments((prev) => prev.map((x) => (x.id === c.id ? updated : x)))
    } catch {
      toast.error('Failed to update comment.')
    } finally {
      setBusyId(null)
    }
  }

  const handleDelete = async (c: ReportComment) => {
    if (!window.confirm(`Delete comment from ${c.client_name}? This cannot be undone.`)) return
    setBusyId(c.id)
    try {
      await commentsApi.delete(c.id)
      setComments((prev) => prev.filter((x) => x.id !== c.id))
      toast.success('Comment deleted')
    } catch {
      toast.error('Failed to delete comment.')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <CardTitle className="text-base text-slate-700 flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-indigo-600" />
            Client Comments
            {unresolvedCount > 0 && (
              <span className="rounded-full bg-rose-50 border border-rose-200 px-2 py-0.5 text-xs font-semibold text-rose-600">
                {unresolvedCount} unresolved
              </span>
            )}
          </CardTitle>

          <div className="flex gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1">
            {([
              { id: 'unresolved' as const, label: 'Unresolved' },
              { id: 'all'        as const, label: 'All' },
            ]).map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setFilter(id)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  filter === id
                    ? 'bg-white text-indigo-700 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-10 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-8">
            {comments.length === 0
              ? 'No comments yet. Clients can leave feedback directly on the shared report.'
              : 'No comments match this filter.'}
          </p>
        ) : (
          <ul className="space-y-3">
            {filtered.map((c) => (
              <li
                key={c.id}
                className={`rounded-lg border px-4 py-3 space-y-1.5 ${
                  c.is_resolved
                    ? 'border-slate-100 bg-slate-50 opacity-80'
                    : 'border-slate-200 bg-white'
                }`}
              >
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-800">
                      {c.client_name}
                      <span className="ml-2 text-xs font-normal text-slate-400">
                        &lt;{c.client_email}&gt;
                      </span>
                    </p>
                    <p className="text-[11px] text-slate-400">
                      {targetLabel(c)} &middot; {formatTimestamp(c.created_at)}
                    </p>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => handleResolveToggle(c)}
                      disabled={busyId === c.id}
                      className={`inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-60 ${
                        c.is_resolved
                          ? 'border-slate-200 text-slate-500 hover:bg-slate-100'
                          : 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                      }`}
                    >
                      {busyId === c.id
                        ? <Loader2 className="h-3 w-3 animate-spin" />
                        : c.is_resolved
                          ? <RotateCcw className="h-3 w-3" />
                          : <Check className="h-3 w-3" />}
                      {c.is_resolved ? 'Reopen' : 'Resolve'}
                    </button>
                    <button
                      onClick={() => handleDelete(c)}
                      disabled={busyId === c.id}
                      className="inline-flex items-center rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-400 hover:text-rose-600 hover:border-rose-200 transition-colors disabled:opacity-60"
                      title="Delete comment"
                      aria-label="Delete comment"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </div>

                <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                  {c.comment_text}
                </p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
