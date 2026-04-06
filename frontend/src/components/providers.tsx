'use client'

import { AppProgressBar as ProgressBar } from 'next-nprogress-bar'

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <ProgressBar
        height="3px"
        color="#4338CA"
        options={{ showSpinner: false }}
        shallowRouting
      />
    </>
  )
}
