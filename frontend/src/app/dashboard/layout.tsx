// Dashboard layout — authenticated users only
// Server component: fetches user server-side for defense in depth
// Sidebar and SignOutButton are client components rendered inside

import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { Sidebar } from '@/components/layout/sidebar'
import { SignOutButton } from '@/components/layout/sign-out-button'

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  // Defense in depth — middleware handles this first, but double-check server-side
  if (!user) {
    redirect('/login')
  }

  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar />

      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Header */}
        <header className="h-16 shrink-0 flex items-center justify-between px-6 bg-white border-b border-slate-200">
          <span className="text-sm text-slate-500 font-medium">{user.email}</span>
          <SignOutButton />
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}
