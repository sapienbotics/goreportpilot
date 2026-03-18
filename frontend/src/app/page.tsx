// Landing page — public marketing page (placeholder)
// Full marketing page with hero, features, pricing, and footer will be built in Phase 4

import Link from 'next/link'
import { Button } from '@/components/ui/button'

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
          <Button asChild className="bg-indigo-700 hover:bg-indigo-800 text-white">
            <Link href="/signup">Get Started</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/login">Sign In</Link>
          </Button>
        </div>
      </div>
    </div>
  )
}
