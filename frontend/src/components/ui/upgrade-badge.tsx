'use client'

import Link from 'next/link'
import { Lock } from 'lucide-react'

interface UpgradeBadgeProps {
  /** Short label like "Pro" or "Pro plan required" */
  label?: string
  /** Inline text (default) or as a small pill badge */
  variant?: 'inline' | 'pill'
}

/**
 * A small, non-intrusive upgrade prompt that links to the billing page.
 * Used on locked features to nudge Starter-plan users to upgrade.
 */
export function UpgradeBadge({ label = 'Upgrade to Pro', variant = 'inline' }: UpgradeBadgeProps) {
  if (variant === 'pill') {
    return (
      <Link
        href="/dashboard/billing"
        className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-xs font-medium text-amber-700 hover:bg-amber-100 transition-colors"
      >
        <Lock className="h-3 w-3" />
        {label}
      </Link>
    )
  }

  return (
    <Link
      href="/dashboard/billing"
      className="inline-flex items-center gap-1 text-xs text-amber-600 hover:text-amber-700 transition-colors"
    >
      <Lock className="h-3 w-3" />
      {label}
    </Link>
  )
}
