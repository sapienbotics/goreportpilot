# ReportPilot — Remaining Features Checklist

**Last updated:** March 21, 2026
**Status:** MVP core complete. Building production features.

---

## Block 1: Report Customization & Editing

- [ ] **Section toggles per client** — On client settings, toggle report sections on/off: Cover Page, Executive Summary, KPI Scorecard, Website Traffic, Meta Ads Performance, Key Wins, Concerns, Next Steps, Custom Text Section
- [ ] **KPI selection per client** — Choose which 4-6 KPIs appear in scorecard from all available metrics (sessions, users, conversions, bounce rate, ad spend, ROAS, CPA, CPC, CTR, impressions, clicks)
- [ ] **Inline report editing** — Click any AI-generated paragraph in report preview to edit text. Edits saved in `user_edits` JSON column. Manual edits persist across AI regenerations
- [ ] **Regenerate individual sections** — Button on each narrative section to re-run AI for just that section (not whole report)
- [ ] **3 report templates** — Monthly Performance Review (default 8 slides), Weekly Pulse (3-4 slides, KPIs + highlights only), Executive Brief (2 slides, one-page summary)
- [ ] **Template selection on generate** — Dropdown when generating report to pick template
- [ ] **Custom text section** — Add a manual text-only section to any report (agency notes, strategic commentary)

## Block 2: Email Delivery

