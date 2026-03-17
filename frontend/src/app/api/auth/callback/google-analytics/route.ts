// Google Analytics OAuth callback route
// Receives the auth code from Google after the user authorizes GA4 access
// Forwards the code to the FastAPI backend for token exchange
// IMPORTANT: This is separate from the Google SSO login flow
// See docs/reportpilot-auth-integration-deepdive.md for full OAuth flow

import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  // Placeholder — will be implemented in Phase 2
  return NextResponse.redirect(new URL('/dashboard/integrations', request.url))
}
