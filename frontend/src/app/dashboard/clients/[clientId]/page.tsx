'use client'

// Client detail page — tab-based layout.
// All data fetching and state live here; each tab receives only what it needs.
// Tab is controlled via ?tab= search param (default: overview).

import { useEffect, useRef, useState, useCallback } from 'react'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import { toast } from 'sonner'
import {
  LayoutDashboard, Link2, FileText, Clock, Settings,
  Building2, Image as ImageIcon,
} from 'lucide-react'
import { clientsApi, reportsApi, connectionsApi, authApi, scheduledReportsApi, uploadClientLogo, customSectionApi } from '@/lib/api'
import type { ScheduledReport, ScheduledReportPayload } from '@/lib/api'
import type { ParsedCSV } from '@/components/reports/CSVUploadForReport'
import { cn } from '@/lib/utils'
import { detectUserTimezone, localTimeToUtc, utcToLocalTime } from '@/lib/timezone-utils'
import type { Client, Report, Connection, ReportConfig } from '@/types'
import { DEFAULT_REPORT_CONFIG } from '@/types'

// Lazy tab components
import OverviewTab      from '@/components/clients/tabs/OverviewTab'
import IntegrationsTab  from '@/components/clients/tabs/IntegrationsTab'
import ReportsTab       from '@/components/clients/tabs/ReportsTab'
import SchedulesTab     from '@/components/clients/tabs/SchedulesTab'
import SettingsTab      from '@/components/clients/tabs/SettingsTab'
import DesignTab            from '@/components/clients/tabs/DesignTab'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Props {
  params: { clientId: string }
}

type TabId = 'overview' | 'integrations' | 'reports' | 'schedules' | 'design' | 'settings'

const TABS: { id: TabId; label: string; icon: React.FC<{ className?: string }> }[] = [
  { id: 'overview',      label: 'Overview',     icon: LayoutDashboard },
  { id: 'integrations',  label: 'Integrations', icon: Link2 },
  { id: 'reports',       label: 'Reports',      icon: FileText },
  { id: 'schedules',     label: 'Schedules',    icon: Clock },
  { id: 'design',        label: 'Design',       icon: ImageIcon },
  { id: 'settings',      label: 'Settings',     icon: Settings },
]

// ── Helper ────────────────────────────────────────────────────────────────────

