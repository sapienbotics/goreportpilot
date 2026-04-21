'use client'

// Phase 6B — Goals & Alerts tab.
// Self-contained: fetches its own data via goalsApi on mount. This differs
// from SchedulesTab (which receives everything via props from the parent)
// because goals data is only needed when this tab is active and the parent
// page is already carrying a lot of state.

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { toast } from 'sonner'
import { Target, Plus, Pencil, Trash2, Loader2, AlertCircle, Info } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
  goalsApi,
  type Goal,
  type GoalComparison,
  type GoalCreatePayload,
  type GoalListResponse,
  type GoalMetric,
  type GoalPeriod,
  type GoalStatus,
} from '@/lib/api'

interface Props {
  clientId: string
}

// ---------------------------------------------------------------------------
// Status badge — matches ReportsTab colour system.
// ---------------------------------------------------------------------------

const STATUS_STYLES: Record<GoalStatus, { bg: string; fg: string; label: string }> = {
  on_track: { bg: 'bg-emerald-50', fg: 'text-emerald-700', label: 'On track' },
  at_risk:  { bg: 'bg-amber-50',   fg: 'text-amber-700',   label: 'At risk'  },
  missed:   { bg: 'bg-rose-50',    fg: 'text-rose-600',    label: 'Missed'   },
  no_data:  { bg: 'bg-slate-100',  fg: 'text-slate-500',   label: 'No data'  },
}

