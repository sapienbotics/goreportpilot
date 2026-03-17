// Supabase browser client — for use in Client Components
// Use this in 'use client' components that need Supabase access
// See: https://supabase.com/docs/guides/auth/server-side/nextjs

import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
