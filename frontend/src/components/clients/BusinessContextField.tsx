'use client'

// Shared Business Context field (Phase 7 UX).
// Used by both AddClientDialog (create) and SettingsTab (edit). The two
// parents pass a controlled value + onChange; everything else (quality dot,
// AI-assist, diff modal, hints) lives here so both flows stay in lockstep.

import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import {
  Info, Sparkles, ChevronDown, ChevronUp, Loader2, Check, X as XIcon,
} from 'lucide-react'

import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { clientsApi } from '@/lib/api'

export const BUSINESS_CONTEXT_MAX = 500
export const BUSINESS_CONTEXT_AI_MIN = 20   // below this, AI button stays disabled

// Simple keyword signal for the "green" quality state. Not a real scorer —
// just a nudge: an agency who mentions any of these has almost certainly
// written something AI-useful. Lowercase-matched on the raw input.
const QUALITY_KEYWORDS = [
  'goal', 'target', 'grow', 'growth', 'increase', 'reduce', 'improve',
  'launch', 'expand', 'kpi', 'mrr', 'arr', 'conversion', 'revenue',
]

export type QualityLevel = 'empty' | 'low' | 'medium' | 'good'

export function computeQuality(text: string): QualityLevel {
  const trimmed = (text || '').trim()
  if (trimmed.length === 0) return 'empty'
  if (trimmed.length < 30) return 'low'
  const lc = trimmed.toLowerCase()
  const hasKeyword = QUALITY_KEYWORDS.some(k => lc.includes(k))
  if (trimmed.length >= 50 && hasKeyword) return 'good'
  return 'medium'
}

const QUALITY_META: Record<QualityLevel, { color: string; label: string; hint: string }> = {
  empty: {
    color: 'bg-rose-500',
    label: 'Empty',
    hint: 'Reports will use generic AI analysis. Add context for more strategic insights.',
  },
  low: {
    color: 'bg-amber-500',
    label: 'Too short',
    hint: 'Add more detail — at least 30 characters — so the AI has something specific to work with.',
  },
  medium: {
    color: 'bg-amber-400',
    label: 'OK',
    hint: 'Good start. Mention goals (grow/reduce/target/KPI…) to unlock stronger recommendations.',
  },
  good: {
    color: 'bg-emerald-500',
    label: 'Strong',
    hint: 'Great — the AI has enough signal to produce client-specific recommendations.',
  },
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  value: string
  onChange: (next: string) => void
  /** Optional id for the <textarea> — pair with an external <label htmlFor>. */
  id?: string
  /** Height in rows. Defaults to 4. */
  rows?: number
  /** Render the "Business Context" label + tooltip internally. Parents that
   *  already render their own label (e.g. SettingsTab's Field wrapper) can
   *  set this to false to avoid a double label. */
  showLabel?: boolean
  /** When true, the textarea is read-only and the AI button is hidden. */
  readOnly?: boolean
}