- [ ] **Send report via email** — "Send to Client" button on report preview. Sends branded email with PDF and/or PPTX attached
- [ ] **Customizable email template** — Subject line (default: "[Client] — [Month] Performance Report"), body text with AI summary, sender name, reply-to address
- [ ] **Multiple recipients** — Send to multiple client email addresses (from client's `contact_emails` field)
- [ ] **Email delivery tracking** — Log sent/delivered/opened status in `report_deliveries` table
- [ ] **Resend integration** — Use Resend API for email sending (free tier: 3,000 emails/month)
- [ ] **Email delivery UI** — After generating report, show "Send" dialog with recipient list, subject, body preview, attachment choice (PDF/PPTX/both)

## Block 3: Scheduled Reports

- [ ] **Per-client schedule config** — On client settings: frequency (weekly/monthly), day of week/month, time (UTC), auto-send toggle
- [ ] **Auto-generate + auto-send** — System generates report and emails it automatically on schedule
- [ ] **Auto-generate + review-then-send** — System generates report as draft, sends notification to user to review and approve before sending to client
- [ ] **Background scheduler** — APScheduler or FastAPI BackgroundTasks that runs daily, checks `scheduled_reports` table for due reports, generates and sends
- [ ] **Schedule management UI** — Per-client schedule settings + global "Scheduled Reports" page showing all upcoming/past scheduled runs
- [ ] **Next run indicator** — Show "Next report: March 25, 2026" on client page

## Block 4: White-Label Branding

- [ ] **Agency branding settings page** — Upload agency logo (stored in Supabase Storage), set primary brand color, agency name, agency email, agency website URL
- [ ] **Per-client logo** — Upload client logo, displayed on report cover page
- [ ] **Apply branding to PowerPoint** — Agency logo in footer/header, client logo on cover, brand color on slide headers and chart accents
- [ ] **Apply branding to PDF** — Same branding as PPTX
- [ ] **Apply branding to emails** — Agency name as sender, agency email as reply-to, brand color in email template header
- [ ] **Remove "Powered by ReportPilot"** — On Pro and Agency plans, remove ReportPilot branding from reports and emails. Starter plan keeps it.
- [ ] **Logo upload API** — Backend endpoint to upload logo to Supabase Storage, return URL, save to user profile or client record

## Block 5: Settings Page

- [ ] **Account settings** — Edit name, email, change password, set timezone
- [ ] **Agency branding tab** — (from Block 4) Logo upload, brand color picker, agency name, email, website
- [ ] **AI preferences** — Default tone (Professional/Conversational/Executive/Data-Heavy), default comparison period (previous period / same period last year)
- [ ] **Email settings** — Default sender name, reply-to email, email footer text/signature
- [ ] **Notification preferences** — Toggle email notifications: report generated, connection expired, payment failed
- [ ] **Danger zone** — Delete account (with confirmation), export all data

## Block 6: Billing & Subscription (Razorpay)

- [ ] **Database migration** — Add `subscriptions` table: id, user_id, razorpay_subscription_id, razorpay_customer_id, plan (starter/pro/agency), status (trialing/active/past_due/cancelled), current_period_start, current_period_end, trial_ends_at, cancelled_at, created_at
- [ ] **Razorpay plan setup** — Create 3 plans in Razorpay dashboard: Starter ($19/mo), Pro ($39/mo), Agency ($69/mo) + annual variants
- [ ] **Plan enforcement middleware** — Backend middleware checks user's plan before allowing actions: client creation (enforce limit 3/10/25), PPT export (Pro+ only), white-label (Pro+ only), scheduling frequency, template count
- [ ] **Checkout flow** — Landing page pricing → "Start Free Trial" → signup → Razorpay checkout → subscription activated
- [ ] **14-day free trial** — No credit card required. User gets Pro features during trial. Trial end → prompt to upgrade. Grace period (3 days) then downgrade to free (reports stop, data preserved)
- [ ] **Razorpay webhook handler** — POST /api/webhooks/razorpay handling: subscription.activated, subscription.charged, subscription.cancelled, subscription.paused, payment.failed, payment.captured
- [ ] **Plan upgrade/downgrade** — From billing settings, switch plans. Razorpay handles prorated billing
- [ ] **Billing settings page** — Current plan name, usage stats (X/Y clients used), next billing date, payment history, update payment method link, cancel subscription button
- [ ] **Dunning flow** — Payment fails → 3 auto-retries over 7 days → email "update payment method" → 3-day grace period → downgrade to free tier
- [ ] **Feature gating on frontend** — Show upgrade prompts when user hits plan limits ("You've used 3/3 clients. Upgrade to Pro for 10 clients.")
- [ ] **Razorpay config** — Add RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET to backend config

## Block 7: Legal & Polish

- [ ] **Privacy Policy page** — `/privacy` route. Must mention: Google Analytics data usage, Meta Ads data usage, how tokens are stored (encrypted), data deletion policy, no data selling. Required for Google/Meta OAuth verification
- [ ] **Terms of Service page** — `/terms` route. Standard SaaS terms: service description, pricing, cancellation policy, data ownership, liability limitations
- [ ] **404 page** — Custom not-found page with navigation back to dashboard
- [ ] **Loading states** — Skeleton loaders on all data-fetching pages (clients list, reports list, report preview, settings)
- [ ] **Error boundaries** — Graceful error handling with retry buttons on all pages
- [ ] **Mobile responsiveness** — Dashboard usable on tablet (768px+). Client list, reports list, report preview should work. Report generation stays desktop-only.
- [ ] **Dashboard home page** — Replace basic card with real metrics: total clients (with plan limit), reports generated this month, reports due this week, recent activity feed, connection health summary
- [ ] **Toast notifications** — Consistent success/error toasts for all user actions (already using sonner, ensure coverage)
- [ ] **Favicon + meta tags** — ReportPilot icon, OpenGraph tags for social sharing

## Block 8: Deployment

- [ ] **Frontend → Vercel** — Connect GitHub repo, set env vars, deploy
- [ ] **Backend → Railway** — Docker or Procfile deploy, set env vars, connect to Supabase
- [ ] **Domain** — Buy reportpilot.co/.app/.io, configure DNS on Vercel
- [ ] **SSL** — Automatic via Vercel
- [ ] **Update OAuth redirect URIs** — Change localhost to production domain in Google Cloud Console and Meta Developer Dashboard
- [ ] **Update Supabase auth redirect** — Point to production URL
- [ ] **CORS** — Update FastAPI CORS to allow production domain
- [ ] **Google OAuth verification** — Submit for review (required for non-test users)
- [ ] **Meta App Review** — Submit for ads_read permission review

---

## Build Order (4 Prompts)

1. **Prompt 9**: Report Customization + Editing + Email Delivery (Block 1 + Block 2)
2. **Prompt 10**: White-Label + Scheduled Reports + Settings (Block 3 + Block 4 + Block 5)
3. **Prompt 11**: Billing & Subscription with Razorpay (Block 6)
4. **Prompt 12**: Legal, Polish & Deploy-Ready (Block 7 + Block 8)
