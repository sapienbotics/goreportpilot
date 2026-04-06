'use client'

import { useEffect, useState } from 'react'
import { Loader2, Plus, Shield } from 'lucide-react'
import { adminApi } from '@/lib/api'
import { StatsCard } from '@/components/admin/StatsCard'
import { DataTable, type Column } from '@/components/admin/DataTable'
import { StatusBadge } from '@/components/admin/StatusBadge'
import { GDPRRequestModal } from '@/components/admin/GDPRRequestModal'

export default function AdminGDPRPage() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [requests, setRequests] = useState<any[]>([])
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [inactive, setInactive] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [editReq, setEditReq] = useState<any>(null)
  const [showNew, setShowNew] = useState(false)

  const fetchData = async () => {
    try {
      const [r, i] = await Promise.all([adminApi.getGDPRRequests(), adminApi.getInactiveUsers()])
      setRequests(r.requests || [])
      setInactive(i.users || [])
    } catch { /* silent */ }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])

  const handleCreate = async (data: { user_email: string; request_type: string; admin_notes?: string }) => {
    await adminApi.createGDPRRequest(data)
    await fetchData()
  }

  const handleUpdate = async (data: { user_email: string; request_type: string; admin_notes?: string; status?: string }) => {
    if (!editReq?.id) return
    await adminApi.updateGDPRRequest(editReq.id, { status: data.status, admin_notes: data.admin_notes })
    setEditReq(null)
    await fetchData()
  }

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-slate-300" /></div>

  const pending = requests.filter((r) => r.status === 'pending').length
  const inProgress = requests.filter((r) => r.status === 'in_progress').length
  const completed = requests.filter((r) => r.status === 'completed').length

  const reqCols: Column<Record<string, unknown>>[] = [
    { key: 'user_email', label: 'User Email', render: (r) => <span className="font-medium">{String(r.user_email ?? '')}</span> },
    { key: 'request_type', label: 'Type', render: (r) => <StatusBadge status={String(r.request_type ?? '')} /> },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={String(r.status ?? '')} /> },
    { key: 'admin_notes', label: 'Notes', render: (r) => <span className="text-xs truncate max-w-[200px] block">{String(r.admin_notes ?? '—')}</span> },
    { key: 'created_at', label: 'Created', render: (r) => <span className="text-xs">{r.created_at ? new Date(String(r.created_at)).toLocaleDateString() : ''}</span> },
    { key: 'actions', label: '', render: (r) => (
      <button onClick={(e) => { e.stopPropagation(); setEditReq(r) }} className="text-xs text-indigo-600 hover:underline">Edit</button>
    )},
  ]

  const inactiveCols: Column<Record<string, unknown>>[] = [
    { key: 'email', label: 'Email', render: (r) => <span className="font-medium">{String(r.email ?? '')}</span> },
    { key: 'full_name', label: 'Name' },
    { key: 'updated_at', label: 'Last Active', render: (r) => <span className="text-xs">{r.updated_at ? new Date(String(r.updated_at)).toLocaleDateString() : ''}</span> },
  ]

  return (
    <div className="space-y-6 max-w-7xl">
      {showNew && <GDPRRequestModal onSave={handleCreate} onClose={() => setShowNew(false)} />}
      {editReq && <GDPRRequestModal initial={editReq} onSave={handleUpdate} onClose={() => setEditReq(null)} />}

      <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>GDPR</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard label="Pending" value={pending} icon={Shield} color="amber" />
        <StatsCard label="In Progress" value={inProgress} icon={Shield} color="indigo" />
        <StatsCard label="Completed" value={completed} icon={Shield} color="emerald" />
        <StatsCard label="Total Requests" value={requests.length} icon={Shield} color="slate" />
      </div>

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">GDPR Requests</h2>
        <button
          onClick={() => setShowNew(true)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-700 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-800"
        >
          <Plus className="h-4 w-4" /> Add Request
        </button>
      </div>
      <DataTable columns={reqCols} data={requests} emptyMessage="No GDPR requests" />

      {/* Data Processing Summary */}
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h3 className="text-sm font-semibold text-slate-900 mb-3">Data Processing Summary</h3>
        <div className="text-xs text-slate-500 space-y-1.5">
          <p><strong>Processor:</strong> SapienBotics (GoReportPilot)</p>
          <p><strong>Data subjects:</strong> Marketing agency users and their clients</p>
          <p><strong>Data types:</strong> Email, name, agency details, OAuth tokens (encrypted), report data</p>
          <p><strong>Retention:</strong> Active accounts — indefinite. Cancelled — 30 days. Deleted — immediate erasure.</p>
          <p><strong>Third parties:</strong> Supabase (DB), OpenAI (AI narratives), Resend (email), Razorpay (billing), Google/Meta (OAuth)</p>
        </div>
      </div>

      {inactive.length > 0 && (
        <>
          <h2 className="text-lg font-semibold text-amber-700">Inactive Users (12+ months)</h2>
          <DataTable columns={inactiveCols} data={inactive} emptyMessage="No inactive users" />
        </>
      )}
    </div>
  )
}
