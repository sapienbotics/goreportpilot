// Terms of Service — public page (no auth required)

import Link from 'next/link'
import type { Metadata } from 'next'
import { Logo } from '@/components/ui/Logo'

export const metadata: Metadata = {
  title: 'Terms of Service — GoReportPilot',
  description: 'Terms and conditions for using the GoReportPilot service.',
}

const LAST_UPDATED = 'March 23, 2026'

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="border-b border-slate-100 bg-white/95 backdrop-blur-sm sticky top-0 z-50">
        <div className="mx-auto max-w-5xl px-6 h-16 flex items-center justify-between">
          <Link href="/">
            <Logo size="sm" />
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <Link href="/privacy" className="text-slate-600 hover:text-slate-900">Privacy</Link>
            <Link href="/login" className="text-slate-600 hover:text-slate-900">Sign In</Link>
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="mx-auto max-w-3xl px-6 py-14">
        <h1 className="text-3xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>
          Terms of Service
        </h1>
        <p className="text-sm text-slate-400 mb-10">Last updated: {LAST_UPDATED}</p>

        <div className="space-y-10 text-slate-700 leading-relaxed">

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">1. Service Description</h2>
            <p>
              ReportPilot is a software-as-a-service (SaaS) platform that enables digital marketing agencies
              and freelancers to generate AI-powered client performance reports. The service connects to
              third-party platforms (Google Analytics, Meta Ads) via OAuth, pulls data, generates narrative
              insights using AI, and exports branded reports as PowerPoint and PDF files.
            </p>
            <p className="mt-2">
              ReportPilot is operated by <strong>SapienBotics</strong>, a sole proprietorship registered in
              New Delhi, India.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">2. Account Terms</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>You must be at least 18 years old and have legal capacity to enter into this agreement.</li>
              <li>You must provide accurate, complete, and current information when creating your account.</li>
              <li>You are responsible for maintaining the security of your account password.</li>
              <li>You are responsible for all activity that occurs under your account.</li>
              <li>You must notify us immediately at <a href="mailto:support@reportpilot.co" className="text-indigo-600 hover:underline">support@reportpilot.co</a> if you suspect unauthorized access.</li>
              <li>One account per person or business entity. You may not share accounts.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">3. Subscription & Billing</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>
                <strong>Free Trial:</strong> All new accounts receive a 14-day free trial with full Pro-tier
                features. No credit card is required to start a trial.
              </li>
              <li>
                <strong>Plans:</strong> After the trial, you may subscribe to Starter (₹1,599/mo), Pro
                (₹3,299/mo), or Agency (₹5,799/mo) plans. Annual billing is available at a discount.
              </li>
              <li>
                <strong>Billing:</strong> Subscriptions are billed in advance via Razorpay. By subscribing, you
                authorize Razorpay to charge your payment method on a recurring basis.
              </li>
              <li>
                <strong>Cancellation:</strong> You may cancel your subscription at any time from the Billing
                page. Your access continues until the end of the current billing period. We do not provide
                refunds for partial periods.
              </li>
              <li>
                <strong>Plan changes:</strong> Upgrades take effect immediately. Downgrades take effect at the
                next billing cycle.
              </li>
              <li>
                <strong>Failed payments:</strong> If a payment fails, we will retry automatically. After 3
                failed attempts, your account will be downgraded to a restricted state until payment is resolved.
              </li>
              <li>
                <strong>Taxes:</strong> Prices listed are exclusive of applicable taxes (GST, etc.). Tax will be
                added at checkout where required by law.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">4. Acceptable Use</h2>
            <p>You agree not to:</p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li>Use the service for any illegal purpose or in violation of any applicable laws.</li>
              <li>Attempt to access another user&apos;s account, data, or connections.</li>
              <li>
                Abuse third-party API rate limits by making excessive automated requests through ReportPilot.
              </li>
              <li>Reverse-engineer, decompile, or attempt to extract the source code of the service.</li>
              <li>Resell or sublicense access to the service without our written consent.</li>
              <li>Use the service to generate reports containing false or misleading data.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">5. Data Ownership</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>
                <strong>Your data:</strong> You retain full ownership of all data you bring into ReportPilot —
                your client information, connected account data, and generated reports.
              </li>
              <li>
                <strong>License to us:</strong> By using the service, you grant SapienBotics a limited,
                non-exclusive license to process your data solely for the purpose of providing the service to you.
                We do not claim ownership of your reports or client data.
              </li>
              <li>
                <strong>Report content:</strong> Reports generated by ReportPilot belong to you. You may share,
                edit, and distribute them as you see fit.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">6. Third-Party Integrations</h2>
            <p>
              ReportPilot connects to Google Analytics and Meta Ads via OAuth. By connecting these integrations,
              you authorize ReportPilot to read data from those platforms on your behalf.
            </p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li>
                We are not responsible for changes to third-party APIs, service outages at Google or Meta, or
                discrepancies between data shown in ReportPilot and data shown directly in those platforms.
              </li>
              <li>
                Your use of connected platforms remains subject to their own terms of service and privacy policies.
              </li>
              <li>
                You may revoke any integration at any time from the Integrations page in your dashboard.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">7. Limitation of Liability</h2>
            <p>
              The service is provided <strong>&quot;as is&quot;</strong> without warranties of any kind, express or
              implied.
            </p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li>
                ReportPilot reports are generated from data provided by third-party APIs. Minor discrepancies
                between our reports and native platform dashboards are normal due to attribution windows,
                time-zone differences, and API sampling. We are not liable for business decisions made based
                on report data.
              </li>
              <li>
                To the maximum extent permitted by law, SapienBotics shall not be liable for any indirect,
                incidental, special, consequential, or punitive damages, or any loss of profits or revenues.
              </li>
              <li>
                Our total liability to you for any claim shall not exceed the amount you paid us in the three
                months preceding the claim.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">8. Termination</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>
                <strong>By you:</strong> You may cancel your subscription and delete your account at any time
                from the Settings page.
              </li>
              <li>
                <strong>By us:</strong> We may suspend or terminate accounts that violate these terms, with
                immediate effect for serious violations, or with 30 days&apos; notice otherwise.
              </li>
              <li>
                <strong>After termination:</strong> Your data will be retained for 30 days to allow recovery,
                then permanently deleted.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">9. Changes to These Terms</h2>
            <p>
              We may update these Terms of Service from time to time. We will notify you by email at least
              30 days before material changes take effect. Continued use of the service after the effective
              date constitutes acceptance of the revised terms.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">10. Governing Law</h2>
            <p>
              These terms are governed by and construed in accordance with the laws of India. Any disputes
              shall be subject to the exclusive jurisdiction of the courts in New Delhi, India.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">11. Contact</h2>
            <address className="not-italic">
              <strong>SapienBotics</strong><br />
              New Delhi, India<br />
              GSTIN: 09CYVPS3328G1ZQ<br />
              Email: <a href="mailto:support@reportpilot.co" className="text-indigo-600 hover:underline">support@reportpilot.co</a>
            </address>
          </section>

        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-100 py-8 mt-10">
        <div className="mx-auto max-w-5xl px-6 flex flex-wrap items-center justify-between gap-4 text-sm text-slate-400">
          <span>© {new Date().getFullYear()} SapienBotics. All rights reserved.</span>
          <div className="flex gap-6">
            <Link href="/privacy" className="hover:text-slate-600">Privacy</Link>
            <Link href="/terms" className="hover:text-slate-600">Terms</Link>
            <Link href="/" className="hover:text-slate-600">Home</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
