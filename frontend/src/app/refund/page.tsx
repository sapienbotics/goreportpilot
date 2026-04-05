import Link from 'next/link'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Cancellation & Refund Policy — GoReportPilot',
  description: 'Understand GoReportPilot\'s cancellation and refund terms. No contracts, cancel anytime, pro-rated refunds available under certain conditions.',
}

export default function RefundPage() {
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
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Cancellation &amp; Refund Policy</h1>
        <p className="text-slate-500 text-sm mb-2">
          <strong>Effective date:</strong> 1 May 2025 &nbsp;|&nbsp; <strong>Entity:</strong> SapienBotics, Bareilly, Uttar Pradesh, India
        </p>
        <p className="text-slate-500 mb-10">
          We want you to feel confident subscribing to GoReportPilot. This policy explains how cancellations
          and refunds work. If you have any questions, email us at{' '}
          <a href="mailto:support@goreportpilot.com" className="text-indigo-600 hover:underline">
            support@goreportpilot.com
          </a>.
        </p>

        <div className="prose prose-slate max-w-none space-y-8 text-[15px] leading-7 text-slate-700">

          {/* 1 */}
          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">1. Subscription Model</h2>
            <p>
              GoReportPilot is offered as a monthly or annual subscription. Your subscription renews
              automatically at the end of each billing period unless you cancel before the renewal date.
              All prices are listed in USD and billed through Razorpay, our payment processor.
            </p>
          </section>

          {/* 2 */}
          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">2. Free Trial</h2>
            <p>
              New accounts receive a <strong>14-day free trial</strong> with full access to all features on
              the Starter plan. No credit card is required to start the trial. If you do not upgrade to a
              paid plan by the end of your trial, your account will revert to the free tier automatically —
              you will not be charged.
            </p>
          </section>

          {/* 3 */}
          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">3. How to Cancel</h2>
            <p>
              You can cancel your subscription at any time from <strong>Settings → Billing → Cancel Plan</strong>{' '}
              inside the GoReportPilot dashboard. No phone calls, no forms, no waiting.
            </p>
            <ul className="list-disc pl-5 space-y-2 mt-3">
              <li>
                <strong>Monthly plans:</strong> Cancellation takes effect at the end of the current billing
                month. You retain access until that date.
              </li>
              <li>
                <strong>Annual plans:</strong> Cancellation takes effect at the end of the current annual
                billing period. You retain access until that date.
              </li>
            </ul>
            <p className="mt-3">
              After cancellation, your data (clients, connections, generated reports) is preserved for
              <strong> 30 days</strong>. You may reactivate your subscription within that window and all
              data will be restored. After 30 days, data is permanently deleted.
            </p>
          </section>

          {/* 4 */}
          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">4. Refund Eligibility</h2>
            <p>
              We handle refunds on a case-by-case basis and aim to be fair. The following guidelines apply:
            </p>
            <ul className="list-disc pl-5 space-y-2 mt-3">
              <li>
                <strong>7-day money-back guarantee (monthly plans):</strong> If you are dissatisfied within
                the first 7 days of your first paid month, contact us and we will issue a full refund — no
                questions asked.
              </li>
              <li>
                <strong>Annual plans — early cancellation:</strong> If you cancel an annual plan within the
                first 30 days of payment, you are eligible for a refund for the unused months (i.e., total
                paid minus the monthly equivalent for months used).
              </li>
              <li>
                <strong>Annual plans — after 30 days:</strong> Refunds are not issued for the remaining
                months of an annual plan after the first 30 days. You retain access until the end of your
                paid period.
              </li>
              <li>
                <strong>Renewal charges:</strong> If you forgot to cancel before renewal, contact us within
                <strong> 48 hours</strong> of the charge and we will process a full refund for that renewal,
                provided you have not used the service significantly in that new period.
              </li>
              <li>
                <strong>Downgrade:</strong> If you downgrade from a higher plan to a lower plan mid-cycle,
                no partial refund is issued — the downgrade takes effect at the next billing date.
              </li>
            </ul>
          </section>

          {/* 5 */}
          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">5. Non-Refundable Situations</h2>
            <p>Refunds will not be issued in the following circumstances:</p>
            <ul className="list-disc pl-5 space-y-2 mt-3">
              <li>Requests made after the eligibility windows described in Section 4.</li>
              <li>
                Account termination due to violation of our{' '}
                <Link href="/terms" className="text-indigo-600 hover:underline">Terms of Service</Link>{' '}
                (e.g., abuse, fraud, misuse).
              </li>
              <li>Dissatisfaction due to third-party API limitations (e.g., Google or Meta API rate limits
                or downtime) that are outside our control.</li>
              <li>Failure to cancel before an automatic renewal where no request was submitted within 48
                hours of the charge.</li>
              <li>Promotional, discounted, or lifetime deal purchases (unless explicitly stated otherwise
                at the time of purchase).</li>
            </ul>
          </section>

          {/* 6 */}
          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">6. How to Request a Refund</h2>
            <p>To request a refund, email us at:</p>
            <p className="mt-2">
              <a href="mailto:support@goreportpilot.com" className="text-indigo-600 font-medium hover:underline">
                support@goreportpilot.com
              </a>
            </p>
            <p className="mt-3">Please include:</p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li>The email address associated with your GoReportPilot account.</li>
              <li>The date and amount of the charge you are requesting a refund for.</li>
              <li>A brief reason for your request (helps us improve the product).</li>
            </ul>
            <p className="mt-3">
              We aim to respond within <strong>2 business days</strong>. Approved refunds are processed
              through Razorpay and typically appear in your account within 5–10 business days depending on
              your bank or card issuer.
            </p>
          </section>

          {/* 7 */}
          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">7. Service Credits</h2>
            <p>
              In cases where a full refund is not applicable but the service experienced significant downtime
              or a critical failure affecting your account (e.g., more than 24 hours of confirmed outage),
              we may offer service credits at our discretion. Service credits are applied to your next
              billing cycle and cannot be redeemed for cash.
            </p>
          </section>

          {/* 8 */}
          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-3">8. Changes to This Policy</h2>
            <p>
              We may update this policy from time to time. Material changes will be communicated via email
              at least 14 days before taking effect. Continued use of the service after the effective date
              constitutes acceptance of the updated policy.
            </p>
            <p className="mt-3">
              If you have any concerns or questions about this policy, please contact us at{' '}
              <a href="mailto:support@goreportpilot.com" className="text-indigo-600 hover:underline">
                support@goreportpilot.com
              </a>.
            </p>
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
