// Google Analytics OAuth callback route
// Google redirects here after the user grants GA4 access.
// We extract the code + state from the URL, then forward them to the
// frontend google-callback page which handles the token exchange UI.
// IMPORTANT: This is separate from the Google SSO login flow.
// See docs/reportpilot-auth-integration-deepdive.md for full OAuth flow.

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

  // Forward code + state to the client-side callback page for token exchange
  const callbackUrl = new URL('/dashboard/integrations/google-callback', request.url)
  callbackUrl.searchParams.set('code', code)
  callbackUrl.searchParams.set('state', state)

  return NextResponse.redirect(callbackUrl)
}
