'use client'

import Link from 'next/link'
import { ArrowRight } from 'lucide-react'

/**
 * Primary hero CTA isolated in its own client component so we can fire a
 * GA4 ``cta_click`` event on click without forcing the entire landing
 * page to become a client component. The server component renders the
 * surrounding layout and embeds this client island for interactivity.
 */
export default function HeroCTA() {
  const handleClick = () => {
    if (typeof window !== 'undefined' && window.gtag) {
      window.gtag('event', 'cta_click', { location: 'hero' })
    }
  }

  return (
    <Link
      href="/signup"
      onClick={handleClick}
      className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-6 py-3 text-base font-semibold text-white hover:bg-indigo-800 transition-colors shadow-sm"
    >
      Start My Free Trial <ArrowRight className="h-4 w-4" />
    </Link>
  )
}
