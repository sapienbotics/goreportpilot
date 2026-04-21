'use client'

// Public comments UI for the shared-report page.
//
// Exports:
//   <CommentsProvider>          — fetches + holds all comments for a share
//   useComments()               — hook to read state + mutate
//   <CommentButton>             — per-section inline trigger (shows count badge)
//   <CommentsDrawer>            — right-side drawer with thread + post form
//   <FloatingCommentFAB>        — global "leave a comment" FAB (general feedback)

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { MessageSquare, Loader2, X, Send } from 'lucide-react'
import { publicCommentsApi, type ReportComment } from '@/lib/api'

// ---------------------------------------------------------------------------
// Types + context
// ---------------------------------------------------------------------------

type CommentTarget =
  | { kind: 'section'; sectionKey: string; label: string }
  | { kind: 'slide';   slideNumber: number; label: string }
  | { kind: 'general'; label: string }

interface CommentsContextValue {
  comments:       ReportComment[]
  loading:        boolean
  error:          string | null
  openTarget:     CommentTarget | null
  openDrawer:     (target: CommentTarget) => void
  closeDrawer:    () => void
  postComment:    (payload: { name: string; email: string; text: string; target: CommentTarget }) => Promise<void>
  refetch:        () => Promise<void>
  countForSection: (sectionKey: string) => number
  countForSlide:   (slideNumber: number) => number
  countGeneral:    () => number
}

const CommentsContext = createContext<CommentsContextValue | null>(null)

export function useComments(): CommentsContextValue {
  const ctx = useContext(CommentsContext)
  if (!ctx) throw new Error('useComments must be used inside <CommentsProvider>')
  return ctx
}

// ---------------------------------------------------------------------------
// Provider — owns the fetch + post lifecycle.
// ---------------------------------------------------------------------------

export function CommentsProvider({
  shareToken,
  children,
}: {
  shareToken: string
  children: React.ReactNode
}) {
  const [comments,   setComments]   = useState<ReportComment[]>([])
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState<string | null>(null)
  const [openTarget, setOpenTarget] = useState<CommentTarget | null>(null)

  const refetch = useCallback(async () => {
    try {
      setError(null)
      const res = await publicCommentsApi.list(shareToken)
      setComments(res.comments)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load comments')
    } finally {
      setLoading(false)
    }
  }, [shareToken])

  useEffect(() => {
    refetch()
  }, [refetch])

  const postComment = useCallback(
    async ({ name, email, text, target }: { name: string; email: string; text: string; target: CommentTarget }) => {
      const created = await publicCommentsApi.create(shareToken, {
        client_name:  name,
        client_email: email,
        comment_text: text,
        slide_number: target.kind === 'slide'   ? target.slideNumber : null,
        section_key:  target.kind === 'section' ? target.sectionKey  : null,
      })
      setComments((prev) => [...prev, created])
    },
    [shareToken],
  )

  const countForSection = useCallback(
    (key: string) => comments.filter((c) => c.section_key === key).length,
    [comments],
  )
  const countForSlide = useCallback(
    (n: number) => comments.filter((c) => c.slide_number === n).length,
    [comments],
  )
  const countGeneral = useCallback(
    () => comments.filter((c) => !c.section_key && c.slide_number == null).length,
    [comments],
  )

  const value: CommentsContextValue = useMemo(
    () => ({
      comments,
      loading,
      error,
      openTarget,
      openDrawer:      (target) => setOpenTarget(target),
      closeDrawer:     () => setOpenTarget(null),
      postComment,
      refetch,
      countForSection,
      countForSlide,
      countGeneral,
    }),
    [comments, loading, error, openTarget, postComment, refetch, countForSection, countForSlide, countGeneral],
  )

  return <CommentsContext.Provider value={value}>{children}</CommentsContext.Provider>
}

// ---------------------------------------------------------------------------
// Per-section inline trigger — shows the count and opens the drawer.
// ---------------------------------------------------------------------------

export function CommentButton({
  sectionKey,
  sectionLabel,
}: {
  sectionKey: string
  sectionLabel: string
}) {
  const { countForSection, openDrawer } = useComments()
  const count = countForSection(sectionKey)

  return (
    <button
      onClick={() => openDrawer({ kind: 'section', sectionKey, label: sectionLabel })}
      className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-500 hover:text-indigo-700 hover:border-indigo-200 hover:bg-indigo-50 transition-colors"
      aria-label={`Comment on ${sectionLabel}`}
    >
      <MessageSquare className="h-3.5 w-3.5" />
      {count > 0 ? <span>{count}</span> : <span>Comment</span>}
    </button>
  )
}

// ---------------------------------------------------------------------------
// Floating FAB — page-level "leave a comment" anchor.
// ---------------------------------------------------------------------------

