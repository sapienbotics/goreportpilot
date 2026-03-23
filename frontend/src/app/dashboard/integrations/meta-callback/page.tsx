'use client'

// Meta Ads OAuth callback page.
// Receives code + state from the Next.js API route, exchanges them for tokens
// via the FastAPI backend, then shows the user a list of their ad accounts
// to connect to a client account.
//
// clientId is stored in sessionStorage by the "Connect Meta Ads" button.

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { CheckCircle, Loader2, AlertTriangle, Megaphone } from 'lucide-react'
import { authApi, connectionsApi } from '@/lib/api'
import type { MetaAdAccount } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

type Step = 'exchanging' | 'select' | 'saving' | 'done' | 'error'

export default function MetaCallbackPage() {
  const router       = useRouter()
  const searchParams = useSearchParams()

  const code  = searchParams.get('code')
  // clientId is stored in sessionStorage by the Connect Meta Ads button
  const [clientId, setClientId] = useState<string | null>(null)

  useEffect(() => {
    setClientId(sessionStorage.getItem('meta_connect_client_id'))
  }, [])

  const [step,        setStep]        = useState<Step>('exchanging')
  const [adAccounts,  setAdAccounts]  = useState<MetaAdAccount[]>([])
  const [tokenHandle, setTokenHandle] = useState('')
  const [selected,    setSelected]    = useState('')
  const [errorMsg,    setErrorMsg]    = useState('')

  // ── Step 1: exchange the auth code for tokens + ad account list ───────────
  useEffect(() => {
    if (clientId === null) return  // still loading from sessionStorage

    if (!code) {
      setErrorMsg('Missing OAuth code. Please try connecting again.')
      setStep('error')
      return
    }

    const exchange = async () => {
      try {
        const result = await authApi.metaCallback(code)
        setAdAccounts(result.ad_accounts)
        setTokenHandle(result.token_handle)
        setStep('select')
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Token exchange failed.'
        setErrorMsg(msg)
        setStep('error')
      }
    }

    exchange()
  }, [code, clientId])

  // ── Step 2: user picks an ad account → save connection ───────────────────
  const handleSave = async () => {
    if (!selected || !clientId) return
    setStep('saving')
    try {
      const acct = adAccounts.find((a) => a.account_id === selected)!
      await connectionsApi.create({
        client_id:    clientId,
        platform:     'meta_ads',
        account_id:   selected,
        account_name: acct.account_name,
        token_handle: tokenHandle,
        currency:     acct.currency,
      })
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

  // ── Render ────────────────────────────────────────────────────────────────

  if (step === 'exchanging') {
    return (
      <PageShell>
        <div className="flex flex-col items-center gap-4 py-12">
          <Loader2 className="h-10 w-10 text-indigo-600 animate-spin" />
          <p className="font-semibold text-slate-700">Connecting to Meta Ads…</p>
          <p className="text-sm text-slate-400">Exchanging authorisation code for tokens.</p>
        </div>
      </PageShell>
    )
  }

  if (step === 'error') {
    return (
      <PageShell>
        <div className="flex flex-col items-center gap-4 py-12">
          <AlertTriangle className="h-10 w-10 text-rose-500" />
          <p className="font-semibold text-slate-700">Connection failed</p>
          <p className="text-sm text-rose-600 text-center max-w-sm">{errorMsg}</p>
          <button
            onClick={() => router.push(clientId ? `/dashboard/clients/${clientId}` : '/dashboard/integrations')}
            className="mt-2 rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
          >
            Go back
          </button>
        </div>
      </PageShell>
    )
  }

  if (step === 'done') {
    return (
      <PageShell>
        <div className="flex flex-col items-center gap-4 py-12">
          <CheckCircle className="h-10 w-10 text-emerald-500" />
          <p className="font-semibold text-slate-700">Meta Ads connected!</p>
          <p className="text-sm text-slate-400">Redirecting back to client…</p>
        </div>
      </PageShell>
    )
  }

  if (step === 'saving') {
    return (
      <PageShell>
        <div className="flex flex-col items-center gap-4 py-12">
          <Loader2 className="h-10 w-10 text-indigo-600 animate-spin" />
          <p className="font-semibold text-slate-700">Saving connection…</p>
        </div>
      </PageShell>
    )
  }

  // step === 'select'
  return (
    <PageShell>
      <p className="text-sm text-slate-500 mb-6">
        Choose which Meta ad account to connect to this client. You can change this later.
      </p>

      {adAccounts.length === 0 ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          No Meta ad accounts were found. Make sure you have access to at least one ad account,
          and that it has the <strong>ads_read</strong> permission.
        </div>
      ) : (
        <ul className="space-y-2 mb-6">
          {adAccounts.map((acct) => (
            <li key={acct.account_id}>
              <button
                onClick={() => setSelected(acct.account_id)}
                className={`w-full text-left rounded-lg border px-4 py-3 transition-colors flex items-center gap-3 ${
                  selected === acct.account_id
                    ? 'border-indigo-400 bg-indigo-50 ring-1 ring-indigo-300'
                    : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <Megaphone className={`h-4 w-4 shrink-0 ${selected === acct.account_id ? 'text-indigo-600' : 'text-slate-400'}`} />
                <div>
                  <p className="text-sm font-medium text-slate-800">{acct.account_name}</p>
                  <p className="text-xs text-slate-400">{acct.account_id} · {acct.currency}</p>
                </div>
                {selected === acct.account_id && (
                  <CheckCircle className="h-4 w-4 text-indigo-600 ml-auto" />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex gap-3">
        <button
          onClick={() => router.push(clientId ? `/dashboard/clients/${clientId}` : '/dashboard/integrations')}
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={!selected || !clientId}
          className="rounded-lg bg-indigo-700 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-50"
        >
          Connect this account
        </button>
      </div>
    </PageShell>
  )
}

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-w-lg mx-auto">
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700 flex items-center gap-2">
            <Megaphone className="h-4 w-4 text-blue-500" />
            Connect Meta Ads
          </CardTitle>
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </div>
  )
}
