'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Check } from 'lucide-react'

const PLANS = [
  {
    name: 'Starter',
    monthly: 19,
    annual: 15,
    description: 'For freelancers getting started with automation.',
    features: [
      'Up to 3 clients',
      'Google Analytics + Meta Ads',
      'AI narrative insights',
      'PDF export',
      'Monthly scheduling',
    ],
    cta: 'Start Free Trial',
    popular: false,
  },
  {
    name: 'Pro',
    monthly: 39,
    annual: 31,
    description: 'For growing agencies managing multiple clients.',
    features: [
      'Up to 10 clients',
      'Google Ads integration',
      'PowerPoint export',
      'White-label branding',
      'Weekly + Monthly scheduling',
    ],
    cta: 'Start Free Trial',
    popular: true,
  },
  {
    name: 'Agency',
    monthly: 69,
    annual: 55,
    description: 'For established agencies at scale.',
    features: [
      'Up to 25 clients',
      'All integrations',
      'Custom report templates',
      'Priority support',
      'Any frequency scheduling',
    ],
    cta: 'Start Free Trial',
    popular: false,
  },
]

export default function PricingToggle() {
  const [annual, setAnnual] = useState(false)

  return (
    <div>
      {/* Toggle */}
      <div className="flex items-center justify-center gap-3 mt-8 mb-10">
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

      {/* Cards */}
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
                  ${annual ? plan.annual : plan.monthly}
                </span>
                <span className={`mb-1 text-sm ${plan.popular ? 'text-indigo-300' : 'text-slate-400'}`}>/mo</span>
              </div>
              {annual && (
                <p className={`mt-0.5 text-xs ${plan.popular ? 'text-indigo-300' : 'text-slate-400'}`}>
                  billed annually (${plan.annual * 12}/yr)
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
    </div>
  )
}
