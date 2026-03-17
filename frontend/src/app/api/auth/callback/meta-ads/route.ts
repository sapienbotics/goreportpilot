// Meta Ads OAuth callback route
// Receives the auth code from Meta after the user authorizes Meta Ads access
// Forwards the code to the FastAPI backend for short → long-lived token exchange
// See docs/reportpilot-auth-integration-deepdive.md for full OAuth flow

import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  // Placeholder — will be implemented in Phase 2
  return NextResponse.redirect(new URL('/dashboard/integrations', request.url))
}
