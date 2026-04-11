// Ambient declaration for the Google Analytics 4 runtime globals injected
// by the gtag.js loader in <AnalyticsProvider>. Keeps `window.gtag(...)`
// calls in application code type-checked without resorting to `as any`.

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type GtagFn = (...args: any[]) => void

interface Window {
  gtag?: GtagFn
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  dataLayer?: any[]
}
