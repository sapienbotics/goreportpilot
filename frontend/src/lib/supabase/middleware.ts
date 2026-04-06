// Supabase auth middleware helper
// Refreshes the user's session on every request to keep it alive
// Enforces email confirmation: unconfirmed users are redirected to /confirm-email
// Used by the root middleware.ts file

import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          )
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  const {
    data: { user },
  } = await supabase.auth.getUser()

  // Unauthenticated users cannot access /dashboard
  if (!user && request.nextUrl.pathname.startsWith('/dashboard')) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }

  // Authenticated but unconfirmed users: redirect to /confirm-email from /dashboard
  if (
    user &&
    !user.email_confirmed_at &&
    request.nextUrl.pathname.startsWith('/dashboard')
  ) {
    const url = request.nextUrl.clone()
    url.pathname = '/confirm-email'
    return NextResponse.redirect(url)
  }

  // Confirmed users shouldn't stay on /confirm-email
  if (
    user &&
    user.email_confirmed_at &&
    request.nextUrl.pathname === '/confirm-email'
  ) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  // Unauthenticated users cannot access /admin
  if (!user && request.nextUrl.pathname.startsWith('/admin')) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }

  // Admin / disabled routing for /dashboard and /admin paths
  if (
    user &&
    user.email_confirmed_at &&
    (request.nextUrl.pathname.startsWith('/dashboard') || request.nextUrl.pathname.startsWith('/admin'))
  ) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('is_admin,is_disabled')
      .eq('id', user.id)
      .single()

    // Disabled users get kicked to login
    if (profile?.is_disabled) {
      const url = request.nextUrl.clone()
      url.pathname = '/login'
      url.searchParams.set('error', 'account_disabled')
      await supabase.auth.signOut()
      return NextResponse.redirect(url)
    }

    // Admin users on /dashboard root → redirect to /admin
    if (profile?.is_admin && request.nextUrl.pathname === '/dashboard') {
      const url = request.nextUrl.clone()
      url.pathname = '/admin'
      return NextResponse.redirect(url)
    }

    // Non-admin users trying to access /admin/* → redirect to /dashboard
    if (!profile?.is_admin && request.nextUrl.pathname.startsWith('/admin')) {
      const url = request.nextUrl.clone()
      url.pathname = '/dashboard'
      return NextResponse.redirect(url)
    }
  }

  // Authenticated users on /login or /signup: redirect to /dashboard
  if (
    user &&
    user.email_confirmed_at &&
    (request.nextUrl.pathname === '/login' || request.nextUrl.pathname === '/signup')
  ) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  return supabaseResponse
}
