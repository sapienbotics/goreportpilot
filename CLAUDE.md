# CLAUDE.md — GoReportPilot Project Instructions

## Project Overview
**GoReportPilot** — AI-powered client reporting tool for digital marketing agencies and freelancers.
Automates pulling data from GA4, Meta Ads, Google Ads, and Search Console, generating AI-written narrative insights via GPT-4.1, and exporting branded reports as PowerPoint and PDF.

**Founder:** Saurabh Singh / SapienBotics (Bareilly, Uttar Pradesh, India)
**Legal Entity:** Sole proprietorship under Richa Singh, trade name Sahaj Bharat (GSTIN: 09CYVPS3328G1ZQ)
**Brand:** SapienBotics (tech brand), GoReportPilot (product)
**Stage:** LIVE in production, pre-launch (awaiting Google OAuth verification + Meta App Review)

**Live URLs:**
- Frontend: https://goreportpilot.com (Vercel)
- Backend: https://goreportpilot-production.up.railway.app (Railway)
- GitHub: sapienbotics/goreportpilot (auto-deploy on push to main)
- Supabase: kbytzqviqzcvfdepjyby.supabase.co

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Frontend | Next.js (App Router) | 14.x | Web app + marketing pages |
| Frontend Language | TypeScript | 5.x | Type safety |
| CSS Framework | Tailwind CSS | 3.x | Styling |
| UI Components | shadcn/ui | latest | Pre-built accessible components |
| Backend API | Python + FastAPI | Python 3.12, FastAPI 0.110+ | OAuth, data pulls, AI, report gen |
| Database | Supabase (PostgreSQL) | latest | Data storage, RLS, auth |
| Auth | Supabase Auth | (included) | Email/password signup/login, JWT |
| AI | OpenAI GPT-4.1 | latest | Narrative commentary generation |
| Report Gen | python-pptx 0.6.23+ | latest | PowerPoint generation |
| Report Gen | LibreOffice (headless) | 7.x+ | PPTX→PDF conversion (all Unicode scripts) |
| Report Gen | ReportLab 4.x | latest | PDF fallback (Latin languages only) |
| Charts | matplotlib 3.8+ | latest | Static chart images for reports |
| Fonts | Google Noto fonts | latest | Full script coverage (Devanagari, CJK, Arabic) |
| Scheduling | APScheduler | latest | Background scheduled report generation |
| Email | Resend | latest | Transactional email (reports@goreportpilot.com) |
| Email (receiving) | Zoho Mail | free tier | support@, info@ aliases |
| Frontend Hosting | Vercel | — | Next.js deployment |
| Backend Hosting | Railway | — | FastAPI + LibreOffice Docker |
| File Storage | Supabase Storage | — | Logos bucket (public) |
| Report Files | Local FS (Railway) | — | Ephemeral — regenerate on 410 |
| Payments | Razorpay | latest | Subscription billing (12 plans, dual INR/USD) |
| Token Encryption | cryptography (Python) | 42.x+ | AES-256-GCM for OAuth tokens |
| Analytics | GA4 | G-GMTY15QRRZ | Cookie-consent gated |
| DNS | Namecheap + Vercel | — | goreportpilot.com |
| Rate Limiting | slowapi | latest | Key endpoint protection |

---

## Local Dev Environment

- **OS:** Windows 11
- **Project root:** `F:\Sapienbotics\ClaudeCode\reportpilot\`
- **Python:** 3.12 (venv at `backend\venv\`)
- **Node:** 20+
- **LibreOffice:** `C:\Program Files\LibreOffice\program\soffice.exe`

### Running Locally

```bash
# Backend
cd backend && python -m uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

**Access:** http://localhost:3000

---

## Critical Rules — READ BEFORE EVERY PROMPT

1. **NEVER modify .env or .env.local files** — Claude Code must not write to these
2. **NEVER auto-start dev servers** — Saurabh starts them manually
3. **ALWAYS run `cd frontend && npx tsc --noEmit` after frontend changes** — must pass with zero errors
4. **Database changes run manually in Supabase SQL Editor** — never via Supabase CLI
5. **Single source of truth for pricing:** Always import from `backend/services/plans.py` — never hardcode amounts
6. **Systemic over narrow:** Fix all cases generically, not targeted patches for specific instances
7. **Production = MVP:** No quality distinction — potential clients may evaluate at any time
8. **Incremental safety:** When risk of breaking existing functionality, split into safe incremental steps
9. **Git commit after every change set** with descriptive message

---

## Project Structure

