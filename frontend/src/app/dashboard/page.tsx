// Dashboard home — authenticated users only
// Fetches user server-side and shows welcome state

import Link from 'next/link'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Users } from 'lucide-react'

export default async function DashboardPage() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    redirect('/login')
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>
          Welcome to ReportPilot
        </h1>
        <p className="mt-1 text-slate-500 text-sm">{user.email}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-700">
            <Users className="h-5 w-5 text-indigo-600" />
            Get started
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-slate-600 text-sm mb-4">
            You have <span className="font-semibold text-slate-900">0 clients</span>. Add your first client to get started.
          </p>
          <Link
            href="/dashboard/clients"
            className="inline-flex items-center justify-center rounded-lg bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-800"
          >
            Add Client
          </Link>
        </CardContent>
      </Card>
    </div>
  )
}
