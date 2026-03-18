// Landing page — public marketing page (placeholder)
// Full marketing page with hero, features, pricing, and footer will be built in Phase 4

import Link from 'next/link'

export default function LandingPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center px-4 max-w-xl">
        <h1
          className="text-4xl font-bold text-indigo-700 mb-4"
          style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
        >
          ReportPilot
        </h1>
        <p className="text-lg text-slate-600 mb-8 text-balance">
          AI writes your client reports. You review and send. 5 minutes, not 3 hours.
        </p>
        <div className="flex gap-3 justify-center">
          <Link
            href="/signup"
            className="inline-flex items-center justify-center rounded-lg bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-800"
          >
            Get Started
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          >
            Sign In
          </Link>
        </div>
      </div>
    </div>
  )
}