function lastMonthRange(): { start: string; end: string } {
  const now   = new Date()
  const first = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  const last  = new Date(now.getFullYear(), now.getMonth(), 0)
  const fmt   = (d: Date) => d.toISOString().slice(0, 10)
  return { start: fmt(first), end: fmt(last) }
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ClientDetailPage({ params }: Props) {
  const router      = useRouter()
  const pathname    = usePathname()
  const searchParams = useSearchParams()
  const { clientId } = params

  const activeTab = (searchParams.get('tab') as TabId) || 'overview'

  const setTab = (id: TabId) => {
    const sp = new URLSearchParams(searchParams.toString())
    sp.set('tab', id)
    router.push(`${pathname}?${sp.toString()}`, { scroll: false })
  }

  // ── Core data ──────────────────────────────────────────────────────────────

  const [client,  setClient]  = useState<Client | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    clientsApi.get(clientId)
      .then((data) => {
        setClient(data)
        setEditValues(data)
        if (data.logo_url)     setClientLogo(data.logo_url as string)
        if (data.report_config) {
          const rc = data.report_config
          setReportConfig(() => ({ ...DEFAULT_REPORT_CONFIG, ...rc, sections: { ...DEFAULT_REPORT_CONFIG.sections, ...rc.sections } }))
        }
      })
      .catch(() => setError('Client not found or failed to load.'))
      .finally(() => setLoading(false))
  }, [clientId])

  // ── Connections ────────────────────────────────────────────────────────────

  const [connections,        setConnections]        = useState<Connection[]>([])
  const [connectionsLoading, setConnectionsLoading] = useState(true)
  const [connectingGa4,      setConnectingGa4]      = useState(false)
  const [connectingMeta,     setConnectingMeta]     = useState(false)
  const [connectingGads,     setConnectingGads]     = useState(false)
  const [connectingGsc,      setConnectingGsc]      = useState(false)
  const [disconnecting,      setDisconnecting]      = useState<string | null>(null)

  const refreshConnections = useCallback(async () => {
    try {
      const { connections: data } = await connectionsApi.listByClient(clientId)
      setConnections(data)
    } catch { /* non-fatal */ }
  }, [clientId])

  useEffect(() => {
    connectionsApi.listByClient(clientId)
      .then(({ connections: data }) => setConnections(data))
      .catch(() => {})
      .finally(() => setConnectionsLoading(false))
  }, [clientId])

  const clearOAuthSessionKeys = () => {
    sessionStorage.removeItem('ga4_connect_client_id')
    sessionStorage.removeItem('gads_connect_client_id')
    sessionStorage.removeItem('gsc_connect_client_id')
    sessionStorage.removeItem('meta_connect_client_id')
  }

  const handleConnectGa4 = async () => {
    setConnectingGa4(true)
    try {
      const { url } = await authApi.getGoogleAuthUrl()
      clearOAuthSessionKeys()
      sessionStorage.setItem('ga4_connect_client_id', clientId)
      window.location.href = url
    } catch { setConnectingGa4(false); setError('Failed to start Google Analytics authorisation.') }
  }

  const handleConnectMeta = async () => {
    setConnectingMeta(true)
    try {
      const { url } = await authApi.getMetaAuthUrl()
      clearOAuthSessionKeys()
      sessionStorage.setItem('meta_connect_client_id', clientId)
      window.location.href = url
    } catch { setConnectingMeta(false); setError('Failed to start Meta Ads authorisation.') }
  }

  const handleConnectGoogleAds = async () => {
    setConnectingGads(true)
    try {
      const { url } = await authApi.getGoogleAdsAuthUrl()
      clearOAuthSessionKeys()
      sessionStorage.setItem('gads_connect_client_id', clientId)
      window.location.href = url
    } catch { setConnectingGads(false); setError('Failed to start Google Ads authorisation.') }
  }

  const handleConnectSearchConsole = async () => {
    setConnectingGsc(true)
    try {
      const { url } = await authApi.getSearchConsoleAuthUrl()
      clearOAuthSessionKeys()
      sessionStorage.setItem('gsc_connect_client_id', clientId)
      window.location.href = url
    } catch { setConnectingGsc(false); setError('Failed to start Search Console authorisation.') }
  }

  const handleDisconnect = async (connectionId: string) => {
    if (!window.confirm('Remove this connection? Reports will not include this platform\'s data until reconnected.')) return
    setDisconnecting(connectionId)
    try {
      await connectionsApi.delete(connectionId)
      setConnections(prev => prev.filter(c => c.id !== connectionId))
    } catch { setError('Failed to remove connection.') }
    finally { setDisconnecting(null) }
  }

  // ── Reports ────────────────────────────────────────────────────────────────

  const [reports,        setReports]        = useState<Report[]>([])
  const [reportsLoading, setReportsLoading] = useState(true)

  useEffect(() => {
    reportsApi.listByClient(clientId)
      .then(({ reports: data }) => setReports(data))
      .catch(() => {})
      .finally(() => setReportsLoading(false))
  }, [clientId])

  const defaultRange = lastMonthRange()
  const [periodStart,      setPeriodStart]      = useState(defaultRange.start)
  const [periodEnd,        setPeriodEnd]        = useState(defaultRange.end)
  const [selectedTemplate, setSelectedTemplate] = useState<'full' | 'summary' | 'brief'>('full')
  const [generating,       setGenerating]       = useState(false)
  const [genError,         setGenError]         = useState<string | null>(null)
  const [csvFiles,         setCsvFiles]         = useState<ParsedCSV[]>([])

  const hasDataSources = connections.some(c => c.status === 'active') || csvFiles.length > 0

  const handleGenerate = async () => {
    if (!hasDataSources) {
      setGenError('Connect at least one data source (GA4, Meta Ads) or upload a CSV to generate a report.')
      return
    }
    setGenerating(true); setGenError(null)
    try {
      // Design System (Option F v1) — theme now lives on the client row.
      // No visual_template sent; backend reads client.theme authoritatively.
      const report = await reportsApi.generate({
        client_id:       clientId,
        period_start:    periodStart,
        period_end:      periodEnd,
        template:        selectedTemplate,
        csv_sources:     csvFiles.length > 0
          ? csvFiles.map(c => ({ source_name: c.sourceName, metrics: c.metrics }))
          : undefined,
      })
      toast.success('Report generated successfully')
      router.push(`/dashboard/reports/${report.id}`)
    } catch (err: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const detail = (err as any)?.response?.data?.detail
      const msg = typeof detail === 'string' ? detail : (err instanceof Error ? err.message : 'Failed to generate report.')
      toast.error(msg)
      setGenError(msg)
      setGenerating(false)
    }
  }

  // ── Report config ──────────────────────────────────────────────────────────

  const [reportConfig, setReportConfig] = useState<ReportConfig>(DEFAULT_REPORT_CONFIG)
  const [savingConfig, setSavingConfig] = useState(false)
  const [configSaved,  setConfigSaved]  = useState(false)

  const customImgInputRef    = useRef<HTMLInputElement>(null)
  const [customImgUploading, setCustomImgUploading] = useState(false)

  const handleSaveConfig = async () => {
    if (!client) return
    setSavingConfig(true)
    try {
      const updated = await clientsApi.update(client.id, { report_config: reportConfig })
      setClient(updated)
      setConfigSaved(true)
      setTimeout(() => setConfigSaved(false), 2500)
    } catch { setError('Failed to save report configuration.') }
    finally { setSavingConfig(false) }
  }

  const handleCustomSectionImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !client) return
    setCustomImgUploading(true)
    try {
      const { url } = await customSectionApi.uploadImage(client.id, file)
      setReportConfig(c => ({ ...c, custom_section_image_url: url }))
    } catch { setError('Image upload failed. Max 5 MB, PNG/JPEG/WebP.') }
    finally { setCustomImgUploading(false); if (customImgInputRef.current) customImgInputRef.current.value = '' }
  }

  // ── Schedules ──────────────────────────────────────────────────────────────

  const [schedule,     setSchedule]     = useState<ScheduledReport | null>(null)
  const [schedEnabled, setSchedEnabled] = useState(false)
  // `schedTimezone` is the IANA timezone the user is picking the time in.
  // `schedForm.time_utc` always holds the *local* HH:MM in that timezone while
  // the form is open; it is converted to UTC just before hitting the API.
  const [schedTimezone, setSchedTimezone] = useState<string>(() => detectUserTimezone())
  const [schedForm,    setSchedForm]    = useState<ScheduledReportPayload>({
    client_id: clientId, frequency: 'monthly', day_of_month: 1,
    time_utc: '09:00', template: 'full', auto_send: false, send_to_emails: [],
    attachment_type: 'both',
    // Design System (Option F v1) — scheduler reads client.theme; legacy
    // visual_template on scheduled_reports is ignored. Keeping a default
    // here only so new rows don't NULL-fail if the column still exists.
    visual_template: 'modern_clean',
  })
  const [savingSched, setSavingSched] = useState(false)
  const [schedSaved,  setSchedSaved]  = useState(false)

  useEffect(() => {
    scheduledReportsApi.getByClient(clientId)
      .then(schedules => {
        const active = schedules[0] ?? null
        setSchedule(active)
        if (active) {
          setSchedEnabled(active.is_active)
          // Convert stored UTC time into the user's current timezone for display.
          const localTime = utcToLocalTime(active.time_utc, detectUserTimezone())
          setSchedForm({
            client_id: clientId,
            frequency: active.frequency as ScheduledReportPayload['frequency'],
            day_of_week: active.day_of_week ?? undefined,
            day_of_month: active.day_of_month ?? 1,
            time_utc: localTime,
            template: active.template,
            auto_send: active.auto_send,
            send_to_emails: active.send_to_emails,
            attachment_type: active.attachment_type ?? 'both',
            visual_template: active.visual_template ?? 'modern_clean',
          })
        }
      })
      .catch(() => {})
  }, [clientId])

  const handleSaveSchedule = async () => {
    if (!client) return
    setSavingSched(true)
    try {
      // Convert the local time (in the selected timezone) back to UTC
      // before sending to the API — the backend only deals in UTC.
      const payload: ScheduledReportPayload = {
        ...schedForm,
        time_utc: localTimeToUtc(schedForm.time_utc ?? '09:00', schedTimezone),
      }
      if (schedule) {
        const updated = await scheduledReportsApi.update(schedule.id, { ...payload, is_active: schedEnabled })
        setSchedule(updated)
      } else if (schedEnabled) {
        const created = await scheduledReportsApi.create(payload)
        setSchedule(created)
      }
      setSchedSaved(true)
      setTimeout(() => setSchedSaved(false), 2500)
    } catch { setError('Failed to save schedule.') }
    finally { setSavingSched(false) }
  }

  // ── Settings ───────────────────────────────────────────────────────────────

  const [editing,    setEditing]    = useState(false)
  const [saving,     setSaving]     = useState(false)
  const [deleting,   setDeleting]   = useState(false)
  const [editValues, setEditValues] = useState<Partial<Client>>({})

  const logoInputRef    = useRef<HTMLInputElement>(null)
  const [logoUploading, setLogoUploading] = useState(false)
  const [clientLogo,    setClientLogo]    = useState<string>('')

  const handleSave = async () => {
    if (!client) return
    setSaving(true)
    try {
      const updated = await clientsApi.update(client.id, { name: editValues.name, website_url: editValues.website_url ?? undefined, industry: editValues.industry ?? undefined, primary_contact_email: editValues.primary_contact_email ?? undefined, goals_context: editValues.goals_context ?? undefined, notes: editValues.notes ?? undefined, report_language: editValues.report_language ?? 'en' })
      setClient(updated)
      setEditing(false)
      toast.success('Client saved')
    } catch { toast.error('Failed to save changes.') }
    finally { setSaving(false) }
  }

  const handleDelete = async () => {
    if (!client) return
    if (!window.confirm(`Delete ${client.name}? This cannot be undone.`)) return
    setDeleting(true)
    try {
      await clientsApi.delete(client.id)
      router.push('/dashboard/clients')
    } catch { setError('Failed to delete client.'); setDeleting(false) }
  }

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !client) return
    setLogoUploading(true)
    try {
      const { url } = await uploadClientLogo(client.id, file)
      setClientLogo(url)
    } catch { setError('Logo upload failed. Max 2 MB, PNG/JPEG/GIF/WebP.') }
    finally { setLogoUploading(false); if (logoInputRef.current) logoInputRef.current.value = '' }
  }

  // ── Loading / error states ─────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto space-y-4">
        <div className="h-8 w-48 rounded bg-slate-100 animate-pulse" />
        <div className="h-10 rounded-lg bg-slate-100 animate-pulse" />
        <div className="h-64 rounded-xl bg-slate-100 animate-pulse" />
      </div>
    )
  }

  if (error && !client) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      </div>
    )
  }

  if (!client) return null

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-7xl mx-auto space-y-0">

      {/* Page header */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        {clientLogo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={clientLogo}
            alt=""
            className="h-9 w-9 object-contain rounded-md border border-slate-200 bg-slate-50 p-0.5 shrink-0"
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
          />
        ) : (
          <div className="h-9 w-9 flex items-center justify-center rounded-md border border-slate-200 bg-slate-50 shrink-0">
            <Building2 className="h-4 w-4 text-slate-300" />
          </div>
        )}
        <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>
          {client.name}
        </h1>
        {client.industry && (
          <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">{client.industry}</span>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      )}

      {/* Tab bar — sticky, single scrollable row on mobile */}
      <div className="sticky top-0 z-10 bg-slate-50 -mx-4 px-4 md:-mx-6 md:px-6 border-b border-slate-200 mb-6">
        <nav className="flex gap-0 overflow-x-auto scrollbar-none -mb-px">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={cn(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors shrink-0',
                activeTab === id
                  ? 'border-indigo-600 text-indigo-700 bg-indigo-50/50'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="hidden sm:inline">{label}</span>
              <span className="sm:hidden">{label.slice(0, 3)}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <OverviewTab
          client={client}
          reports={reports}
          connections={connections}
          reportsLoading={reportsLoading}
          connectionsLoading={connectionsLoading}
        />
      )}

      {activeTab === 'integrations' && (
        <IntegrationsTab
          clientId={clientId}
          connections={connections}
          connectionsLoading={connectionsLoading}
          connectingGa4={connectingGa4}
          connectingMeta={connectingMeta}
          connectingGads={connectingGads}
          connectingGsc={connectingGsc}
          disconnecting={disconnecting}
          handleConnectGa4={handleConnectGa4}
          handleConnectMeta={handleConnectMeta}
          handleConnectGoogleAds={handleConnectGoogleAds}
          handleConnectSearchConsole={handleConnectSearchConsole}
          handleDisconnect={handleDisconnect}
          onConnectionsRefresh={refreshConnections}
        />
      )}

      {activeTab === 'reports' && (
        <ReportsTab
          clientId={clientId}
          reports={reports}
          reportsLoading={reportsLoading}
          periodStart={periodStart}
          periodEnd={periodEnd}
          setPeriodStart={setPeriodStart}
          setPeriodEnd={setPeriodEnd}
          selectedTemplate={selectedTemplate}
          setSelectedTemplate={setSelectedTemplate}
          generating={generating}
          genError={genError}
          reportConfig={reportConfig}
          setReportConfig={setReportConfig}
          savingConfig={savingConfig}
          configSaved={configSaved}
          customImgInputRef={customImgInputRef}
          customImgUploading={customImgUploading}
          csvFiles={csvFiles}
          setCsvFiles={setCsvFiles}
          handleGenerate={handleGenerate}
          handleSaveConfig={handleSaveConfig}
          handleCustomSectionImageUpload={handleCustomSectionImageUpload}
        />
      )}

      {activeTab === 'schedules' && (
        <SchedulesTab
          client={client}
          schedule={schedule}
          schedEnabled={schedEnabled}
          setSchedEnabled={setSchedEnabled}
          schedForm={schedForm}
          setSchedForm={setSchedForm}
          schedTimezone={schedTimezone}
          setSchedTimezone={setSchedTimezone}
          savingSched={savingSched}
          schedSaved={schedSaved}
          handleSaveSchedule={handleSaveSchedule}
        />
      )}

      {activeTab === 'design' && (
        <DesignTab
          client={client}
          onClientUpdate={(updated) => {
            setClient(updated)
            setEditValues(updated)
          }}
        />
      )}

      {activeTab === 'settings' && (
        <SettingsTab
          client={client}
          editing={editing}
          setEditing={setEditing}
          saving={saving}
          deleting={deleting}
          editValues={editValues}
          setEditValues={setEditValues}
          clientLogo={clientLogo}
          logoUploading={logoUploading}
          logoInputRef={logoInputRef}
          handleSave={handleSave}
          handleDelete={handleDelete}
          handleLogoUpload={handleLogoUpload}
        />
      )}
    </div>
  )
}
