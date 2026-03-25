'use client'

// Integrations page — manage per-client data source connections.
// Select a client at the top, then connect/disconnect any platform directly
// from this page without navigating to the client detail screen.

import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import {
  BarChart2, TrendingUp, Megaphone, Search, FileText,
  CheckCircle, AlertTriangle, ExternalLink, Loader2,
  Link2, Unlink, RefreshCw, ChevronDown,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { clientsApi, connectionsApi, authApi } from '@/lib/api'
import CSVUploadDialog from '@/components/clients/CSVUploadDialog'
import type { Client, Connection } from '@/types'

// ── Platform definitions ──────────────────────────────────────────────────────

interface PlatformDef {
  id: string                       // integrations page identifier
  connectionPlatform: string       // value stored in connections.platform
  name: string
  description: string
  icon: React.ReactNode
  sessionKey?: string              // sessionStorage key for clientId (OAuth platforms)
  isCsv?: boolean                  // handled differently — shows CSV dialog
  oauthType?: 'google' | 'meta' | 'google-ads' | 'search-console'
}

const PLATFORMS: PlatformDef[] = [
  {
    id: 'google_analytics',
    connectionPlatform: 'google_analytics',
    name: 'Google Analytics 4',
    description: 'Sessions, users, traffic sources, and conversion events from GA4 properties.',
    icon: <BarChart2 className="h-6 w-6 text-orange-500" />,
    sessionKey: 'ga4_connect_client_id',
    oauthType: 'google',
  },
  {
    id: 'meta_ads',
    connectionPlatform: 'meta_ads',
    name: 'Meta Ads',
    description: 'Spend, impressions, clicks, ROAS, and campaign performance from Facebook and Instagram.',
    icon: <Megaphone className="h-6 w-6 text-blue-500" />,
    sessionKey: 'meta_connect_client_id',
    oauthType: 'meta',
  },
  {
    id: 'google_ads',
    connectionPlatform: 'google_ads',
    name: 'Google Ads',
    description: 'Search, display, and shopping campaign data — spend, conversions, and ROAS.',
    icon: <TrendingUp className="h-6 w-6 text-green-500" />,
    sessionKey: 'gads_connect_client_id',
    oauthType: 'google-ads',
  },
  {
    id: 'search_console',
    connectionPlatform: 'search_console',
    name: 'Search Console',
    description: 'Organic search impressions, clicks, average position, and top queries.',
    icon: <Search className="h-6 w-6 text-purple-500" />,
    sessionKey: 'gsc_connect_client_id',
    oauthType: 'search-console',
  },
  {
    id: 'csv_upload',
    connectionPlatform: 'csv_',   // prefix — CSV connections use csv_<slug>
    name: 'CSV / Manual Data',
    description: 'Upload data from LinkedIn Ads, TikTok, Mailchimp, Shopify, or any custom source.',
    icon: <FileText className="h-6 w-6 text-slate-500" />,
    isCsv: true,
  },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function findConnection(connections: Connection[], platform: PlatformDef): Connection | undefined {
  if (platform.isCsv) {
    return connections.find((c) => c.platform.startsWith('csv_'))
  }
  return connections.find((c) => c.platform === platform.connectionPlatform)
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function IntegrationsPage() {
  const searchParams = useSearchParams()
  const oauthError   = searchParams.get('error')

  const [clients,              setClients]              = useState<Client[]>([])
  const [clientsLoading,       setClientsLoading]       = useState(true)
  const [selectedClientId,     setSelectedClientId]     = useState<string>('')
  const [connections,          setConnections]          = useState<Connection[]>([])
  const [connectionsLoading,   setConnectionsLoading]   = useState(false)
  const [connecting,           setConnecting]           = useState<Record<string, boolean>>({})
  const [disconnecting,        setDisconnecting]        = useState<Record<string, boolean>>({})
  const [showCsvUpload,        setShowCsvUpload]        = useState(false)

  // Load clients on mount
  useEffect(() => {
    clientsApi.list()
      .then(({ clients: data }) => {
        setClients(data)
        if (data.length === 1) setSelectedClientId(data[0].id)
      })
      .catch(() => {/* non-fatal */})
      .finally(() => setClientsLoading(false))
  }, [])

  // Load connections whenever selected client changes
  const loadConnections = useCallback(async (clientId: string) => {
    if (!clientId) { setConnections([]); return }
    setConnectionsLoading(true)
    try {
      const { connections: data } = await connectionsApi.listByClient(clientId)
      setConnections(data)
    } catch {
      setConnections([])
    } finally {
      setConnectionsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadConnections(selectedClientId)
  }, [selectedClientId, loadConnections])

  // ── OAuth connect handlers ─────────────────────────────────────────────────

  const handleConnect = async (platform: PlatformDef) => {
    if (!selectedClientId || platform.isCsv) return
    setConnecting((prev) => ({ ...prev, [platform.id]: true }))
    try {
      if (platform.sessionKey) {
        sessionStorage.setItem(platform.sessionKey, selectedClientId)
      }
      let url: string
      if (platform.oauthType === 'google')          url = (await authApi.getGoogleAuthUrl()).url
      else if (platform.oauthType === 'meta')       url = (await authApi.getMetaAuthUrl()).url
      else if (platform.oauthType === 'google-ads') url = (await authApi.getGoogleAdsAuthUrl()).url
      else                                           url = (await authApi.getSearchConsoleAuthUrl()).url
      window.location.href = url
    } catch {
      setConnecting((prev) => ({ ...prev, [platform.id]: false }))
    }
  }

  const handleDisconnect = async (connection: Connection, platformId: string) => {
    setDisconnecting((prev) => ({ ...prev, [connection.id]: true }))
    try {
      await connectionsApi.delete(connection.id)
      await loadConnections(selectedClientId)
    } catch {
      // non-fatal
    } finally {
      setDisconnecting((prev) => ({ ...prev, [connection.id]: false }))
    }
    void platformId  // referenced to avoid lint warning
  }

  const selectedClient = clients.find((c) => c.id === selectedClientId) ?? null

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* Header */}
      <div>
        <h1
          className="text-2xl font-bold text-slate-900"
          style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
        >
          Integrations
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Connect data sources for each client. Select a client below to manage their connections.
        </p>
      </div>

      {/* OAuth error banner */}
      {oauthError && (
        <div className="flex items-start gap-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3">
          <AlertTriangle className="h-4 w-4 text-rose-500 shrink-0 mt-0.5" />
          <p className="text-sm text-rose-700">
            Authorisation was cancelled or failed ({oauthError}). Please try again.
          </p>
        </div>
      )}

      {/* Client selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-slate-600 whitespace-nowrap">
          Client:
        </label>
        {clientsLoading ? (
          <div className="h-9 w-48 rounded-lg bg-slate-100 animate-pulse" />
        ) : clients.length === 0 ? (
          <Link
            href="/dashboard/clients"
            className="inline-flex items-center gap-1.5 text-sm text-indigo-700 hover:underline"
          >
            Create a client first →
          </Link>
        ) : (
          <div className="relative">
            <select
              value={selectedClientId}
              onChange={(e) => setSelectedClientId(e.target.value)}
              className="h-9 w-64 appearance-none rounded-lg border border-slate-200 bg-white pl-3 pr-8 text-sm text-slate-700 shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
            >
              <option value="">— Select a client —</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-2.5 h-4 w-4 text-slate-400" />
          </div>
        )}
        {selectedClientId && (
          <button
            onClick={() => loadConnections(selectedClientId)}
            disabled={connectionsLoading}
            className="rounded-lg border border-slate-200 p-1.5 text-slate-400 hover:border-slate-300 hover:text-slate-600 transition-colors disabled:opacity-50"
            title="Refresh connections"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${connectionsLoading ? 'animate-spin' : ''}`} />
          </button>
        )}
      </div>

      {/* No client selected hint */}
      {!selectedClientId && !clientsLoading && clients.length > 0 && (
        <p className="text-sm text-slate-400">
          Select a client above to see and manage their integrations.
        </p>
      )}

      {/* Platform cards */}
      {(selectedClientId || clients.length === 0) && (
        <div className="space-y-4">
          {PLATFORMS.map((platform) => {
            const conn = selectedClientId ? findConnection(connections, platform) : undefined
            const isConnecting   = connecting[platform.id]
            const isDisconnecting = conn ? disconnecting[conn.id] : false
            const isConnected    = !!conn && conn.status === 'active'
            const needsReconnect = !!conn && (conn.status === 'expired' || conn.status === 'error')

            return (
              <Card key={platform.id}>
                <CardContent className="pt-5">
                  <div className="flex items-start gap-4">
                    {/* Platform icon */}
                    <div className="rounded-xl bg-slate-50 border border-slate-100 p-3 shrink-0">
                      {platform.icon}
                    </div>

                    {/* Info + actions */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h2 className="text-base font-semibold text-slate-800">{platform.name}</h2>

                        {/* Connection status badge */}
                        {connectionsLoading && selectedClientId ? (
                          <span className="h-5 w-16 rounded-full bg-slate-100 animate-pulse inline-block" />
                        ) : isConnected ? (
                          <span className="text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded-full flex items-center gap-1">
                            <CheckCircle className="h-3 w-3" /> Connected
                          </span>
                        ) : needsReconnect ? (
                          <span className="text-xs font-medium text-amber-700 bg-amber-50 border border-amber-100 px-2 py-0.5 rounded-full flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" /> Needs reconnect
                          </span>
                        ) : null}
                      </div>

                      <p className="mt-1 text-sm text-slate-500">{platform.description}</p>

                      {/* Connected account info */}
                      {conn && (
                        <p className="mt-1.5 text-xs text-slate-400">
                          Account: <span className="font-medium text-slate-600">{conn.account_name || conn.account_id}</span>
                          {conn.currency ? ` · ${conn.currency}` : ''}
                        </p>
                      )}

                      {/* Action buttons */}
                      {selectedClientId && (
                        <div className="mt-4 flex flex-wrap gap-2">
                          {/* Not yet connected OR needs reconnect → show Connect */}
                          {(!conn || needsReconnect) && (
                            platform.isCsv ? (
                              <button
                                onClick={() => setShowCsvUpload(true)}
                                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:border-indigo-300 hover:text-indigo-700 transition-colors"
                              >
                                <FileText className="h-3.5 w-3.5" />
                                Upload CSV
                              </button>
                            ) : (
                              <button
                                onClick={() => handleConnect(platform)}
                                disabled={isConnecting}
                                className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-60"
                              >
                                {isConnecting
                                  ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                  : <Link2 className="h-3.5 w-3.5" />
                                }
                                {needsReconnect ? 'Reconnect' : `Connect ${platform.name}`}
                              </button>
                            )
                          )}

                          {/* Connected → show Disconnect (+ re-upload for CSV) */}
                          {isConnected && (
                            <>
                              {platform.isCsv && (
                                <button
                                  onClick={() => setShowCsvUpload(true)}
                                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:border-indigo-300 hover:text-indigo-700 transition-colors"
                                >
                                  <FileText className="h-3.5 w-3.5" />
                                  Re-upload CSV
                                </button>
                              )}
                              <button
                                onClick={() => conn && handleDisconnect(conn, platform.id)}
                                disabled={isDisconnecting}
                                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-500 hover:border-rose-200 hover:text-rose-600 transition-colors disabled:opacity-60"
                              >
                                {isDisconnecting
                                  ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                  : <Unlink className="h-3.5 w-3.5" />
                                }
                                Disconnect
                              </button>
                            </>
                          )}
                        </div>
                      )}

                      {/* No client selected — show docs link for GA4 */}
                      {!selectedClientId && platform.id === 'google_analytics' && (
                        <a
                          href="https://developers.google.com/analytics/devguides/reporting/data/v1"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-3 inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors"
                        >
                          API documentation <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* CSV Upload dialog */}
      {showCsvUpload && selectedClient && (
        <CSVUploadDialog
          clientId={selectedClient.id}
          onClose={() => setShowCsvUpload(false)}
          onSuccess={() => {
            setShowCsvUpload(false)
            loadConnections(selectedClientId)
          }}
        />
      )}

      {/* Data privacy note */}
      <Card className="border-slate-100 bg-slate-50">
        <CardContent className="pt-4 pb-4">
          <p className="text-xs font-semibold text-slate-500 mb-1">Data privacy</p>
          <p className="text-xs text-slate-400 leading-relaxed">
            ReportPilot requests read-only access to your analytics and advertising data.
            OAuth tokens are encrypted at rest using AES-256-GCM and are never exposed
            to the browser. You can disconnect any integration at any time.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
