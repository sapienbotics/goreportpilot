'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Check } from 'lucide-react'
import { detectCurrency, type Currency } from '@/lib/detect-currency'

// ---------------------------------------------------------------------------
// Plan data — mirrors backend services/plans.py pricing
// ---------------------------------------------------------------------------

interface PlanDef {
  name: string
  monthlyINR: number
  annualINR: number
  monthlyUSD: number
  annualUSD: number
  description: string
  features: string[]
  cta: string
  popular: boolean
}

// Feature lists are cross-checked against backend/services/plans.py — the
// plans module is the live source of truth for what each tier actually
// enforces. Any drift here becomes a chargeback risk when a customer
// upgrades expecting a feature that doesn't exist.
const PLANS: PlanDef[] = [
  {
    name: 'Starter',
    monthlyINR: 999,
    annualINR: 9590,
    monthlyUSD: 19,
    annualUSD: 182,
    description: 'For freelancers getting started with automation.',
    features: [
      'Up to 5 clients',
      'Google Analytics 4, Meta Ads, Google Ads, Search Console',
      'CSV upload for any other data source',
      'AI narrative — Professional tone',
      'PDF export + email delivery',
      '1 visual template (Modern Clean)',
      '"Powered by GoReportPilot" badge on reports',
    ],
    cta: 'Start My Free Trial',
    popular: false,
  },
  {
    name: 'Pro',
    monthlyINR: 1999,
    annualINR: 19190,
    monthlyUSD: 39,
    annualUSD: 374,
    description: 'For growing agencies managing multiple clients.',
    features: [
      'Up to 15 clients',
      'Everything in Starter, plus:',
      'PPTX + PDF export',
      '6 visual templates',
      'All 4 AI tones (Professional, Conversational, Executive, Data-Heavy)',
      'Scheduled reports (weekly / biweekly / monthly)',
      'White-label branding — no GoReportPilot badge',
      'Multi-language reports (13 languages)',
    ],
    cta: 'Start My Free Trial',
    popular: true,
  },
  {
    name: 'Agency',
    monthlyINR: 3499,
    annualINR: 33590,
    monthlyUSD: 69,
    annualUSD: 662,
    description: 'For established agencies at scale.',
    features: [
      'Unlimited clients',
      'Everything in Pro, plus:',
      'Unlimited scheduled reports',
      'Unlimited email delivery',
    ],
    cta: 'Start My Free Trial',
    popular: false,
  },
]

export default function PricingToggle() {
  const [annual, setAnnual] = useState(false)
  const [currency, setCurrency] = useState<Currency>('USD')

  useEffect(() => {
    setCurrency(detectCurrency())
  }, [])

  const isINR = currency === 'INR'

  const fmtPrice = (plan: PlanDef) => {
    if (isINR) {
      const price = annual ? Math.round(plan.annualINR / 12) : plan.monthlyINR
      return `\u20B9${price.toLocaleString('en-IN')}`
    }
    const price = annual ? Math.round(plan.annualUSD / 12) : plan.monthlyUSD
    return `$${price}`
  }

  const fmtAnnualTotal = (plan: PlanDef) => {
    if (isINR) return `\u20B9${plan.annualINR.toLocaleString('en-IN')}/yr`
    return `$${plan.annualUSD}/yr`
  }

  return (
    <div>
      <div className="flex items-center justify-center gap-3 mt-8 mb-4">
        <span className={`text-sm font-medium ${!annual ? 'text-slate-900' : 'text-slate-400'}`}>Monthly</span>
        <button
          onClick={() => setAnnual((v) => !v)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
            annual ? 'bg-indigo-600' : 'bg-slate-200'
          }`}
          role="switch"
          aria-checked={annual}
          aria-label="Toggle annual billing"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
              annual ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
        <span className={`text-sm font-medium ${annual ? 'text-slate-900' : 'text-slate-400'}`}>
          Annual{' '}
          <span className="ml-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
            Save 20%
          </span>
        </span>
      </div>

      <div className="mb-10" />

      <div className="grid md:grid-cols-3 gap-6">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={`relative rounded-2xl p-7 flex flex-col ${
              plan.popular
                ? 'bg-indigo-700 text-white shadow-xl ring-2 ring-indigo-700'
                : 'bg-white border border-slate-200 shadow-sm'
            }`}
          >
            {plan.popular && (
              <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 rounded-full bg-emerald-500 px-3.5 py-1 text-xs font-bold text-white uppercase tracking-wide shadow">
                Most Popular
              </span>
            )}

            <div className="mb-5">
              <p
                className={`text-base font-bold ${plan.popular ? 'text-indigo-200' : 'text-slate-500'}`}
              >
                {plan.name}
              </p>
              <div className="mt-2 flex items-end gap-1">
                <span
                  className={`text-4xl font-extrabold ${plan.popular ? 'text-white' : 'text-slate-900'}`}
                  style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
                >
                  {fmtPrice(plan)}
                </span>
                <span className={`mb-1 text-sm ${plan.popular ? 'text-indigo-300' : 'text-slate-400'}`}>/mo</span>
              </div>
              {annual && (
                <p className={`mt-0.5 text-xs ${plan.popular ? 'text-indigo-300' : 'text-slate-400'}`}>
                  billed annually ({fmtAnnualTotal(plan)})
                </p>
              )}
              <p className={`mt-2 text-sm ${plan.popular ? 'text-indigo-200' : 'text-slate-500'}`}>
                {plan.description}
              </p>
            </div>

            <ul className="space-y-3 mb-7 flex-1">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2.5">
                  <Check
                    className={`mt-0.5 h-4 w-4 shrink-0 ${plan.popular ? 'text-emerald-400' : 'text-emerald-500'}`}
                  />
                  <span className={`text-sm ${plan.popular ? 'text-indigo-100' : 'text-slate-600'}`}>{f}</span>
                </li>
              ))}
            </ul>

            <Link
              href="/signup"
              onClick={() => {
                if (typeof window !== 'undefined' && window.gtag) {
                  window.gtag('event', 'select_plan', {
                    plan_name: plan.name,
                    billing_cycle: annual ? 'annual' : 'monthly',
                  })
                }
              }}
              className={`block rounded-lg px-5 py-3 text-center text-sm font-semibold transition-colors ${
                plan.popular
                  ? 'bg-white text-indigo-700 hover:bg-indigo-50'
                  : 'border border-indigo-700 text-indigo-700 hover:bg-indigo-50'
              }`}
            >
              {plan.cta}
            </Link>
          </div>
        ))}
      </div>

      <p className="mt-8 text-center text-sm text-slate-400">
        All plans include a 14-day free trial. No credit card required.
      </p>
      <p className="mt-2 text-center text-xs text-slate-400">
        Prices shown in {isINR ? 'INR' : 'USD'}. International cards accepted.
      </p>
    </div>
  )
}