```
reportpilot/
├── CLAUDE.md                              # THIS FILE
├── frontend/
│   ├── src/app/
│   │   ├── layout.tsx                     # Root layout (fonts, metadata, Toaster, ProgressBar)
│   │   ├── page.tsx                       # Landing page (hero, features, pricing, FAQ, CTA)
│   │   ├── sitemap.ts                     # Dynamic sitemap
│   │   ├── robots.ts                      # Robots.txt
│   │   ├── login/page.tsx
│   │   ├── signup/page.tsx
│   │   ├── privacy/page.tsx
│   │   ├── terms/page.tsx
│   │   ├── contact/page.tsx
│   │   ├── refund/page.tsx
│   │   ├── shared/[hash]/page.tsx         # Public shared report viewer
│   │   ├── api/auth/callback/
│   │   │   ├── route.ts                   # Supabase auth callback
│   │   │   ├── google-analytics/route.ts
│   │   │   ├── google-ads/route.ts
│   │   │   ├── meta-ads/route.ts
│   │   │   └── search-console/route.ts
│   │   ├── dashboard/
│   │   │   ├── layout.tsx                 # Auth guard + DashboardShell + ProgressBar
│   │   │   ├── page.tsx                   # Dashboard home (stats, onboarding checklist)
│   │   │   ├── loading.tsx                # Loading spinner
│   │   │   ├── clients/
│   │   │   │   ├── page.tsx               # Client list
│   │   │   │   ├── loading.tsx
│   │   │   │   └── [clientId]/page.tsx    # Client detail (5 tabs: Overview, Integrations, Reports, Schedules, Settings)
│   │   │   ├── reports/
│   │   │   │   ├── page.tsx               # All reports list
│   │   │   │   ├── loading.tsx
│   │   │   │   └── [reportId]/page.tsx    # Report preview/edit/send/share/download
│   │   │   ├── integrations/
│   │   │   │   ├── page.tsx               # Integration hub
│   │   │   │   ├── google-callback/page.tsx
│   │   │   │   └── meta-callback/page.tsx
│   │   │   ├── settings/page.tsx          # Settings (5 tabs: Account, Branding, AI, Email, Notifications)
│   │   │   ├── settings/loading.tsx
│   │   │   ├── billing/page.tsx           # Billing + Razorpay checkout
│   │   │   └── billing/loading.tsx
│   │   └── admin/
│   │       ├── layout.tsx                 # Admin guard (profiles.is_admin)
│   │       ├── page.tsx                   # Admin overview
│   │       └── analytics/page.tsx         # Admin analytics dashboard
│   ├── src/components/
│   │   ├── ui/                            # shadcn/ui base components
│   │   ├── dashboard/                     # Stat cards, activity feed, onboarding
│   │   ├── clients/                       # Client cards, forms, tabs
│   │   │   └── tabs/SchedulesTab.tsx      # Schedule management
│   │   ├── reports/
│   │   │   └── CSVUploadForReport.tsx     # CSV upload in report generation flow
│   │   ├── billing/UpgradePrompt.tsx      # Reusable upgrade gate
│   │   ├── landing/CookieConsent.tsx      # GDPR cookie banner
│   │   ├── AnalyticsProvider.tsx          # GA4 gating on consent
│   │   └── Logo.tsx, LogoIcon.tsx         # SVG logo components
│   ├── src/lib/
│   │   ├── api.ts                         # Axios wrapper for backend
│   │   ├── detect-currency.ts             # Timezone-based INR/USD detection
│   │   └── supabase/                      # Client + server Supabase helpers
│   └── middleware.ts                      # Route protection
│
├── backend/
│   ├── main.py                            # FastAPI app, CORS, router includes
│   ├── config.py                          # Pydantic Settings (auto-derives redirect URIs from FRONTEND_URL)
│   ├── Dockerfile                         # Python 3.12-slim + LibreOffice + Noto fonts
│   ├── routers/
│   │   ├── auth.py                        # OAuth flows (GA4, Meta, Google Ads, Search Console)
│   │   ├── clients.py                     # Client CRUD
│   │   ├── connections.py                 # Connection management
│   │   ├── reports.py                     # Report generation, list, download, send, share, regenerate
│   │   ├── admin.py                       # Admin endpoints
│   │   ├── admin_analytics.py             # Admin analytics API
│   │   └── webhooks.py                    # Razorpay webhooks
│   ├── services/
│   │   ├── google_analytics.py            # GA4 Data API client (6 API calls)
│   │   ├── meta_ads.py                    # Meta Marketing API client
│   │   ├── google_ads.py                  # Google Ads API client (MCC: 815-247-5096)
│   │   ├── search_console.py             # Search Console API client
│   │   ├── ai_narrative.py                # GPT-4.1 prompt engine (4 tones, 13 languages)
│   │   ├── report_generator.py            # python-pptx orchestration, PPTX→PDF
│   │   ├── chart_generator.py             # matplotlib (19 chart types, 3 themes, 300 DPI)
│   │   ├── slide_selector.py              # Smart slide selection + KPI scoring
│   │   ├── csv_parser.py                  # Production-grade CSV parser
│   │   ├── text_formatter.py              # Rich text parsing for custom sections
│   │   ├── email_service.py               # Resend SDK wrapper
│   │   ├── encryption.py                  # AES-256-GCM token encryption
│   │   ├── plans.py                       # Pricing source of truth (3 plans × 2 currencies × 2 cycles)
│   │   ├── scheduler.py                   # APScheduler for scheduled reports
│   │   └── supabase_client.py             # Supabase admin client
│   ├── middleware/
│   │   ├── auth.py                        # JWT verification
│   │   └── plan_enforcement.py            # Plan limit checks
│   ├── templates/pptx/                    # 6 visual templates (19 slides each)
│   │   ├── modern_clean.pptx
│   │   ├── dark_executive.pptx
│   │   ├── colorful_agency.pptx
│   │   ├── bold_geometric.pptx
│   │   ├── minimal_elegant.pptx
│   │   └── gradient_modern.pptx
│   └── scripts/                           # Audit and verification scripts
│
├── supabase/migrations/                   # 001-012 all executed
│
└── docs/
    ├── HANDOVER-APRIL-11-2026.md          # Comprehensive project state
    ├── CLAUDE.md                          # THIS FILE
    ├── MARKETING-VIDEO-PRODUCTION-GUIDE.md
    ├── PRICING-STRATEGY-2026.md
    ├── COMPETITOR-FEATURE-MATRIX-2026.md
    └── DEPLOYMENT-GUIDE.md
```

