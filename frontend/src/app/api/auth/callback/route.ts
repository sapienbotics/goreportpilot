// Supabase Auth callback route
// Handles the OAuth redirect from Supabase after Google SSO login
// Exchanges the code for a session and redirects to /dashboard

import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  // Placeholder — will be implemented with Supabase SSR in Phase 1
  return NextResponse.redirect(new URL('/dashboard', request.url))
}
