// /features — dedicated SEO + nav page listing all shipped features with depth.
// Landing page is the pitch; /features is the proof.
// Server Component — no client-side state needed.

import type { Metadata } from 'next'
import Link from 'next/link'
import {
  ArrowRight,
  // Data Sources
  TrendingUp, Megaphone, Target, Globe2, Upload, Activity,
  // AI Narrative
  Brain, Microscope, SlidersHorizontal, Languages, BookOpen, RefreshCw,
  // Visual Design
  LayoutTemplate, PieChart, Sparkles, Palette,
  Image as ImageIcon,
  // White-Label
  Building2, Users, EyeOff, Settings,
  // Delivery & Collaboration
  FileText, FileDown, Mail, Calendar, Link2, MessageSquare,
  // Account & Billing
  Zap, DollarSign, Percent, CreditCard, ShieldCheck,
} from 'lucide-react'
import { Logo } from '@/components/ui/Logo'
import MobileNav from '@/components/landing/mobile-nav'
import ComparisonTable from '@/components/landing/ComparisonTable'

export const metadata: Metadata = {
  title: 'Features — GoReportPilot',
  description:
    'Multi-paragraph AI narrative, editable PPTX, white-label branding, 13 languages. Connects GA4, Meta Ads, Google Ads, Search Console + CSVs. From $19/mo.',
  alternates: { canonical: 'https://goreportpilot.com/features' },
  openGraph: {
    title: 'Features — GoReportPilot',
    description:
      'Multi-paragraph AI narrative, editable PPTX, white-label branding, 13 languages. Connects GA4, Meta Ads, Google Ads, Search Console + CSVs.',
    url: 'https://goreportpilot.com/features',
    siteName: 'GoReportPilot',
    type: 'website',
  },
}

// ─── Shared feature block component ─────────────────────────────────────────

type IconType = React.ComponentType<{ className?: string }>

function FeatureBlock({
  Icon,
  name,
  description,
}: {
  Icon: IconType
  name: string
  description: string
}) {
  return (
    <div className="rounded-xl bg-white border border-slate-100 p-6 shadow-sm">
      <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 mb-4">
        <Icon className="h-5 w-5 text-indigo-600" />
      </div>
      <h3
        className="text-base font-semibold text-slate-900 mb-2"
        style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
      >
        {name}
      </h3>
      <p className="text-sm text-slate-500 leading-relaxed">{description}</p>
    </div>
  )
}

// ─── Section wrapper ─────────────────────────────────────────────────────────