---

## Database Schema (12 Migrations)

| Table | Purpose |
|---|---|
| profiles | User profiles (extends auth.users) — plan, agency branding, timezone |
| clients | Client records — name, industry, logo, AI tone, language, report_config |
| connections | OAuth connections — platform, encrypted tokens, account IDs |
| reports | Generated reports — raw_data, ai_narrative, user_edits, metadata |
| data_snapshots | Cached API data per report |
| report_templates | Report section configuration |
| subscriptions | Billing — plan, status, Razorpay IDs, trial management |
| payment_history | Payment records |
| shared_reports | Shareable report links with optional password/expiry |
| report_views | View tracking for shared links |
| scheduled_reports | Recurring report configuration |
| admin_activity_log | Admin actions audit trail |
| gdpr_requests | GDPR compliance requests |

RLS enabled on ALL tables. Users can only access their own data.

---

## Pricing (source: backend/services/plans.py)

| Plan | Monthly USD | Annual USD | Monthly INR | Annual INR | Client Limit |
|---|---|---|---|---|---|
| Starter | $19 | $15/mo | ₹999 | ₹799/mo | 5 |
| Pro | $39 | $31/mo | ₹1,999 | ₹1,599/mo | 15 |
| Agency | $69 | $55/mo | ₹3,499 | ₹2,799/mo | Unlimited |

Currency auto-detected via timezone (Asia/Kolkata → INR, else USD). 12 Razorpay plans configured.
Trial: 14 days, Pro-level access, 5-report limit, "Powered by GoReportPilot" badge.

---

## Feature Inventory (Complete)

### Built & Shipped ✅
- Auth: email/password, email confirmation, forgot password, account deletion, admin guard
- Client CRUD with logo upload, AI tone, language (13), report_config
- GA4 OAuth + real data pull (6 API calls)
- Meta Ads OAuth + short→long-lived token
- Google Ads OAuth + MCC support
- Search Console OAuth
- CSV upload (production-grade parser, 5 templates)
- AI narrative via GPT-4.1 (4 tones, 13 languages, 6 sections)
- PPTX generation: 6 visual templates, 19 chart types, smart slide selection
- PDF via LibreOffice (all scripts) + ReportLab fallback (Latin only)
- Report preview with inline editing, per-section regenerate
- Send to client via email (Resend)
- Share via public link (optional password + expiry + view tracking)
- Scheduled reports (weekly/biweekly/monthly, timezone, auto-send)
- White-label: agency logo, brand color, client logo, "Powered by" badge on Starter
- Plan enforcement: feature gating, client limits, trial management
- Razorpay billing: dual currency, checkout, webhooks, payment history
- Admin dashboard: analytics, user management, GDPR
- Landing page: hero, features (9 cards), pricing, FAQ (10 questions), SEO
- Cookie consent + GA4 tracking
- Navigation progress bar + loading skeletons
- Rate limiting on public endpoints
- Legal pages: privacy, terms, refund, contact

