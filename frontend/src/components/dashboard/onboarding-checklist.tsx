'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { CheckCircle2, ArrowRight, X, Sparkles } from 'lucide-react'

interface OnboardingStatus {
  has_client: boolean
  has_connection: boolean
  has_report: boolean
  complete: boolean
}

interface Props {
  onboarding: OnboardingStatus
}

const STORAGE_KEY = 'rp_onboarding_dismissed'

const STEPS = [
  {
    key: 'has_client' as const,
    label: 'Add your first client',
    href: '/dashboard/clients',
    cta: 'Add Client',
  },
  {
    key: 'has_connection' as const,
    label: 'Connect a data source (GA4, Meta Ads, etc.)',
    href: '/dashboard/clients',
    cta: 'Connect',
  },
  {
    key: 'has_report' as const,
    label: 'Generate your first report',
    href: '/dashboard/clients',
    cta: 'Generate',
  },
]

export default function OnboardingChecklist({ onboarding }: Props) {
  const [dismissed, setDismissed] = useState(true) // start hidden to avoid flash

  useEffect(() => {
    setDismissed(localStorage.getItem(STORAGE_KEY) === '1')
  }, [])

  if (dismissed) return null
  if (onboarding.complete) {
    // Show success state briefly before allowing dismiss
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-6 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
            <Sparkles className="h-5 w-5 text-emerald-600" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-emerald-800">You&apos;re all set!</h2>
            <p className="text-sm text-emerald-600">You&apos;ve completed all onboarding steps. Happy reporting!</p>
          </div>
        </div>
        <button
          onClick={() => {
            localStorage.setItem(STORAGE_KEY, '1')
            setDismissed(true)
          }}
          className="shrink-0 rounded-lg border border-emerald-300 bg-white px-3 py-1.5 text-sm font-medium text-emerald-700 hover:bg-emerald-50 transition-colors"
        >
          Dismiss
        </button>
      </div>
    )
  }

  const completedCount = STEPS.filter((s) => onboarding[s.key]).length

  return (
    <div className="rounded-xl border border-indigo-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4 mb-5">
        <div>
          <h2 className="text-lg font-bold text-slate-900">
            Welcome to GoReportPilot!
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Generate your first AI-powered report in 3 steps.
          </p>
        </div>
        <button
          onClick={() => {
            localStorage.setItem(STORAGE_KEY, '1')
            setDismissed(true)
          }}
          className="text-slate-400 hover:text-slate-600 transition-colors shrink-0"
          aria-label="Dismiss onboarding"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Progress bar */}
      <div className="flex items-center gap-2 mb-5">
        <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-600 rounded-full transition-all duration-500"
            style={{ width: `${(completedCount / 3) * 100}%` }}
          />
        </div>
        <span className="text-xs text-slate-400 font-medium">{completedCount}/3</span>
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {STEPS.map((step, i) => {
          const done = onboarding[step.key]
          return (
            <div
              key={step.key}
              className={`flex items-center justify-between rounded-lg border px-4 py-3 transition-colors ${
                done
                  ? 'border-emerald-200 bg-emerald-50/50'
                  : 'border-slate-200 bg-white hover:border-indigo-200 hover:bg-indigo-50/30'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                  done ? 'bg-emerald-100 text-emerald-600' : 'bg-indigo-100 text-indigo-600'
                }`}>
                  {done ? <CheckCircle2 className="h-4 w-4" /> : i + 1}
                </div>
                <span className={`text-sm font-medium ${done ? 'text-emerald-700 line-through' : 'text-slate-700'}`}>
                  {step.label}
                </span>
              </div>
              {!done && (
                <Link
                  href={step.href}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition-colors"
                >
                  {step.cta}
                  <ArrowRight className="h-3 w-3" />
                </Link>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
