'use client'
import {
  Globe, Mail, Building2, Pencil, Trash2, Check, X as XIcon,
  Upload, Loader2,
} from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import LanguageSelector, { LANGUAGES } from '@/components/clients/LanguageSelector'
import BusinessContextField, { computeQuality } from '@/components/clients/BusinessContextField'
import type { Client } from '@/types'

interface Props {
  client: Client
  editing: boolean
  setEditing: (v: boolean) => void
  saving: boolean
  deleting: boolean
  editValues: Partial<Client>
  setEditValues: React.Dispatch<React.SetStateAction<Partial<Client>>>
  clientLogo: string
  logoUploading: boolean
  logoInputRef: React.RefObject<HTMLInputElement>
  handleSave: () => void
  handleDelete: () => void
  handleLogoUpload: (e: React.ChangeEvent<HTMLInputElement>) => void
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-4 items-start">
      <span className="text-sm font-medium text-slate-500 pt-1">{label}</span>
      <div className="col-span-2 text-sm text-slate-800">{children}</div>
    </div>
  )
}

export default function SettingsTab({
  client, editing, setEditing, saving, deleting,
  editValues, setEditValues,
  clientLogo, logoUploading, logoInputRef,
  handleSave, handleDelete, handleLogoUpload,
}: Props) {
  return (
    <div className="space-y-4 max-w-2xl">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              {/* Logo */}
              {clientLogo ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={clientLogo} alt="Client logo" className="h-10 w-10 object-contain rounded-md border border-slate-200 bg-slate-50 p-0.5" />
              ) : (
                <div className="flex h-10 w-10 items-center justify-center rounded-md border-2 border-dashed border-slate-200 bg-slate-50">
                  <Building2 className="h-4 w-4 text-slate-300" />
                </div>
              )}
              <button onClick={() => logoInputRef.current?.click()} disabled={logoUploading}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600 hover:bg-slate-50 transition-colors disabled:opacity-60">
                {logoUploading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Upload className="h-3 w-3" />}
                {logoUploading ? 'Uploading…' : 'Logo'}
              </button>
              <input ref={logoInputRef} type="file" accept="image/*" onChange={handleLogoUpload} className="hidden" />
            </div>
            {/* Edit / Save / Cancel / Delete */}
            <div className="flex gap-2">
              {editing ? (
                <>
                  <button onClick={() => { setEditing(false); setEditValues(client) }}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 transition-colors">
                    <XIcon className="h-4 w-4" /> Cancel
                  </button>
                  <button onClick={handleSave} disabled={saving}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-800 transition-colors disabled:opacity-60">
                    <Check className="h-4 w-4" /> {saving ? 'Saving…' : 'Save'}
                  </button>
                </>
              ) : (
                <>
                  <button onClick={() => setEditing(true)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 transition-colors">
                    <Pencil className="h-4 w-4" /> Edit
                  </button>
                  <button onClick={handleDelete} disabled={deleting}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-white px-3 py-1.5 text-sm text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-60">
                    <Trash2 className="h-4 w-4" /> {deleting ? 'Deleting…' : 'Delete'}
                  </button>
                </>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          <Field label="Name">
            {editing ? (
              <Input value={editValues.name ?? ''} onChange={e => setEditValues(v => ({ ...v, name: e.target.value }))} />
            ) : <span>{client.name}</span>}
          </Field>

          <Field label="Website">
            {editing ? (
              <Input value={editValues.website_url ?? ''} onChange={e => setEditValues(v => ({ ...v, website_url: e.target.value }))} placeholder="https://example.com" type="url" />
            ) : client.website_url ? (
              <a href={client.website_url} target="_blank" rel="noopener noreferrer" className="text-indigo-700 hover:underline flex items-center gap-1">
                <Globe className="h-3.5 w-3.5" />
                {client.website_url.replace(/^https?:\/\//, '')}
              </a>
            ) : <span className="text-slate-400">—</span>}
          </Field>

          <Field label="Industry">
            {editing ? (
              <Input value={editValues.industry ?? ''} onChange={e => setEditValues(v => ({ ...v, industry: e.target.value }))} placeholder="e.g. E-commerce" />
            ) : <span>{client.industry ?? <span className="text-slate-400">—</span>}</span>}
          </Field>

          <Field label="Contact email">
            {editing ? (
              <Input value={editValues.primary_contact_email ?? ''} onChange={e => setEditValues(v => ({ ...v, primary_contact_email: e.target.value }))} type="email" placeholder="jane@example.com" />
            ) : client.primary_contact_email ? (
              <a href={`mailto:${client.primary_contact_email}`} className="text-indigo-700 hover:underline flex items-center gap-1">
                <Mail className="h-3.5 w-3.5" />
                {client.primary_contact_email}
              </a>
            ) : <span className="text-slate-400">—</span>}
          </Field>

          <Field label="Business Context">
            {editing ? (
              <BusinessContextField
                value={editValues.goals_context ?? ''}
                onChange={(next) => setEditValues(v => ({ ...v, goals_context: next }))}
                showLabel={false}
                rows={4}
              />
            ) : (
              <div className="space-y-1">
                {client.goals_context ? (
                  <>
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-block h-2 w-2 rounded-full ${
                          computeQuality(client.goals_context) === 'good' ? 'bg-emerald-500'
                          : computeQuality(client.goals_context) === 'medium' ? 'bg-amber-400'
                          : computeQuality(client.goals_context) === 'low' ? 'bg-amber-500'
                          : 'bg-rose-500'
                        }`}
                        title="Context quality — longer and goal-oriented text unlocks better AI recommendations."
                      />
                      <span className="text-xs text-slate-400">
                        {client.goals_context.length} characters
                      </span>
                    </div>
                    <span className="whitespace-pre-wrap">{client.goals_context}</span>
                  </>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="inline-block h-2 w-2 rounded-full bg-rose-500" title="Empty — reports will use generic AI analysis." />
                    <span className="text-slate-400">—</span>
                  </div>
                )}
              </div>
            )}
          </Field>

          <Field label="Report language">
            {editing ? (
              <LanguageSelector
                value={editValues.report_language ?? 'en'}
                onChange={lang => setEditValues(v => ({ ...v, report_language: lang }))}
                showLabel={false}
              />
            ) : (() => {
              const lang = LANGUAGES.find(l => l.code === (client.report_language ?? 'en'))
              return (
                <span className="flex items-center gap-1.5 text-slate-700">
                  <span>{lang?.flag ?? '🇺🇸'}</span>
                  <span>{lang?.name ?? 'English'}</span>
                  {!client.report_language && (
                    <span className="text-slate-400 text-xs">(default)</span>
                  )}
                </span>
              )
            })()}
          </Field>
        </CardContent>
      </Card>

      {/* Danger zone */}
      <Card className="border-rose-100">
        <CardContent className="pt-5">
          <p className="text-sm font-semibold text-rose-600 mb-1">Danger Zone</p>
          <p className="text-xs text-slate-500 mb-3">Deleting this client removes all their connections and report history permanently.</p>
          <button onClick={handleDelete} disabled={deleting}
            className="inline-flex items-center gap-1.5 rounded-lg border border-rose-300 bg-white px-3 py-1.5 text-sm text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-60">
            <Trash2 className="h-4 w-4" /> {deleting ? 'Deleting…' : `Delete ${client.name}`}
          </button>
        </CardContent>
      </Card>
    </div>
  )
}
