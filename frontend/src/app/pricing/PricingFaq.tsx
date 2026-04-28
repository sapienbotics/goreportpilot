'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

const FAQS = [
  {
    q: "What's included in the 14-day free trial?",
    a: "Everything in the Pro plan — PPTX export, all 6 visual templates, all 4 AI tones, white-label branding, and scheduled reports. You can manage up to 10 clients and generate up to 5 reports during the trial. No credit card required to start.",
  },
  {
    q: 'Do I need a credit card to start?',
    a: "No. Sign up with just your email. Your card details are only collected if you choose a paid plan after the trial ends.",
  },
  {
    q: 'What happens when my trial ends?',
    a: "Your account moves to read-only mode — all reports, client data, and integrations are preserved. Choose a plan to continue generating new reports. Nothing is deleted.",
  },
  {
    q: 'Can I switch plans at any time?',
    a: "Yes. Upgrades take effect immediately and are prorated. Downgrades take effect at the end of your current billing cycle. All your clients, reports, and connections carry over.",
  },
  {
    q: 'What payment methods do you accept?',
    a: "All major credit and debit cards via Razorpay. INR payments are processed domestically; international cards are accepted in USD.",
  },
  {
    q: 'Is there an annual commitment?',
    a: "No commitment required. Monthly billing is the default. Switch to annual to save 20% — you can switch back anytime.",
  },
  {
    q: 'Can I get a refund?',
    a: "We offer a 7-day refund on your first payment if you're not satisfied. See our Refund Policy for full details.",
  },
  {
    q: "What happens to my data if I cancel?",
    a: "Your reports and client data are preserved for 30 days after cancellation. Export anytime before that window closes.",
  },
  {
    q: 'Do you offer discounts for agencies or nonprofits?',
    a: "Yes — evaluated case by case. Email support@goreportpilot.com with a brief description of your situation.",
  },
  {
    q: "I have more than 15 clients. Which plan is right for me?",
    a: "Agency plan at $69/mo gives unlimited clients. Most Pro users find 15 covers their active roster comfortably — inactive clients don't count against the limit.",
  },
]

export default function PricingFaq() {
  const [open, setOpen] = useState<number | null>(null)

  return (
    <div className="divide-y divide-slate-100 rounded-xl border border-slate-100 bg-white overflow-hidden shadow-sm">
      {FAQS.map((faq, i) => (
        <div key={i}>
          <button
            onClick={() => setOpen(open === i ? null : i)}
            className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left hover:bg-slate-50 transition-colors"
            aria-expanded={open === i}
          >
            <span className="text-sm font-semibold text-slate-900">{faq.q}</span>
            <ChevronDown
              className={`h-4 w-4 shrink-0 text-slate-400 transition-transform duration-200 ${
                open === i ? 'rotate-180' : ''
              }`}
            />
          </button>
          {open === i && (
            <div className="px-6 pb-5">
              <p className="text-sm text-slate-500 leading-relaxed">{faq.a}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