### Pending
- Google OAuth production verification (submitted, awaiting approval)
- Meta App Review (submitted, review in progress ~April 18)
- Multi-language slide titles/KPI labels/footer (currently English-only — narrative translated)
- Annual pricing as default display on landing page
- PPTX fixes: sparkline ordering, agency logo bounding box, traffic label capitalization
- Demo video polish
- Marketing outreach launch

---

## OAuth Integrations

| Platform | Status | Scopes |
|---|---|---|
| GA4 | ✅ Production (pending verification) | analytics.readonly |
| Meta Ads | ✅ Production (pending review) | ads_read, ads_management, business_management, pages_read_engagement, pages_show_list, public_profile |
| Google Ads | ✅ Production | adwords scope + MCC (815-247-5096) |
| Search Console | ✅ Production | webmasters.readonly |

All tokens encrypted with AES-256-GCM. Redirect URIs auto-derived from FRONTEND_URL via config.py.

---

## Environment Variables

### Backend (.env)
```
SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY
OPENAI_API_KEY (GPT-4.1)
TOKEN_ENCRYPTION_KEY (AES-256-GCM)
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
META_APP_ID, META_APP_SECRET
GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_LOGIN_CUSTOMER_ID
RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET
RESEND_API_KEY
FRONTEND_URL (https://goreportpilot.com)
BACKEND_URL (https://goreportpilot-production.up.railway.app)
```

### Frontend (.env.local)
```
NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
NEXT_PUBLIC_API_URL, NEXT_PUBLIC_APP_URL
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-GMTY15QRRZ
```

---

## What NOT To Do

1. **DO NOT expose OAuth tokens to the frontend.** Tokens live in backend only.
2. **DO NOT use `localStorage` for auth tokens.** Supabase handles via httpOnly cookies.
3. **DO NOT skip Row-Level Security.** Every table with user data has RLS policies.
4. **DO NOT confuse Google SSO with GA4 OAuth.** Separate flows, different scopes.
5. **DO NOT use the `requests` library in FastAPI.** Use `httpx` with async.
6. **DO NOT store encryption key in database.** Environment variable only.
7. **DO NOT modify .env files via Claude Code.** Manual only.
8. **DO NOT start dev servers automatically.** Saurabh starts manually.
9. **DO NOT include `prompt=consent` only sometimes for Google OAuth.** Always include `prompt=consent&access_type=offline`.
10. **DO NOT assume Meta tokens last forever.** ~60 days. Store `token_expires_at`.
11. **DO NOT log OAuth tokens or encryption keys.** Log connection IDs and status only.
12. **DO NOT import from relative paths in frontend.** Use `@/` alias.
13. **DO NOT hardcode pricing.** Import from `backend/services/plans.py`.
14. **DO NOT forget LibreOffice for PDF.** Primary path for all Unicode scripts. ReportLab is Latin-only fallback.

---

## Development Workflow

1. Saurabh describes requirements in Claude.ai chat
2. Claude.ai writes detailed numbered prompts (PROMPT-N format)
3. Saurabh pastes into Claude Code (Opus 4.6 for complex, Sonnet 4.6 for simple)
4. Saurabh reports back with screenshots/terminal output
5. Claude.ai diagnoses and writes fix prompts
6. DB changes run manually in Supabase SQL Editor
7. Always run `cd frontend && npx tsc --noEmit` after frontend changes

---

## Prompt History

Prompts 1-64: Core product build (March-April 2026)
Prompt 65-69: Marketing video production
Prompt 70: Trial watermark removal + navigation loading UX
Prompt 71: Multi-language translation (pending)

See `docs/HANDOVER-APRIL-11-2026.md` for detailed prompt-by-prompt history.

---

## Accounts & Credentials

| Service | Account |
|---|---|
| Google Cloud | sapienbotics@gmail.com |
| Meta Developer | sapienbotics@gmail.com |
| Supabase | sapienbotics@gmail.com |
| Railway | sapienbotics@gmail.com |
| Vercel | sapienbotics@gmail.com |
| Razorpay | Proprietorship (Sahaj Bharat) |
| Resend | reports@goreportpilot.com (DKIM verified) |
| Namecheap | goreportpilot.com |
| GitHub | sapienbotics/goreportpilot |

---

*Updated: April 13, 2026. 71 prompts executed.*
