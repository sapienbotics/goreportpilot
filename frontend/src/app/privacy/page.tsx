// Privacy Policy — public page (no auth required)
// Required for Google API Services and Meta Platform OAuth verification

import Link from 'next/link'
import type { Metadata } from 'next'
import { Logo } from '@/components/ui/Logo'

export const metadata: Metadata = {
  title: 'Privacy Policy — GoReportPilot',
  description: 'How GoReportPilot collects, uses, and protects your data.',
}

const LAST_UPDATED = 'March 23, 2026'

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="border-b border-slate-100 bg-white/95 backdrop-blur-sm sticky top-0 z-50">
        <div className="mx-auto max-w-5xl px-6 h-16 flex items-center justify-between">
          <Link href="/">
            <Logo size="sm" />
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <Link href="/terms" className="text-slate-600 hover:text-slate-900">Terms</Link>
            <Link href="/login" className="text-slate-600 hover:text-slate-900">Sign In</Link>
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="mx-auto max-w-3xl px-6 py-14">
        <h1 className="text-3xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}>
          Privacy Policy
        </h1>
        <p className="text-sm text-slate-400 mb-10">Last updated: {LAST_UPDATED}</p>

        <div className="prose prose-slate max-w-none space-y-10 text-slate-700 leading-relaxed">

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">1. Who We Are</h2>
            <p>
              ReportPilot is operated by <strong>SapienBotics</strong>, a sole proprietorship registered in
              New Delhi, India (GSTIN: 09CYVPS3328G1ZQ). We build AI-powered reporting tools for digital
              marketing agencies and freelancers.
            </p>
            <p className="mt-2">
              Contact: <a href="mailto:support@goreportpilot.com" className="text-indigo-600 hover:underline">support@goreportpilot.com</a>
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">2. What Data We Collect</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>
                <strong>Account information:</strong> Your email address and name when you sign up.
              </li>
              <li>
                <strong>Google Analytics data</strong> (when you connect a GA4 property): sessions, users,
                pageviews, traffic sources, and conversion events — read-only. We never write to your
                Analytics account.
              </li>
              <li>
                <strong>Meta Ads data</strong> (when you connect an ad account): ad spend, impressions, clicks,
                and conversions — read-only. We never modify or publish ads on your behalf.
              </li>
              <li>
                <strong>Client information:</strong> Names, website URLs, contact emails, and goals you enter
                for your clients.
              </li>
              <li>
                <strong>Usage data:</strong> Pages visited, features used, error logs — for product improvement only.
              </li>
              <li>
                <strong>Payment information:</strong> Processed exclusively by Razorpay. We do not store card numbers or banking details.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">3. How We Use Your Data</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Generate performance reports for your clients.</li>
              <li>Produce AI-written narrative insights using the data you have connected.</li>
              <li>Display metrics and dashboards within your ReportPilot account.</li>
              <li>Send reports to client email addresses you specify.</li>
              <li>Process subscription payments and send billing communications.</li>
              <li>Provide customer support when you contact us.</li>
            </ul>
            <p className="mt-3">
              We do <strong>not</strong> use your data for advertising, profiling, or any purpose beyond providing
              the ReportPilot service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">4. How We Store and Protect Your Data</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>
                All data is stored in <strong>Supabase PostgreSQL</strong> databases, hosted on AWS infrastructure
                with encryption at rest and in transit (TLS 1.2+).
              </li>
              <li>
                OAuth access tokens (Google, Meta) are encrypted with <strong>AES-256-GCM</strong> at the
                application layer before being stored. Even if the database were compromised, tokens would
                be unreadable without the encryption key.
              </li>
              <li>
                Row-Level Security (RLS) policies enforce that each user can only access their own data.
              </li>
              <li>
                Encryption keys are stored as server environment variables — never in the database.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">5. Third-Party Services</h2>
            <p>We use the following third-party services to operate ReportPilot:</p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li>
                <strong>Supabase</strong> — Database, authentication, and file storage.
                (<a href="https://supabase.com/privacy" className="text-indigo-600 hover:underline" target="_blank" rel="noopener noreferrer">Privacy Policy</a>)
              </li>
              <li>
                <strong>OpenAI</strong> — AI narrative generation. Analytics data is sent to OpenAI&apos;s API
                to generate text summaries. OpenAI does not store or train on this data under the API terms.
                (<a href="https://openai.com/policies/privacy-policy" className="text-indigo-600 hover:underline" target="_blank" rel="noopener noreferrer">Privacy Policy</a>)
              </li>
              <li>
                <strong>Razorpay</strong> — Payment processing for subscriptions. We do not see or store your
                payment card details.
                (<a href="https://razorpay.com/privacy/" className="text-indigo-600 hover:underline" target="_blank" rel="noopener noreferrer">Privacy Policy</a>)
              </li>
              <li>
                <strong>Resend</strong> — Transactional email delivery (report delivery, billing receipts).
                (<a href="https://resend.com/privacy" className="text-indigo-600 hover:underline" target="_blank" rel="noopener noreferrer">Privacy Policy</a>)
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">6. Google API Services</h2>
            <p>
              ReportPilot&apos;s use and transfer of information received from Google APIs adheres to the{' '}
              <a
                href="https://developers.google.com/terms/api-services-user-data-policy"
                className="text-indigo-600 hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                Google API Services User Data Policy
              </a>
              , including the Limited Use requirements.
            </p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li>We request only the <code className="bg-slate-100 px-1 rounded">analytics.readonly</code> scope.</li>
              <li>Google Analytics data is used solely to generate performance reports for your clients.</li>
              <li>We do not share Google user data with third parties except as necessary to provide the service.</li>
              <li>We do not use Google user data for advertising or to train AI/ML models.</li>
              <li>Humans at SapienBotics do not read your Google Analytics data except to provide technical support at your request.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">7. Meta Platform Terms</h2>
            <p>
              Our use of Meta&apos;s APIs complies with the{' '}
              <a
                href="https://developers.facebook.com/terms/"
                className="text-indigo-600 hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                Meta Platform Terms
              </a>
              .
            </p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li>We request only the <code className="bg-slate-100 px-1 rounded">ads_read</code> permission.</li>
              <li>Meta Ads data is used solely to generate advertising performance reports.</li>
              <li>We do not share Meta ad account data with third parties beyond what is necessary to provide the service.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">8. Data Retention</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Your data is kept while your account is active.</li>
              <li>
                On account deletion, all data — including OAuth tokens, client records, and generated reports
                — is permanently deleted within <strong>30 days</strong>.
              </li>
              <li>
                You may export your data at any time from the Settings page before deletion.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">9. Your Rights</h2>
            <p>You have the right to:</p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li><strong>Access</strong> your data — visible in your dashboard at all times.</li>
              <li><strong>Export</strong> your data — from Settings → Danger Zone.</li>
              <li><strong>Delete</strong> your account and all associated data — from Settings → Danger Zone.</li>
              <li><strong>Disconnect</strong> integrations — revoke access from Settings → Integrations at any time.</li>
            </ul>
            <p className="mt-3">
              For any data requests, email us at{' '}
              <a href="mailto:support@goreportpilot.com" className="text-indigo-600 hover:underline">support@goreportpilot.com</a>.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">10. Cookies</h2>
            <p>
              ReportPilot uses <strong>session cookies only</strong> — specifically the Supabase authentication
              JWT stored as an <code className="bg-slate-100 px-1 rounded">httpOnly</code> cookie. We do not use
              tracking cookies, advertising cookies, or third-party analytics on the application.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">11. Changes to This Policy</h2>
            <p>
              We may update this Privacy Policy from time to time. We will notify you by email at least 30 days
              before material changes take effect. Continued use of the service after that date constitutes
              acceptance of the updated policy.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">12. Contact</h2>
            <address className="not-italic">
              <strong>SapienBotics</strong><br />
              New Delhi, India<br />
              GSTIN: 09CYVPS3328G1ZQ<br />
              Email: <a href="mailto:support@goreportpilot.com" className="text-indigo-600 hover:underline">support@goreportpilot.com</a>
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
            <Link href="/refund" className="hover:text-slate-600">Refund</Link>
            <Link href="/contact" className="hover:text-slate-600">Contact</Link>
            <Link href="/" className="hover:text-slate-600">Home</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
