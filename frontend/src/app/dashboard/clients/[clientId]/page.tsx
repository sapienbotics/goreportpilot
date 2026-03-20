'use client'

// Client detail page — shows client info, connected platforms, recent reports
// Includes edit-in-place and delete (soft-delete)

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Globe, Mail, Building2, Pencil, Trash2, Check, X as XIcon } from 'lucide-react'
import { clientsApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type { Client } from '@/types'

interface Props {
  params: { clientId: string }
}

export default function ClientDetailPage({ params }: Props) {
  const router = useRouter()
  const { clientId } = params

  const [client, setClient] = useState<Client | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [editValues, setEditValues] = useState<Partial<Client>>({})

  useEffect(() => {
    const fetchClient = async () => {
      try {
        const data = await clientsApi.get(clientId)
        setClient(data)
        setEditValues(data)
      } catch {
        setError('Client not found or failed to load.')
      } finally {
        setLoading(false)
      }
    }
    fetchClient()
  }, [clientId])

  const handleSave = async () => {
    if (!client) return
    setSaving(true)
    try {
      const updated = await clientsApi.update(client.id, {
        name: editValues.name,
        website_url: editValues.website_url ?? undefined,
        industry: editValues.industry ?? undefined,
        primary_contact_email: editValues.primary_contact_email ?? undefined,
        goals_context: editValues.goals_context ?? undefined,
        notes: editValues.notes ?? undefined,
      })
      setClient(updated)
      setEditing(false)
    } catch {
      setError('Failed to save changes.')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!client) return
    if (!window.confirm(`Delete ${client.name}? This cannot be undone.`)) return
    setDeleting(true)
    try {
      await clientsApi.delete(client.id)
      router.push('/dashboard/clients')
    } catch {
      setError('Failed to delete client.')
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="h-8 w-48 rounded bg-slate-100 animate-pulse" />
        <div className="h-64 rounded-xl bg-slate-100 animate-pulse" />
      </div>
    )
  }

  if (error || !client) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error ?? 'Client not found.'}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Page header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1
            className="text-2xl font-bold text-slate-900"
            style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
          >
            {client.name}
          </h1>
          {client.industry && (
            <p className="mt-1 text-slate-500 text-sm flex items-center gap-1">
              <Building2 className="h-3.5 w-3.5" />
              {client.industry}
            </p>
          )}
        </div>

        <div className="flex gap-2">
          {editing ? (
            <>
              <button
                onClick={() => { setEditing(false); setEditValues(client) }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
              >
                <XIcon className="h-4 w-4" /> Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-800 transition-colors disabled:opacity-60"
              >
                <Check className="h-4 w-4" /> {saving ? 'Saving…' : 'Save'}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setEditing(true)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
              >
                <Pencil className="h-4 w-4" /> Edit
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-white px-3 py-1.5 text-sm text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-60"
              >
                <Trash2 className="h-4 w-4" /> {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700">Client details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <Field label="Name">
            {editing ? (
              <Input
                value={editValues.name ?? ''}
                onChange={(e) => setEditValues((v) => ({ ...v, name: e.target.value }))}
              />
            ) : (
              <span>{client.name}</span>
            )}
          </Field>

          <Field label="Website">
            {editing ? (
              <Input
                value={editValues.website_url ?? ''}
                onChange={(e) => setEditValues((v) => ({ ...v, website_url: e.target.value }))}
                placeholder="https://example.com"
                type="url"
              />
            ) : client.website_url ? (
              <a
                href={client.website_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-700 hover:underline flex items-center gap-1"
              >
                <Globe className="h-3.5 w-3.5" />
                {client.website_url.replace(/^https?:\/\//, '')}
              </a>
            ) : (
              <span className="text-slate-400">—</span>
            )}
          </Field>

          <Field label="Industry">
            {editing ? (
              <Input
                value={editValues.industry ?? ''}
                onChange={(e) => setEditValues((v) => ({ ...v, industry: e.target.value }))}
                placeholder="e.g. E-commerce"
              />
            ) : (
              <span>{client.industry ?? <span className="text-slate-400">—</span>}</span>
            )}
          </Field>

          <Field label="Contact email">
            {editing ? (
              <Input
                value={editValues.primary_contact_email ?? ''}
                onChange={(e) => setEditValues((v) => ({ ...v, primary_contact_email: e.target.value }))}
                type="email"
                placeholder="jane@example.com"
              />
            ) : client.primary_contact_email ? (
              <a
                href={`mailto:${client.primary_contact_email}`}
                className="text-indigo-700 hover:underline flex items-center gap-1"
              >
                <Mail className="h-3.5 w-3.5" />
                {client.primary_contact_email}
              </a>
            ) : (
              <span className="text-slate-400">—</span>
            )}
          </Field>

          <Field label="Goals & context">
            {editing ? (
              <Textarea
                value={editValues.goals_context ?? ''}
                onChange={(e) => setEditValues((v) => ({ ...v, goals_context: e.target.value }))}
                placeholder="Goals, KPIs, context for AI reports…"
                rows={4}
              />
            ) : (
              <span className="whitespace-pre-wrap">
                {client.goals_context ?? <span className="text-slate-400">—</span>}
              </span>
            )}
          </Field>
        </CardContent>
      </Card>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-4 items-start">
      <span className="text-sm font-medium text-slate-500 pt-1">{label}</span>
      <div className="col-span-2 text-sm text-slate-800">{children}</div>
    </div>
  )
}
