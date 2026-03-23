'use client'

import Link from 'next/link'

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <h2 className="text-xl font-semibold text-slate-900 mb-2">Something went wrong</h2>
      <p className="text-slate-500 mb-6 max-w-sm">
        {error.message || 'An unexpected error occurred. Please try again.'}
      </p>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
        >
          Try again
        </button>
        <Link
          href="/dashboard"
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
        >
          Go to Dashboard
        </Link>
      </div>
    </div>
  )
}
