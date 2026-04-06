'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft, Loader2, Download, ShieldOff, ShieldCheck, Trash2,
  User, CreditCard, Briefcase, Link2, FileText, Shield,
} from 'lucide-react'
import { adminApi } from '@/lib/api'
import { StatusBadge } from '@/components/admin/StatusBadge'
import { DataTable, type Column } from '@/components/admin/DataTable'
import { ConfirmDeleteDialog } from '@/components/admin/ConfirmDeleteDialog'

const TABS = [
  { key: 'profile',      label: 'Profile',               icon: User },
  { key: 'subscription', label: 'Subscription & Payments', icon: CreditCard },
  { key: 'clients',      label: 'Clients',               icon: Briefcase },
  { key: 'connections',  label: 'Connections',            icon: Link2 },
  { key: 'reports',      label: 'Reports',                icon: FileText },
  { key: 'gdpr',         label: 'GDPR Actions',           icon: Shield },
] as const

export default function AdminUserDetailPage() {
  const params = useParams<{ userId: string }>()
  const router = useRouter()
  const userId = params.userId

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [detail, setDetail] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<string>('profile')
  const [showDelete, setShowDelete] = useState(false)
  const [toggling, setToggling] = useState(false)

  useEffect(() => {
    adminApi.getUser(userId)
      .then(setDetail)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [userId])

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-slate-300" /></div>
  if (!detail) return <p className="text-sm text-rose-600">User not found.</p>

  const profile = detail.profile || {}
  const sub = detail.subscription
  const payments = detail.payment_history || []
  const clients = detail.clients || []
  const connections = detail.connections || []
  const reports = detail.reports || []
  const shared = detail.shared_reports || []
  const scheduled = detail.scheduled_reports || []

  const handleToggleDisable = async () => {
    setToggling(true)
    try {
      if (profile.is_disabled) {
        await adminApi.enableUser(userId)
      } else {
        await adminApi.disableUser(userId)
      }
      const updated = await adminApi.getUser(userId)
      setDetail(updated)
    } catch { /* silent */ }
    finally { setToggling(false) }
  }

  const handleDelete = async () => {
    await adminApi.deleteUser(userId)
    router.push('/admin/users')
  }

  // Column definitions for sub-tabs
  const clientCols: Column<Record<string, unknown>>[] = [
    { key: 'name', label: 'Name', render: (r) => <span className="font-medium">{String(r.name ?? '')}</span> },
    { key: 'industry', label: 'Industry' },
    { key: 'is_active', label: 'Active', render: (r) => <StatusBadge status={r.is_active ? 'active' : 'inactive'} /> },
    { key: 'report_count', label: 'Reports' },
    { key: 'created_at', label: 'Created', render: (r) => <span className="text-xs">{r.created_at ? new Date(String(r.created_at)).toLocaleDateString() : ''}</span> },
  ]

  const connCols: Column<Record<string, unknown>>[] = [
    { key: 'client_name', label: 'Client' },
    { key: 'platform', label: 'Platform', render: (r) => <StatusBadge status={String(r.platform ?? '')} /> },
    { key: 'account_name', label: 'Account' },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={String(r.status ?? '')} /> },
    { key: 'token_expires_at', label: 'Expires', render: (r) => <span className="text-xs">{r.token_expires_at ? new Date(String(r.token_expires_at)).toLocaleDateString() : '—'}</span> },
  ]

  const reportCols: Column<Record<string, unknown>>[] = [
    { key: 'title', label: 'Title', render: (r) => <span className="font-medium truncate max-w-[200px] block">{String(r.title ?? '')}</span> },
    { key: 'client_name', label: 'Client' },
    { key: 'period_start', label: 'Period', render: (r) => <span className="text-xs">{String(r.period_start ?? '')} → {String(r.period_end ?? '')}</span> },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={String(r.status ?? '')} /> },
    { key: 'created_at', label: 'Created', render: (r) => <span className="text-xs">{r.created_at ? new Date(String(r.created_at)).toLocaleDateString() : ''}</span> },
  ]

  return (
    <div className="space-y-6 max-w-7xl">
      {showDelete && (
        <ConfirmDeleteDialog
          email={profile.email}
          onConfirm={handleDelete}
          onClose={() => setShowDelete(false)}
        />
      )}

      {/* Header */}
      <div>
        <Link href="/admin/users" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-600 mb-3">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Users
        </Link>
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-2xl font-bold text-slate-900">{profile.email}</h1>
          <StatusBadge status={sub?.plan || 'free'} />
          <StatusBadge status={sub?.status || 'none'} />
          {profile.is_disabled && <StatusBadge status="disabled" />}
          {profile.is_admin && <span className="text-xs font-bold text-rose-500 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">ADMIN</span>}
        </div>
        {profile.agency_name && (
          <p className="text-lg font-semibold text-slate-700 mt-0.5">{profile.agency_name}</p>
        )}
        {profile.name && <p className="text-sm text-slate-500">{profile.name}</p>}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 overflow-x-auto border-b border-slate-200">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              tab === key ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-400 hover:text-slate-600'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'profile' && (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            {[
              ['Email', profile.email],
              ['Name', profile.name],
              ['Agency Name', profile.agency_name],
              ['Agency Website', profile.agency_website],
              ['Brand Color', profile.brand_color],
              ['Sender Name', profile.sender_name],
              ['Agency Email', profile.agency_email],
              ['Created', profile.created_at ? new Date(profile.created_at).toLocaleString() : ''],
              ['Updated', profile.updated_at ? new Date(profile.updated_at).toLocaleString() : ''],
            ].map(([label, value]) => (
              <div key={label}>
                <span className="text-xs font-bold text-slate-400 uppercase">{label}</span>
                <p className="text-slate-700 mt-0.5">{value || '—'}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'subscription' && (
        <div className="space-y-4">
          {sub ? (
            <div className="rounded-xl border border-slate-200 bg-white p-6">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                {[
                  ['Plan', sub.plan],
                  ['Status', sub.status],
                  ['Billing Cycle', sub.billing_cycle],
                  ['Current Period End', sub.current_period_end ? new Date(sub.current_period_end).toLocaleDateString() : '—'],
                  ['Trial Ends', sub.trial_ends_at ? new Date(sub.trial_ends_at).toLocaleDateString() : '—'],
                  ['Cancel at End', sub.cancel_at_period_end ? 'Yes' : 'No'],
                ].map(([label, value]) => (
                  <div key={label}>
                    <span className="text-xs font-bold text-slate-400 uppercase">{label}</span>
                    <p className="text-slate-700 mt-0.5">{value || '—'}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">No subscription</p>
          )}
          <h3 className="text-sm font-semibold text-slate-700">Payment History</h3>
          {payments.length > 0 ? (
            <DataTable
              columns={[
                { key: 'amount', label: 'Amount', render: (r) => <span>{'\u20b9'}{String(r.amount ?? 0)}</span> },
                { key: 'status', label: 'Status', render: (r) => <StatusBadge status={String(r.status ?? '')} /> },
                { key: 'created_at', label: 'Date', render: (r) => <span className="text-xs">{r.created_at ? new Date(String(r.created_at)).toLocaleDateString() : ''}</span> },
              ]}
              data={payments}
              emptyMessage="No payments"
            />
          ) : <p className="text-sm text-slate-400">No payment records</p>}
        </div>
      )}

      {tab === 'clients' && <DataTable columns={clientCols} data={clients} emptyMessage="No clients" />}
      {tab === 'connections' && <DataTable columns={connCols} data={connections} emptyMessage="No connections" />}
      {tab === 'reports' && (
        <div className="space-y-4">
          <DataTable columns={reportCols} data={reports} emptyMessage="No reports" />
          {shared.length > 0 && (
            <>
              <h3 className="text-sm font-semibold text-slate-700">Shared Reports</h3>
              <DataTable
                columns={[
                  { key: 'share_hash', label: 'Hash', render: (r) => <span className="font-mono text-xs">{String(r.share_hash ?? '').slice(0, 12)}...</span> },
                  { key: 'is_active', label: 'Active', render: (r) => <StatusBadge status={r.is_active ? 'active' : 'inactive'} /> },
                  { key: 'is_active', label: 'Active', render: (r: Record<string, unknown>) => <span>{r.is_active ? 'Yes' : 'No'}</span> },
                  { key: 'expires_at', label: 'Expires', render: (r) => <span className="text-xs">{r.expires_at ? new Date(String(r.expires_at)).toLocaleDateString() : 'Never'}</span> },
                ]}
                data={shared}
              />
            </>
          )}
          {scheduled.length > 0 && (
            <>
              <h3 className="text-sm font-semibold text-slate-700">Scheduled Reports</h3>
              <DataTable
                columns={[
                  { key: 'client_name', label: 'Client' },
                  { key: 'frequency', label: 'Frequency' },
                  { key: 'auto_send', label: 'Auto Send', render: (r) => <span>{r.auto_send ? 'Yes' : 'No'}</span> },
                  { key: 'is_active', label: 'Active', render: (r) => <StatusBadge status={r.is_active ? 'active' : 'inactive'} /> },
                  { key: 'next_run_at', label: 'Next Run', render: (r) => <span className="text-xs">{r.next_run_at ? new Date(String(r.next_run_at)).toLocaleDateString() : '—'}</span> },
                ]}
                data={scheduled}
              />
            </>
          )}
        </div>
      )}

      {tab === 'gdpr' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => adminApi.exportUser(userId)}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-800"
            >
              <Download className="h-4 w-4" /> Export User Data
            </button>
            <button
              onClick={handleToggleDisable}
              disabled={toggling}
              className={`inline-flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-semibold ${
                profile.is_disabled
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                  : 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100'
              }`}
            >
              {toggling ? <Loader2 className="h-4 w-4 animate-spin" /> : profile.is_disabled ? <ShieldCheck className="h-4 w-4" /> : <ShieldOff className="h-4 w-4" />}
              {profile.is_disabled ? 'Enable Account' : 'Disable Account'}
            </button>
            <button
              onClick={() => setShowDelete(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-rose-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-rose-700"
            >
              <Trash2 className="h-4 w-4" /> Delete Account
            </button>
          </div>
          <p className="text-xs text-slate-400">
            Export produces a JSON file with all non-sensitive user data. Delete is irreversible GDPR erasure.
          </p>
        </div>
      )}
    </div>
  )
}
