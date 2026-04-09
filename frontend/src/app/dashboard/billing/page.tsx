'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { billingApi, type SubscriptionStatus } from '@/lib/api'
import { toast } from 'sonner'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PaymentRecord {
  id: string
  razorpay_payment_id: string | null
  amount: number
  currency: string
  status: string
  plan: string | null
  description: string | null
  created_at: string
}

interface PlanCard {
  key: string
  name: string
  monthly_inr: number
  annual_inr: number
  monthly_usd: number
  annual_usd: number
  client_limit: number
  features: string[]
  highlight?: boolean
}

// ---------------------------------------------------------------------------
// Plan data (mirrors backend config/plans.py)
// ---------------------------------------------------------------------------

const PLAN_CARDS: PlanCard[] = [
  {
    key: 'starter',
    name: 'Starter',
    monthly_inr: 999,
    annual_inr: 9599,
    monthly_usd: 19,
    annual_usd: 182,
    client_limit: 5,
    features: [
      '5 clients',
      'PDF export',
      'Email delivery',
      'Professional AI tone',
      '1 visual template',
    ],
  },
  {
    key: 'pro',
    name: 'Pro',
    monthly_inr: 1999,
    annual_inr: 19199,
    monthly_usd: 39,
    annual_usd: 374,
    client_limit: 15,
    features: [
      '15 clients',
      'PDF + PPTX export',
      'Scheduled reports',
      'All 4 AI tones',
      'All 3 visual templates',
      'White-label branding',
      'No "Powered by" badge',
    ],
    highlight: true,
  },
  {
    key: 'agency',
    name: 'Agency',
    monthly_inr: 3499,
    annual_inr: 33599,
    monthly_usd: 69,
    annual_usd: 662,
    client_limit: 999,
    features: [
      'Unlimited clients',
      'PDF + PPTX export',
      'Scheduled reports',
      'All 4 AI tones',
      'All 3 visual templates',
      'White-label branding',
      'Priority support + API',
    ],
  },
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatAmount(amount: number, currency: string): string {
  if (currency === 'INR') return `₹${(amount / 100).toLocaleString('en-IN')}`
  return `$${(amount / 100).toFixed(2)}`
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function loadRazorpayScript(): Promise<void> {
  return new Promise((resolve) => {
    if ((window as unknown as Record<string, unknown>)['Razorpay']) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.onload = () => resolve()
    document.body.appendChild(script)
  })
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    trialing: 'bg-blue-100 text-blue-700',
    active: 'bg-emerald-100 text-emerald-700',
    past_due: 'bg-amber-100 text-amber-700',
    cancelled: 'bg-slate-100 text-slate-600',
    expired: 'bg-rose-100 text-rose-700',
    paused: 'bg-orange-100 text-orange-700',
  }
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full capitalize ${map[status] ?? 'bg-slate-100 text-slate-600'}`}>
      {status.replace('_', ' ')}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function BillingPage() {
  const router = useRouter()
  const [sub, setSub] = useState<SubscriptionStatus | null>(null)
  const [payments, setPayments] = useState<PaymentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly')
  const [currency, setCurrency] = useState<'INR' | 'USD'>('INR')
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null)
  const [cancelLoading, setCancelLoading] = useState(false)
  const [showCancelConfirm, setShowCancelConfirm] = useState(false)

  // Detect currency on mount
  useEffect(() => {
    try {
      const lang = navigator.language || ''
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''
      if (lang.startsWith('hi') || tz.includes('Calcutta') || tz.includes('Kolkata')) {
        setCurrency('INR')
      } else {
        setCurrency('USD')
      }
    } catch {
      // default INR
    }
  }, [])

  const fetchData = useCallback(async () => {
    try {
      const [subData, histData] = await Promise.all([
        billingApi.getSubscription(),
        billingApi.getPaymentHistory(),
      ])
      setSub(subData)
      setPayments((histData.payments as unknown as PaymentRecord[]) ?? [])
    } catch {
      toast.error('Failed to load billing information')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  // ── Checkout ────────────────────────────────────────────────────────────

  const handleSubscribe = async (planKey: string) => {
    setCheckoutLoading(planKey)
    try {
      const { subscription_id, razorpay_key_id } = await billingApi.createSubscription({
        plan: planKey,
        billing_cycle: billingCycle,
        currency,
      })

      await loadRazorpayScript()

      const options = {
        key: razorpay_key_id,
        subscription_id,
        name: 'GoReportPilot',
        description: `${planKey.charAt(0).toUpperCase() + planKey.slice(1)} Plan — ${billingCycle}`,
        handler: async (response: { razorpay_payment_id: string; razorpay_subscription_id: string; razorpay_signature: string }) => {
          await billingApi.verifyPayment({
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_subscription_id: response.razorpay_subscription_id,
            razorpay_signature: response.razorpay_signature,
          })
          toast.success('Subscription activated!')
          router.refresh()
          fetchData()
        },
        prefill: {},
        theme: { color: '#4338CA' },
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const rzp = new (window as any).Razorpay(options)
      rzp.open()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to start checkout'
      if (msg.includes('not configured')) {
        toast.error('Razorpay not configured yet — add API keys to backend .env')
      } else {
        toast.error(msg)
      }
    } finally {
      setCheckoutLoading(null)
    }
  }

  // ── Cancel ──────────────────────────────────────────────────────────────

  const handleCancel = async () => {
    setCancelLoading(true)
    try {
      await billingApi.cancel()
      toast.success('Subscription will cancel at end of billing period')
      setShowCancelConfirm(false)
      fetchData()
    } catch {
      toast.error('Failed to cancel subscription')
    } finally {
      setCancelLoading(false)
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="h-8 w-48 bg-slate-200 rounded animate-pulse" />
        <div className="h-32 bg-slate-200 rounded-lg animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => <div key={i} className="h-64 bg-slate-200 rounded-lg animate-pulse" />)}
        </div>
      </div>
    )
  }

  const isTrialing = sub?.status === 'trialing'
  const isExpired = sub?.status === 'expired'
  const isPastDue = sub?.status === 'past_due'

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-slate-900">Billing & Subscription</h1>

      {/* ── Trial/Status banners ─────────────────────────────────────────── */}
      {isExpired && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 flex items-center justify-between">
          <p className="text-sm text-rose-800 font-medium">
            Your free trial has ended. Subscribe to continue generating reports.
          </p>
          <a href="#plans" className="text-sm font-semibold text-rose-700 hover:underline">View Plans →</a>
        </div>
      )}
      {isPastDue && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <p className="text-sm text-amber-800 font-medium">
            Your payment failed. Please update your payment method to keep your subscription active.
          </p>
        </div>
      )}

      {/* ── Section 1: Current Plan ──────────────────────────────────────── */}
      {sub && (
        <div className="bg-white border border-slate-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Current Plan</h2>
          <div className="flex flex-wrap items-start gap-6">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-2xl font-bold text-indigo-700">{sub.display_name}</span>
                <StatusBadge status={sub.status} />
              </div>
              {isTrialing && sub.trial_days_remaining !== null && (
                <p className="text-sm text-slate-500">
                  Trial ends in <strong>{sub.trial_days_remaining}</strong> day{sub.trial_days_remaining !== 1 ? 's' : ''}
                  {sub.trial_ends_at ? ` (${formatDate(sub.trial_ends_at)})` : ''}
                </p>
              )}
              {sub.current_period_end && sub.status === 'active' && (
                <p className="text-sm text-slate-500">
                  {sub.cancel_at_period_end
                    ? `Cancels on ${formatDate(sub.current_period_end)}`
                    : `Renews ${formatDate(sub.current_period_end)}`}
                </p>
              )}
            </div>

            <div className="flex-1 min-w-[200px]">
              <div className="flex justify-between text-sm text-slate-600 mb-1">
                <span>Clients</span>
                <span className="font-medium">{sub.client_count} / {sub.client_limit}</span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    sub.client_count >= sub.client_limit ? 'bg-rose-500' : 'bg-indigo-500'
                  }`}
                  style={{ width: `${Math.min(100, (sub.client_count / sub.client_limit) * 100)}%` }}
                />
              </div>
              {sub.client_count >= sub.client_limit && (
                <p className="text-xs text-rose-600 mt-1">Client limit reached — upgrade to add more</p>
              )}
            </div>
          </div>

          {/* Cancel / manage */}
          {sub.status === 'active' && !sub.cancel_at_period_end && (
            <div className="mt-4 pt-4 border-t border-slate-100">
              <button
                onClick={() => setShowCancelConfirm(true)}
                className="text-sm text-rose-600 hover:underline"
              >
                Cancel subscription
              </button>
            </div>
          )}
        </div>
      )}

      {/* Cancel confirmation dialog */}
      {showCancelConfirm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900 mb-2">Cancel subscription?</h3>
            <p className="text-sm text-slate-600 mb-4">
              Your plan will remain active until the end of the current billing period. After that, you&apos;ll be downgraded to free tier.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowCancelConfirm(false)}
                className="flex-1 px-4 py-2 border border-slate-200 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Keep subscription
              </button>
              <button
                onClick={handleCancel}
                disabled={cancelLoading}
                className="flex-1 px-4 py-2 bg-rose-600 text-white rounded-md text-sm font-medium hover:bg-rose-700 disabled:opacity-50"
              >
                {cancelLoading ? 'Cancelling…' : 'Yes, cancel'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Section 2: Plan Comparison ───────────────────────────────────── */}
      <div id="plans">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Plans</h2>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
              <button
                onClick={() => setBillingCycle('monthly')}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  billingCycle === 'monthly' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                Monthly
              </button>
              <button
                onClick={() => setBillingCycle('annual')}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  billingCycle === 'annual' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                Annual
                <span className="ml-1 text-xs text-emerald-600 font-semibold">Save 20%</span>
              </button>
            </div>
            <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
              <button
                onClick={() => setCurrency('INR')}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  currency === 'INR' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                INR
              </button>
              <button
                onClick={() => setCurrency('USD')}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  currency === 'USD' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                USD
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {PLAN_CARDS.map((plan) => {
            const isCurrent = sub?.plan === plan.key
            const isINR = currency === 'INR'
            const priceMain = isINR
              ? (billingCycle === 'monthly' ? plan.monthly_inr : Math.round(plan.annual_inr / 12))
              : (billingCycle === 'monthly' ? plan.monthly_usd : Math.round(plan.annual_usd / 12))
            const priceLabel = isINR
              ? `\u20B9${priceMain.toLocaleString('en-IN')}`
              : `$${priceMain}`
            const annualTotal = isINR
              ? `\u20B9${plan.annual_inr.toLocaleString('en-IN')}/year`
              : `$${plan.annual_usd}/year`
            return (
              <div
                key={plan.key}
                className={`relative rounded-xl border p-6 flex flex-col ${
                  plan.highlight
                    ? 'border-indigo-500 bg-indigo-50 shadow-md'
                    : 'border-slate-200 bg-white'
                } ${isCurrent ? 'ring-2 ring-indigo-500' : ''}`}
              >
                {plan.highlight && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-xs font-semibold px-3 py-0.5 rounded-full">
                    Most Popular
                  </span>
                )}
                {isCurrent && (
                  <span className="absolute top-3 right-3 bg-indigo-100 text-indigo-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                    Current
                  </span>
                )}

                <h3 className="text-lg font-bold text-slate-900">{plan.name}</h3>
                <div className="mt-2 mb-1">
                  <span className="text-3xl font-extrabold text-slate-900">{priceLabel}</span>
                  <span className="text-slate-500 text-sm">/mo</span>
                </div>
                {billingCycle === 'annual' && (
                  <p className="text-xs text-emerald-600 font-medium mb-3">
                    Billed {annualTotal} (save 20%)
                  </p>
                )}

                <ul className="mt-3 space-y-1.5 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-slate-700">
                      <svg className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      {f}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleSubscribe(plan.key)}
                  disabled={isCurrent || checkoutLoading === plan.key}
                  className={`mt-5 w-full py-2 rounded-md text-sm font-semibold transition-colors disabled:opacity-50 ${
                    isCurrent
                      ? 'bg-slate-100 text-slate-400 cursor-default'
                      : plan.highlight
                      ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                      : 'bg-white border border-indigo-600 text-indigo-700 hover:bg-indigo-50'
                  }`}
                >
                  {checkoutLoading === plan.key
                    ? 'Loading…'
                    : isCurrent
                    ? 'Current plan'
                    : sub?.plan && sub.plan !== 'trial' && sub.status === 'active'
                    ? plan.key > sub.plan ? 'Upgrade' : 'Downgrade'
                    : 'Subscribe'}
                </button>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Section 3: Payment History ───────────────────────────────────── */}
      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Payment History</h2>
        {payments.length === 0 ? (
          <p className="text-sm text-slate-500">No payments yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left py-2 text-slate-500 font-medium">Date</th>
                  <th className="text-left py-2 text-slate-500 font-medium">Amount</th>
                  <th className="text-left py-2 text-slate-500 font-medium">Plan</th>
                  <th className="text-left py-2 text-slate-500 font-medium">Status</th>
                  <th className="text-left py-2 text-slate-500 font-medium">Payment ID</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((p) => (
                  <tr key={p.id} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="py-2.5 text-slate-700">{formatDate(p.created_at)}</td>
                    <td className="py-2.5 text-slate-900 font-medium">{formatAmount(p.amount, p.currency)}</td>
                    <td className="py-2.5 text-slate-700 capitalize">{p.plan ?? '—'}</td>
                    <td className="py-2.5">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                        p.status === 'captured' ? 'bg-emerald-100 text-emerald-700' :
                        p.status === 'failed' ? 'bg-rose-100 text-rose-700' :
                        'bg-slate-100 text-slate-600'
                      }`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="py-2.5 text-slate-400 font-mono text-xs">{p.razorpay_payment_id ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
