// Meta Ads OAuth callback route
// Meta redirects here after the user grants ad account access.
// We extract the code + state from the URL, then forward them to the
// frontend meta-callback page which handles the token exchange UI.

import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const code  = searchParams.get('code')
  const state = searchParams.get('state')
  const error = searchParams.get('error')

  // If Meta returned an error (user denied access etc.) redirect to integrations
  if (error || !code) {
    const reason = error ?? 'missing_code'
    return NextResponse.redirect(
      new URL(`/dashboard/integrations?error=${reason}`, request.url),
    )
  }

  // Forward code + state to the client-side callback page for token exchange
  const callbackUrl = new URL('/dashboard/integrations/meta-callback', request.url)
  callbackUrl.searchParams.set('code', code)
  if (state) callbackUrl.searchParams.set('state', state)

  return NextResponse.redirect(callbackUrl)
}
