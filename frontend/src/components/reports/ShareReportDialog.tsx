'use client'

// Share Report Dialog — creates a shareable public link with optional password and expiry.

import { useEffect, useState } from 'react'
import { Copy, Check, Loader2, Trash2, X as XIcon, Share2, ExternalLink } from 'lucide-react'
import { shareApi } from '@/lib/api'
import type { ShareLink } from '@/types'

interface Props {
  reportId: string
  onClose: () => void
}

export default function ShareReportDialog({ reportId, onClose }: Props) {
  const [links,     setLinks]     = useState<ShareLink[]>([])
  const [loading,   setLoading]   = useState(true)
  const [creating,  setCreating]  = useState(false)
  const [revoking,  setRevoking]  = useState<string | null>(null)
  const [error,     setError]     = useState<string | null>(null)
  const [copied,    setCopied]    = useState<string | null>(null)

  // New link form state
  const [password,     setPassword]     = useState('')
  const [expiresDays,  setExpiresDays]  = useState<number | ''>('')
  const [showPassword, setShowPassword] = useState(false)

  // Load existing share links
  useEffect(() => {
    const load = async () => {
      try {
        const data = await shareApi.list(reportId)
        setLinks(Array.isArray(data) ? data : (data.links ?? []))
      } catch {
        // Non-fatal — just show empty state
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [reportId])

  const handleCreate = async () => {
    setCreating(true)
    setError(null)
    try {
      const payload: { password?: string; expires_days?: number } = {}
      if (password.trim()) payload.password = password.trim()
      if (expiresDays !== '' && Number(expiresDays) > 0) payload.expires_days = Number(expiresDays)
      const newLink: ShareLink = await shareApi.create(reportId, payload)
      setLinks((prev) => [newLink, ...prev])
      setPassword('')
      setExpiresDays('')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create link.')
    } finally {
      setCreating(false)
    }
  }

  const handleRevoke = async (hash: string) => {
    setRevoking(hash)
    setError(null)
    try {
      await shareApi.revoke(reportId, hash)
      setLinks((prev) => prev.filter((l) => l.share_hash !== hash))
    } catch {
      setError('Failed to revoke link.')
    } finally {
      setRevoking(null)
    }
  }

  const handleCopy = (url: string, hash: string) => {
    navigator.clipboard.writeText(url).then(() => {
      setCopied(hash)
      setTimeout(() => setCopied(null), 2000)
    })
  }

  const formatDate = (d: string | null) => {
    if (!d) return 'Never expires'
    try {
      return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
    } catch {
      return d
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl bg-white shadow-2xl border border-slate-200 flex flex-col max-h-[90vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Share2 className="h-5 w-5 text-indigo-600" />
            Share Report
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
            <XIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="overflow-y-auto flex-1 px-6 py-4 space-y-5">

          {/* Create new link form */}
          <div className="rounded-lg border border-slate-200 p-4 space-y-3 bg-slate-50">
            <p className="text-sm font-semibold text-slate-700">Create new link</p>

            <div className="grid sm:grid-cols-2 gap-3">
              {/* Optional password */}
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">
                  Password (optional)
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Leave blank for public"
                    className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 pr-16 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? 'hide' : 'show'}
                  </button>
                </div>
              </div>

              {/* Expiry in days */}
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">
                  Expires after (days, optional)
                </label>
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={expiresDays}
                  onChange={(e) => setExpiresDays(e.target.value === '' ? '' : Number(e.target.value))}
                  placeholder="e.g. 30"
                  className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
            </div>

            {error && (
              <p className="text-xs text-rose-600 bg-rose-50 border border-rose-100 rounded-md px-3 py-2">
                {error}
              </p>
            )}

            <button
              onClick={handleCreate}
              disabled={creating}
              className="flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors disabled:opacity-60"
            >
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Share2 className="h-4 w-4" />}
              {creating ? 'Creating…' : 'Generate Link'}
            </button>
          </div>

          {/* Existing links */}
          <div>
            <p className="text-sm font-semibold text-slate-700 mb-3">
              Active links{links.length > 0 && <span className="text-slate-400 font-normal"> ({links.length})</span>}
            </p>

            {loading ? (
              <div className="flex justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-slate-300" />
              </div>
            ) : links.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-4">
                No share links yet. Create one above.
              </p>
            ) : (
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link.share_hash} className="rounded-lg border border-slate-200 bg-white p-3 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <p className="text-xs text-slate-500 truncate font-mono">{link.share_url}</p>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`text-[10px] font-semibold rounded-full px-2 py-0.5 ${
                            link.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'
                          }`}>
                            {link.is_active ? 'Active' : 'Inactive'}
                          </span>
                          {link.has_password && (
                            <span className="text-[10px] font-semibold rounded-full px-2 py-0.5 bg-amber-50 text-amber-700">
                              Password protected
                            </span>
                          )}
                          <span className="text-[10px] text-slate-400">
                            Expires: {formatDate(link.expires_at)}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <a
                          href={link.share_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          title="Open in new tab"
                          className="p-1.5 rounded-md text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                        <button
                          onClick={() => handleCopy(link.share_url, link.share_hash)}
                          title="Copy link"
                          className="p-1.5 rounded-md text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                        >
                          {copied === link.share_hash
                            ? <Check className="h-4 w-4 text-emerald-600" />
                            : <Copy className="h-4 w-4" />}
                        </button>
                        <button
                          onClick={() => handleRevoke(link.share_hash)}
                          disabled={revoking === link.share_hash}
                          title="Revoke link"
                          className="p-1.5 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-60"
                        >
                          {revoking === link.share_hash
                            ? <Loader2 className="h-4 w-4 animate-spin" />
                            : <Trash2 className="h-4 w-4" />}
                        </button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-100 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-md border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
