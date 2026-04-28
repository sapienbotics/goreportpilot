// /pricing — dedicated public marketing page
// Server Component. Client sub-components: PricingToggle (plan cards), PricingFaq (accordion).
// All pricing data flows from PricingToggle which mirrors backend/services/plans.py.

import type { Metadata } from 'next'
import Link from 'next/link'
import { Check, Minus, ArrowRight, Shield, Clock, Zap } from 'lucide-react'
import { Logo } from '@/components/ui/Logo'
import MobileNav from '@/components/landing/mobile-nav'
import PricingToggle from '@/components/landing/pricing-toggle'
import PricingFaq from './PricingFaq'

export const metadata: Metadata = {
  title: 'Pricing — GoReportPilot',
  description:
    'Simple, flat pricing for AI-powered client reporting. Starter from $19/mo, Pro from $39/mo, Agency from $69/mo. 14-day free trial, no credit card required.',
  alternates: { canonical: 'https://goreportpilot.com/pricing' },
  openGraph: {
    title: 'Pricing — GoReportPilot',
    description: 'Simple, flat pricing for AI-powered client reporting. 14-day free trial, no credit card.',
    url: 'https://goreportpilot.com/pricing',
    siteName: 'GoReportPilot',
    type: 'website',
  },
}

// ─── Feature matrix data ────────────────────────────────────────────────────
// Keep in sync with backend/services/plans.py and PricingToggle PLANS constant.

type Cell = 'yes' | 'no' | string  // 'yes' → Check icon, 'no' → Dash, string → text

interface MatrixRow {
  label: string
  starter: Cell
  pro: Cell
  agency: Cell
  note?: string
}

interface MatrixSection {
  title: string
  rows: MatrixRow[]
}

const MATRIX: MatrixSection[] = [
  {
    title: 'Clients & Scale',
    rows: [
      { label: 'Clients managed',     starter: '5',          pro: '15',         agency: 'Unlimited' },
      { label: 'Active integrations', starter: 'Unlimited',  pro: 'Unlimited',  agency: 'Unlimited' },
    ],
  },
  {
    title: 'Data Integrations',
    rows: [
      { label: 'Google Analytics 4',          starter: 'yes', pro: 'yes', agency: 'yes' },
      { label: 'Meta Ads (Facebook & Instagram)', starter: 'yes', pro: 'yes', agency: 'yes' },
      { label: 'Google Ads + MCC',            starter: 'yes', pro: 'yes', agency: 'yes' },
      { label: 'Google Search Console',       starter: 'yes', pro: 'yes', agency: 'yes' },
      { label: 'CSV upload (any data source)', starter: 'yes', pro: 'yes', agency: 'yes',
        note: 'LinkedIn Ads, TikTok, Shopify, HubSpot, and any other platform' },
    ],
  },
  {
    title: 'Report Generation',
    rows: [
      { label: 'PDF export',                         starter: 'yes',       pro: 'yes',  agency: 'yes' },
      { label: 'PPTX export (editable PowerPoint)',  starter: 'no',        pro: 'yes',  agency: 'yes' },
      { label: 'AI-written narrative',               starter: 'yes',       pro: 'yes',  agency: 'yes' },
      { label: 'AI tone options',                    starter: '1 (Professional)', pro: '4 tones', agency: '4 tones' },
      { label: 'Visual PPTX templates',              starter: '1',         pro: '6',    agency: '6' },
      { label: '19 chart types',                     starter: 'yes',       pro: 'yes',  agency: 'yes' },
      { label: 'Reports in 13 languages',            starter: 'yes',       pro: 'yes',  agency: 'yes' },
      { label: 'Per-section edit & regenerate',      starter: 'yes',       pro: 'yes',  agency: 'yes' },
      { label: 'Share via public link',              starter: 'yes',       pro: 'yes',  agency: 'yes' },
      { label: 'Client comments on shared reports',  starter: 'yes',       pro: 'yes',  agency: 'yes' },
      { label: 'Custom cover page per client',       starter: 'no',        pro: 'yes',  agency: 'yes' },
    ],
  },
  {
    title: 'Scheduling & Delivery',
    rows: [
      { label: 'Email delivery to clients',                   starter: 'yes', pro: 'yes', agency: 'yes' },
      { label: 'Scheduled reports (weekly/biweekly/monthly)', starter: 'no',  pro: 'yes', agency: 'yes' },
      { label: 'Timezone-aware auto-delivery',                starter: 'no',  pro: 'yes', agency: 'yes' },
    ],
  },
  {
    title: 'White-Label Branding',
    rows: [
      { label: 'GoReportPilot badge on reports', starter: 'shown', pro: 'removed', agency: 'removed' },
      { label: 'Agency logo on every report',    starter: 'no',    pro: 'yes',     agency: 'yes' },
      { label: 'Custom brand color',             starter: 'no',    pro: 'yes',     agency: 'yes' },
      { label: 'Custom footer text',             starter: 'no',    pro: 'yes',     agency: 'yes' },
    ],
  },
  {
    title: 'Account',
    rows: [
      { label: '14-day free trial, no credit card', starter: 'yes', pro: 'yes', agency: 'yes' },
      { label: 'Cancel anytime',                    starter: 'yes', pro: 'yes', agency: 'yes' },
      { label: 'Data preserved 30 days on cancel',  starter: 'yes', pro: 'yes', agency: 'yes' },
    ],
  },
]

