'use client'

import { useState } from 'react'
import { Loader2, X } from 'lucide-react'

interface GDPRRequestModalProps {
  initial?: { id?: string; user_email?: string; request_type?: string; status?: string; admin_notes?: string }
  onSave: (data: { user_email: string; request_type: string; admin_notes?: string; status?: string }) => Promise<void>
  onClose: () => void
}

const TYPES = ['access', 'portability', 'erasure', 'rectification', 'restriction'] as const
const STATUSES = ['pending', 'in_progress', 'completed', 'rejected'] as const

export function GDPRRequestModal({ initial, onSave, onClose }: GDPRRequestModalProps) {
  const isEdit = !!initial?.id
  const [email, setEmail] = useState(initial?.user_email ?? '')
  const [type, setType] = useState(initial?.request_type ?? 'access')
  const [reqStatus, setReqStatus] = useState(initial?.status ?? 'pending')
  const [notes, setNotes] = useState(initial?.admin_notes ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSave = async () => {
    if (!email.trim()) { setError('Email is required'); return }
    setSaving(true); setError(null)
    try {
      await onSave({ user_email: email, request_type: type, admin_notes: notes, status: isEdit ? reqStatus : undefined })
      onClose()
    } catch {
      setError('Failed to save. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-xl bg-white shadow-2xl border border-slate-200 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">{isEdit ? 'Edit GDPR Request' : 'New GDPR Request'}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X className="h-5 w-5" /></button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">User Email</label>
            <input
              type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              disabled={isEdit}
              className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm disabled:bg-slate-50"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">Request Type</label>
            <select
              value={type} onChange={(e) => setType(e.target.value)} disabled={isEdit}
              className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm disabled:bg-slate-50"
            >
              {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          {isEdit && (
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Status</label>
              <select
                value={reqStatus} onChange={(e) => setReqStatus(e.target.value)}
                className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
              >
                {STATUSES.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">Admin Notes</label>
            <textarea
              value={notes} onChange={(e) => setNotes(e.target.value)} rows={3}
              className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm resize-y"
            />
          </div>
        </div>

        {error && <p className="text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">{error}</p>}

        <div className="flex gap-2 pt-1">
          <button
            onClick={handleSave} disabled={saving}
            className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-60"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {saving ? 'Saving...' : isEdit ? 'Update' : 'Create'}
          </button>
          <button onClick={onClose} className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50">Cancel</button>
        </div>
      </div>
    </div>
  )
}
