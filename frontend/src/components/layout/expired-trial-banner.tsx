'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { AlertTriangle } from 'lucide-react'
import { billingApi } from '@/lib/api'

/**
 * Shows a persistent banner when the user's trial has expired.
 * Fetches subscription status once on mount — hidden while loading
 * and for active/trialing users.
 */
export function ExpiredTrialBanner() {
  const [status, setStatus] = useState<string | null>(null)

  useEffect(() => {
    billingApi
      .getSubscription()
      .then((sub) => setStatus(sub.status))
      .catch(() => {})
  }, [])

  if (status !== 'expired') return null

  return (
    <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0" />
        <p className="text-sm font-medium text-rose-800">
          Your free trial has ended. Upgrade to continue generating reports.
        </p>
      </div>
      <Link
        href="/dashboard/billing"
        className="shrink-0 rounded-lg bg-indigo-700 px-4 py-1.5 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors"
      >
        View Plans
      </Link>
    </div>
  )
}
