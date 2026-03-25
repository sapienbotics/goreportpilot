'use client'

// Unified Google OAuth callback page.
// Handles GA4, Google Ads, and Search Console — all share the same Google
// OAuth redirect URI and are distinguished by which sessionStorage key is set.
//
// Flow:
//   1. Client detail / integrations page stores client_id in sessionStorage
//      and initiates the OAuth redirect.
//      Key names:  ga4_connect_client_id | gads_connect_client_id | gsc_connect_client_id
//   2. Google redirects → /api/auth/callback/google-analytics → here
//   3. This page detects the platform, exchanges the code via the correct
//      backend endpoint, then presents the user with a list of
//      properties / accounts / sites.
//   4. User picks one → saved as a connection → redirect to client detail page.
//
// IMPORTANT: Platform detection + sessionStorage cleanup + code exchange all
// happen inside a SINGLE useEffect to avoid React Strict Mode double-mount
// clearing the keys before the exchange can read them.

import { useEffect, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  CheckCircle, Loader2, AlertTriangle,
  BarChart2, TrendingUp, Search,
} from 'lucide-react'
import { authApi, connectionsApi } from '@/lib/api'
import type {
  Ga4Property,
  GoogleAdsAccount,
  SearchConsoleSite,
} from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

// ── Types ─────────────────────────────────────────────────────────────────────

type Platform = 'ga4' | 'google_ads' | 'search_console'
type Step = 'init' | 'exchanging' | 'select' | 'saving' | 'done' | 'error'

interface PlatformMeta {
  label: string
  connectionLabel: string
  icon: React.ReactNode
  platformValue: string          // value stored in connections.platform
  emptyMessage: string
  selectLabel: string
  itemNoun: string               // "property" | "account" | "site"
}

const PLATFORM_META: Record<Platform, PlatformMeta> = {
  ga4: {
    label: 'Google Analytics',
    connectionLabel: 'Connect Google Analytics',
    icon: <BarChart2 className="h-4 w-4 text-indigo-600" />,
    platformValue: 'google_analytics',
    emptyMessage:
      'No GA4 properties found. Make sure your Google account has access to at least one Google Analytics 4 property.',
    selectLabel: 'Choose which GA4 property to connect to this client.',
    itemNoun: 'property',
  },
  google_ads: {
    label: 'Google Ads',
    connectionLabel: 'Connect Google Ads',
    icon: <TrendingUp className="h-4 w-4 text-green-600" />,
    platformValue: 'google_ads',
    emptyMessage:
      'No Google Ads accounts found. Make sure your Google account has access to a Google Ads account and that you have the correct developer token and login customer ID configured.',
    selectLabel: 'Choose which Google Ads account to connect to this client.',
    itemNoun: 'account',
  },
  search_console: {
    label: 'Search Console',
    connectionLabel: 'Connect Search Console',
    icon: <Search className="h-4 w-4 text-purple-600" />,
    platformValue: 'search_console',
    emptyMessage:
      'No verified sites found. Make sure your Google account has at least one verified site in Google Search Console.',
    selectLabel: 'Choose which Search Console site to connect to this client.',
    itemNoun: 'site',
  },
}

// ── Generic list item shape ───────────────────────────────────────────────────

interface ListItem {
  id: string        // property_id | customer_id | site URL
  label: string     // display_name | name | site URL
  sublabel?: string // property_id | customer_id | permission level
  currency?: string
}

