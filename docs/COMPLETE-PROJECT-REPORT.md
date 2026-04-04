# GoReportPilot -- Complete Project Report

**Generated:** April 4, 2026
**Founder:** Saurabh Singh / SapienBotics (New Delhi, India)
**Repository:** github.com/sapienbotics/goreportpilot
**Domain:** goreportpilot.com
**Stage:** MVP functionally complete, deployed to Vercel + Railway

---

## Table of Contents

1. [Project Vision & Business Context](#section-1-project-vision--business-context)
2. [Brand & Domain](#section-2-brand--domain)
3. [Tech Stack](#section-3-tech-stack)
4. [Complete File Structure](#section-4-complete-file-structure)
5. [Database Schema](#section-5-database-schema)
6. [Authentication & OAuth](#section-6-authentication--oauth)
7. [Report Generation Pipeline](#section-7-report-generation-pipeline)
8. [Frontend Architecture](#section-8-frontend-architecture)
9. [Backend Architecture](#section-9-backend-architecture)
10. [Deployment](#section-10-deployment)
11. [OAuth Redirect URIs](#section-11-oauth-redirect-uris)
12. [Development Workflow](#section-12-development-workflow)
13. [Prompt History](#section-13-prompt-history)
14. [Known Issues & Bugs](#section-14-known-issues--bugs)
15. [What's Remaining](#section-15-whats-remaining)
16. [Cost Analysis](#section-16-cost-analysis)
17. [Test Account & Sample Data](#section-17-test-account--sample-data)
18. [Security Checklist](#section-18-security-checklist)

---

## Section 1: Project Vision & Business Context

### What is GoReportPilot?

GoReportPilot is an AI-powered client reporting tool for digital marketing agencies and freelancers. It automates the workflow of pulling data from Google Analytics 4, Meta Ads, Google Ads, and Google Search Console, generating AI-written narrative insights via GPT-4.1, and exporting branded reports as PowerPoint (editable) and PDF files.

### The Problem

Marketing agencies spend 2-3 hours per client per month creating performance reports manually. For a freelancer with 10 clients, that's 20-30 hours/month of billable time lost. 86% of agencies still report manually. Existing tools (AgencyAnalytics at $179/mo, DashThis at $159/mo, Whatagraph at $223/mo) are expensive, none export to editable PowerPoint, and most charge AI narrative as an add-on.

### Target Customers

**Primary:** Indian digital marketing agencies (5-50 clients) priced out of Western tools. The INR pricing (starting Rs 1,599/mo vs $179/mo for competitors) makes GoReportPilot accessible.

**Secondary:** Global freelance marketers and small agencies wanting AI-written reports without enterprise pricing.

**Tertiary:** Medium agencies (50-200 clients) wanting PowerPoint export for client presentations.

### Competitive Positioning -- Four Core Differentiators

1. **AI Narrative Insights included** -- GPT-4.1 writes analysis, not just data tables. Competitors charge extra or don't offer it.
2. **Editable PowerPoint export** -- No competitor exports to .pptx. Agencies present in PowerPoint; this is the "presentation gap."
3. **Flat pricing** -- No per-client or per-dashboard fees. $19-69/month covers everything.
4. **Affordable** -- 5-10x cheaper than alternatives for the same client count.

### Revenue Model

| Plan | Monthly (INR) | Monthly (USD) | Annual (INR) | Annual (USD) | Client Limit | Key Features |
|------|--------------|--------------|-------------|-------------|-------------|--------------|
| Trial | Free | Free | -- | -- | 10 | 14 days, all features, "Powered by" badge |
| Starter | Rs 1,599 | $19 | Rs 15,350 | $15/mo | 3 | PDF only, 1 template, 1 tone |
| Pro | Rs 3,299 | $39 | Rs 31,670 | $31/mo | 10 | All exports, white-label, all templates/tones |
| Agency | Rs 5,799 | $69 | Rs 55,670 | $55/mo | 25 | Same as Pro, 25 clients |

Annual plans save approximately 20%.

### Three-Stakeholder Model

- **Developer (Saurabh/SapienBotics):** Builds and maintains the platform
- **Agency user:** Logs into GoReportPilot, manages clients, connects data sources, generates and sends reports
- **End clients:** Receive polished branded reports via email. They NEVER interact with GoReportPilot directly.

---

## Section 2: Brand & Domain

### Brand Identity

- **Brand name:** GoReportPilot
- **Domain:** goreportpilot.com (purchased, DNS pending configuration)
- **Deployed URLs:** goreportpilot.vercel.app (frontend), goreportpilot-production.up.railway.app (backend)

### Logo Design

The logo is an SVG wordmark: the letter "G" rendered normally in indigo (#4338CA), followed by an "o" replaced by a circle with a forward arrow (-->) inside it (also in indigo), followed by "Report" in the current text color, and "Pilot" in indigo. The arrow-in-circle represents movement, progress, "go forward."

### Logo Components

| File | Purpose |
|------|---------|
| `frontend/src/components/ui/Logo.tsx` | Main SVG wordmark. Props: `size` (sm/md/lg), `variant` (light/dark), `className` |
| `frontend/src/components/ui/LogoIcon.tsx` | Square icon (indigo background, white G + arrow-circle). Props: `size` (default 32) |
| `frontend/public/favicon.svg` | Static SVG favicon with same icon design |

### Size Variants

| Size | Font Size | Circle Radius | SVG Width | SVG Height |
|------|-----------|--------------|-----------|------------|
| sm | 18px | 8.5 | 220 | 34 |
| md | 23px | 11 | 280 | 44 |
| lg | 30px | 14 | 360 | 54 |

### Dark Variant

- Light (default): "G" and "Pilot" in #4338CA, "Report" in currentColor (dark text)
- Dark: "G" and "Pilot" in #818CF8 (lighter indigo), "Report" in #F8FAFC (near-white)

### Brand Color Palette

- **Primary (Indigo):** #4338CA (`indigo-700`)
- **Accent/Success:** #059669 (`emerald-600`)
- **Danger:** #E11D48 (`rose-600`)
- **Warning:** #D97706 (`amber-600`)
- **Background:** #FFFFFF + #F8FAFC (`slate-50`)
- **Primary text:** #0F172A (`slate-900`)
- **Secondary text:** #64748B (`slate-500`)

### Naming Rule

- Page titles, headers, footer copyright, comparison tables --> "GoReportPilot"
- Inside body copy / sentences --> "ReportPilot" (shorter, reads better)
- The Logo SVG component always renders the full "Go[arrow]ReportPilot" visual

### Where Logo Is Used

| Location | Size | Variant |
|----------|------|---------|
| Landing page navbar | md | light |
| Landing page footer | sm | dark |
| Dashboard sidebar | sm | light |
| Login page | lg | light |
| Signup page | lg | light |
| Privacy page nav | sm | light |
| Terms page nav | sm | light |

---

## Section 3: Tech Stack

| Layer | Technology | Version | Purpose | Config Location |
|-------|-----------|---------|---------|-----------------|
| Frontend Framework | Next.js (App Router) | 14.2.35 | Web app + marketing pages | `frontend/package.json` |
| Frontend Language | TypeScript | 5.x | Type safety | `frontend/tsconfig.json` |
| CSS Framework | Tailwind CSS | 3.4.1 | Utility-first styling | `frontend/tailwind.config.ts` |
| UI Components | shadcn/ui | latest | Accessible, copy-paste components | `frontend/src/components/ui/` |
| Heading Font | Plus Jakarta Sans | Google Fonts | Headings | `frontend/src/app/layout.tsx` |
| Body Font | Inter | Google Fonts | Body text | `frontend/src/app/layout.tsx` |
| Backend Framework | FastAPI | 0.110.0 | REST API, OAuth, report generation | `backend/main.py` |
| Backend Language | Python | 3.12+ | Type-hinted Python | `backend/Dockerfile` |
| Settings | Pydantic Settings | 2.2-2.4 | Environment variable loading | `backend/config.py` |
| Database | Supabase (PostgreSQL) | Latest | Data storage, RLS, auth | `supabase/migrations/` |
| Auth | Supabase Auth | Included | Signup/login, JWT, session | `frontend/src/lib/supabase/` |
| AI | OpenAI GPT-4.1 | Latest | Narrative commentary generation | `backend/services/ai_narrative.py` |
| PPTX Generation | python-pptx | 0.6.23 | PowerPoint file creation | `backend/services/report_generator.py` |
| PDF (Primary) | LibreOffice headless | 7.x+ | PPTX to PDF conversion (all scripts) | `backend/Dockerfile` |
| PDF (Fallback) | ReportLab | 4.1.0 | PDF for Latin languages only | `backend/services/report_generator.py` |
| Charts | matplotlib | 3.8.3 | Static chart images (300 DPI) | `backend/services/chart_generator.py` |
| Fonts (PDF) | Google Noto fonts | Latest | Full script coverage (Devanagari, CJK, Arabic) | `backend/Dockerfile` |
| Token Encryption | cryptography | 42.0.5 | AES-256-GCM for OAuth tokens | `backend/services/encryption.py` |
| CSV Parsing | chardet | 5.x+ | Encoding detection | `backend/services/csv_parser.py` |
| Billing | Razorpay | 1.4.2 | Subscription billing (India) | `backend/services/razorpay_service.py` |
| Email | Resend | 0.8.0 | Branded report delivery emails | `backend/services/email_service.py` |
| GA4 API | google-analytics-data | 0.18.5 | Google Analytics 4 data pull | `backend/services/google_analytics.py` |
| Meta API | facebook-business | 19.0.0 | Meta Marketing API (v21.0) | `backend/services/meta_ads.py` |
| Google Ads | google-ads | 24.1.0 | Google Ads API | `backend/services/google_ads.py` |
| HTTP Client | httpx | 0.24-0.27 | Async HTTP requests | `backend/requirements.txt` |
| Image Processing | Pillow | 10.2.0 | Logo background removal | `backend/services/logo_processor.py` |
| Scheduling | APScheduler (custom) | -- | Background report generation | `backend/services/scheduler.py` |
| Frontend Hosting | Vercel | -- | Next.js deployment | `frontend/` root |
| Backend Hosting | Railway | -- | Docker deployment | `backend/Dockerfile` |
| Version Control | GitHub | -- | sapienbotics/goreportpilot | `.git/` |

### Why Razorpay Instead of Stripe

Stripe is invite-only in India and requires a lengthy approval process. Razorpay is the standard Indian payment gateway with immediate access, INR-native pricing, and subscription billing support.

### Why GPT-4.1 Instead of GPT-4o

GPT-4.1 was migrated from GPT-4o for better instruction-following and lower cost. GPT-4.1 is more literal in style (the conversational tone modifier was adjusted to compensate with extra warmth instructions). The `ai_model` field in report metadata tracks which model generated each report.

---

## Section 4: Complete File Structure

```
reportpilot/
+-- CLAUDE.md                          # Master project instructions
+-- README.md                          # Public readme
+-- .env.example                       # Environment variable template
+-- .gitignore                         # Git ignore rules
|
+-- frontend/                          # Next.js 14 app
|   +-- package.json
|   +-- next.config.mjs
|   +-- tsconfig.json
|   +-- tailwind.config.ts
|   +-- postcss.config.mjs
|   +-- public/
|   |   +-- favicon.svg                # SVG favicon (G + arrow-circle)
|   +-- src/
|       +-- app/
|       |   +-- layout.tsx             # Root layout (fonts, metadata, Toaster)
|       |   +-- page.tsx               # Landing page (10 sections)
|       |   +-- globals.css            # Tailwind directives + CSS vars
|       |   +-- error.tsx              # Global error boundary
|       |   +-- not-found.tsx          # 404 page
|       |   +-- favicon.ico            # ICO fallback favicon
|       |   +-- login/page.tsx         # Login form
|       |   +-- signup/page.tsx        # Signup form
|       |   +-- pricing/page.tsx       # Pricing (stub)
|       |   +-- privacy/page.tsx       # Privacy policy
|       |   +-- terms/page.tsx         # Terms of service
|       |   +-- shared/[hash]/page.tsx # Public shared report viewer
|       |   +-- api/auth/callback/
|       |   |   +-- route.ts           # Supabase auth callback
|       |   |   +-- google-analytics/route.ts
|       |   |   +-- google-ads/route.ts
|       |   |   +-- meta-ads/route.ts
|       |   |   +-- search-console/route.ts
|       |   +-- dashboard/
|       |       +-- layout.tsx         # Auth guard + DashboardShell
|       |       +-- error.tsx          # Dashboard error boundary
|       |       +-- page.tsx           # Dashboard home (stats)
|       |       +-- clients/
|       |       |   +-- page.tsx       # Client list
|       |       |   +-- [clientId]/page.tsx  # Client detail (5 tabs)
|       |       +-- reports/
|       |       |   +-- page.tsx       # All reports list
|       |       |   +-- [reportId]/page.tsx  # Report preview/edit/send
|       |       +-- integrations/
|       |       |   +-- page.tsx       # Integration hub
|       |       |   +-- google-callback/page.tsx  # Unified Google OAuth callback
|       |       |   +-- meta-callback/page.tsx    # Meta OAuth callback
|       |       +-- settings/page.tsx  # Settings (5 tabs)
|       |       +-- billing/page.tsx   # Billing + Razorpay checkout
|       +-- components/
|       |   +-- ui/                    # shadcn/ui components (button, card, dialog, etc.)
|       |   |   +-- Logo.tsx           # Brand wordmark SVG
|       |   |   +-- LogoIcon.tsx       # Square icon SVG
|       |   +-- layout/
|       |   |   +-- dashboard-shell.tsx
|       |   |   +-- sidebar.tsx
|       |   |   +-- sign-out-button.tsx
|       |   +-- landing/
|       |   |   +-- mobile-nav.tsx
|       |   |   +-- pricing-toggle.tsx
|       |   |   +-- faq-accordion.tsx
|       |   +-- clients/
|       |   |   +-- add-client-dialog.tsx
|       |   |   +-- CSVPreviewTable.tsx
|       |   |   +-- CSVUploadDialog.tsx
|       |   |   +-- LanguageSelector.tsx
|       |   |   +-- RichTextEditor.tsx
|       |   |   +-- tabs/             # OverviewTab, IntegrationsTab, ReportsTab, SchedulesTab, SettingsTab
|       |   +-- reports/
|       |   |   +-- ShareReportDialog.tsx
|       |   |   +-- ViewAnalytics.tsx
|       |   |   +-- CSVUploadForReport.tsx
|       |   +-- dashboard/
|       |       +-- upgrade-prompt.tsx
|       +-- lib/
|       |   +-- api.ts                # Axios client + all API functions
|       |   +-- utils.ts              # cn(), formatDate, formatCurrency, formatNumber
|       |   +-- supabase/
|       |       +-- client.ts          # Browser Supabase client
|       |       +-- server.ts          # Server-side Supabase client
|       |       +-- middleware.ts       # Session refresh + auth redirects
|       +-- hooks/
|       |   +-- use-auth.ts            # useAuth() hook
|       +-- types/
|       |   +-- index.ts              # All TypeScript interfaces
|       +-- middleware.ts              # Next.js middleware (auth protection)
|
+-- backend/
|   +-- main.py                        # FastAPI app, CORS, routers, health check
|   +-- config.py                      # Pydantic Settings + model_post_init
|   +-- Dockerfile                     # Python 3.12 + LibreOffice + Noto fonts
|   +-- railway.toml                   # Railway deployment config
|   +-- requirements.txt               # Python dependencies
|   +-- routers/
|   |   +-- auth.py                    # OAuth endpoints (Google, Meta, Ads, Search Console)
|   |   +-- clients.py                 # Client CRUD + logo upload
|   |   +-- connections.py             # Connection save/list/delete
|   |   +-- csv_upload.py              # CSV upload + parse + templates
|   |   +-- reports.py                 # Report generate/list/get/download/edit/send
|   |   +-- settings.py               # Profile get/update + logo upload
|   |   +-- scheduled_reports.py       # Schedule CRUD
|   |   +-- billing.py                 # Razorpay subscription + webhooks
|   |   +-- dashboard.py              # Dashboard stats aggregation
|   |   +-- shared.py                  # Share links + public view + analytics
|   +-- services/
|   |   +-- ai_narrative.py           # GPT-4.1 narrative engine
|   |   +-- report_generator.py       # PPTX + PDF generation orchestrator
|   |   +-- chart_generator.py        # matplotlib charts (15 types, 3 themes)
|   |   +-- csv_parser.py             # Production CSV parser
|   |   +-- encryption.py             # AES-256-GCM token encryption
|   |   +-- google_analytics.py       # GA4 Data API client
|   |   +-- meta_ads.py               # Meta Marketing API client
|   |   +-- google_ads.py             # Google Ads API client
|   |   +-- search_console.py         # Search Console API client
|   |   +-- email_service.py          # Resend email delivery
|   |   +-- razorpay_service.py       # Razorpay billing integration
|   |   +-- scheduler.py              # Background scheduled report runner
|   |   +-- plans.py                  # Plan config (limits, features, pricing)
|   |   +-- mock_data.py              # Fake GA4 + Meta data for dev
|   |   +-- demo_data.py              # Rich demo data for showcase
|   |   +-- logo_processor.py         # Pillow background removal
|   |   +-- slide_selector.py         # Smart slide selection + KPI scoring
|   |   +-- text_formatter.py         # Text to structured blocks for PPTX
|   |   +-- supabase_client.py        # Singleton admin client
|   +-- middleware/
|   |   +-- auth.py                   # JWT verification (get_current_user_id)
|   |   +-- plan_enforcement.py       # Plan limits + feature gates
|   +-- models/
|   |   +-- schemas.py                # Pydantic request/response models
|   +-- templates/
|   |   +-- pptx/                     # 6 PPTX visual templates
|   |   +-- csv_templates/            # 5 CSV templates (linkedin, tiktok, etc.)
|   |   +-- email_templates/          # report_delivery.html
|   +-- scripts/                       # Utility scripts (key generation, template auditing)
|   +-- generated_reports/            # Runtime output directory (.gitkeep)
|   +-- static/logos/                 # Uploaded logos (.gitkeep)
|
+-- supabase/migrations/              # 9 SQL migration files (001-009)
+-- docs/                             # Project documentation
+-- scripts/                          # Setup and seed scripts
```

---

## Section 5: Database Schema

**Supabase Project URL:** https://kbytzqviqzcvfdepjyby.supabase.co

### Tables (12 Total)

#### profiles
Extends auth.users. Stores agency settings and branding.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | References auth.users(id) ON DELETE CASCADE |
| email | TEXT NOT NULL | |
| name | TEXT | |
| avatar_url | TEXT | |
| plan | TEXT | DEFAULT 'starter' |
| agency_name | TEXT | |
| agency_email | TEXT | |
| agency_logo_url | TEXT | |
| brand_color | TEXT | DEFAULT '#4338CA' |
| agency_website | TEXT | |
| timezone | TEXT | DEFAULT 'UTC' |
| default_ai_tone | TEXT | DEFAULT 'professional' |
| sender_name | TEXT | For email delivery |
| reply_to_email | TEXT | |
| email_footer | TEXT | |
| notification_report_generated | BOOLEAN | DEFAULT true |
| notification_connection_expired | BOOLEAN | DEFAULT true |
| notification_payment_failed | BOOLEAN | DEFAULT true |
| preferences | JSONB | DEFAULT '{}' |
| created_at / updated_at | TIMESTAMPTZ | |

#### clients
Agency's clients with report configuration.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | gen_random_uuid() |
| user_id | UUID FK | --> profiles(id) CASCADE |
| name | TEXT NOT NULL | |
| industry | TEXT | |
| logo_url | TEXT | |
| website_url | TEXT | |
| goals_context | TEXT | |
| primary_contact_email | TEXT | |
| ai_tone | TEXT | DEFAULT 'professional' |
| report_config | JSONB | Section toggles, KPIs, template |
| report_language | TEXT | DEFAULT 'en' |
| notes | TEXT | |
| is_active | BOOLEAN | DEFAULT true (soft-delete) |
| created_at / updated_at | TIMESTAMPTZ | |

#### connections
OAuth tokens for data sources (encrypted at application level).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| client_id | UUID FK | --> clients(id) CASCADE |
| platform | TEXT | ga4, meta_ads, google_ads, search_console, csv_* |
| account_id | TEXT | |
| account_name | TEXT | |
| currency | TEXT | DEFAULT 'USD' |
| access_token_encrypted | TEXT | AES-256-GCM encrypted |
| refresh_token_encrypted | TEXT | AES-256-GCM encrypted |
| token_expires_at | TIMESTAMPTZ | |
| status | TEXT | active, expiring_soon, expired, error, revoked |
| created_at / updated_at | TIMESTAMPTZ | |

#### reports
Generated reports with AI narrative and file paths.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| client_id | UUID FK | --> clients(id) CASCADE |
| user_id | UUID FK | --> profiles(id) CASCADE |
| title | TEXT | |
| period_start / period_end | DATE | |
| status | TEXT | generating, draft, approved, sent, failed |
| ai_narrative | JSONB | Full AI output |
| user_edits | JSONB | Manual overrides per section |
| pptx_file_url | TEXT | File path to generated PPTX |
| pdf_file_url | TEXT | File path to generated PDF |
| created_at / updated_at | TIMESTAMPTZ | |

#### subscriptions (Migration 006)
Razorpay billing state per user.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK UNIQUE | --> auth.users(id) CASCADE |
| razorpay_customer_id | TEXT | |
| razorpay_subscription_id | TEXT | |
| plan | TEXT | trial, starter, pro, agency |
| billing_cycle | TEXT | monthly, annual |
| status | TEXT | trialing, active, past_due, cancelled, expired, paused |
| trial_ends_at | TIMESTAMPTZ | DEFAULT NOW() + 14 days |
| cancel_at_period_end | BOOLEAN | DEFAULT false |
| created_at / updated_at | TIMESTAMPTZ | |

#### shared_reports (Migration 008)
Shareable public links for reports.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| report_id | UUID FK | --> reports(id) CASCADE |
| user_id | UUID FK | --> auth.users(id) |
| share_hash | VARCHAR(32) UNIQUE | URL token |
| password_hash | VARCHAR(255) | Optional bcrypt hash |
| expires_at | TIMESTAMPTZ | Optional expiry |
| is_active | BOOLEAN | DEFAULT true |

#### report_views (Migration 008)
View tracking for shared links.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| shared_report_id | UUID FK | --> shared_reports(id) CASCADE |
| viewer_ip | VARCHAR(45) | First 2 octets only (privacy) |
| device_type | VARCHAR(20) | mobile, desktop, tablet |
| duration_seconds | INTEGER | |
| viewed_at | TIMESTAMPTZ | |

Also: data_snapshots, report_templates, report_deliveries, scheduled_reports, payment_history (see migration details in Section 5 continuation).

### Migrations (001-009)

| Migration | Purpose |
|-----------|---------|
| 001_initial_schema | 8 core tables, 28 RLS policies, 15 indexes, 5 triggers, 1 seed template |
| 002_add_currency | Added currency column to connections |
| 003_report_customization | report_config JSONB on clients, agency profile fields |
| 004_whitelabel_scheduling | White-label branding fields, scheduled_reports enhancements |
| 005_profiles_missing_columns | Idempotent safety net for profile fields |
| 006_billing | subscriptions + payment_history tables with RLS |
| 007_add_language | report_language on clients |
| 008_shared_reports | shared_reports + report_views tables |
| 009_widen_platform_constraint | Allow csv_* platform values via regex constraint |

### Row-Level Security

RLS is enabled on ALL tables. Every table with user data has policies ensuring `auth.uid() = user_id` (or joined through the clients table for connections, data_snapshots, etc.). Users can ONLY access their own data.

---

## Section 6: Authentication & OAuth

### Supabase Auth (User Login)

**Signup flow:** Email + password --> Supabase sends confirmation email --> User clicks link --> Redirects to `/api/auth/callback` --> Exchanges code for session --> Redirects to `/dashboard`.

**Login flow:** Email + password --> `supabase.auth.signInWithPassword()` --> JWT stored in httpOnly cookie --> Redirect to `/dashboard`.

**Session management:** Supabase handles JWTs automatically. The Next.js middleware (`src/middleware.ts`) refreshes the session on every request. Backend validates the JWT via `supabase.auth.get_user(token)` in `middleware/auth.py`.

**Known issue:** Users can currently sign in without confirming their email. Supabase email confirmation is enabled but not enforced at login.

### Google Analytics 4 OAuth

**Full flow:**
1. User clicks "Connect GA4" on client integrations tab
2. Frontend stores `clientId` in `sessionStorage` key `ga4_connect_client_id`
3. Frontend calls `GET /api/auth/google/url` --> backend returns Google OAuth consent URL
4. User grants access on Google consent screen (scopes: `analytics.readonly`)
5. Google redirects to `{FRONTEND_URL}/api/auth/callback/google-analytics?code=...&state=...`
6. Next.js route handler (`route.ts`) forwards code+state to `/dashboard/integrations/google-callback`
7. `google-callback` page detects platform via sessionStorage, calls `POST /api/auth/google/callback`
8. Backend exchanges code for tokens via Google token endpoint
9. Backend encrypts tokens with AES-256-GCM, queries GA4 properties
10. Returns encrypted `token_handle` + property list to frontend
11. User selects a property --> frontend calls `POST /api/connections` to save

**Token refresh:** Backend auto-refreshes expired access tokens using the stored refresh token before each API call. Always includes `prompt=consent&access_type=offline` to guarantee a refresh token.

### Meta Ads OAuth

**Full flow:**
1. User clicks "Connect Meta Ads" --> stores clientId in `sessionStorage` key `meta_connect_client_id`
2. Frontend calls `GET /api/auth/meta/url` --> backend returns Facebook OAuth URL
3. User logs into Facebook, grants access (scope: `ads_read`)
4. Meta redirects to `{FRONTEND_URL}/api/auth/callback/meta-ads?code=...`
5. Next.js route handler forwards to `/dashboard/integrations/meta-callback`
6. Page calls `POST /api/auth/meta/callback` --> backend exchanges code for short-lived token
7. Backend upgrades to long-lived token (~60 days via `oauth/access_token?grant_type=fb_exchange_token`)
8. Backend lists ad accounts, returns encrypted handle + account list
9. User selects account --> saved as connection

**Token expiry:** Long-lived tokens expire after 60 days. `token_expires_at` is stored for health monitoring.

### Google Ads OAuth

Same Google OAuth flow as GA4 but with different scopes (`adwords` scope). Uses dedicated redirect URI `/api/auth/callback/google-ads`. The `google-callback` page detects this via `sessionStorage` key `gads_connect_client_id` and calls `POST /api/auth/google-ads/callback`.

**MCC Account ID:** 815-247-5096 (stored as `GOOGLE_ADS_LOGIN_CUSTOMER_ID` without dashes: `8152475096`)

**Developer token:** Required for Google Ads API access. Configured via `GOOGLE_ADS_DEVELOPER_TOKEN`.

### Search Console OAuth

Same Google OAuth flow with Search Console scopes (`webmasters.readonly`). Redirect URI: `/api/auth/callback/search-console`. SessionStorage key: `gsc_connect_client_id`. Backend calls `POST /api/auth/search-console/callback`.

### Token Encryption (AES-256-GCM)

**Implementation:** `backend/services/encryption.py`

1. `encrypt_token(plaintext)`: Generates 12-byte random nonce, encrypts with AES-256-GCM using 32-byte key from `TOKEN_ENCRYPTION_KEY` env var, returns `base64(nonce || ciphertext+tag)`
2. `decrypt_token(encrypted)`: Base64-decodes, splits first 12 bytes as nonce, decrypts remainder
3. Key is base64-encoded 32-byte value stored ONLY in environment variables, never in database
4. Tokens are encrypted before database storage, decrypted only when needed for API calls

---

## Section 7: Report Generation Pipeline

This is the core product. The full pipeline from button click to downloadable files.

### Data Flow

1. **User clicks "Generate Report"** on client Reports tab with date range, template, and optional CSV files
2. **Frontend sends** `POST /api/reports/generate` with `client_id`, `period_start`, `period_end`, `template` (full/summary/brief), `visual_template` (6 options), `csv_sources` (optional)
3. **Backend pulls real data** from connected sources (GA4 Data API, Meta Marketing API, Search Console API, Google Ads API). Falls back to mock data if no connections.
4. **Data sanitization:** `_sanitize_data_for_ai()` rounds all floats to 2 decimal places to prevent JSON serialization issues
5. **AI narrative generation:** GPT-4.1 call with structured system prompt, data payload, tone modifier, and language instruction. Returns JSON with 6-9 sections.
6. **Chart generation:** matplotlib renders up to 15 chart types at 300 DPI, theme-matched to the visual template
7. **PPTX generation:** Template-based with slide pool architecture (19 possible slides, unused deleted based on data availability)
8. **PDF generation:** LibreOffice headless converts PPTX to PDF (primary path). ReportLab fallback for Latin-only. Returns None for non-Latin without LibreOffice.
9. **Files saved** to `backend/generated_reports/{uuid}/` and report record persisted to Supabase

### Slide Pool Architecture

Templates contain ALL 19 possible slides. The generator:
1. Analyzes which data sources are available
2. Selects relevant slides, deletes irrelevant ones
3. Performs save-reload cycle to purge orphaned python-pptx parts
4. Duplicates CSV slides for multiple CSV sources
5. Populates all `{{placeholder}}` tokens with real data
6. Embeds chart PNG images
7. Renumbers page footers

**19 Slide Types:**

| Index | ID | Data Requirement |
|-------|-----|-----------------|
| 0 | cover | Always |
| 1 | executive_summary | Always |
| 2 | kpi_scorecard | Always |
| 3 | website_traffic | GA4 + daily data |
| 4 | website_engagement | GA4 + device/pages |
| 5 | website_audience | GA4 + countries/new-returning |
| 6 | bounce_rate_analysis | GA4 + daily bounce rate |
| 7 | meta_ads_overview | Meta Ads |
| 8 | meta_ads_audience | Meta + demographics |
| 9 | meta_ads_creative | Meta + top ads |
| 10 | google_ads_overview | Google Ads |
| 11 | google_ads_keywords | Google Ads + search terms |
| 12 | seo_overview | Search Console |
| 13 | csv_data | CSV sources (duplicated per source) |
| 14 | conversion_funnel | GA4 + conversions > 0 |
| 15 | key_wins | Always (full/summary) |
| 16 | concerns | Always (full/summary) |
| 17 | next_steps | Always |
| 18 | custom_section | Only if has title + text |

### 6 Visual PPTX Templates

| Template | Chart Theme | Style |
|----------|-------------|-------|
| modern_clean | light | White background, indigo accents |
| dark_executive | dark | Dark navy background, cyan/teal accents |
| colorful_agency | colorful | White background, orange/violet accents |
| bold_geometric | light | Geometric shapes, indigo tones |
| minimal_elegant | light | Clean minimal design |
| gradient_modern | colorful | Gradient backgrounds |

### AI Narrative Engine

**Model:** GPT-4.1 (`gpt-4.1`)

**System prompt core rules:**
- Be specific with numbers (never "traffic increased" without exact figures)
- Always compare to previous period
- Don't hide declining metrics -- explain and suggest fixes
- Keep paragraphs 2-3 sentences max
- Structure: headline insight --> data support --> recommendation

**4 Tone Presets (+ aliases):**
- `professional`: Authoritative, data-supported, clear transitions
- `conversational` / `friendly`: Warm, advisory, like explaining over coffee
- `executive`: Bullet points, max 100 words/section, every sentence needs data
- `data_heavy` / `technical`: Thorough analytical review, all percentages and campaign names

**13 Supported Languages:** English (default), Spanish, Portuguese, French, German, Hindi, Arabic, Japanese, Italian, Korean, Chinese Simplified, Dutch, Turkish

**Output format:** JSON with sections: executive_summary, website_performance, paid_advertising, google_ads_performance, seo_performance, csv_performance, key_wins, concerns, next_steps

### Chart Generator

**15 chart types**, each checking for minimum data before rendering:

Sessions (area line), Traffic Sources (horizontal bar), Spend vs Conversions (dual-axis), Campaign Performance (grouped bar), Device Breakdown (donut), Top Pages (horizontal bar), New vs Returning (grouped bar), Top Countries (horizontal bar), Audience Demographics (grouped bar), Placements (horizontal bar), Bounce Rate Trend (line + avg), Conversion Funnel (horizontal decreasing), Google Ads Spend (dual-axis), Google Ads Campaigns (grouped bar), CSV Data (auto bar)

**Sizing:** 5.6" x 3.0" at 300 DPI. CSV charts capped at 8.0" centered. Pie/donut charts keep original width when solo; bar/line charts expand to max 8.5".

### Smart KPI Selection

`select_kpis()` in `slide_selector.py` scores all available metrics by priority (conversions=10, sessions=9, spend=8, etc.), picks top 6. Never shows N/A or zero-value KPIs.

### CSV Parser

Production-grade with: encoding detection (UTF-8 BOM --> UTF-8 --> chardet --> Latin-1), delimiter detection, binary file rejection (xlsx/pdf/images), flexible column aliases, number parsing (K/M/B suffixes, European decimals, currency symbols), unit auto-detection, filename cleaning with brand capitalization (35 brands). Max 20 metrics per file.

---

## Section 8: Frontend Architecture

### Page Routes

| Route | Auth | Purpose |
|-------|------|---------|
| `/` | Public | Landing page (10 marketing sections) |
| `/login` | Public (redirects if logged in) | Email/password login |
| `/signup` | Public (redirects if logged in) | Account creation |
| `/pricing` | Public | Pricing page (stub) |
| `/privacy` | Public | Privacy policy |
| `/terms` | Public | Terms of service |
| `/shared/[hash]` | Public | Shared report viewer (optional password) |
| `/dashboard` | Protected | Dashboard home (stats cards, activity) |
| `/dashboard/clients` | Protected | Client list with Add dialog |
| `/dashboard/clients/[clientId]` | Protected | Client detail (5 tabs) |
| `/dashboard/reports` | Protected | All reports with filters |
| `/dashboard/reports/[reportId]` | Protected | Report preview, edit, send, share |
| `/dashboard/integrations` | Protected | Connect GA4/Meta/Ads/GSC |
| `/dashboard/settings` | Protected | Account, branding, email, AI, notifications |
| `/dashboard/billing` | Protected | Plan management, Razorpay checkout |

### API Client (`src/lib/api.ts`)

Centralized Axios instance. Base URL from `NEXT_PUBLIC_API_URL`. Auto-attaches Supabase JWT via request interceptor. All API calls go through this -- never raw `fetch()` in components.

---

## Section 9: Backend Architecture

### FastAPI App (`main.py`)

- 11 router mounts under `/api/`
- Environment-aware CORS (production domain + localhost in development)
- Background scheduler loop (hourly check for due scheduled reports)
- Enhanced `/health` endpoint checking Supabase, OpenAI, LibreOffice
- Structured logging (INFO in production, DEBUG in development)
- Static file serving for logos at `/static`

### Config (`config.py`)

Pydantic Settings with `model_post_init` that auto-derives OAuth redirect URIs from `FRONTEND_URL` when not explicitly set. All redirect URIs empty by default, constructed as `{FRONTEND_URL}/api/auth/callback/{platform}`.

### All Endpoints

**Auth (8):** GET/POST for google, meta, google-ads, search-console (url + callback each)

**Clients (7):** GET list, POST create, GET/PATCH/DELETE by ID, POST upload-logo, POST custom-section-image

**Connections (3):** POST create, GET by client, DELETE by ID

**CSV (4):** POST upload, POST parse, GET templates, GET template by name

**Reports (9):** POST generate, GET list, GET by client, GET by ID, GET download PPTX/PDF, PATCH edit, POST regenerate-section, POST send

**Settings (3):** GET profile, PATCH profile, POST upload-logo

**Scheduled Reports (5):** POST create, GET list, GET by client, PATCH update, DELETE

**Billing (7):** GET subscription, POST create/verify/change/cancel, GET history, POST webhook

**Dashboard (1):** GET stats

**Sharing (8):** POST create share, GET shares, DELETE share, GET analytics, GET public metadata, GET public data, POST verify password, POST log view

---

## Section 10: Deployment

### GitHub

- **Repository:** sapienbotics/goreportpilot
- **Branch:** main
- **Auto-deploy:** Both Vercel and Railway trigger on push to main

### Railway (Backend)

- **Service URL:** goreportpilot-production.up.railway.app
- **Dockerfile:** `backend/Dockerfile` (Python 3.12-slim + LibreOffice + Noto fonts)
- **railway.toml:** builder=dockerfile, dockerfilePath=backend/Dockerfile, healthcheckPath=/health, timeout=300s
- **PORT handling:** `CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]`

**Backend environment variables (names):** SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, META_APP_ID, META_APP_SECRET, OPENAI_API_KEY, TOKEN_ENCRYPTION_KEY, FRONTEND_URL, BACKEND_URL, ENVIRONMENT, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET, RAZORPAY_PLAN_STARTER_MONTHLY, RAZORPAY_PLAN_STARTER_ANNUAL, RAZORPAY_PLAN_PRO_MONTHLY, RAZORPAY_PLAN_PRO_ANNUAL, RAZORPAY_PLAN_AGENCY_MONTHLY, RAZORPAY_PLAN_AGENCY_ANNUAL, RESEND_API_KEY, EMAIL_FROM_DOMAIN, GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_LOGIN_CUSTOMER_ID

### Vercel (Frontend)

- **Project URL:** goreportpilot.vercel.app
- **Root directory:** `frontend`
- **Framework:** Next.js (auto-detected)

**Frontend environment variables:** NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL, NEXT_PUBLIC_APP_URL

### Supabase

- **Project URL:** https://kbytzqviqzcvfdepjyby.supabase.co
- **Auth settings:** Site URL and redirect URLs configured for both localhost and production
- RLS policies active on all 12 tables

### DNS & Domain (Pending)

- Domain `goreportpilot.com` purchased, DNS not yet pointed
- Plan: `goreportpilot.com` CNAME to Vercel, `api.goreportpilot.com` CNAME to Railway

---

## Section 11: OAuth Redirect URIs

### Google Cloud Console

**Authorized redirect URIs:**
- `http://localhost:3000/api/auth/callback/google-analytics`
- `https://goreportpilot.vercel.app/api/auth/callback/google-analytics`
- `https://goreportpilot.com/api/auth/callback/google-analytics`
- `http://localhost:3000/api/auth/callback/google-ads`
- `https://goreportpilot.vercel.app/api/auth/callback/google-ads`
- `https://goreportpilot.com/api/auth/callback/google-ads`
- `http://localhost:3000/api/auth/callback/search-console`
- `https://goreportpilot.vercel.app/api/auth/callback/search-console`
- `https://goreportpilot.com/api/auth/callback/search-console`

### Meta Developer Portal

**Valid OAuth Redirect URIs:**
- `http://localhost:3000/api/auth/callback/meta-ads`
- `https://goreportpilot.vercel.app/api/auth/callback/meta-ads`
- `https://goreportpilot.com/api/auth/callback/meta-ads`

### Supabase Auth

**Site URL:** https://goreportpilot.vercel.app
**Redirect URLs:** localhost:3000, goreportpilot.vercel.app, goreportpilot.com

---

## Section 12: Development Workflow

### How Development Works

1. Saurabh writes detailed feature prompts (numbered PROMPT-1 through PROMPT-32+)
2. Prompts are pasted into Claude Code (Opus 4.6 for complex/systemic tasks, Sonnet 4.6 for simple fixes)
3. Claude Code reads codebase, makes changes, runs verification
4. Saurabh reviews, tests locally, provides feedback
5. Changes are committed and pushed via Claude Code or manually

### Commands

**Frontend dev server:** `cd frontend && npm run dev` (port 3000)
**Backend dev server:** `cd backend && venv\Scripts\activate && uvicorn main:app --reload --port 8000`
**TypeScript check:** `cd frontend && npx tsc --noEmit`
**ESLint check:** `cd frontend && npx next lint`

### Rules

- Claude Code NEVER modifies .env or .env.local files
- Claude Code NEVER starts dev servers
- Database changes are done manually in Supabase Dashboard SQL Editor
- All git pushes auto-deploy to Vercel (30-60s) and Railway (2-5min)

---

## Section 13: Prompt History

| # | Description | Model |
|---|-------------|-------|
| 1 | Initial project scaffold (monorepo, Next.js 14, FastAPI) | Opus |
| 2 | Supabase schema and RLS policies (8 tables, 28 policies) | Opus |
| 3 | Supabase Auth (signup, login, logout, protected routes) | Opus |
| 4 | Dashboard layout (sidebar, header, navigation) | Opus |
| 5 | Client CRUD (create, list, get, update, soft-delete) | Opus |
| 6 | Landing page (10 sections: hero, problem, features, pricing, FAQ, CTA) | Opus |
| 7 | Mock data service (GA4 + Meta Ads realistic fake data) | Opus |
| 8 | AI narrative engine (GPT-4o, 4 tones, structured JSON output) | Opus |
| 9 | Chart generator (matplotlib, 19 chart types, 3 themes, 300 DPI) | Opus |
| 10 | PowerPoint generator (python-pptx, 8-slide branded deck) | Opus |
| 11 | PDF generator (ReportLab fallback) | Opus |
| 12 | Report API endpoints (generate, list, get, download PPTX/PDF) | Opus |
| 13 | Report preview UI (KPI cards, narrative sections, download buttons) | Opus |
| 14 | GA4 OAuth (consent -> callback -> token exchange -> property listing -> real data) | Opus |
| 15 | Meta Ads OAuth (Facebook login -> token exchange -> ad account listing) | Opus |
| 16 | Token encryption (AES-256-GCM) | Opus |
| 17 | Currency handling (dynamic symbols across AI, charts, PDF, PPTX, frontend) | Opus |
| 18 | Connection management (save, list, delete, platform normalization) | Opus |
| 19 | 19-slide template system with slide pool architecture | Opus |
| 20 | Google Ads OAuth + Search Console OAuth | Opus |
| 21 | CSV upload system (per-report data source, modal with templates) | Opus |
| 22 | Multi-CSV slide duplication system (save-reload cycle, slide reordering) | Opus |
| 23 | Systemic robustness + bulletproof CSV parser rewrite | Opus |
| 24 | Three production fixes: CSV chart overlap, dual-chart expansion, brand names | Opus |
| 25 | Template geometry audit, fix at source, chart thresholds | Opus |
| 26 | Chart sizing: CSV chart centering (8"), type-aware dual-chart expansion | Opus |
| 27 | Chat handover document generation | Opus |
| 28 | Report customization, editing, email delivery, scheduled reports, white-label, settings, billing, legal pages, dashboard, sharing, 6 visual templates | Opus |
| 29 | Demo data system, 6 PPTX template creation, multi-language, KPI scoring | Opus |
| 30 | Production deployment preparation (Vercel + Railway, env-aware config) | Opus |
| 31 | GoReportPilot logo implementation (SVG wordmark, favicon, brand rename) | Opus |
| 32 | This comprehensive project report | Opus |

Additional fix prompts between 30-32: Dockerfile libgl1 fix, COPY paths fix, ESLint errors fix, dashboard stats 500 fix, OAuth callback routes for Google Ads/Search Console.

---

## Section 14: Known Issues & Bugs

### Fixed Issues

| Issue | Root Cause | Fix | File |
|-------|-----------|-----|------|
| Dashboard stats 500 with zero clients | `.in_("client_id", ["none"])` passed invalid UUID | Skip connections query when client_ids empty | `routers/dashboard.py` |
| CSV slide content corruption | python-pptx orphaned SlidePart name collision | Save-reload cycle after deletion | `services/report_generator.py` |
| Only 1 CSV slide from N uploads | Architecture only handled first source | Multi-slide duplication system | `services/report_generator.py` |
| PDF always "unavailable" | Silent exception swallowing | Per-exception logging | `services/report_generator.py` |
| CSV chart too wide (11.7") | Template placeholder was full-slide width | Cap at 8.0" EMU, center | `services/chart_generator.py` |
| Pie chart stretched when solo | Expansion code merged both bounding boxes | Type detection via PIE_CHART_HINTS | `services/report_generator.py` |
| Chart overlapping KPI cards | Template chart started above KPI bottom | Fixed all 6 templates at source | `templates/pptx/*.pptx` |
| Duplicate narrative on slides 4+5 | Narrative map hit wrong slides | Removed from map, leftover cleanup | `services/report_generator.py` |
| React Strict Mode double OAuth | useEffect ran twice, cleared sessionStorage | useRef guard in google-callback page | `integrations/google-callback/page.tsx` |
| Google Ads/Search Console OAuth 404 | Missing frontend API route handlers | Created route.ts files | `api/auth/callback/google-ads/route.ts` |
| Vercel ESLint build failures | Unused imports/vars, unescaped entities | Removed unused, escaped entities | Multiple frontend files |
| Dockerfile libgl1-mesa-glx | Package renamed in Debian Trixie | Changed to libgl1 | `backend/Dockerfile` |

### Open Issues

| Issue | Details | Status |
|-------|---------|--------|
| Users can sign in without email confirmation | Supabase confirmation enabled but not enforced at login | Unfixed -- needs Supabase config change |
| No forgot password flow | No "Forgot password?" link on login page | Not built |
| Supabase sends unbranded emails | Confirmation/reset emails use default Supabase templates | Not customized |
| Google Ads invalid_grant on test account | Expected -- test email has no Ads accounts | Not a bug |
| LibreOffice not in PATH on Windows | Local dev must install and add to PATH manually | Documented workaround |
| Website Engagement slide missing narrative | No specific narrative section for this slide | Low priority |
| Cover slide shows "Your Agency" default | Agency name not flowing to cover slide from profile | Needs fix |
| Scheduled reports need continuous process | APScheduler runs in FastAPI lifespan, works on Railway but not for one-off local runs | Works in production |
| Google OAuth in "Testing" mode | Only test users can OAuth until verification submitted | Needs Google review (2-6 weeks) |
| Meta App Review pending | ads_read permission not yet approved | Needs Meta review (1-4 weeks) |

---

## Section 15: What's Remaining

### Must Do (Before Public Launch)

- [ ] Custom domain DNS setup (goreportpilot.com --> Vercel, api.goreportpilot.com --> Railway)
- [ ] Forgot password flow (Supabase reset email + frontend page)
- [ ] Email confirmation enforcement (block login until confirmed)
- [ ] Supabase email template branding (custom HTML for confirmation/reset emails)
- [ ] Google OAuth production verification (submit privacy policy, terms, scope justification)
- [ ] Meta App Review for ads_read permission
- [ ] Update Supabase Auth Site URL to production domain

### Should Do (First Week After Launch)

- [ ] Razorpay account setup + create 6 subscription plans + paste plan IDs into Railway env vars
- [ ] Resend account + domain verification (goreportpilot.com DNS records)
- [ ] Test report email delivery end-to-end
- [ ] Agency name flowing to report cover slide from profile settings
- [ ] Dunning emails for failed payments (webhook exists, email not wired)

### Nice to Have (Post-Launch)

- [ ] Multi-language testing (Japanese, Arabic, Chinese PDFs via LibreOffice)
- [ ] Rich text custom sections with image upload (editor exists, image embedding in PPTX needs work)
- [ ] Website Engagement narrative text section
- [ ] CSV chart mixed-unit scaling fix (% vs $ on same chart)
- [ ] Delete account flow (danger zone in settings)
- [ ] Loading skeleton states on all data-fetching pages

---

## Section 16: Cost Analysis

### Per-Report Cost

| Component | Cost | Notes |
|-----------|------|-------|
| GPT-4.1 input | ~$0.005 | ~2K tokens of data + prompt |
| GPT-4.1 output | ~$0.015 | ~1K tokens of narrative |
| Compute (Railway) | ~$0.001 | Chart generation + PPTX build |
| PDF conversion | ~$0.001 | LibreOffice subprocess |
| **Total per report** | **~$0.022** | |

### Monthly Cost at Scale

| Reports/Month | AI Cost | Railway ($5 base) | Total Variable |
|--------------|---------|-------------------|---------------|
| 50 | $1.10 | $5.00 | ~$6.10 |
| 200 | $4.40 | $5.00 | ~$9.40 |
| 500 | $11.00 | $10.00 | ~$21.00 |
| 1,000 | $22.00 | $15.00 | ~$37.00 |

### Fixed Monthly Costs

| Service | Cost |
|---------|------|
| Supabase (free tier) | $0 |
| Railway (Hobby) | $5/mo + usage |
| Vercel (free tier) | $0 |
| Domain (annual) | ~$12/year |
| **Total fixed** | **~$6/mo** |

### GPT-4.1 vs GPT-4o Cost Comparison

GPT-4.1 is roughly 30-50% cheaper than GPT-4o for the same quality of narrative output, with better instruction-following (fewer re-runs needed). The migration reduced per-report AI cost from ~$0.04 to ~$0.02.

### Breakeven

With fixed costs of ~$6/mo, breakeven requires just 1 paying customer on Starter ($19/mo). At 10 Pro customers ($39/mo = $390/mo revenue), the margin is >95%.

---

## Section 17: Test Account & Sample Data

### Development Account

- **Email:** sapienbotics@gmail.com
- **Role:** Original developer account with full access

### Production Test Account

- **Email:** biotaction.saurabh@gmail.com
- **Role:** Used for production testing on goreportpilot.vercel.app

### Test Client: Videogenie

- **GA4:** Connected (property linked to sapienbotics@gmail.com)
- **Meta Ads:** Connected (test ad account)
- **Search Console:** Connected (sc-domain:videogenie.tech)
- **Google Ads:** No accounts available on test email (invalid_grant expected)

### How to Generate a Test Report

1. Log in at goreportpilot.vercel.app with test credentials
2. Go to Dashboard --> Clients --> Select "Videogenie"
3. Click "Reports" tab
4. Set date range (e.g., last 30 days)
5. Select visual template (e.g., "Modern Clean")
6. Click "Generate Report"
7. Wait ~15-30 seconds for AI + charts + PPTX/PDF
8. Download PPTX or PDF from the report preview page

---

## Section 18: Security Checklist

| Item | Status | Notes |
|------|--------|-------|
| OAuth tokens encrypted at application level (AES-256-GCM) | DONE | `services/encryption.py` |
| Encryption key in env vars only, never in DB | DONE | `TOKEN_ENCRYPTION_KEY` |
| Tokens never exposed to frontend | DONE | Frontend only sees `token_handle` |
| RLS on all tables | DONE | 28+ policies across 12 tables |
| JWT verification on all authenticated endpoints | DONE | `middleware/auth.py` |
| CORS restricted to FRONTEND_URL | DONE | `main.py` |
| httpOnly cookies for auth (Supabase) | DONE | Supabase SSR handles this |
| No secrets in code | DONE | All via .env |
| No console.log with sensitive data | DONE | |
| prompt=consent&access_type=offline always set | DONE | Guarantees refresh token |
| Token refresh before API calls | DONE | In GA4/Meta/Ads service files |
| Meta long-lived token upgrade | DONE | Short --> long in callback |
| token_expires_at stored for monitoring | DONE | connections table |
| Service role key never exposed to frontend | DONE | Backend only |
| Plan enforcement on client creation | DONE | `can_create_client()` check |
| Webhook signature verification (Razorpay) | DONE | `razorpay_service.py` |
| IP masking on shared report views | DONE | First 2 octets only |
| Password hashing for shared links | DONE | bcrypt in `routers/shared.py` |
| XSS prevention in shared report display | PARTIAL | React auto-escapes, but custom HTML sections need review |
| Rate limiting on public endpoints | NOT DONE | No rate limiting implemented |
| CSRF protection | NOT DONE | SameSite cookies provide partial protection |
| Content Security Policy headers | NOT DONE | Not configured |
| Input validation on all endpoints | DONE | Pydantic models validate all requests |
| SQL injection prevention | DONE | Supabase client uses parameterized queries |
| File upload size limits | DONE | 2MB logos, 5MB custom images, 1MB CSV |
| Binary file rejection in CSV parser | DONE | Detects xlsx, pdf, images |

---

*This document was generated on April 4, 2026. It reflects the complete state of the GoReportPilot codebase at commit `08b40f7` on the `main` branch.*
