'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

const FAQS = [
  {
    q: 'What data sources do you support?',
    a: 'Google Analytics 4, Meta Ads (Facebook & Instagram), Google Ads, and Google Search Console — all via secure OAuth. For any platform we don\'t directly integrate with (LinkedIn Ads, TikTok Ads, Shopify, HubSpot, etc.), you can upload a CSV with your metrics and we\'ll include them in the report with AI-generated narrative.',
  },
  {
    q: 'How does the AI narrative work?',
    a: 'We send your client\'s performance data to GPT-4.1 with context about their goals and industry. The AI writes 3–4 paragraphs of narrative analysis — not generic summaries, but specific insights referencing actual numbers and trends.',
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
    q: 'What happens when I reach my client limit?',
    a: 'Starter allows up to 5 clients, Pro up to 15. If you need more, upgrade to Agency for unlimited clients. Upgrading is instant — your existing reports, schedules, and connections stay exactly as they are. You can also downgrade anytime.',
  },
  {
    q: 'Can I cancel anytime?',
    a: 'Yes. No contracts, no cancellation fees. Your data is preserved for 30 days after cancellation in case you want to come back.',
  },
  {
    q: 'Does it work for SEO clients?',
    a: 'Yes. Connect Google Search Console to include organic search performance — queries, clicks, CTR, and average position — in your reports with AI-written SEO narrative.',
  },
  {
    q: 'Can I schedule reports to auto-deliver?',
    a: 'Yes, on Pro and Agency plans. Set weekly, biweekly, or monthly schedules with timezone-aware delivery. Reports auto-generate and email to your clients as PDF, PPTX, or both — you choose the format.',
  },
  {
    q: 'What languages can reports be written in?',
    a: 'GoReportPilot supports 13 languages for AI-generated narrative: English, Spanish, French, German, Portuguese, Italian, Dutch, Hindi, Japanese, Korean, Chinese (Simplified), Arabic, and Russian.',
  },
  {
    q: 'Will my clients know I\'m using GoReportPilot?',
    a: 'On Pro and Agency plans, white-label branding removes all GoReportPilot branding. Your logo, your colors, your agency name — clients see only your brand. On Starter, a small "Powered by GoReportPilot" badge appears on reports.',
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