export default function BusinessContextField({
  value,
  onChange,
  id = 'business-context',
  rows = 4,
  showLabel = true,
  readOnly = false,
}: Props) {
  const [hintsOpen,    setHintsOpen]    = useState(false)
  const [enhancing,    setEnhancing]    = useState(false)
  const [diffOpen,     setDiffOpen]     = useState(false)
  const [enhanced,     setEnhanced]     = useState<string>('')

  const trimmedLen = value.trim().length
  const quality    = useMemo(() => computeQuality(value), [value])
  const qMeta      = QUALITY_META[quality]
  const canEnhance = !readOnly && trimmedLen >= BUSINESS_CONTEXT_AI_MIN && !enhancing

  // ── AI assist ────────────────────────────────────────────────────────────

  const handleEnhance = async () => {
    if (!canEnhance) return
    setEnhancing(true)
    try {
      const { enhanced: out } = await clientsApi.enhanceContext(value)
      setEnhanced(out)
      setDiffOpen(true)
    } catch (err: unknown) {
      const e = err as { response?: { status?: number; data?: { detail?: unknown } } }
      if (e?.response?.status === 429) {
        toast.error('You\u2019ve hit the AI-assist limit (10/hour). Please try again later.')
      } else {
        const detail = typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : null
        toast.error(detail || 'AI enhancement failed. Please try again.')
      }
    } finally {
      setEnhancing(false)
    }
  }

  const acceptEnhancement = () => {
    onChange(enhanced.slice(0, BUSINESS_CONTEXT_MAX))
    setDiffOpen(false)
    setEnhanced('')
    toast.success('Enhanced context applied.')
  }

  const rejectEnhancement = () => {
    setDiffOpen(false)
    setEnhanced('')
  }

  // ── Input handler (soft cap at BUSINESS_CONTEXT_MAX) ─────────────────────

  const handleInput = (next: string) => {
    // Hard-cap typed input. Paste of longer text gets truncated silently; the
    // counter turning red signals what happened.
    if (next.length > BUSINESS_CONTEXT_MAX) next = next.slice(0, BUSINESS_CONTEXT_MAX)
    onChange(next)
  }

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="space-y-2">
      {showLabel && (
        <div className="flex items-center gap-2">
          <label htmlFor={id} className="text-sm font-medium text-slate-700">
            Business Context
          </label>
          <span
            className="text-slate-400 hover:text-slate-600 cursor-help"
            title="This text is used to personalize AI narrative, recommendations, and executive summaries in every generated report."
          >
            <Info className="h-3.5 w-3.5" />
          </span>
          {/* Quality dot */}
          <span
            className={`inline-block h-2 w-2 rounded-full ${qMeta.color}`}
            title={`${qMeta.label} — ${qMeta.hint}`}
            aria-label={`Context quality: ${qMeta.label}`}
          />
        </div>
      )}

      {showLabel && (
        <p className="text-xs text-slate-500 leading-relaxed">
          Describe this client&apos;s business, goals, and target audience.
          This context shapes AI-written recommendations in every report —
          more detail = more strategic insight.
        </p>
      )}

      <Textarea
        id={id}
        value={value}
        onChange={(e) => handleInput(e.target.value)}
        placeholder="e.g., SaaS platform targeting SMB marketers. Goal: grow MRR 30% by Q4. Key competitors: Canva, Figma. Focus on conversion rate optimization and content marketing."
        rows={rows}
        readOnly={readOnly}
        maxLength={BUSINESS_CONTEXT_MAX}
        className="resize-none"
      />

      {/* Bottom row: counter + AI button */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <span
          className={`text-xs ${value.length >= BUSINESS_CONTEXT_MAX ? 'text-rose-600 font-medium' : 'text-slate-400'}`}
        >
          {value.length} / {BUSINESS_CONTEXT_MAX} characters
        </span>

        {!readOnly && (
          <button
            type="button"
            onClick={handleEnhance}
            disabled={!canEnhance}
            title={
              trimmedLen < BUSINESS_CONTEXT_AI_MIN
                ? `Write at least ${BUSINESS_CONTEXT_AI_MIN} characters to enable AI assist`
                : 'Rewrite into a concise, report-ready paragraph using GPT-4.1'
            }
            className="inline-flex items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {enhancing ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5" />
            )}
            {enhancing ? 'Enhancing\u2026' : 'Improve with AI'}
          </button>
        )}
      </div>

      {/* Collapsible hints */}
      {!readOnly && (
        <div className="rounded-md border border-slate-200 bg-slate-50/60">
          <button
            type="button"
            onClick={() => setHintsOpen(o => !o)}
            className="flex items-center justify-between w-full px-3 py-2 text-xs font-medium text-slate-600 hover:text-slate-800"
            aria-expanded={hintsOpen}
          >
            <span>Not sure what to write?</span>
            {hintsOpen
              ? <ChevronUp className="h-3.5 w-3.5" />
              : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
          {hintsOpen && (
            <ul className="px-4 pb-3 space-y-1.5 text-xs text-slate-600 list-disc list-outside">
              <li>What does this client sell and to whom?</li>
              <li>What are their 1-3 primary business goals this quarter?</li>
              <li>What channels/strategies are they investing in?</li>
            </ul>
          )}
        </div>
      )}

      {/* Diff modal */}
      <Dialog
        open={diffOpen}
        onOpenChange={(v) => { if (!v) rejectEnhancement() }}
      >
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Review AI enhancement</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">
                Original
              </p>
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 min-h-[8rem] whitespace-pre-wrap">
                {value}
              </div>
            </div>
            <div>
              <p className="text-xs font-medium text-indigo-700 uppercase tracking-wide mb-1">
                Enhanced
              </p>
              <div className="rounded-md border border-indigo-200 bg-indigo-50 p-3 text-sm text-slate-800 min-h-[8rem] whitespace-pre-wrap">
                {enhanced}
              </div>
            </div>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {enhanced.length} characters. Accepting replaces your current text.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={rejectEnhancement}>
              <XIcon className="h-3.5 w-3.5 mr-1" />
              Keep original
            </Button>
            <Button onClick={acceptEnhancement}>
              <Check className="h-3.5 w-3.5 mr-1" />
              Use enhanced version
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
