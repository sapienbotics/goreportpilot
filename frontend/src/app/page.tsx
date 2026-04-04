// Landing page — full conversion-focused marketing page
// Server Component — interactive subsections use client components from /components/landing/

import Link from 'next/link'
import {
  Clock,
  DollarSign,
  AlertTriangle,
  Brain,
  FileText,
  BadgeDollarSign,
  Zap,
  Palette,
  Calendar,
  ArrowRight,
} from 'lucide-react'
import { Logo } from '@/components/ui/Logo'
import MobileNav from '@/components/landing/mobile-nav'
import PricingToggle from '@/components/landing/pricing-toggle'
import FaqAccordion from '@/components/landing/faq-accordion'

export default function LandingPage() {
  return (
    <>
      {/* Smooth scroll */}
      <style>{`html { scroll-behavior: smooth; }`}</style>

      {/* ─── NAVIGATION ─── */}
      <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-slate-100">
        <div className="mx-auto max-w-7xl px-6 h-16 flex items-center justify-between">
          <Logo size="md" />

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm text-slate-600 hover:text-slate-900 transition-colors">
              Features
            </a>
            <a href="#pricing" className="text-sm text-slate-600 hover:text-slate-900 transition-colors">
              Pricing
            </a>
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

          {/* Mobile hamburger */}
          <MobileNav />
        </div>
      </nav>

      <main>
        {/* ─── HERO ─── */}
        <section className="py-20 md:py-28 bg-white overflow-hidden">
          <div className="mx-auto max-w-7xl px-6">
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              {/* Copy */}
              <div>
                <h1
                  className="text-4xl md:text-5xl font-bold text-slate-900 leading-tight"
                  style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
                >
                  AI Writes Your Client Reports.{' '}
                  <span className="text-indigo-700">You Review and Send.</span>
                </h1>
                <p className="mt-6 text-lg text-slate-500 leading-relaxed">
                  Stop spending 3 hours per client on manual reporting. ReportPilot pulls data from
                  Google Analytics &amp; Meta Ads, writes narrative insights with AI, and exports
                  branded PowerPoint &amp; PDF reports — in 5 minutes.
                </p>
                <div className="mt-8 flex flex-wrap gap-3">
                  <Link
                    href="/signup"
                    className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-6 py-3 text-base font-semibold text-white hover:bg-indigo-800 transition-colors shadow-sm"
                  >
                    Start Free Trial <ArrowRight className="h-4 w-4" />
                  </Link>
                  <a
                    href="#how-it-works"
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-6 py-3 text-base font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    See How It Works
                  </a>
                </div>
                <p className="mt-5 text-sm text-slate-400">
                  Join 100+ agencies automating their client reports
                </p>
              </div>

              {/* Hero visual — CSS-only report mockup */}
              <div className="relative lg:pl-4">
                <div className="rounded-2xl border border-slate-200 bg-white shadow-2xl overflow-hidden">
                  {/* Report header bar */}
                  <div className="bg-indigo-700 px-6 py-4 flex items-center justify-between">
                    <div>
                      <p className="text-indigo-200 text-xs font-medium uppercase tracking-widest">
                        Monthly Report
                      </p>
                      <p className="text-white font-semibold text-sm mt-0.5">
                        Acme Corporation — March 2026
                      </p>
                    </div>
                    <span className="rounded-md bg-white/20 px-2.5 py-1 text-white text-xs font-semibold">
                      GoReportPilot
                    </span>
                  </div>

                  <div className="p-5">
                    {/* KPI cards */}
                    <div className="grid grid-cols-3 gap-3 mb-4">
                      {[
                        { label: 'Sessions', value: '24,891', change: '+18%', positive: true },
                        { label: 'Ad Spend', value: '$3,240', change: '−6%', positive: false },
                        { label: 'Conversions', value: '312', change: '+31%', positive: true },
                      ].map((kpi) => (
                        <div key={kpi.label} className="rounded-lg bg-slate-50 p-3">
                          <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wide">
                            {kpi.label}
                          </p>
                          <p className="text-base font-bold text-slate-900 mt-0.5">{kpi.value}</p>
                          <p
                            className={`text-[11px] font-semibold mt-0.5 ${
                              kpi.positive ? 'text-emerald-600' : 'text-rose-500'
                            }`}
                          >
                            {kpi.change} vs last mo
                          </p>
                        </div>
                      ))}
                    </div>

                    {/* Mini bar chart */}
                    <div className="rounded-lg border border-slate-100 bg-slate-50/50 p-3 mb-4">
                      <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wide mb-2">
                        Sessions Over Time
                      </p>
                      <div className="flex items-end gap-1 h-14">
                        {[38, 50, 42, 58, 48, 65, 60, 75, 68, 82, 74, 90].map((h, i) => (
                          <div
                            key={i}
                            className="flex-1 rounded-sm bg-indigo-300"
                            style={{ height: `${h}%` }}
                          />
                        ))}
                      </div>
                      <div className="flex justify-between mt-1.5">
                        <span className="text-[9px] text-slate-300">Mar 1</span>
                        <span className="text-[9px] text-slate-300">Mar 31</span>
                      </div>
                    </div>

                    {/* AI narrative block */}
                    <div className="rounded-lg border-l-4 border-indigo-500 bg-indigo-50 p-3">
                      <div className="flex items-center gap-1.5 mb-1.5">
                        <div className="flex h-4 w-4 items-center justify-center rounded-full bg-indigo-600">
                          <span className="text-[8px] font-bold text-white">AI</span>
                        </div>
                        <p className="text-[10px] font-bold text-indigo-700 uppercase tracking-widest">
                          AI Insights
                        </p>
                      </div>
                      <p className="text-[11px] leading-relaxed text-slate-700">
                        March was a strong month. Organic traffic grew 18% driven by the new blog
                        content strategy, while paid spend was optimised down 6% without sacrificing
                        conversions — which hit a record 312, up 31% month-over-month.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Background decorations */}
                <div className="absolute -z-10 -top-10 -right-10 h-72 w-72 rounded-full bg-indigo-50 blur-3xl opacity-70" />
                <div className="absolute -z-10 -bottom-6 -left-6 h-40 w-40 rounded-full bg-emerald-50 blur-2xl opacity-60" />
              </div>
            </div>
          </div>
        </section>

        {/* ─── PROBLEM ─── */}
        <section id="problem" className="py-20 bg-slate-50">
          <div className="mx-auto max-w-7xl px-6">
            <div className="text-center mb-12">
              <h2
                className="text-3xl md:text-4xl font-bold text-slate-900"
                style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
              >
                Reporting Shouldn&apos;t Eat Your Weekends
              </h2>
            </div>
            <div className="grid md:grid-cols-3 gap-6">
              {[
                {
                  Icon: Clock,
                  iconColor: 'text-rose-500',
                  iconBg: 'bg-rose-50',
                  title: '2–3 Hours Per Client',
                  text: 'Log into GA4, export data, copy to spreadsheets, build charts, write commentary, triple-check numbers. Every. Single. Month.',
                },
                {
                  Icon: DollarSign,
                  iconColor: 'text-amber-500',
                  iconBg: 'bg-amber-50',
                  title: '$1,500/Month in Lost Time',
                  text: "A freelancer with 10 clients spends 20–30 hours/month just on reporting. That's billable time you're giving away.",
                },
                {
                  Icon: AlertTriangle,
                  iconColor: 'text-orange-500',
                  iconBg: 'bg-orange-50',
                  title: '86% Still Manual',
                  text: "Most agencies haven't automated reporting. The tools that exist cost $179+/month and still don't write the narrative.",
                },
              ].map(({ Icon, iconColor, iconBg, title, text }) => (
                <div
                  key={title}
                  className="rounded-xl bg-white border border-slate-100 p-6 shadow-sm"
                >
                  <div
                    className={`inline-flex h-10 w-10 items-center justify-center rounded-lg ${iconBg} mb-4`}
                  >
                    <Icon className={`h-5 w-5 ${iconColor}`} />
                  </div>
                  <h3
                    className="text-lg font-semibold text-slate-900 mb-2"
                    style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
                  >
                    {title}
                  </h3>
                  <p className="text-sm text-slate-500 leading-relaxed">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ─── HOW IT WORKS ─── */}
        <section id="how-it-works" className="py-20 bg-white">
          <div className="mx-auto max-w-7xl px-6">
            <div className="text-center mb-14">
              <h2
                className="text-3xl md:text-4xl font-bold text-slate-900"
                style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
              >
                From Data to Report in 5 Minutes
              </h2>
            </div>

            <div className="relative grid md:grid-cols-4 gap-8 md:gap-6">
              {/* Connecting line — desktop only */}
              <div className="hidden md:block absolute top-[22px] left-[calc(12.5%+24px)] right-[calc(12.5%+24px)] h-px bg-indigo-100 z-0" />

              {[
                {
                  n: '1',
                  title: 'Connect',
                  text: 'Link your Google Analytics and Meta Ads accounts with one click. OAuth — no passwords shared.',
                },
                {
                  n: '2',
                  title: 'Pull',
                  text: 'ReportPilot automatically fetches performance data for each client. Sessions, spend, clicks, conversions — all of it.',
                },
                {
                  n: '3',
                  title: 'Generate',
                  text: 'AI writes narrative insights explaining trends, wins, and concerns. Not just numbers — actual analysis your clients understand.',
                },
                {
                  n: '4',
                  title: 'Send',
                  text: 'Download as PowerPoint or PDF. Email directly to clients. Schedule for automatic monthly delivery.',
                },
              ].map(({ n, title, text }) => (
                <div key={n} className="relative z-10 flex flex-col items-center text-center">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-indigo-700 text-white font-bold text-base shadow-md mb-4">
                    {n}
                  </div>
                  <h3
                    className="text-base font-semibold text-slate-900 mb-2"
                    style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
                  >
                    {title}
                  </h3>
                  <p className="text-sm text-slate-500 leading-relaxed">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ─── FEATURES ─── */}
        <section id="features" className="py-20 bg-slate-50">
          <div className="mx-auto max-w-7xl px-6">
            <div className="text-center mb-12">
              <h2
                className="text-3xl md:text-4xl font-bold text-slate-900"
                style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
              >
                Everything Agencies Need. Nothing They Don&apos;t.
              </h2>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {[
                {
                  Icon: Brain,
                  title: 'AI Narrative Insights',
                  text: "Not just charts. AI writes paragraphs explaining what happened, why it matters, and what to do next. Contextualized by your client's goals.",
                },
                {
                  Icon: FileText,
                  title: 'PowerPoint & PDF Export',
                  text: 'The format agencies actually present in. No competitor exports to PowerPoint. Download, tweak, present.',
                },
                {
                  Icon: BadgeDollarSign,
                  title: 'Flat Pricing, No Surprises',
                  text: '$39/month for 10 clients. No per-client overages. No hidden fees. Know exactly what you\'ll pay.',
                },
                {
                  Icon: Zap,
                  title: '5-Minute Setup',
                  text: 'Connect accounts via OAuth, AI generates your first report instantly. No templates to configure, no widgets to arrange.',
                },
                {
                  Icon: Palette,
                  title: 'White-Label Branding',
                  text: 'Your logo, your colors, your name. Clients see your agency brand, not ours.',
                },
                {
                  Icon: Calendar,
                  title: 'Scheduled Delivery',
                  text: 'Set it and forget it. Reports auto-generate and email to clients weekly or monthly.',
                },
              ].map(({ Icon, title, text }) => (
                <div
                  key={title}
                  className="rounded-xl bg-white border border-slate-100 p-6 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 mb-4">
                    <Icon className="h-5 w-5 text-indigo-600" />
                  </div>
                  <h3
                    className="text-base font-semibold text-slate-900 mb-2"
                    style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
                  >
                    {title}
                  </h3>
                  <p className="text-sm text-slate-500 leading-relaxed">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ─── COMPARISON ─── */}
        <section id="comparison" className="py-20 bg-white">
          <div className="mx-auto max-w-5xl px-6">
            <div className="text-center mb-12">
              <h2
                className="text-3xl md:text-4xl font-bold text-slate-900"
                style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
              >
                How GoReportPilot Compares
              </h2>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-100 shadow-sm">
              <table className="w-full min-w-[560px] text-sm">
                <thead>
                  <tr className="border-b border-slate-100">
                    <th className="text-left py-4 px-6 text-slate-400 font-medium text-xs uppercase tracking-wide w-2/5">
                      Feature
                    </th>
                    <th className="text-center py-4 px-4 text-slate-400 font-medium text-xs uppercase tracking-wide">
                      AgencyAnalytics
                    </th>
                    <th className="text-center py-4 px-4 text-slate-400 font-medium text-xs uppercase tracking-wide">
                      DashThis
                    </th>
                    <th className="text-center py-4 px-4 bg-indigo-50 text-indigo-700 font-bold text-xs uppercase tracking-wide">
                      GoReportPilot
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['Price (10 clients)', '$179–239/mo', '$159/mo', '$39/mo ✓'],
                    ['AI Narrative Insights', 'Add-on only', 'Add-on ($19/mo)', 'Included ✓'],
                    ['PowerPoint Export', '✗', '✗', 'Yes ✓'],
                    ['Flat Pricing', 'No (per-client)', 'No (per-dashboard)', 'Yes ✓'],
                    ['White-Label', 'Higher tiers', 'Yes', 'All plans ✓'],
                    ['Setup Time', '30–60 min', '15–30 min', '< 5 min ✓'],
                  ].map(([feature, aa, dt, rp], i) => (
                    <tr
                      key={feature}
                      className={`border-b border-slate-50 last:border-0 ${i % 2 === 0 ? '' : 'bg-slate-50/40'}`}
                    >
                      <td className="py-3.5 px-6 text-slate-700 font-medium text-sm">{feature}</td>
                      <td className="py-3.5 px-4 text-center text-slate-400 text-sm">{aa}</td>
                      <td className="py-3.5 px-4 text-center text-slate-400 text-sm">{dt}</td>
                      <td className="py-3.5 px-4 text-center bg-indigo-50 text-indigo-700 font-semibold text-sm">
                        {rp}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* ─── PRICING ─── */}
        <section id="pricing" className="py-20 bg-slate-50">
          <div className="mx-auto max-w-5xl px-6">
            <div className="text-center">
              <h2
                className="text-3xl md:text-4xl font-bold text-slate-900"
                style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
              >
                Simple, Flat Pricing
              </h2>
              <p className="mt-3 text-slate-500">
                No per-client fees. No surprises. Cancel anytime.
              </p>
            </div>
            <PricingToggle />
          </div>
        </section>

        {/* ─── FAQ ─── */}
        <section id="faq" className="py-20 bg-white">
          <div className="mx-auto max-w-3xl px-6">
            <div className="text-center mb-12">
              <h2
                className="text-3xl md:text-4xl font-bold text-slate-900"
                style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
              >
                Frequently Asked Questions
              </h2>
            </div>
            <FaqAccordion />
          </div>
        </section>

        {/* ─── FINAL CTA ─── */}
        <section className="py-24 bg-indigo-700">
          <div className="mx-auto max-w-3xl px-6 text-center">
            <h2
              className="text-3xl md:text-4xl font-bold text-white"
              style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
            >
              Stop Wasting Time on Reports. Start Winning Clients.
            </h2>
            <p className="mt-4 text-lg text-indigo-200">
              Join agencies who automated their reporting and got their weekends back.
            </p>
            <Link
              href="/signup"
              className="mt-8 inline-flex items-center gap-2 rounded-lg bg-white px-8 py-3.5 text-base font-semibold text-indigo-700 hover:bg-indigo-50 transition-colors shadow-md"
            >
              Start Your Free Trial <ArrowRight className="h-4 w-4" />
            </Link>
            <p className="mt-4 text-sm text-indigo-300">
              14-day free trial. No credit card required.
            </p>
          </div>
        </section>
      </main>

      {/* ─── FOOTER ─── */}
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
                  { label: 'Features', href: '#features' },
                  { label: 'Pricing', href: '#pricing' },
                  { label: 'Integrations', href: '#' },
                  { label: 'Changelog', href: '#' },
                ].map(({ label, href }) => (
                  <li key={label}>
                    <a
                      href={href}
                      className="text-slate-400 text-sm hover:text-white transition-colors"
                    >
                      {label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <p className="text-white font-semibold text-sm mb-4">Company</p>
              <ul className="space-y-2.5">
                {[
                  { label: 'About', href: '#' },
                  { label: 'Blog', href: '#' },
                  { label: 'Contact', href: 'mailto:hello@goreportpilot.com' },
                  { label: 'Privacy Policy', href: '/privacy' },
                  { label: 'Terms of Service', href: '/terms' },
                ].map(({ label, href }) => (
                  <li key={label}>
                    <a
                      href={href}
                      className="text-slate-400 text-sm hover:text-white transition-colors"
                    >
                      {label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </>
  )
}
