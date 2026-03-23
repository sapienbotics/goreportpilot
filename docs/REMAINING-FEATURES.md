# ReportPilot — Remaining Features Checklist

**Last updated:** March 21, 2026
**Status:** MVP core complete. Prompt 9 (Report Customization + Editing + Email Delivery) ✅ DONE.

---

## Block 1: Report Customization & Editing ✅ COMPLETE

- [x] **Section toggles per client** — On client settings, toggle report sections on/off: Cover Page, Executive Summary, KPI Scorecard, Website Traffic, Meta Ads Performance, Key Wins, Concerns, Next Steps, Custom Text Section
- [x] **KPI selection per client** — `report_config.kpis` field stores selected KPI keys (UI shows checkboxes)
- [x] **Inline report editing** — Edit/Save/Cancel controls on every AI narrative card. Edits saved in `user_edits` JSONB column. Manual edits merged over AI narrative at display time.
- [x] **Regenerate individual sections** — "Regenerate" button on each narrative card. Re-runs GPT-4o for just that section using stored `narrative_data`.
- [x] **3 report templates** — Monthly (8 slides), Weekly Pulse (4 slides), Executive Brief (2 slides). Both PPTX and PDF respect template.
- [x] **Template selection per client** — Dropdown in Report Configuration card on client detail page.
- [x] **Custom text section** — Toggle on in sections, enter title + text. Appended as final slide/section.

## Block 2: Email Delivery ✅ COMPLETE

- [x] **Send report via email** — "Send to Client" button on report preview header. Opens Send dialog.
- [x] **Customizable email template** — Subject line editable, AI executive summary snippet, attachment choice, branded HTML template.
- [x] **Multiple recipients** — Comma-separated emails in Send dialog.
- [x] **Email delivery tracking** — Logged in `report_deliveries` table with status, resend_id, recipient_emails, error_message.
- [x] **Resend integration** — `email_service.py` uses Resend API (`httpx` POST to api.resend.com/emails).
- [x] **Email delivery UI** — Send dialog with To, Subject, Attachment type. Success confirmation screen.

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

## Block 6: Billing & Subscription (Razorpay) ✅ COMPLETE

- [x] **Database migration** — `supabase/migrations/006_billing.sql`: subscriptions + payment_history tables with RLS
- [x] **Plan configuration** — `backend/config/plans.py`: limits, features, pricing for trial/starter/pro/agency
- [x] **Razorpay service** — `backend/services/razorpay_service.py`: customer, subscription, webhook verification
- [x] **Billing router** — `backend/routers/billing.py`: subscription CRUD, payment verification, change-plan, cancel, history
- [x] **Razorpay webhook handler** — POST /api/billing/webhooks/razorpay: subscription.activated, charged, cancelled, paused, payment.failed
- [x] **Plan enforcement middleware** — `backend/middleware/plan_enforcement.py`: client limit check, feature gate
- [x] **Client creation enforced** — `clients.py` calls `can_create_client()` before inserting
- [x] **Razorpay config** — RAZORPAY_KEY_ID, KEY_SECRET, WEBHOOK_SECRET + 6 plan IDs in config.py and .env
- [x] **14-day free trial** — Auto-created on first visit to /dashboard/billing; trial_ends_at checked on every request
- [x] **Checkout flow** — Billing page opens Razorpay checkout modal, verifies payment, activates subscription
- [x] **Plan upgrade/downgrade** — Change-plan endpoint cancels current and creates new subscription
- [x] **Cancel subscription** — Sets cancel_at_period_end = true, confirmed via dialog
- [x] **Billing page** — Current plan card with usage bar, trial countdown, plan comparison (3 columns, annual/monthly toggle), payment history table
- [x] **UpgradePrompt component** — Reusable `<UpgradePrompt>` for gated feature prompts
- [x] **Billing nav item** — Added to sidebar between Settings and bottom
- [ ] **Razorpay plan setup** — ⚠️ MANUAL STEP: Create 6 plans in Razorpay dashboard (Subscriptions → Plans) and paste plan IDs into backend/.env
- [ ] **Dunning emails** — Payment failed webhook increments counter; email notification not yet wired (needs Resend integration)

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
