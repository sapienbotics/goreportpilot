'use client'

// Settings page — agency profile, white-label branding, email, AI prefs, notifications.
// Each tab calls PATCH /api/settings/profile with the relevant field subset.

import { useEffect, useRef, useState } from 'react'
import { Check, Loader2, Upload, User, Palette, Mail, Sparkles, Bell } from 'lucide-react'
import { settingsApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

// ── Tab definitions ──────────────────────────────────────────────────────────

const TABS = [
  { id: 'account',       label: 'Account',        Icon: User     },
  { id: 'branding',      label: 'Agency Branding', Icon: Palette  },
  { id: 'email',         label: 'Email Settings',  Icon: Mail     },
  { id: 'ai',            label: 'AI Preferences',  Icon: Sparkles },
  { id: 'notifications', label: 'Notifications',   Icon: Bell     },
] as const

type TabId = typeof TABS[number]['id']

// ── Timezone options ─────────────────────────────────────────────────────────

const TIMEZONES = [
  'UTC', 'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific',
  'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Istanbul',
  'Asia/Kolkata', 'Asia/Dubai', 'Asia/Singapore', 'Asia/Tokyo',
  'Asia/Shanghai', 'Australia/Sydney', 'America/Sao_Paulo',
]

const AI_TONES = [
  { value: 'professional',  label: 'Professional — authoritative, data-backed'    },
  { value: 'conversational', label: 'Conversational — warm, jargon-free'           },
  { value: 'executive',     label: 'Executive — ultra-concise, bullet-point style' },
  { value: 'data_heavy',    label: 'Data-Heavy — comprehensive, analytical'        },
]

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('account')
  const [loading,   setLoading]   = useState(true)
  const [profile,   setProfile]   = useState<Record<string, unknown>>({})

  // Per-tab save state
  const [saving,  setSaving]  = useState(false)
  const [saved,   setSaved]   = useState(false)
  const [saveErr, setSaveErr] = useState<string | null>(null)

  // Logo upload
  const logoInputRef    = useRef<HTMLInputElement>(null)
  const [logoUploading, setLogoUploading] = useState(false)
  const [logoPreview,   setLogoPreview]   = useState<string>('')

  // ── Load profile on mount ──────────────────────────────────────────────────
  useEffect(() => {
    settingsApi.getProfile()
      .then((data) => {
        setProfile(data)
        setLogoPreview((data.agency_logo_url as string) || '')
      })
      .catch(() => { /* non-fatal */ })
      .finally(() => setLoading(false))
  }, [])

  // ── Save helpers ──────────────────────────────────────────────────────────
  const save = async (fields: Record<string, unknown>) => {
    setSaving(true)
    setSaved(false)
    setSaveErr(null)
    try {
      const updated = await settingsApi.updateProfile(fields)
      setProfile((p) => ({ ...p, ...updated }))
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch {
      setSaveErr('Failed to save. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const str = (k: string) => (profile[k] as string) ?? ''
  const bool = (k: string, def = true) => profile[k] !== undefined ? !!profile[k] : def

  // ── Logo upload ───────────────────────────────────────────────────────────
  const handleLogoChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setLogoUploading(true)
    try {
      const { url } = await settingsApi.uploadLogo(file)
      setLogoPreview(url)
      setProfile((p) => ({ ...p, agency_logo_url: url }))
    } catch {
      setSaveErr('Logo upload failed. Max 2 MB, PNG/JPEG/GIF/WebP.')
    } finally {
      setLogoUploading(false)
      if (logoInputRef.current) logoInputRef.current.value = ''
    }
  }

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="h-8 w-48 rounded bg-slate-100 animate-pulse" />
        <div className="h-96 rounded-xl bg-slate-100 animate-pulse" />
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Page header */}
      <div>
        <h1
          className="text-2xl font-bold text-slate-900"
          style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
        >
          Settings
        </h1>
        <p className="mt-1 text-sm text-slate-500">Manage your agency profile, branding, and preferences.</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1 overflow-x-auto">
        {TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => { setActiveTab(id); setSaved(false); setSaveErr(null) }}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors ${
              activeTab === id
                ? 'bg-white text-indigo-700 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Save feedback banner */}
      {(saved || saveErr) && (
        <div className={`rounded-lg px-4 py-3 text-sm ${
          saved
            ? 'bg-emerald-50 border border-emerald-200 text-emerald-700'
            : 'bg-rose-50 border border-rose-200 text-rose-700'
        }`}>
          {saved ? '✓ Settings saved successfully.' : saveErr}
        </div>
      )}

      {/* ── Account tab ─────────────────────────────────────────────────── */}
      {activeTab === 'account' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base text-slate-700">Account</CardTitle>
          </CardHeader>
          <CardContent>
            <AccountTab
              agencyName={str('agency_name')}
              agencyEmail={str('agency_email')}
              timezone={str('timezone') || 'UTC'}
              onSave={(fields) => save(fields)}
              saving={saving}
            />
          </CardContent>
        </Card>
      )}

      {/* ── Branding tab ────────────────────────────────────────────────── */}
      {activeTab === 'branding' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base text-slate-700">Agency Branding</CardTitle>
          </CardHeader>
          <CardContent>
            <BrandingTab
              agencyName={str('agency_name')}
              agencyWebsite={str('agency_website')}
              brandColor={str('brand_color') || '#4338CA'}
              logoPreview={logoPreview}
              logoUploading={logoUploading}
              logoInputRef={logoInputRef}
              onLogoChange={handleLogoChange}
              onSave={(fields) => save(fields)}
              saving={saving}
            />
          </CardContent>
        </Card>
      )}

      {/* ── Email tab ───────────────────────────────────────────────────── */}
      {activeTab === 'email' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base text-slate-700">Email Settings</CardTitle>
          </CardHeader>
          <CardContent>
            <EmailTab
              senderName={str('sender_name')}
              replyTo={str('reply_to_email')}
              footer={str('email_footer')}
              onSave={(fields) => save(fields)}
              saving={saving}
            />
          </CardContent>
        </Card>
      )}

      {/* ── AI tab ──────────────────────────────────────────────────────── */}
      {activeTab === 'ai' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base text-slate-700">AI Preferences</CardTitle>
          </CardHeader>
          <CardContent>
            <AITab
              defaultTone={str('default_ai_tone') || 'professional'}
              onSave={(fields) => save(fields)}
              saving={saving}
            />
          </CardContent>
        </Card>
      )}

      {/* ── Notifications tab ───────────────────────────────────────────── */}
      {activeTab === 'notifications' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base text-slate-700">Notifications</CardTitle>
          </CardHeader>
          <CardContent>
            <NotificationsTab
              reportGenerated={bool('notification_report_generated')}
              connectionExpired={bool('notification_connection_expired')}
              paymentFailed={bool('notification_payment_failed')}
              onSave={(fields) => save(fields)}
              saving={saving}
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}


