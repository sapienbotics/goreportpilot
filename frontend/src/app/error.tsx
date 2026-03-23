'use client'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-6 text-center">
      <h2 className="text-xl font-semibold text-slate-900 mb-2">Something went wrong</h2>
      <p className="text-slate-500 mb-6 max-w-sm">
        {error.message || 'An unexpected error occurred.'}
      </p>
      <button
        onClick={reset}
        className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
      >
        Try again
      </button>
    </div>
  )
}