function StatusBadge({ status }: { status: GoalStatus | null }) {
  const style = STATUS_STYLES[status ?? 'no_data']
  return (
    <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${style.bg} ${style.fg}`}>
      {style.label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Value formatting — mirrors backend email helper so the UI and the alert
// email agree on how a goal is displayed.
// ---------------------------------------------------------------------------

function formatValue(value: number | null, unit: string | undefined): string {
  if (value === null || value === undefined) return '—'
  switch (unit) {
    case 'percent':  return `${value.toFixed(1)}%`
    case 'ratio':    return `${value.toFixed(2)}x`
    case 'currency': return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    default:         return value.toLocaleString(undefined, { maximumFractionDigits: 0 })
  }
}

const CMP_SYMBOL: Record<GoalComparison, string> = { gte: '≥', lte: '≤', eq: '=' }

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function GoalsTab({ clientId }: Props) {
  const [resp,    setResp]    = useState<GoalListResponse | null>(null)
  const [metrics, setMetrics] = useState<GoalMetric[]>([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  // Dialog state — editing === null means "create new".
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing,    setEditing]    = useState<Goal | null>(null)

  // ── Data loading ──────────────────────────────────────────────────────────

  const refresh = useCallback(async () => {
    try {
      const [listData, metricsData] = await Promise.all([
        goalsApi.listByClient(clientId),
        goalsApi.listMetrics(),
      ])
      setResp(listData)
      setMetrics(metricsData)
      setError(null)
    } catch {
      setError('Failed to load goals.')
    } finally {
      setLoading(false)
    }
  }, [clientId])

  useEffect(() => { void refresh() }, [refresh])

  const metricsByKey = useMemo(() => {
    const m = new Map<string, GoalMetric>()
    metrics.forEach(x => m.set(x.key, x))
    return m
  }, [metrics])

  // ── Derived: plan/limit state ─────────────────────────────────────────────

  const goals         = resp?.goals ?? []
  const limit         = resp?.limit ?? 1
  const plan          = resp?.plan ?? 'trial'
  const isTrial       = resp?.is_trial ?? false
  const postTrialLimit = resp?.plan_goal_limit ?? limit
  const atLimit       = goals.length >= limit

  // ── Handlers ──────────────────────────────────────────────────────────────

  const openCreate = () => { setEditing(null);  setDialogOpen(true) }
  const openEdit   = (g: Goal) => { setEditing(g); setDialogOpen(true) }

  const handleDelete = async (goal: Goal) => {
    if (!window.confirm(`Delete goal "${goal.metric_label ?? goal.metric}"? This cannot be undone.`)) return
    try {
      await goalsApi.delete(clientId, goal.id)
      toast.success('Goal deleted.')
      await refresh()
    } catch {
      toast.error('Failed to delete goal.')
    }
  }

  const handleSaved = async () => {
    setDialogOpen(false)
    setEditing(null)
    await refresh()
  }

  // ── Render ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="max-w-3xl space-y-3">
        <div className="h-10 rounded-lg bg-slate-100 animate-pulse" />
        <div className="h-24 rounded-lg bg-slate-100 animate-pulse" />
        <div className="h-24 rounded-lg bg-slate-100 animate-pulse" />
      </div>
    )
  }

  return (
    <div className="space-y-4 max-w-3xl">
      {/* Error banner */}
      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Trial heads-up banner */}
      {isTrial && postTrialLimit < limit && (
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-800 flex items-start gap-2">
          <Info className="h-4 w-4 mt-0.5 shrink-0 text-indigo-500" />
          <div className="flex-1">
            <p className="font-medium">
              Trial: {limit} goals available, drops to {postTrialLimit} after trial.
            </p>
            <p className="text-xs text-indigo-700 mt-0.5">
              Upgrade to keep all your goals active after your 14-day trial ends.{' '}
              <Link href="/dashboard/billing" className="underline font-medium">View plans →</Link>
            </p>
          </div>
        </div>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base text-slate-700 flex items-center gap-2">
              <Target className="h-4 w-4 text-slate-400" />
              Goals & Alerts
            </CardTitle>
            <p className="text-xs text-slate-400 mt-1">
              Set metric targets and get an email when this client misses (or approaches) them.
            </p>
          </div>
          <div className="text-xs text-slate-500 whitespace-nowrap">
            <span className="font-medium text-slate-700">{goals.length}/{limit}</span>
            {' '}goals used
            {!isTrial && <span className="ml-1 capitalize">on {plan} plan</span>}
          </div>
        </CardHeader>

        <CardContent className="space-y-3">
          {goals.length === 0 && (
            <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center">
              <Target className="h-8 w-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-500">No goals yet for this client.</p>
              <p className="text-xs text-slate-400 mt-1">
                Create a goal to track metrics like ROAS, sessions, or conversions against a target.
              </p>
            </div>
          )}

          {goals.map(goal => {
            const meta = metricsByKey.get(goal.metric)
            const unit = meta?.unit
            return (
              <div
                key={goal.id}
                className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 px-4 py-3 hover:bg-slate-50 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm text-slate-800 truncate">
                      {goal.metric_label ?? goal.metric}
                    </span>
                    <StatusBadge status={goal.status} />
                    {!goal.is_active && (
                      <span className="text-[10px] uppercase tracking-wide text-slate-400">Paused</span>
                    )}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    <span className="text-slate-700 font-medium">{formatValue(goal.current_value, unit)}</span>
                    {' '}<span className="text-slate-400">vs target</span>{' '}
                    <span>{CMP_SYMBOL[goal.comparison]}</span>{' '}
                    <span className="text-slate-700 font-medium">{formatValue(goal.target_value, unit)}</span>
                    {' '}<span className="text-slate-400">· {goal.period}</span>
                    {goal.period_key && <span className="text-slate-400"> · {goal.period_key}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button variant="ghost" size="sm" onClick={() => openEdit(goal)} aria-label="Edit goal">
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(goal)}
                    aria-label="Delete goal"
                    className="text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            )
          })}

          {/* Create button / at-limit CTA */}
          {atLimit ? (
            <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 text-sm">
              <p className="text-indigo-800 font-medium">
                You&apos;ve reached the {isTrial ? 'trial' : plan} plan&apos;s goal limit ({limit}/{limit}).
              </p>
              <p className="text-xs text-indigo-700 mt-1">
                {plan === 'agency'
                  ? 'Contact support if you need more goals on your Agency plan.'
                  : <>Upgrade to add more goals. <Link href="/dashboard/billing" className="underline font-medium">View plans →</Link></>
                }
              </p>
            </div>
          ) : (
            <Button onClick={openCreate} className="w-full sm:w-auto" disabled={metrics.length === 0}>
              <Plus className="h-4 w-4 mr-1" />
              Add goal
            </Button>
          )}
        </CardContent>
      </Card>

      <GoalFormDialog
        open={dialogOpen}
        onOpenChange={(v) => { setDialogOpen(v); if (!v) setEditing(null) }}
        clientId={clientId}
        metrics={metrics}
        editing={editing}
        onSaved={handleSaved}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Create / Edit dialog
// ---------------------------------------------------------------------------

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  clientId: string
  metrics: GoalMetric[]
  editing: Goal | null
  onSaved: () => void | Promise<void>
}

function GoalFormDialog({ open, onOpenChange, clientId, metrics, editing, onSaved }: DialogProps) {
  // Form state — plain useState, no react-hook-form (matches existing tabs).
  const [metric,        setMetric]        = useState<string>('')
  const [comparison,    setComparison]    = useState<GoalComparison>('gte')
  const [targetValue,   setTargetValue]   = useState<string>('')
  const [tolerancePct,  setTolerancePct]  = useState<string>('5')
  const [period,        setPeriod]        = useState<GoalPeriod>('monthly')
  const [isActive,      setIsActive]      = useState<boolean>(true)
  const [alertEmails,   setAlertEmails]   = useState<string>('')   // comma-separated
  const [saving,        setSaving]        = useState<boolean>(false)

  // Reset form when opening for create vs edit.
  useEffect(() => {
    if (!open) return
    if (editing) {
      setMetric(editing.metric)
      setComparison(editing.comparison)
      setTargetValue(String(editing.target_value))
      setTolerancePct(String(editing.tolerance_pct))
      setPeriod(editing.period)
      setIsActive(editing.is_active)
      setAlertEmails((editing.alert_emails ?? []).join(', '))
    } else {
      // Default metric = first one with a sane higher-is-better direction.
      const first = metrics[0]
      setMetric(first?.key ?? '')
      setComparison(first?.direction === 'lower_is_better' ? 'lte' : 'gte')
      setTargetValue('')
      setTolerancePct('5')
      setPeriod('monthly')
      setIsActive(true)
      setAlertEmails('')
    }
  }, [open, editing, metrics])

  // Auto-flip comparison when user picks a new metric, so a CPA goal defaults
  // to "lte" and a sessions goal defaults to "gte". User can still override.
  const handleMetricChange = (key: string) => {
    setMetric(key)
    if (!editing) {
      const meta = metrics.find(m => m.key === key)
      if (meta) setComparison(meta.direction === 'lower_is_better' ? 'lte' : 'gte')
    }
  }

  const selectedMeta = metrics.find(m => m.key === metric)
  const unitHint = selectedMeta ? unitLabel(selectedMeta.unit) : ''

  const handleSave = async () => {
    const targetNum = Number(targetValue)
    if (!metric) { toast.error('Select a metric.'); return }
    if (!Number.isFinite(targetNum) || targetNum <= 0) {
      toast.error('Target must be a positive number.')
      return
    }
    const tolNum = Number(tolerancePct)
    if (!Number.isFinite(tolNum) || tolNum < 0 || tolNum > 100) {
      toast.error('Tolerance must be between 0 and 100.')
      return
    }
    const emails = alertEmails
      .split(',')
      .map(e => e.trim())
      .filter(Boolean)
    const bad = emails.find(e => !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e))
    if (bad) { toast.error(`"${bad}" is not a valid email.`); return }

    const payload: GoalCreatePayload = {
      metric,
      comparison,
      target_value: targetNum,
      tolerance_pct: tolNum,
      period,
      is_active: isActive,
      alert_emails: emails,
    }

    setSaving(true)
    try {
      if (editing) {
        await goalsApi.update(clientId, editing.id, payload)
        toast.success('Goal updated.')
      } else {
        await goalsApi.create(clientId, payload)
        toast.success('Goal created.')
      }
      await onSaved()
    } catch (err: unknown) {
      // Surface backend validation / plan-limit messages when available.
      const detail = extractErrorDetail(err)
      toast.error(detail || 'Failed to save goal.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{editing ? 'Edit goal' : 'Add goal'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Metric selector */}
          <div>
            <label className="text-xs font-medium text-slate-700 block mb-1">Metric</label>
            <select
              value={metric}
              onChange={e => handleMetricChange(e.target.value)}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {metrics.length === 0 && <option value="">Loading metrics…</option>}
              {metrics.map(m => (
                <option key={m.key} value={m.key}>
                  {platformLabel(m.platform)} — {m.label}
                </option>
              ))}
            </select>
          </div>

          {/* Comparison + target */}
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="text-xs font-medium text-slate-700 block mb-1">Goal is</label>
              <select
                value={comparison}
                onChange={e => setComparison(e.target.value as GoalComparison)}
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="gte">≥ at least</option>
                <option value="lte">≤ at most</option>
                <option value="eq">= equal to</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="text-xs font-medium text-slate-700 block mb-1">
                Target {unitHint && <span className="text-slate-400">({unitHint})</span>}
              </label>
              <Input
                type="number"
                inputMode="decimal"
                step="any"
                min={0}
                value={targetValue}
                onChange={e => setTargetValue(e.target.value)}
                placeholder="e.g. 1000"
              />
            </div>
          </div>

          {/* Tolerance — only meaningful for eq goals, but shown always for consistency */}
          {comparison === 'eq' && (
            <div>
              <label className="text-xs font-medium text-slate-700 block mb-1">
                Tolerance (±%)
              </label>
              <Input
                type="number"
                min={0}
                max={100}
                step={1}
                value={tolerancePct}
                onChange={e => setTolerancePct(e.target.value)}
              />
              <p className="text-xs text-slate-400 mt-1">
                On-track if actual is within ±{tolerancePct || '5'}% of target.
              </p>
            </div>
          )}

          {/* Period */}
          <div>
            <label className="text-xs font-medium text-slate-700 block mb-1">Period</label>
            <div className="flex gap-2">
              {(['monthly', 'weekly'] as GoalPeriod[]).map(p => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPeriod(p)}
                  className={`flex-1 px-3 py-2 text-sm rounded-md border transition-colors capitalize
                    ${period === p
                      ? 'border-indigo-500 bg-indigo-50 text-indigo-700 font-medium'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'}`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Alert recipients */}
          <div>
            <label className="text-xs font-medium text-slate-700 block mb-1">
              Alert recipients <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <Input
              type="text"
              value={alertEmails}
              onChange={e => setAlertEmails(e.target.value)}
              placeholder="hello@agency.com, pm@agency.com"
            />
            <p className="text-xs text-slate-400 mt-1">
              Leave empty to use your agency email. Separate multiple with commas.
            </p>
          </div>

          {/* Active toggle */}
          <label className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 cursor-pointer hover:bg-slate-50">
            <div>
              <p className="text-sm font-medium text-slate-700">Goal is active</p>
              <p className="text-xs text-slate-400">Disable to pause alerts without deleting.</p>
            </div>
            <input
              type="checkbox"
              checked={isActive}
              onChange={e => setIsActive(e.target.checked)}
              className="h-4 w-4 accent-indigo-600"
            />
          </label>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving && <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />}
            {editing ? 'Save changes' : 'Create goal'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

function unitLabel(unit: string): string {
  switch (unit) {
    case 'percent':  return '%'
    case 'ratio':    return 'x'
    case 'currency': return '$'
    case 'int':      return 'count'
    default:         return unit
  }
}

function platformLabel(platform: string): string {
  switch (platform) {
    case 'ga4':            return 'GA4'
    case 'meta_ads':       return 'Meta Ads'
    case 'google_ads':     return 'Google Ads'
    case 'search_console': return 'Search Console'
    default:               return platform
  }
}

function extractErrorDetail(err: unknown): string | null {
  if (typeof err !== 'object' || err === null) return null
  const e = err as { response?: { data?: { detail?: unknown } } }
  const d = e.response?.data?.detail
  return typeof d === 'string' ? d : null
}
