'use client'

// Clients list page — shows all agency clients as cards
// Includes Add Client button and empty state

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Plus, Globe, Mail, Building2 } from 'lucide-react'
import { clientsApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import AddClientDialog from '@/components/clients/add-client-dialog'
import type { Client } from '@/types'

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  const fetchClients = async () => {
    try {
      const { clients } = await clientsApi.list()
      setClients(clients)
    } catch {
      setError('Failed to load clients. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchClients()
  }, [])

  const handleClientAdded = (newClient: Client) => {
    setClients((prev) => [newClient, ...prev])
    setDialogOpen(false)
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1
            className="text-2xl font-bold text-slate-900"
            style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
          >
            Clients
          </h1>
          <p className="mt-1 text-slate-500 text-sm">
            {loading ? 'Loading…' : `${clients.length} client${clients.length !== 1 ? 's' : ''}`}
          </p>
        </div>

        <button
          onClick={() => setDialogOpen(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-800"
        >
          <Plus className="h-4 w-4" />
          Add Client
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-36 rounded-xl border border-slate-200 bg-slate-50 animate-pulse" />
          ))}
        </div>
      ) : clients.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Building2 className="h-10 w-10 text-slate-300 mb-4" />
            <h2 className="text-base font-semibold text-slate-700 mb-1">No clients yet</h2>
            <p className="text-slate-500 text-sm mb-6 max-w-xs">
              Add your first client to start generating AI-powered reports.
            </p>
            <button
              onClick={() => setDialogOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-800"
            >
              <Plus className="h-4 w-4" />
              Add Client
            </button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {clients.map((client) => (
            <Link key={client.id} href={`/dashboard/clients/${client.id}`}>
              <Card className="h-full transition-shadow hover:shadow-md cursor-pointer">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base text-slate-800 truncate">{client.name}</CardTitle>
                  {client.industry && (
                    <p className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                      <Building2 className="h-3 w-3" />
                      {client.industry}
                    </p>
                  )}
                </CardHeader>
                <CardContent className="space-y-1.5">
                  {client.website_url && (
                    <p className="text-xs text-slate-500 flex items-center gap-1.5 truncate">
                      <Globe className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                      {client.website_url.replace(/^https?:\/\//, '')}
                    </p>
                  )}
                  {client.primary_contact_email && (
                    <p className="text-xs text-slate-500 flex items-center gap-1.5 truncate">
                      <Mail className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                      {client.primary_contact_email}
                    </p>
                  )}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <AddClientDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onClientAdded={handleClientAdded}
      />
    </div>
  )
}