// ── Account tab component ───────────────────────────────────────────────────

function AccountTab({
  agencyName, agencyEmail, timezone,
  onSave, saving,
}: {
  agencyName: string; agencyEmail: string; timezone: string
  onSave: (f: Record<string, unknown>) => void; saving: boolean
}) {
  const [name,  setName]  = useState(agencyName)
  const [email, setEmail] = useState(agencyEmail)
  const [tz,    setTz]    = useState(timezone)

  return (
    <div className="space-y-4">
      <FieldRow label="Agency name">
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Digital Agency" />
      </FieldRow>
      <FieldRow label="Agency email">
        <Input value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="hello@acme.com" />
      </FieldRow>
      <FieldRow label="Timezone">
        <select
          value={tz}
          onChange={(e) => setTz(e.target.value)}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {TIMEZONES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </FieldRow>
      <SaveButton onClick={() => onSave({ agency_name: name, agency_email: email, timezone: tz })} saving={saving} />
    </div>
  )
}


// ── Branding tab component ──────────────────────────────────────────────────

function BrandingTab({
  agencyName, agencyWebsite, brandColor,
  logoPreview, logoUploading, logoInputRef, onLogoChange,
  onSave, saving,
}: {
  agencyName: string; agencyWebsite: string; brandColor: string
  logoPreview: string; logoUploading: boolean
  logoInputRef: React.RefObject<HTMLInputElement>
  onLogoChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onSave: (f: Record<string, unknown>) => void; saving: boolean
}) {
  const [name,    setName]    = useState(agencyName)
  const [website, setWebsite] = useState(agencyWebsite)
  const [color,   setColor]   = useState(brandColor)

  return (
    <div className="space-y-5">
      <FieldRow label="Agency name">
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Digital Agency" />
      </FieldRow>
      <FieldRow label="Website">
        <Input value={website} onChange={(e) => setWebsite(e.target.value)} placeholder="https://acme.com" type="url" />
      </FieldRow>
      <FieldRow label="Brand color">
        <div className="flex items-center gap-3">
          <input
            type="color"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="h-9 w-20 cursor-pointer rounded border border-slate-200 p-0.5"
          />
          <Input
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="w-32 font-mono text-sm"
            placeholder="#4338CA"
            maxLength={7}
          />
          <div
            className="h-8 w-8 rounded-full border border-slate-200 shadow-sm"
            style={{ backgroundColor: color }}
          />
        </div>
      </FieldRow>

      {/* Logo upload */}
      <FieldRow label="Agency logo">
        <div className="flex items-center gap-4">
          {logoPreview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={logoPreview} alt="Agency logo" className="h-16 w-16 object-contain rounded-lg border border-slate-200 bg-slate-50 p-1" />
          ) : (
            <div className="flex h-16 w-16 items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 text-slate-400">
              <Upload className="h-6 w-6" />
            </div>
          )}
          <div>
            <button
              onClick={() => logoInputRef.current?.click()}
              disabled={logoUploading}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 transition-colors disabled:opacity-60"
            >
              {logoUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              {logoUploading ? 'Uploading…' : 'Upload logo'}
            </button>
            <p className="mt-1 text-xs text-slate-400">PNG, JPEG, or WebP · max 2 MB</p>
            <input ref={logoInputRef} type="file" accept="image/*" onChange={onLogoChange} className="hidden" />
          </div>
        </div>
      </FieldRow>

      <SaveButton
        onClick={() => onSave({ agency_name: name, agency_website: website, brand_color: color })}
        saving={saving}
        label="Save Branding"
      />
    </div>
  )
}


// ── Email tab component ─────────────────────────────────────────────────────

function EmailTab({
  senderName, replyTo, footer,
  onSave, saving,
}: {
  senderName: string; replyTo: string; footer: string
  onSave: (f: Record<string, unknown>) => void; saving: boolean
}) {
  const [name,     setName]    = useState(senderName)
  const [reply,    setReply]   = useState(replyTo)
  const [footText, setFoot]    = useState(footer)

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        These settings apply to all report delivery emails sent via ReportPilot.
      </p>
      <FieldRow label="Sender name">
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Digital Agency" />
        <p className="mt-1 text-xs text-slate-400">Shown as "From" name in clients' inboxes.</p>
      </FieldRow>
      <FieldRow label="Reply-to email">
        <Input value={reply} onChange={(e) => setReply(e.target.value)} type="email" placeholder="hello@acme.com" />
        <p className="mt-1 text-xs text-slate-400">Where client replies will land.</p>
      </FieldRow>
      <FieldRow label="Email footer">
        <Textarea
          value={footText}
          onChange={(e) => setFoot(e.target.value)}
          placeholder="Acme Digital Agency · hello@acme.com · acme.com"
          rows={3}
        />
        <p className="mt-1 text-xs text-slate-400">Appears at the bottom of every delivery email.</p>
      </FieldRow>
      <SaveButton
        onClick={() => onSave({ sender_name: name, reply_to_email: reply, email_footer: footText })}
        saving={saving}
        label="Save Email Settings"
      />
    </div>
  )
}


