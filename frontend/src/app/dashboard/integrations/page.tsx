'use client'

// Integrations page — available platform integrations and how to connect them.
// GA4 connections are per-client (done from the client detail page).
// This page explains the integrations and provides direct entry points.

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import {
  BarChart2, TrendingUp, Megaphone, CheckCircle,
  ArrowRight, AlertTriangle, ExternalLink, Search, FileText,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { clientsApi } from '@/lib/api'
import type { Client } from '@/types'

// ── Platform definitions ──────────────────────────────────────────────────────
interface Platform {
  id: string
  name: string
  description: string
  icon: React.ReactNode
  status: 'available' | 'coming_soon'
  docsUrl?: string
}

const PLATFORMS: Platform[] = [
  {
    id: 'google_analytics',
    name: 'Google Analytics 4',
    description:
      'Pull session data, user metrics, traffic sources, and conversion events directly from GA4 properties. Connected per client.',
    icon: <BarChart2 className="h-6 w-6 text-orange-500" />,
    status: 'available',
    docsUrl: 'https://developers.google.com/analytics/devguides/reporting/data/v1',
  },
  {
    id: 'meta_ads',
    name: 'Meta Ads',
    description:
      'Import spend, impressions, clicks, ROAS, and campaign performance from Facebook and Instagram ad accounts.',
    icon: <Megaphone className="h-6 w-6 text-blue-500" />,
    status: 'available',
  },
  {
    id: 'google_ads',
    name: 'Google Ads',
    description:
      'Connect Google Ads accounts to include search, display, and shopping campaign data in your reports.',
    icon: <TrendingUp className="h-6 w-6 text-green-500" />,
    status: 'available',
  },
  {
    id: 'search_console',
    name: 'Google Search Console',
    description:
      'Import organic search impressions, clicks, average position, and top queries to power the SEO slides in your reports.',
    icon: <Search className="h-6 w-6 text-purple-500" />,
    status: 'available',
  },
  {
    id: 'csv_upload',
    name: 'CSV / Manual Data',
    description:
      'Upload data from LinkedIn Ads, TikTok Ads, Mailchimp, Shopify, or any custom source using a simple CSV template.',
    icon: <FileText className="h-6 w-6 text-slate-500" />,
    status: 'available',
  },
]

export default function IntegrationsPage() {
  const searchParams = useSearchParams()
  const oauthError   = searchParams.get('error')

  const [clients,        setClients]        = useState<Client[]>([])
  const [clientsLoading, setClientsLoading] = useState(true)

  useEffect(() => {
    clientsApi.list()
      .then(({ clients: data }) => setClients(data))
      .catch(() => {/* non-fatal */})
      .finally(() => setClientsLoading(false))
  }, [])

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
          Connect data sources to power AI-generated reports. Each integration is
          linked per client from the client detail page.
        </p>
      </div>

      {/* OAuth error banner */}
      {oauthError && (
        <div className="flex items-start gap-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3">
          <AlertTriangle className="h-4 w-4 text-rose-500 shrink-0 mt-0.5" />
          <p className="text-sm text-rose-700">
            Authorisation was cancelled or failed ({oauthError}). You can
            try again from the client detail page.
          </p>
        </div>
      )}

      {/* Platform cards */}
      <div className="space-y-4">
        {PLATFORMS.map((platform) => (
          <Card key={platform.id} className={platform.status === 'coming_soon' ? 'opacity-60' : ''}>
            <CardContent className="pt-5">
              <div className="flex items-start gap-4">
                <div className="rounded-xl bg-slate-50 border border-slate-100 p-3 shrink-0">
                  {platform.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-base font-semibold text-slate-800">{platform.name}</h2>
                    {platform.status === 'available' ? (
                      <span className="text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded-full flex items-center gap-1">
                        <CheckCircle className="h-3 w-3" /> Available
                      </span>
                    ) : (
                      <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                        Coming soon
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-slate-500">{platform.description}</p>

                  {platform.status === 'available' && (
                    <div className="mt-4">
                      <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">
                        Connect via a client
                      </p>
                      {clientsLoading ? (
                        <div className="h-8 w-48 rounded bg-slate-100 animate-pulse" />
                      ) : clients.length === 0 ? (
                        <Link
                          href="/dashboard/clients"
                          className="inline-flex items-center gap-1.5 text-sm text-indigo-700 hover:underline"
                        >
                          Create a client first <ArrowRight className="h-3.5 w-3.5" />
                        </Link>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {clients.slice(0, 6).map((client) => (
                            <Link
                              key={client.id}
                              href={`/dashboard/clients/${client.id}`}
                              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 hover:border-indigo-300 hover:text-indigo-700 transition-colors"
                            >
                              {client.name} <ArrowRight className="h-3 w-3" />
                            </Link>
                          ))}
                          {clients.length > 6 && (
                            <Link
                              href="/dashboard/clients"
                              className="inline-flex items-center gap-1 rounded-lg border border-dashed border-slate-200 px-3 py-1.5 text-xs text-slate-400 hover:border-slate-300 transition-colors"
                            >
                              +{clients.length - 6} more
                            </Link>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {platform.docsUrl && (
                    <a
                      href={platform.docsUrl}
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
        ))}
      </div>

      {/* Data privacy note */}
      <Card className="border-slate-100 bg-slate-50">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-slate-600">Data privacy</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-slate-500 leading-relaxed">
            ReportPilot requests read-only access to your analytics and advertising data.
            OAuth tokens are encrypted at rest using AES-256-GCM and are never exposed
            to the browser. You can disconnect any integration at any time from the
            client detail page.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
