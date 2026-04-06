// Dashboard layout — authenticated users only
// Server component: fetches user server-side for defense in depth

import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { DashboardShell } from '@/components/layout/dashboard-shell'

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    redirect('/login')
  }

  // Fetch agency_name from profile
  const { data: profile } = await supabase
    .from('profiles')
    .select('agency_name')
    .eq('id', user.id)
    .single()

  return (
    <DashboardShell email={user.email ?? ''} agencyName={profile?.agency_name || ''}>
      {children}
    </DashboardShell>
  )
}
