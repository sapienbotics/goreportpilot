'use client'

import Script from 'next/script'
import { useEffect, useState } from 'react'

// GA4 measurement ID. Read from NEXT_PUBLIC_GA_MEASUREMENT_ID so each
// environment (preview / production) can point at its own property, with
// a hardcoded fallback so the tag loads out of the box on the primary
// goreportpilot.com property without extra deployer config.
const GA_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID || 'G-GMTY15QRRZ'

/**
 * GDPR-compliant GA4 loader. Returns null until the visitor has granted
 * cookie consent via the <CookieConsent> banner — only then are the gtag
 * scripts injected. Listens for:
 *   - storage events (so consent granted in another tab propagates)
 *   - the custom `cookie_consent_change` event dispatched by the banner
 *     so consent takes effect immediately without a page reload
 */
export default function AnalyticsProvider() {
  const [consented, setConsented] = useState(false)

  useEffect(() => {
    const check = () =>
      setConsented(localStorage.getItem('cookie_consent') === 'accepted')
    check()
    window.addEventListener('storage', check)
    window.addEventListener('cookie_consent_change', check)
    return () => {
      window.removeEventListener('storage', check)
      window.removeEventListener('cookie_consent_change', check)
    }
  }, [])

  if (!consented || !GA_ID) return null

  return (
    <>
      <Script
        src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
        strategy="afterInteractive"
      />
      <Script id="google-analytics" strategy="afterInteractive">
        {`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','${GA_ID}');`}
      </Script>
    </>
  )
}
