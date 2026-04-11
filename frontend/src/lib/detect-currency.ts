/**
 * Shared browser-side currency detection used by the landing page and
 * `PricingToggle`. Memoised at the module level because the result cannot
 * change during a single page session — running the `Intl` probe for each
 * mount is pure waste.
 *
 * Detection logic:
 *   - `navigator.language` starting with "hi" (Hindi) → INR
 *   - Timezone "Asia/Calcutta" or "Asia/Kolkata"      → INR
 *   - Everything else                                 → USD
 *
 * Must only be called from client components or inside `useEffect`.
 * During SSR and the first client render, callers should default to USD
 * so the server markup and initial client markup agree.
 */

export type Currency = 'INR' | 'USD'

let _cached: Currency | null = null

export function detectCurrency(): Currency {
  if (_cached !== null) return _cached
  if (typeof navigator === 'undefined') return 'USD'
  try {
    const lang = navigator.language || ''
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''
    if (lang.startsWith('hi') || tz.includes('Calcutta') || tz.includes('Kolkata')) {
      _cached = 'INR'
      return 'INR'
    }
  } catch {
    // Intl unavailable — fall through to USD default.
  }
  _cached = 'USD'
  return 'USD'
}