function toListItems(platform: Platform, data: unknown): ListItem[] {
  if (platform === 'ga4') {
    return (data as Ga4Property[]).map((p) => ({
      id: p.property_id,
      label: p.display_name,
      sublabel: p.property_id,
    }))
  }
  if (platform === 'google_ads') {
    return (data as GoogleAdsAccount[]).map((a) => ({
      id: a.customer_id,
      label: a.name || a.customer_id,
      sublabel: a.customer_id,
      currency: a.currency_code,
    }))
  }
  // search_console — backend returns {site_url, permission_level}
  return (data as SearchConsoleSite[]).map((s) => ({
    id: s.site_url,
    label: s.site_url,
    sublabel: s.permission_level,
  }))
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function GoogleCallbackPage() {
  const router       = useRouter()
  const searchParams = useSearchParams()

  const code  = searchParams.get('code')
  const state = searchParams.get('state')

  const [platform,    setPlatform]    = useState<Platform>('ga4')
  const [clientId,    setClientId]    = useState<string>('')
  const [step,        setStep]        = useState<Step>('init')
  const [items,       setItems]       = useState<ListItem[]>([])
  const [tokenHandle, setTokenHandle] = useState('')
  const [selected,    setSelected]    = useState('')
  const [errorMsg,    setErrorMsg]    = useState('')

  // Ref guard: prevent React Strict Mode from running the effect twice.
  // The first invocation reads + clears sessionStorage and kicks off the
  // async exchange.  A second invocation (from Strict Mode remount) must
  // be a no-op because the keys are already gone.
  const didRunRef = useRef(false)

  // ── Single combined effect: detect platform → exchange code ───────────────
  useEffect(() => {
    if (didRunRef.current) return
    didRunRef.current = true

    // 1. Detect platform from sessionStorage (synchronous)
    let detected: Platform = 'ga4'
    let cid = ''

    const gadsKey = sessionStorage.getItem('gads_connect_client_id')
    const gscKey  = sessionStorage.getItem('gsc_connect_client_id')
    const ga4Key  = sessionStorage.getItem('ga4_connect_client_id')

    if (gadsKey) {
      detected = 'google_ads'
      cid = gadsKey
    } else if (gscKey) {
      detected = 'search_console'
      cid = gscKey
    } else if (ga4Key) {
      detected = 'ga4'
      cid = ga4Key
    }

    // 2. Clear ALL keys immediately — they're single-use
    sessionStorage.removeItem('ga4_connect_client_id')
    sessionStorage.removeItem('gads_connect_client_id')
    sessionStorage.removeItem('gsc_connect_client_id')

    // 3. Persist into React state (for render + handleSave)
    setPlatform(detected)
    setClientId(cid)

    // 4. Validate params
    if (!code || !state) {
      setErrorMsg('Missing OAuth parameters. Please try connecting again.')
      setStep('error')
      return
    }

    if (!cid) {
      setErrorMsg(
        'Could not determine which client this connection is for. ' +
        'Please go back to the client page and try connecting again.'
      )
      setStep('error')
      return
    }

    // 5. Exchange auth code using the detected platform's backend endpoint
    setStep('exchanging')
    const payload = { code, state }

    const exchange = async () => {
      try {
        let rawItems: unknown = []
        let handle = ''

        if (detected === 'google_ads') {
          const result = await authApi.googleAdsCallback(payload)
          rawItems = result.accounts
          handle   = result.token_handle
        } else if (detected === 'search_console') {
          const result = await authApi.searchConsoleCallback(payload)
          rawItems = result.sites
          handle   = result.token_handle
        } else {
          const result = await authApi.googleCallback(payload)
          rawItems = result.properties
          handle   = result.token_handle
        }

        setItems(toListItems(detected, rawItems))
        setTokenHandle(handle)
        setStep('select')
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Token exchange failed.'
        setErrorMsg(msg)
        setStep('error')
      }
    }

    exchange()
  }, [code, state])  // eslint-disable-line react-hooks/exhaustive-deps

  // ── Save handler: user picks an item → create connection ──────────────────
  const handleSave = async () => {
    if (!selected || !clientId || !platform) return
    setStep('saving')
    try {
      const meta = PLATFORM_META[platform]
      const item = items.find((i) => i.id === selected)!
      const createPayload: Parameters<typeof connectionsApi.create>[0] = {
        client_id:    clientId,
        platform:     meta.platformValue,
        account_id:   selected,
        account_name: item.label,
        token_handle: tokenHandle,
      }
      if (item.currency) createPayload.currency = item.currency

      await connectionsApi.create(createPayload)

      setStep('done')
      setTimeout(() => {
        router.push(`/dashboard/clients/${clientId}`)
      }, 1800)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save connection.'
      setErrorMsg(msg)
      setStep('error')
    }
  }

  const meta    = PLATFORM_META[platform]
  const backUrl = clientId ? `/dashboard/clients/${clientId}` : '/dashboard/integrations'

  // ── Render ─────────────────────────────────────────────────────────────────

  if (step === 'init' || step === 'exchanging') {
    return (
      <PageShell meta={meta}>
        <div className="flex flex-col items-center gap-4 py-12">
          <Loader2 className="h-10 w-10 text-indigo-600 animate-spin" />
          <p className="font-semibold text-slate-700">
            Connecting to {meta.label}…
          </p>
          <p className="text-sm text-slate-400">Exchanging authorisation code for tokens.</p>
        </div>
      </PageShell>
    )
  }

  if (step === 'saving') {
    return (
      <PageShell meta={meta}>
        <div className="flex flex-col items-center gap-4 py-12">
          <Loader2 className="h-10 w-10 text-indigo-600 animate-spin" />
          <p className="font-semibold text-slate-700">Saving connection…</p>
        </div>
      </PageShell>
    )
  }

  if (step === 'done') {
    return (
      <PageShell meta={meta}>
        <div className="flex flex-col items-center gap-4 py-12">
          <CheckCircle className="h-10 w-10 text-emerald-500" />
          <p className="font-semibold text-slate-700">{meta.label} connected!</p>
          <p className="text-sm text-slate-400">Redirecting back to client…</p>
        </div>
      </PageShell>
    )
  }

  if (step === 'error') {
    return (
      <PageShell meta={meta}>
        <div className="flex flex-col items-center gap-4 py-12">
          <AlertTriangle className="h-10 w-10 text-rose-500" />
          <p className="font-semibold text-slate-700">Connection failed</p>
          <p className="text-sm text-rose-600 text-center max-w-sm">{errorMsg}</p>
          <button
            onClick={() => router.push(backUrl)}
            className="mt-2 rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
          >
            Go back
          </button>
        </div>
      </PageShell>
    )
  }

  // step === 'select'
  return (
    <PageShell meta={meta}>
      <p className="text-sm text-slate-500 mb-6">{meta.selectLabel}</p>

      {items.length === 0 ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 mb-6">
          {meta.emptyMessage}
        </div>
      ) : (
        <ul className="space-y-2 mb-6">
          {items.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => setSelected(item.id)}
                className={`w-full text-left rounded-lg border px-4 py-3 transition-colors flex items-center gap-3 ${
                  selected === item.id
                    ? 'border-indigo-400 bg-indigo-50 ring-1 ring-indigo-300'
                    : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <div className={`shrink-0 ${selected === item.id ? 'opacity-100' : 'opacity-40'}`}>
                  {meta.icon}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-800 truncate">{item.label}</p>
                  {item.sublabel && (
                    <p className="text-xs text-slate-400">
                      {item.sublabel}
                      {item.currency ? ` · ${item.currency}` : ''}
                    </p>
                  )}
                </div>
                {selected === item.id && (
                  <CheckCircle className="h-4 w-4 text-indigo-600 ml-auto shrink-0" />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex gap-3">
        <button
          onClick={() => router.push(backUrl)}
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
        >
          Cancel
        </button>
        {items.length > 0 && (
          <button
            onClick={handleSave}
            disabled={!selected || !clientId}
            className="rounded-lg bg-indigo-700 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-50"
          >
            Connect this {meta.itemNoun}
          </button>
        )}
      </div>
    </PageShell>
  )
}

// ── Shell wrapper ─────────────────────────────────────────────────────────────

function PageShell({
  meta,
  children,
}: {
  meta: PlatformMeta
  children: React.ReactNode
}) {
  return (
    <div className="max-w-lg mx-auto">
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700 flex items-center gap-2">
            {meta.icon}
            {meta.connectionLabel}
          </CardTitle>
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </div>
  )
}
