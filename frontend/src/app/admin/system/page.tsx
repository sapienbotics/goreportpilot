'use client'

import { useEffect, useState } from 'react'
import { Loader2, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react'
import { adminApi } from '@/lib/api'

function ServiceCard({ label, status }: { label: string; status: string }) {
  const isOk = status === 'connected' || status === 'configured' || status === 'available' || status === 'healthy'
  const isMissing = status === 'missing' || status === 'unavailable'
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 flex items-center gap-4">
      {isOk ? (
        <CheckCircle2 className="h-6 w-6 text-emerald-500 shrink-0" />
      ) : isMissing ? (
        <XCircle className="h-6 w-6 text-slate-300 shrink-0" />
      ) : (
        <AlertTriangle className="h-6 w-6 text-amber-500 shrink-0" />
      )}
      <div>
        <p className="text-sm font-semibold text-slate-900">{label}</p>
        <p className={`text-xs ${isOk ? 'text-emerald-600' : isMissing ? 'text-slate-400' : 'text-amber-600'}`}>{status}</p>
      </div>
    </div>
  )
}

export default function AdminSystemPage() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [health, setHealth] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    adminApi.getSystemHealth()
      .then(setHealth)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-slate-300" /></div>
  if (!health) return <p className="text-sm text-rose-600">Failed to load system health.</p>

  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>System Health</h1>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <ServiceCard label="Overall" status={health.status} />
        <ServiceCard label="Supabase" status={health.supabase} />
        <ServiceCard label="OpenAI" status={health.openai} />
        <ServiceCard label="LibreOffice" status={health.libreoffice} />
        <ServiceCard label="Resend (Email)" status={health.resend} />
        <ServiceCard label="Razorpay" status={health.razorpay} />
      </div>

      <h2 className="text-lg font-semibold text-slate-900">Environment</h2>
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          {[
            ['Service', health.service],
            ['Version', health.version],
            ['Environment', health.environment],
            ['Frontend URL', health.frontend_url],
            ['Backend URL', health.backend_url],
          ].map(([label, value]) => (
            <div key={label}>
              <span className="text-xs font-bold text-slate-400 uppercase">{label}</span>
              <p className="text-slate-700 mt-0.5 font-mono text-xs">{value || '—'}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