// ─── Cell renderer ──────────────────────────────────────────────────────────

function MatrixCell({ value, isPopular }: { value: Cell; isPopular?: boolean }) {
  const highlight = isPopular ? 'text-indigo-700 font-semibold' : 'text-slate-700'
  const muted     = isPopular ? 'text-indigo-300' : 'text-slate-300'

  if (value === 'yes') {
    return (
      <td className={`py-3 px-4 text-center ${isPopular ? 'bg-indigo-50' : ''}`}>
        <Check className={`mx-auto h-4 w-4 ${isPopular ? 'text-indigo-600' : 'text-emerald-500'}`} />
      </td>
    )
  }
  if (value === 'no') {
    return (
      <td className={`py-3 px-4 text-center ${isPopular ? 'bg-indigo-50' : ''}`}>
        <Minus className={`mx-auto h-4 w-4 ${muted}`} />
      </td>
    )
  }
  // Special badges for badge visibility row
  if (value === 'shown') {
    return (
      <td className={`py-3 px-4 text-center ${isPopular ? 'bg-indigo-50' : ''}`}>
        <span className="inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500">
          Shown
        </span>
      </td>
    )
  }
  if (value === 'removed') {
    return (
      <td className={`py-3 px-4 text-center ${isPopular ? 'bg-indigo-50' : ''}`}>
        <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
          isPopular ? 'bg-indigo-100 text-indigo-700' : 'bg-emerald-50 text-emerald-700'
        }`}>
          Removed
        </span>
      </td>
    )
  }
  // Text value (client counts, tone counts, etc.)
  return (
    <td className={`py-3 px-4 text-center text-sm ${isPopular ? 'bg-indigo-50 ' + highlight : highlight}`}>
      {value}
    </td>
  )
}

// ─── Page ───────────────────────────────────────────────────────────────────

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-white">

      {/* ─── NAV ─────────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-slate-100">
        <div className="mx-auto max-w-7xl px-6 h-16 flex items-center justify-between">
          <Link href="/">
            <Logo size="md" />
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <Link href="/#features" className="text-sm text-slate-600 hover:text-slate-900 transition-colors">
              Features
            </Link>
            <Link href="/pricing" className="text-sm font-semibold text-indigo-700">
              Pricing
            </Link>
            <Link href="/login" className="text-sm text-slate-600 hover:text-slate-900 transition-colors">
              Sign In
            </Link>
            <Link
              href="/signup"
              className="rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors"
            >
              Get Started
            </Link>
          </div>
          <MobileNav />
        </div>
      </nav>

      <main>

        {/* ─── HERO ────────────────────────────────────────────────────────── */}
        <section className="py-16 md:py-20 bg-white text-center">
          <div className="mx-auto max-w-3xl px-6">
            <div className="text-xs font-semibold text-indigo-600 uppercase tracking-[0.15em] mb-3">
              Pricing
            </div>
            <h1
              className="text-4xl md:text-5xl font-bold text-slate-900 leading-tight"
              style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
            >
              Simple, flat pricing.{' '}
              <span className="text-indigo-700">No surprises.</span>
            </h1>
            <p className="mt-5 text-lg text-slate-500 leading-relaxed max-w-xl mx-auto">
              One price per tier — unlimited reports, unlimited data pulls, no per-client fees. Start free for 14 days.
            </p>

            {/* Reassurance pills */}
            <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
              {[
                { icon: <Clock className="h-3.5 w-3.5" />, text: '14-day free trial' },
                { icon: <Shield className="h-3.5 w-3.5" />, text: 'No credit card required' },
                { icon: <Zap className="h-3.5 w-3.5" />, text: 'Cancel anytime' },
              ].map(({ icon, text }) => (
                <span
                  key={text}
                  className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3.5 py-1.5 text-xs font-medium text-slate-600"
                >
                  {icon}{text}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* ─── PLAN CARDS (PricingToggle — DRY, already has currency detection) ── */}
        <section className="pb-8 bg-slate-50">
          <div className="mx-auto max-w-5xl px-6">
            <PricingToggle />
          </div>
        </section>

        {/* ─── TRIAL DETAILS BANNER ────────────────────────────────────────── */}
        <section className="bg-indigo-700 py-10">
          <div className="mx-auto max-w-4xl px-6">
            <div className="text-center mb-7">
              <h2
                className="text-xl font-bold text-white"
                style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
              >
                What you get during the 14-day trial
              </h2>
              <p className="mt-1.5 text-sm text-indigo-200">
                Pro-tier features. No credit card. Up to 5 reports.
              </p>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { stat: 'Pro tier',       desc: 'Full Pro features unlocked for 14 days' },
                { stat: '5 reports',      desc: 'Generate up to 5 reports to evaluate quality' },
                { stat: '10 clients',     desc: 'Test with up to 10 clients during trial' },
                { stat: '6 templates',    desc: 'All 6 visual PPTX templates available' },
              ].map(({ stat, desc }) => (
                <div
                  key={stat}
                  className="rounded-xl bg-white/10 px-5 py-4 text-center backdrop-blur-sm"
                >
                  <p className="text-lg font-bold text-white">{stat}</p>
                  <p className="mt-1 text-xs text-indigo-200 leading-snug">{desc}</p>
                </div>
              ))}
            </div>
            <p className="mt-6 text-center text-xs text-indigo-300">
              After 14 days your account moves to read-only mode — all data preserved. No auto-charge.
            </p>
          </div>
        </section>

        {/* ─── FULL FEATURE MATRIX ─────────────────────────────────────────── */}
        <section className="py-20 bg-white">
          <div className="mx-auto max-w-5xl px-6">
            <div className="text-center mb-12">
              <h2
                className="text-3xl md:text-4xl font-bold text-slate-900"
                style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
              >
                Everything in detail
              </h2>
              <p className="mt-3 text-slate-500">
                Every feature, every tier — no marketing blur.
              </p>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-100 shadow-sm">
              <table className="w-full min-w-[560px] text-sm">
                {/* Sticky header */}
                <thead>
                  <tr className="border-b border-slate-100">
                    <th className="text-left py-4 px-6 text-slate-400 font-medium text-xs uppercase tracking-wide w-2/5">
                      Feature
                    </th>
                    <th className="text-center py-4 px-4 text-slate-500 font-semibold text-xs uppercase tracking-wide">
                      Starter
                    </th>
                    <th className="text-center py-4 px-4 bg-indigo-50 text-indigo-700 font-bold text-xs uppercase tracking-wide">
                      Pro ★
                    </th>
                    <th className="text-center py-4 px-4 text-slate-500 font-semibold text-xs uppercase tracking-wide">
                      Agency
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {MATRIX.map((section) => (
                    <>
                      {/* Section header row */}
                      <tr key={`section-${section.title}`} className="bg-slate-50 border-y border-slate-100">
                        <td
                          colSpan={4}
                          className="py-2.5 px-6 text-xs font-bold text-slate-400 uppercase tracking-widest"
                        >
                          {section.title}
                        </td>
                      </tr>
                      {/* Feature rows */}
                      {section.rows.map((row, i) => (
                        <tr
                          key={row.label}
                          className={`border-b border-slate-50 last:border-0 ${i % 2 === 1 ? 'bg-slate-50/30' : ''}`}
                        >
                          <td className="py-3 px-6 text-slate-700 font-medium text-sm">
                            {row.label}
                            {row.note && (
                              <span className="block text-xs text-slate-400 font-normal mt-0.5">
                                {row.note}
                              </span>
                            )}
                          </td>
                          <MatrixCell value={row.starter} />
                          <MatrixCell value={row.pro} isPopular />
                          <MatrixCell value={row.agency} />
                        </tr>
                      ))}
                    </>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="mt-4 text-center text-xs text-slate-400">
              ★ Most popular. Pro plan gives the best value for agencies managing 5–15 clients.
            </p>
          </div>
        </section>

        {/* ─── TRUST SECTION ───────────────────────────────────────────────── */}
        <section className="py-14 bg-slate-50 border-y border-slate-100">
          <div className="mx-auto max-w-4xl px-6">
            <div className="grid sm:grid-cols-3 gap-8 text-center">
              {[
                {
                  icon: <Shield className="h-6 w-6 text-indigo-600 mx-auto mb-2" />,
                  title: 'Your data, isolated',
                  desc: 'Row-Level Security on every table. OAuth tokens encrypted AES-256-GCM. We never share or sell data.',
                },
                {
                  icon: <Clock className="h-6 w-6 text-indigo-600 mx-auto mb-2" />,
                  title: 'First report in 5 minutes',
                  desc: 'Connect GA4, click Generate. First AI-written PDF or PPTX in under 5 minutes — no setup call, no onboarding.',
                },
                {
                  icon: <Zap className="h-6 w-6 text-indigo-600 mx-auto mb-2" />,
                  title: 'Cancel, keep your data',
                  desc: 'Cancel anytime. Reports, connections, and client data preserved for 30 days so you can export and leave without friction.',
                },
              ].map(({ icon, title, desc }) => (
                <div key={title}>
                  {icon}
                  <p className="text-sm font-semibold text-slate-900 mb-1">{title}</p>
                  <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ─── PRICING FAQ ─────────────────────────────────────────────────── */}
        <section className="py-20 bg-white">
          <div className="mx-auto max-w-3xl px-6">
            <div className="text-center mb-12">
              <h2
                className="text-3xl md:text-4xl font-bold text-slate-900"
                style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
              >
                Pricing questions
              </h2>
              <p className="mt-3 text-slate-500">
                Not covered here?{' '}
                <Link href="/contact" className="text-indigo-600 hover:underline">
                  Email us
                </Link>
                .
              </p>
            </div>
            <PricingFaq />
          </div>
        </section>

        {/* ─── FINAL CTA ───────────────────────────────────────────────────── */}
        <section className="py-24 bg-indigo-700">
          <div className="mx-auto max-w-3xl px-6 text-center">
            <h2
              className="text-3xl md:text-4xl font-bold text-white"
              style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
            >
              14 days free. No credit card.
            </h2>
            <p className="mt-4 text-lg text-indigo-200">
              Start your trial, generate your first report, and decide with real data — not a demo.
            </p>
            <Link
              href="/signup"
              className="mt-8 inline-flex items-center gap-2 rounded-lg bg-white px-8 py-3.5 text-base font-semibold text-indigo-700 hover:bg-indigo-50 transition-colors shadow-md"
            >
              Start Free Trial <ArrowRight className="h-4 w-4" />
            </Link>
            <p className="mt-4 text-sm text-indigo-300">
              Up to 5 reports · 10 clients · Pro features · No auto-charge
            </p>
          </div>
        </section>

      </main>

      {/* ─── FOOTER ──────────────────────────────────────────────────────── */}
      <footer className="bg-slate-900 py-14">
        <div className="mx-auto max-w-7xl px-6">
          <div className="grid md:grid-cols-3 gap-10">
            <div>
              <div className="mb-3">
                <Logo size="sm" variant="dark" />
              </div>
              <p className="text-slate-400 text-sm leading-relaxed">
                AI-powered client reporting for digital marketing agencies and freelancers.
                Automated. Branded. Professional.
              </p>
              <p className="mt-5 text-slate-500 text-xs">© 2026 SapienBotics. All rights reserved.</p>
            </div>

            <div>
              <p className="text-white font-semibold text-sm mb-4">Product</p>
              <ul className="space-y-2.5">
                {[
                  { label: 'Features', href: '/#features' },
                  { label: 'Pricing', href: '/pricing' },
                ].map(({ label, href }) => (
                  <li key={label}>
                    <Link href={href} className="text-slate-400 hover:text-white text-sm transition-colors">
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <p className="text-white font-semibold text-sm mb-4">Legal</p>
              <ul className="space-y-2.5">
                {[
                  { label: 'Privacy Policy', href: '/privacy' },
                  { label: 'Terms of Service', href: '/terms' },
                  { label: 'Refund Policy', href: '/refund' },
                  { label: 'Contact', href: '/contact' },
                ].map(({ label, href }) => (
                  <li key={label}>
                    <Link href={href} className="text-slate-400 hover:text-white text-sm transition-colors">
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </footer>

    </div>
  )
}
