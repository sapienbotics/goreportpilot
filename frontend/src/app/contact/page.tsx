import Link from 'next/link'
import { Mail, MapPin, CreditCard, Bug } from 'lucide-react'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Contact Us — GoReportPilot',
  description: 'Get in touch with the GoReportPilot support team. We\'re here to help with billing, technical issues, and general questions.',
}

export default function ContactPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="border-b border-slate-100 py-4 px-6">
        <div className="mx-auto max-w-5xl flex items-center justify-between">
          <Link href="/" className="text-indigo-700 font-bold text-lg">
            GoReportPilot
          </Link>
          <div className="flex gap-4 text-sm text-slate-500">
            <Link href="/login" className="hover:text-slate-900">Login</Link>
            <Link href="/signup" className="hover:text-slate-900 font-medium text-indigo-700">Get Started</Link>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-3xl px-6 py-14">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Contact Us</h1>
        <p className="text-slate-500 mb-10">
          We&apos;re a small team and we read every message. Expect a reply within 1–2 business days.
        </p>

        <div className="space-y-8">

          {/* General / Support */}
          <div className="rounded-xl border border-slate-200 p-6 flex gap-5">
            <div className="mt-0.5 text-indigo-600 shrink-0">
              <Mail size={22} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 mb-1">General &amp; Support</h2>
              <p className="text-slate-600 text-sm mb-2">
                Questions about the product, your account, integrations, or anything else — reach us at:
              </p>
              <a
                href="mailto:support@goreportpilot.com"
                className="text-indigo-600 font-medium hover:underline"
              >
                support@goreportpilot.com
              </a>
              <p className="text-slate-400 text-xs mt-1">Response within 1–2 business days (Mon–Fri, IST)</p>
            </div>
          </div>

          {/* Billing */}
          <div className="rounded-xl border border-slate-200 p-6 flex gap-5">
            <div className="mt-0.5 text-emerald-600 shrink-0">
              <CreditCard size={22} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 mb-1">Billing &amp; Subscriptions</h2>
              <p className="text-slate-600 text-sm mb-2">
                For billing queries, subscription changes, refund requests, or payment issues:
              </p>
              <a
                href="mailto:support@goreportpilot.com"
                className="text-indigo-600 font-medium hover:underline"
              >
                support@goreportpilot.com
              </a>
              <p className="text-slate-500 text-sm mt-2">
                Include your registered email and a brief description in the subject line
                (e.g., &ldquo;Refund Request — May 2025&rdquo;).
              </p>
              <p className="text-slate-400 text-xs mt-1">
                See our{' '}
                <Link href="/refund" className="text-indigo-500 hover:underline">Cancellation &amp; Refund Policy</Link>
                {' '}for details on eligible refunds.
              </p>
            </div>
          </div>

          {/* Bug Reports */}
          <div className="rounded-xl border border-slate-200 p-6 flex gap-5">
            <div className="mt-0.5 text-amber-600 shrink-0">
              <Bug size={22} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 mb-1">Bug Reports &amp; Feature Requests</h2>
              <p className="text-slate-600 text-sm mb-2">
                Found a bug or have an idea to make GoReportPilot better? We genuinely want to hear from you.
              </p>
              <a
                href="mailto:support@goreportpilot.com"
                className="text-indigo-600 font-medium hover:underline"
              >
                support@goreportpilot.com
              </a>
              <p className="text-slate-500 text-sm mt-2">
                For bugs, please include: what you expected to happen, what actually happened, and your
                browser/OS. Screenshots are always helpful.
              </p>
            </div>
          </div>

          {/* Registered Address */}
          <div className="rounded-xl border border-slate-200 p-6 flex gap-5">
            <div className="mt-0.5 text-rose-500 shrink-0">
              <MapPin size={22} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 mb-1">Registered Business Address</h2>
              <address className="not-italic text-slate-600 text-sm leading-6">
                <strong>SapienBotics</strong><br />
                New Delhi, India<br />
                GSTIN: 09CYVPS3328G1ZQ
              </address>
              <p className="text-slate-400 text-xs mt-2">
                GoReportPilot is a product of SapienBotics, a sole proprietorship registered in India.
              </p>
            </div>
          </div>

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
