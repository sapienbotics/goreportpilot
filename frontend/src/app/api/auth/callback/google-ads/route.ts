// Google Ads OAuth callback route
// Google redirects here after the user grants Google Ads access.
// We extract the code + state from the URL, then forward them to the
// unified google-callback page which detects the platform via sessionStorage.

import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const code  = searchParams.get('code')
  const state = searchParams.get('state')
  const error = searchParams.get('error')

  // If Google returned an error (user denied access etc.) redirect to integrations
  if (error || !code || !state) {
    const reason = error ?? 'missing_code'
    return NextResponse.redirect(
      new URL(`/dashboard/integrations?error=${reason}`, request.url),
    )
  }

  // Forward code + state to the unified google-callback page for token exchange
  const callbackUrl = new URL('/dashboard/integrations/google-callback', request.url)
  callbackUrl.searchParams.set('code', code)
  callbackUrl.searchParams.set('state', state)

  return NextResponse.redirect(callbackUrl)
}
