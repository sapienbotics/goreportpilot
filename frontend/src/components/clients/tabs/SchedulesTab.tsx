'use client'
import { Clock, Check, Loader2, Lock } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { ScheduledReport, ScheduledReportPayload } from '@/lib/api'
import type { Client } from '@/types'
import { TIMEZONE_OPTIONS, utcToLocalTime, getTimezoneShortLabel } from '@/lib/timezone-utils'
import { usePlanFeatures } from '@/hooks/usePlanFeatures'

// All visual templates the backend supports. Plan gating is computed
// against the current user's ``features.visual_templates`` list — any
// template NOT in that list is rendered disabled with a "(Pro)" suffix.
const VISUAL_TEMPLATE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'modern_clean',    label: 'Modern Clean' },
  { value: 'dark_executive',  label: 'Dark Executive' },
  { value: 'colorful_agency', label: 'Colorful Agency' },
  { value: 'bold_geometric',  label: 'Bold Geometric' },
  { value: 'minimal_elegant', label: 'Minimal Elegant' },
  { value: 'gradient_modern', label: 'Gradient Modern' },
]

interface Props {
  client: Client
  schedule: ScheduledReport | null
  schedEnabled: boolean
  setSchedEnabled: (v: boolean) => void
  schedForm: ScheduledReportPayload
  setSchedForm: React.Dispatch<React.SetStateAction<ScheduledReportPayload>>
  schedTimezone: string
  setSchedTimezone: (tz: string) => void
  savingSched: boolean
  schedSaved: boolean
  handleSaveSchedule: () => void
}

export default function SchedulesTab({
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  client, schedule,
  schedEnabled, setSchedEnabled,
  schedForm, setSchedForm,
  schedTimezone, setSchedTimezone,
  savingSched, schedSaved, handleSaveSchedule,
}: Props) {
  // The schedule row from the API stores `time_utc` in UTC; convert it for display.
  const scheduleLocalTime = schedule ? utcToLocalTime(schedule.time_utc, schedTimezone) : ''
  const { features: planFeatures } = usePlanFeatures()
  return (
    <div className="space-y-4 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700 flex items-center gap-2">
            <Clock className="h-4 w-4 text-slate-400" />
            Automated Reports
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3 cursor-pointer hover:bg-slate-50 transition-colors">
            <div>
              <p className="text-sm font-medium text-slate-700">Enable automatic report generation</p>
              <p className="text-xs text-slate-400 mt-0.5">Reports will be generated on the schedule below</p>
            </div>
            <div onClick={() => setSchedEnabled(!schedEnabled)}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${schedEnabled ? 'bg-indigo-700' : 'bg-slate-200'}`}>
              <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${schedEnabled ? 'translate-x-4' : 'translate-x-1'}`} />
            </div>
          </label>

          {schedEnabled && (
            <div className="space-y-4 rounded-lg border border-slate-100 bg-slate-50 p-4">
              <div className="flex flex-wrap gap-4 items-end">
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1.5">Frequency</label>
                  <select value={schedForm.frequency}
                    onChange={e => setSchedForm(f => ({ ...f, frequency: e.target.value as ScheduledReportPayload['frequency'] }))}
                    className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                    <option value="weekly">Weekly</option>
                    <option value="biweekly">Bi-weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>

                {schedForm.frequency === 'monthly' ? (
                  <div>
                    <label className="block text-xs font-medium text-slate-500 mb-1.5">On day</label>
                    <select value={schedForm.day_of_month ?? 1}
                      onChange={e => setSchedForm(f => ({ ...f, day_of_month: +e.target.value }))}
                      className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                      {Array.from({ length: 28 }, (_, i) => i + 1).map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                ) : (
                  <div>
                    <label className="block text-xs font-medium text-slate-500 mb-1.5">On</label>
                    <select value={schedForm.day_of_week ?? 0}
                      onChange={e => setSchedForm(f => ({ ...f, day_of_week: +e.target.value }))}
                      className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                      {['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].map((d, i) => <option key={d} value={i}>{d}</option>)}
                    </select>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1.5">At</label>
                  <Input type="time" value={schedForm.time_utc}
                    onChange={e => setSchedForm(f => ({ ...f, time_utc: e.target.value }))}
                    className="w-28" />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1.5">Timezone</label>
                  <select value={schedTimezone}
                    onChange={e => setSchedTimezone(e.target.value)}
                    className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                    {TIMEZONE_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1.5">Report detail level</label>
                <select value={schedForm.template}
                  onChange={e => setSchedForm(f => ({ ...f, template: e.target.value }))}
                  className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  <option value="full">Full Report — 8 slides</option>
                  <option value="summary">Summary — 4 slides</option>
                  <option value="brief">One-Page Brief — 2 slides</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1.5 flex items-center gap-1">
                  Visual style
                  {!planFeatures.visual_templates.includes(schedForm.visual_template ?? 'modern_clean') && (
                    <Lock className="h-3 w-3 text-amber-500" />
                  )}
                </label>
                <select value={schedForm.visual_template ?? 'modern_clean'}
                  onChange={e => setSchedForm(f => ({ ...f, visual_template: e.target.value }))}
                  className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  {VISUAL_TEMPLATE_OPTIONS.map(opt => {
                    const locked = !planFeatures.visual_templates.includes(opt.value)
                    return (
                      <option key={opt.value} value={opt.value} disabled={locked}>
                        {opt.label}{locked ? ' (Pro)' : ''}
                      </option>
                    )
                  })}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1.5">Attachment format</label>
                <select value={schedForm.attachment_type ?? 'both'}
                  onChange={e => setSchedForm(f => ({ ...f, attachment_type: e.target.value as 'pdf' | 'pptx' | 'both' }))}
                  className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  <option value="both">Both (PDF + PPTX)</option>
                  <option value="pdf">PDF only</option>
                  <option value="pptx">PPTX only</option>
                </select>
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={schedForm.auto_send}
                  onChange={e => setSchedForm(f => ({ ...f, auto_send: e.target.checked }))}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                <span className="text-sm text-slate-700">Auto-send report to client via email</span>
              </label>

              {schedForm.auto_send && (
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1.5">Send to (comma-separated emails)</label>
                  <Input value={schedForm.send_to_emails?.join(', ') ?? ''}
                    onChange={e => setSchedForm(f => ({ ...f, send_to_emails: e.target.value.split(',').map(s => s.trim()).filter(Boolean) }))}
                    placeholder="client@company.com, ceo@company.com" />
                </div>
              )}

              {schedule && (
                <div className="text-xs text-gray-400 space-y-0.5">
                  {schedule.next_run_at && (
                    <p>Next report: {new Date(schedule.next_run_at).toLocaleDateString('en-US', { weekday:'short', year:'numeric', month:'short', day:'numeric' })} at {scheduleLocalTime} ({getTimezoneShortLabel(schedTimezone)})</p>
                  )}
                  {schedule.last_generated_at && (
                    <p>Last generated: {new Date(schedule.last_generated_at).toLocaleDateString('en-US', { weekday:'short', year:'numeric', month:'short', day:'numeric' })}</p>
                  )}
                  <p>Scheduled reports may take up to 15 minutes to trigger after the set time.</p>
                </div>
              )}
            </div>
          )}

          <div className="flex items-center gap-3">
            <button onClick={handleSaveSchedule} disabled={savingSched}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-60">
              {savingSched ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              {savingSched ? 'Saving…' : 'Save Schedule'}
            </button>
            {schedSaved && <span className="text-sm text-emerald-600 font-medium">✓ Saved</span>}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
