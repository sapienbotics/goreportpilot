'use client'

import { useState } from 'react'
import { Loader2, AlertTriangle, X } from 'lucide-react'

interface ConfirmDeleteDialogProps {
  email: string
  onConfirm: () => Promise<void>
  onClose: () => void
}

export function ConfirmDeleteDialog({ email, onConfirm, onClose }: ConfirmDeleteDialogProps) {
  const [typed, setTyped] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const matches = typed.trim().toLowerCase() === email.toLowerCase()

  const handleDelete = async () => {
    if (!matches) return
    setDeleting(true)
    setError(null)
    try {
      await onConfirm()
      onClose()
    } catch {
      setError('Failed to delete user. Please try again.')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-xl bg-white shadow-2xl border border-slate-200 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-rose-700 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Delete User Permanently
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <p className="text-sm text-slate-600">
          This action is <strong>irreversible</strong>. All user data including clients, reports,
          connections, and billing records will be permanently deleted (GDPR erasure).
        </p>

        <div>
          <label className="block text-xs font-semibold text-slate-500 mb-1">
            Type <span className="font-mono text-rose-600">{email}</span> to confirm
          </label>
          <input
            type="text"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-rose-300"
            placeholder={email}
          />
        </div>

        {error && (
          <p className="text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">{error}</p>
        )}

        <div className="flex gap-2 pt-1">
          <button
            onClick={handleDelete}
            disabled={!matches || deleting}
            className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-rose-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-rose-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <AlertTriangle className="h-4 w-4" />}
            {deleting ? 'Deleting...' : 'Delete User Forever'}
          </button>
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