export function FloatingCommentFAB() {
  const { comments, openDrawer } = useComments()
  const total = comments.length

  return (
    <button
      onClick={() => openDrawer({ kind: 'general', label: 'General feedback' })}
      className="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 rounded-full bg-indigo-700 px-4 py-3 text-sm font-semibold text-white shadow-lg hover:bg-indigo-800 transition-colors"
      aria-label="Leave a comment"
    >
      <MessageSquare className="h-4 w-4" />
      Comment
      {total > 0 && (
        <span className="ml-1 rounded-full bg-white/20 px-2 py-0.5 text-xs">
          {total}
        </span>
      )}
    </button>
  )
}

// ---------------------------------------------------------------------------
// Drawer — slide-in panel showing the thread for the open target + post form.
// ---------------------------------------------------------------------------

const STORAGE_KEY = 'grp_comment_identity'

function loadIdentity(): { name: string; email: string } {
  if (typeof window === 'undefined') return { name: '', email: '' }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return { name: '', email: '' }
    const parsed = JSON.parse(raw) as { name?: string; email?: string }
    return { name: parsed.name || '', email: parsed.email || '' }
  } catch {
    return { name: '', email: '' }
  }
}

function saveIdentity(name: string, email: string): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ name, email }))
  } catch { /* quota or disabled — ignore */ }
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

export function CommentsDrawer() {
  const { openTarget, closeDrawer, comments, postComment } = useComments()

  const [name,    setName]    = useState('')
  const [email,   setEmail]   = useState('')
  const [text,    setText]    = useState('')
  const [posting, setPosting] = useState(false)
  const [postErr, setPostErr] = useState<string | null>(null)

  // Restore saved identity whenever the drawer opens
  useEffect(() => {
    if (!openTarget) return
    const saved = loadIdentity()
    setName(saved.name)
    setEmail(saved.email)
    setText('')
    setPostErr(null)
  }, [openTarget])

  // Derive the visible thread for the current target
  const visibleComments = useMemo(() => {
    if (!openTarget) return []
    const filtered = comments.filter((c) => {
      if (openTarget.kind === 'section') return c.section_key === openTarget.sectionKey
      if (openTarget.kind === 'slide')   return c.slide_number === openTarget.slideNumber
      return !c.section_key && c.slide_number == null
    })
    return [...filtered].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    )
  }, [comments, openTarget])

  if (!openTarget) return null

  const canSubmit =
    name.trim().length > 0 &&
    email.trim().length > 0 &&
    text.trim().length > 0 &&
    !posting

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setPosting(true)
    setPostErr(null)
    try {
      await postComment({
        name:   name.trim(),
        email:  email.trim(),
        text:   text.trim(),
        target: openTarget,
      })
      saveIdentity(name.trim(), email.trim())
      setText('')
    } catch (err) {
      setPostErr(err instanceof Error ? err.message : 'Failed to post comment')
    } finally {
      setPosting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/30 backdrop-blur-sm"
        onClick={closeDrawer}
      />

      {/* Drawer body */}
      <div className="ml-auto relative h-full w-full sm:max-w-md bg-white shadow-2xl flex flex-col">
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
              Comments
            </p>
            <h2 className="text-base font-semibold text-slate-900 truncate">
              {openTarget.label}
            </h2>
          </div>
          <button
            onClick={closeDrawer}
            className="text-slate-400 hover:text-slate-700 transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Thread */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {visibleComments.length === 0 ? (
            <div className="text-center text-sm text-slate-400 py-10">
              No comments here yet. Be the first to share feedback.
            </div>
          ) : (
            visibleComments.map((c) => (
              <div
                key={c.id}
                className="rounded-lg border border-slate-100 bg-slate-50 px-4 py-3 space-y-1"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-slate-800 truncate">
                    {c.client_name}
                  </p>
                  <p className="text-[11px] text-slate-400 shrink-0">
                    {formatTimestamp(c.created_at)}
                  </p>
                </div>
                <p className="text-sm text-slate-600 whitespace-pre-wrap leading-relaxed">
                  {c.comment_text}
                </p>
                {c.is_resolved && (
                  <p className="text-[11px] font-semibold text-emerald-600">
                    ✓ Resolved by the agency
                  </p>
                )}
              </div>
            ))
          )}
        </div>

        {/* Post form */}
        <form
          onSubmit={handleSubmit}
          className="border-t border-slate-200 px-5 py-4 space-y-3 bg-white"
        >
          <div className="grid grid-cols-2 gap-2">
            <input
              type="text"
              required
              maxLength={120}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              className="rounded-md border border-slate-200 px-3 py-2 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@email.com"
              className="rounded-md border border-slate-200 px-3 py-2 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <textarea
            required
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            maxLength={2000}
            placeholder="Leave a comment…"
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-y"
          />

          {postErr && (
            <p className="text-xs text-rose-600 bg-rose-50 border border-rose-100 rounded-md px-3 py-2">
              {postErr}
            </p>
          )}

          <div className="flex items-center justify-between gap-3">
            <p className="text-[11px] text-slate-400">
              Your email is visible only to the agency.
            </p>
            <button
              type="submit"
              disabled={!canSubmit}
              className="inline-flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-50"
            >
              {posting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
              {posting ? 'Sending…' : 'Post comment'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