// ── AI preferences tab ──────────────────────────────────────────────────────

function AITab({
  defaultTone,
  onSave, saving,
}: {
  defaultTone: string
  onSave: (f: Record<string, unknown>) => void; saving: boolean
}) {
  const [tone, setTone] = useState(defaultTone)

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        Set the default AI writing tone for all new reports. Individual clients can override this.
      </p>
      <FieldRow label="Default tone">
        <select
          value={tone}
          onChange={(e) => setTone(e.target.value)}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {AI_TONES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </FieldRow>
      <SaveButton
        onClick={() => onSave({ default_ai_tone: tone })}
        saving={saving}
        label="Save Preferences"
      />
    </div>
  )
}


// ── Notifications tab ───────────────────────────────────────────────────────

function NotificationsTab({
  reportGenerated, connectionExpired, paymentFailed,
  onSave, saving,
}: {
  reportGenerated: boolean; connectionExpired: boolean; paymentFailed: boolean
  onSave: (f: Record<string, unknown>) => void; saving: boolean
}) {
  const [repGen,  setRepGen]  = useState(reportGenerated)
  const [connExp, setConnExp] = useState(connectionExpired)
  const [payFail, setPayFail] = useState(paymentFailed)

  return (
    <div className="space-y-5">
      <p className="text-sm text-slate-500">Choose which events send you an email notification.</p>

      <div className="space-y-3">
        {[
          { label: 'Email me when a report is generated', value: repGen, set: setRepGen, key: 'notification_report_generated' },
          { label: 'Email me when a platform connection expires', value: connExp, set: setConnExp, key: 'notification_connection_expired' },
          { label: 'Email me when a payment fails', value: payFail, set: setPayFail, key: 'notification_payment_failed' },
        ].map(({ label, value, set }) => (
          <label key={label} className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3 cursor-pointer hover:bg-slate-50 transition-colors">
            <span className="text-sm text-slate-700">{label}</span>
            <div
              onClick={() => set(!value)}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${value ? 'bg-indigo-700' : 'bg-slate-200'}`}
            >
              <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${value ? 'translate-x-4' : 'translate-x-1'}`} />
            </div>
          </label>
        ))}
      </div>

      <SaveButton
        onClick={() => onSave({
          notification_report_generated:  repGen,
          notification_connection_expired: connExp,
          notification_payment_failed:     payFail,
        })}
        saving={saving}
        label="Save Notification Preferences"
      />
    </div>
  )
}


// ── Shared sub-components ───────────────────────────────────────────────────

function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-4 items-start">
      <span className="text-sm font-medium text-slate-500 pt-2">{label}</span>
      <div className="col-span-2">{children}</div>
    </div>
  )
}

function SaveButton({
  onClick, saving, label = 'Save',
}: { onClick: () => void; saving: boolean; label?: string }) {
  return (
    <div className="flex justify-end pt-2">
      <button
        onClick={onClick}
        disabled={saving}
        className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-60"
      >
        {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
        {saving ? 'Saving…' : label}
      </button>
    </div>
  )
}