function Section({
  id,
  bg,
  title,
  intro,
  children,
}: {
  id: string
  bg: 'white' | 'slate'
  title: string
  intro: string
  children: React.ReactNode
}) {
  return (
    <section
      id={id}
      className={`py-20 ${bg === 'white' ? 'bg-white' : 'bg-slate-50'}`}
    >
      <div className="mx-auto max-w-7xl px-6">
        <div className="text-center mb-12">
          <h2
            className="text-3xl md:text-4xl font-bold text-slate-900"
            style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
          >
            {title}
          </h2>
          <p className="mt-3 text-slate-500 max-w-2xl mx-auto">{intro}</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">{children}</div>
      </div>
    </section>
  )
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function FeaturesPage() {
  return (
    <div className="min-h-screen bg-white">

      {/* ─── NAV ─────────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-slate-100">
        <div className="mx-auto max-w-7xl px-6 h-16 flex items-center justify-between">
          <Link href="/">
            <Logo size="md" />
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <Link href="/features" className="text-sm font-semibold text-indigo-700">
              Features
            </Link>
            <Link href="/pricing" className="text-sm text-slate-600 hover:text-slate-900 transition-colors">
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

        {/* ─── HERO ─────────────────────────────────────────────────────── */}
        <section className="py-16 md:py-24 bg-white text-center">
          <div className="mx-auto max-w-3xl px-6">
            <div className="text-xs font-semibold text-indigo-600 uppercase tracking-[0.15em] mb-3">
              All Features
            </div>
            <h1
              className="text-4xl md:text-5xl font-bold text-slate-900 leading-tight"
              style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
            >
              Everything GoReportPilot does
            </h1>
            <p className="mt-5 text-lg text-slate-500 leading-relaxed max-w-xl mx-auto">
              AI-powered client reporting — from data pull to branded PPTX + PDF — in under
              5&nbsp;minutes. Every feature, in detail.
            </p>
            <div className="mt-8">
              <Link
                href="/signup"
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-7 py-3.5 text-base font-semibold text-white hover:bg-indigo-800 transition-colors shadow-md"
              >
                Start 14-day free trial <ArrowRight className="h-4 w-4" />
              </Link>
              <p className="mt-3 text-sm text-slate-400">No credit card required.</p>
            </div>
          </div>
        </section>

        {/* ─── 2.1 DATA SOURCES ─────────────────────────────────────────── */}
        <Section
          id="data-sources"
          bg="slate"
          title="Data Sources"
          intro="Four native OAuth integrations plus a production-grade CSV parser — so every platform your clients run ads or traffic on is covered."
        >
          <FeatureBlock
            Icon={TrendingUp}
            name="Google Analytics 4"
            description="Six-API-call data pull: sessions, users, pageviews, bounce rate, average session duration, conversions, traffic sources, device breakdown, top landing pages, and daily sessions trend. OAuth-secured — no passwords shared. Refreshes automatically for every report."
          />
          <FeatureBlock
            Icon={Megaphone}
            name="Meta Ads"
            description="Connected via Meta Marketing API v21. Pulls spend, impressions, clicks, CTR, CPC, ROAS, conversions, cost-per-conversion, age/gender breakdown, and campaign-level performance for the top 5 campaigns. Long-lived token management handles the 60-day expiry automatically."
          />
          <FeatureBlock
            Icon={Target}
            name="Google Ads"
            description="Full Google Ads OAuth with MCC (manager account) support — connect once and access all child accounts. Pulls campaign spend, impressions, clicks, conversions, and cost-per-conversion. Works for both direct advertiser accounts and agencies managing multiple clients under a single MCC."
          />
          <FeatureBlock
            Icon={Globe2}
            name="Google Search Console"
            description="OAuth-connected to the Search Console API. Pulls organic clicks, impressions, CTR, and average position. Top queries and landing pages included so the SEO narrative has real named data to reference — not just aggregate numbers."
          />
          <FeatureBlock
            Icon={Upload}
            name="CSV Upload (Any Data Source)"
            description="Production-grade parser handles LinkedIn Ads, TikTok Ads, Shopify, HubSpot, and any platform that exports CSVs. Auto-detects delimiter, encoding, and column layout. Applies 35-brand capitalization rules (so 'facebook' becomes 'Facebook'), K/M/B suffix formatting, and five built-in column templates for common export formats."
          />
          <FeatureBlock
            Icon={Activity}
            name="Connection Health Monitor"
            description="GoReportPilot probes every OAuth connection before report generation runs. Expired tokens, revoked permissions, and broken integrations surface immediately — not after a client asks why their report has no data. The integration hub shows connection status with timestamps so you can fix issues proactively."
          />
        </Section>

        {/* ─── 2.2 AI NARRATIVE ─────────────────────────────────────────── */}
        <Section
          id="ai-narrative"
          bg="white"
          title="AI Narrative"
          intro="GPT-4.1 writes the analysis. Not templates, not one-liners — multi-paragraph commentary that reads like a senior analyst wrote it for each specific client."
        >
          <FeatureBlock
            Icon={Brain}
            name="Multi-Paragraph Commentary"
            description="Six narrative sections per report: Executive Summary, Google Analytics, Meta Ads, Google Ads, Search Console, and Next Steps. Each section is 2–4 paragraphs. The AI references actual numbers, period-over-period changes, and named campaigns — not generic observations."
          />
          <FeatureBlock
            Icon={Microscope}
            name="Diagnostic Narrative with Top Movers"
            description="Before generating narrative, GoReportPilot computes the top metric movers — which campaigns drove spend changes, which landing pages drove traffic swings, which channels shifted. The AI cites these named entities as causal drivers instead of writing vague phrases like 'performance improved due to multiple factors.'"
          />
          <FeatureBlock
            Icon={SlidersHorizontal}
            name="4 Writing Tones"
            description="Professional (clear and measured), Conversational (warm, plain-English), Executive (dense, bullet-friendly, boardroom-ready), and Data-Heavy (every number cited, analyst-style). Select per client so the report voice matches the relationship. Pro and Agency plans unlock all four tones; Starter uses Professional."
          />
          <FeatureBlock
            Icon={Languages}
            name="13 Languages"
            description="AI writes narrative natively in English, Spanish, French, German, Portuguese, Italian, Dutch, Hindi, Japanese, Korean, Chinese Simplified, Arabic, and Turkish. Not machine-translated English — the model generates directly in the target language. Slide titles, KPI labels, chart axis labels, and footer text also adapt to the selected language. Available on all plans."
          />
          <FeatureBlock
            Icon={BookOpen}
            name="Per-Client Business Context"
            description="Each client has a business context field: their goals, KPIs they care about, seasonal patterns, key channels, and anything else that shapes how results should be read. The AI reads this context before writing every narrative — so the report for a seasonal e-commerce brand reads differently from the report for a SaaS lead-gen campaign."
          />
          <FeatureBlock
            Icon={RefreshCw}
            name="Per-Section Regenerate"
            description="Every narrative section has a Regenerate button. Didn't like the Executive Summary? Click regenerate — only that section is rewritten, everything else stays. Combine this with inline editing (click any paragraph to edit) to tune the report without starting over."
          />
        </Section>

        {/* ─── 2.3 VISUAL DESIGN ────────────────────────────────────────── */}
        <Section
          id="visual-design"
          bg="slate"
          title="Visual Design"
          intro="Six professionally designed PPTX templates, 19 chart types, and AI-written chart titles — all generated in seconds, ready to present."
        >
          <FeatureBlock
            Icon={LayoutTemplate}
            name="6 PPTX Templates"
            description="Modern Clean (light, minimal, high whitespace), Dark Executive (dark indigo background, gold accents), Colorful Agency (vibrant multi-color, bold typography), Bold Geometric (strong shapes, high contrast), Minimal Elegant (thin lines, muted palette, editorial feel), and Gradient Modern (smooth gradient backgrounds, contemporary). All 6 available on Pro, Agency, and trial. Starter gets Modern Clean."
          />
          <FeatureBlock
            Icon={PieChart}
            name="19 Chart Types"
            description="Sessions trend (line), traffic sources (horizontal bar), device breakdown (donut), top landing pages (bar), daily spend vs. conversions (dual-axis bar), campaign performance (grouped bar), age/gender audience (grouped bar), Search Console impressions/CTR (dual-axis), keyword performance (table), and more. Each chart renders at 300 DPI, embeds cleanly in PPTX, and converts losslessly to PDF."
          />
          <FeatureBlock
            Icon={Sparkles}
            name="AI-Titled Charts"
            description="Chart titles aren't generic labels. The AI generates a one-line active-voice takeaway per chart — 'Sessions grew 23% as organic search recovered' instead of 'Sessions over time.' The title comes from the same GPT-4.1 call as the narrative, so it references the same period and numbers. Chart insights are ≤15 words and always present tense."
          />
          <FeatureBlock
            Icon={TrendingUp}
            name="Sparklines on KPI Cards"
            description="Every KPI card on the report cover shows a mini sparkline — a small trend line for the metric over the report period. Sessions up overall but dipped mid-month? The sparkline shows it without adding another slide. Rendered at 300 DPI with transparent background so they layer cleanly on any template."
          />
          <FeatureBlock
            Icon={Palette}
            name="Color-Blind-Safe Palette"
            description="All chart color sequences follow the Okabe-Ito palette — designed specifically for viewers with deuteranopia (green-blind) and protanopia (red-blind), which affect roughly 8% of men. When you override with a custom brand color, the remaining sequence still shifts to maintain safe contrast ratios. Your reports are readable by every client."
          />
          <FeatureBlock
            Icon={ImageIcon}
            name="Custom Cover Page per Client"
            description="Each client can have a unique cover slide: custom headline, subtitle, hero image or background, and brand color. Edit in a live preview editor — what you see is what renders in the final PPTX. Cover customization is per-client, not per-template, so you can run the same template with different covers across clients. Available on Pro and Agency."
          />
        </Section>

        {/* ─── 2.4 WHITE-LABEL & BRANDING ──────────────────────────────── */}
        <Section
          id="white-label"
          bg="white"
          title="White-Label &amp; Branding"
          intro="Your clients see your brand, not ours. Every visual element of the report is configurable to your agency's identity."
        >
          <FeatureBlock
            Icon={Building2}
            name="Agency Logo & Brand Color"
            description="Upload your agency logo and set your primary brand color in Settings. Both carry through to every report for every client — cover slide, footer, chart accents. The logo placement adapts to its aspect ratio (square badge vs wide wordmark) so it always fits cleanly without overflow. Available on Pro and Agency."
          />
          <FeatureBlock
            Icon={Users}
            name="Client Logo per Client"
            description="Each client can have their own logo uploaded to their profile. The client logo appears on the report cover and is sized proportionally alongside your agency logo. Supports PNG, JPEG, and SVG. Clients receive a report that looks purpose-built for them, not a generic template. Available on Pro and Agency."
          />
          <FeatureBlock
            Icon={EyeOff}
            name="Remove GoReportPilot Branding"
            description="On Starter, a small 'Powered by GoReportPilot' badge appears on reports — your clients know you use the tool. On Pro and Agency, that badge is removed entirely: no GoReportPilot mention anywhere in the PPTX or PDF. Your agency is the only brand visible."
          />
          <FeatureBlock
            Icon={Settings}
            name="Per-Client Configuration"
            description="Branding settings are configured globally (your agency logo, color, footer) and then overridden per client (their logo, custom cover, language, AI tone). Every client's report feels made for them specifically. Change your agency brand color once — all future reports for all clients update automatically."
          />
        </Section>

        {/* ─── 2.5 DELIVERY & COLLABORATION ────────────────────────────── */}
        <Section
          id="delivery"
          bg="slate"
          title="Delivery &amp; Collaboration"
          intro="Reports leave GoReportPilot as editable PowerPoints, print-ready PDFs, and shareable links — with client comments looping you back in."
        >
          <FeatureBlock
            Icon={FileText}
            name="PPTX Export (Editable)"
            description="Every PPTX downloads as a fully editable PowerPoint file — not a locked presentation or image-embedded deck. Your clients can open it in PowerPoint, Google Slides, or Keynote and edit any text, chart, or layout. This is a hard differentiator: AgencyAnalytics and Whatagraph deliver PDF-only. Available on Pro and Agency."
          />
          <FeatureBlock
            Icon={FileDown}
            name="PDF Export (All Tiers)"
            description="PDF generation uses LibreOffice headless — the same engine that produces pixel-perfect PDFs from PPTX. This means full Unicode support: Hindi, Arabic, Japanese, Korean, and Chinese Simplified render correctly in PDFs, not as tofu boxes. A ReportLab fallback handles Latin-script languages if LibreOffice is unavailable. Available on all plans including Starter."
          />
          <FeatureBlock
            Icon={Mail}
            name="Email Delivery"
            description="Send the finished report directly to your client from GoReportPilot. Choose PDF, PPTX, or both as attachments. The email comes from reports@goreportpilot.com with your agency name in the display — or configure your own branding in Settings. DKIM-authenticated via Resend so it lands in the inbox, not spam. Available on all plans."
          />
          <FeatureBlock
            Icon={Calendar}
            name="Scheduled Reports"
            description="Set weekly, biweekly, or monthly schedules per client. GoReportPilot auto-generates the report, writes the AI narrative, and emails it to the client on the configured cadence — all without you logging in. Schedules are timezone-aware: a Monday 9 AM delivery lands at 9 AM in the client's timezone, not yours. Available on Pro and Agency."
          />
          <FeatureBlock
            Icon={Link2}
            name="Shareable Report Links"
            description="Generate a public link for any report. Optional: add a password and an expiry date. The link renders a read-only web view of the full report — no PPTX required, no GoReportPilot account needed. View counts are tracked so you can see when the client opened the link and how many times."
          />
          <FeatureBlock
            Icon={MessageSquare}
            name="Client Comments on Shared Reports"
            description="Clients can leave comments directly on shared report links — no login required. You see real-time unread-comment badges across the dashboard and on the report list. Reply and resolve comments without leaving GoReportPilot. Reports become a conversation thread, not a one-way deliverable. Available on all plans."
          />
        </Section>

        {/* ─── 2.6 ACCOUNT & BILLING ────────────────────────────────────── */}
        <Section
          id="billing"
          bg="white"
          title="Account &amp; Billing"
          intro="Flat pricing, dual currency, no hidden fees. Start free, pay only when you're ready."
        >
          <FeatureBlock
            Icon={Zap}
            name="14-Day Free Trial"
            description="Every new account gets 14 days of Pro-tier access — PPTX export, all 6 visual templates, all 4 AI tones, white-label branding, and scheduled reports. Generate up to 5 reports and manage up to 10 clients during the trial. No credit card required to start. Account moves to read-only (not deleted) at the end of the trial."
          />
          <FeatureBlock
            Icon={DollarSign}
            name="Dual Currency — INR & USD"
            description="GoReportPilot detects your timezone at first visit: visitors in IST are shown Indian Rupee pricing (₹999/₹1,999/₹3,499 per month), everyone else sees USD ($19/$39/$69). Both currencies use Razorpay, which accepts international cards. The pricing page toggle lets you switch currencies manually."
          />
          <FeatureBlock
            Icon={Percent}
            name="Annual Billing — Save 20%"
            description="Switch to annual billing on any plan to save 20% vs monthly. Billed as a single annual charge. The pricing toggle on the landing page and /pricing page shows both cycles side-by-side. Annual plans can be switched back to monthly at renewal — no penalty."
          />
          <FeatureBlock
            Icon={CreditCard}
            name="Razorpay Payments"
            description="All billing runs through Razorpay — one of India's largest payment processors, with international card support. Accepts Visa, Mastercard, American Express, UPI, and net banking. Payments are PCI-DSS compliant. GoReportPilot never stores card details — Razorpay handles the vault."
          />
          <FeatureBlock
            Icon={ShieldCheck}
            name="Cancel Anytime, Keep Your Data"
            description="No contracts, no cancellation fees. Cancel from the Billing page — your subscription ends at the close of the current billing cycle. Reports, client data, connections, and schedules are preserved for 30 days post-cancellation so you can export and move on without friction."
          />
        </Section>

        {/* ─── COMPARISON BAND ──────────────────────────────────────────── */}
        <section id="comparison" className="py-20 bg-slate-50">
          <div className="mx-auto max-w-5xl px-6">
            <div className="text-center mb-12">
              <h2
                className="text-3xl md:text-4xl font-bold text-slate-900"
                style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
              >
                How GoReportPilot Compares
              </h2>
              <p className="mt-3 text-slate-500">
                Editable PPTX, flat pricing, and sub-5-minute setup are hard differentiators — not
                marketing claims.
              </p>
            </div>
            <ComparisonTable />
          </div>
        </section>

        {/* ─── FINAL CTA ────────────────────────────────────────────────── */}
        <section className="py-24 bg-indigo-700">
          <div className="mx-auto max-w-3xl px-6 text-center">
            <h2
              className="text-3xl md:text-4xl font-bold text-white"
              style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
            >
              Start free for 14 days.
            </h2>
            <p className="mt-4 text-lg text-indigo-200">
              Pro-tier features. No credit card. First report in 5 minutes.
            </p>
            <Link
              href="/signup"
              className="mt-8 inline-flex items-center gap-2 rounded-lg bg-white px-8 py-3.5 text-base font-semibold text-indigo-700 hover:bg-indigo-50 transition-colors shadow-md"
            >
              Start Your Free Trial <ArrowRight className="h-4 w-4" />
            </Link>
            <p className="mt-4 text-sm text-indigo-300">
              5 reports · 10 clients · 6 templates · No auto-charge
            </p>
          </div>
        </section>

      </main>

      {/* ─── FOOTER ───────────────────────────────────────────────────── */}
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
                  { label: 'Features', href: '/features' },
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
