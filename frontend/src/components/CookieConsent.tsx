'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

const STORAGE_KEY = 'cookie_consent'

/**
 * GDPR cookie consent banner. Persists the visitor's choice in localStorage
 * under ``cookie_consent`` (``accepted`` | ``declined``) so the banner only
 * shows once. On accept, dispatches a custom ``cookie_consent_change``
 * event so <AnalyticsProvider> loads GA4 immediately — no page reload
 * required.
 *
 * Must be a client component because it reads localStorage on mount; to
 * avoid a hydration-mismatch flash, the banner is hidden during SSR and
 * the initial client render, then slides up only if no prior choice exists.
 */
export default function CookieConsent() {
  // `null` means "undecided, still loading from localStorage" — keeps the
  // banner invisible during the first paint to avoid a flash on refresh.
  const [visible, setVisible] = useState<boolean | null>(null)

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      setVisible(stored !== 'accepted' && stored !== 'declined')
    } catch {
      // localStorage may be blocked (private mode / strict settings) —
      // default to showing the banner so we never track silently.
      setVisible(true)
    }
  }, [])

  const persist = (value: 'accepted' | 'declined') => {
    try {
      localStorage.setItem(STORAGE_KEY, value)
    } catch {
      // Ignore write failures — the user's choice just won't persist.
    }
    // Tell <AnalyticsProvider> to re-check consent in the same tab.
    window.dispatchEvent(new Event('cookie_consent_change'))
    setVisible(false)
  }

  if (visible !== true) return null

  return (
    <div
      role="dialog"
      aria-live="polite"
      aria-label="Cookie consent"
      className="fixed inset-x-0 bottom-0 z-50 border-t border-slate-200 bg-white shadow-lg animate-[slide-up_0.3s_ease-out]"
      style={{
        animation: 'cookieConsentSlideUp 300ms ease-out',
      }}
    >
      <style>{`
        @keyframes cookieConsentSlideUp {
          from { transform: translateY(100%); }
          to   { transform: translateY(0); }
        }
      `}</style>

      <div className="mx-auto max-w-6xl px-4 py-3 sm:px-6 sm:py-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
          <p className="text-sm text-slate-600 leading-relaxed">
            We use cookies to analyze site traffic and improve your experience.{' '}
            <Link href="/privacy" className="text-indigo-700 hover:underline font-medium">
              Privacy Policy
            </Link>
          </p>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => persist('declined')}
              className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
            >
              Decline
            </button>
            <button
              type="button"
              onClick={() => persist('accepted')}
              className="rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors"
            >
              Accept
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
