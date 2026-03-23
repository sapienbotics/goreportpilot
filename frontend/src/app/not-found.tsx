import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-6 text-center">
      <p className="text-7xl font-extrabold text-indigo-700 mb-4" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>
        404
      </p>
      <h1 className="text-2xl font-bold text-slate-900 mb-2">Page not found</h1>
      <p className="text-slate-500 mb-8 max-w-sm">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <div className="flex flex-wrap gap-3 justify-center">
        <Link
          href="/dashboard"
          className="rounded-lg bg-indigo-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors"
        >
          Go to Dashboard
        </Link>
        <Link
          href="/"
          className="rounded-lg border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
        >
          Go to Home
        </Link>
      </div>
    </div>
  )
}
