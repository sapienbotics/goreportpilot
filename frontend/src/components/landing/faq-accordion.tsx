'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

const FAQS = [
  {
    q: 'What data sources do you support?',
    a: 'Currently Google Analytics 4, Meta Ads (Facebook & Instagram), and Google Ads. We\'re adding Google Search Console, LinkedIn Ads, and TikTok Ads soon.',
  },
  {
    q: 'How does the AI narrative work?',
    a: 'We send your client\'s performance data to GPT-4o with context about their goals and industry. The AI writes 3–4 paragraphs of narrative analysis — not generic summaries, but specific insights referencing actual numbers and trends.',
  },
  {
    q: 'Can I edit the AI-generated text?',
    a: 'Absolutely. Every paragraph has an edit button. Change anything you want before sending to your client. Your edits are saved and won\'t be overwritten.',
  },
  {
    q: 'Is my clients\' data secure?',
    a: 'Yes. OAuth tokens are encrypted with AES-256-GCM before storage. We use Supabase with Row-Level Security — your data is isolated from other users at the database level. We never share or sell data.',
  },
  {
    q: 'What if I need more than 25 clients?',
    a: 'Contact us at hello@reportpilot.co and we\'ll set up a custom plan for your agency.',
  },
  {
    q: 'Can I cancel anytime?',
    a: 'Yes. No contracts, no cancellation fees. Your data is preserved for 30 days after cancellation in case you want to come back.',
  },
]

export default function FaqAccordion() {
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
