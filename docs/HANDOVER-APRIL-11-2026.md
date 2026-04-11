# GoReportPilot — Project Handover (April 11, 2026)

> **Purpose:** Single-document handover that brings any new Claude session fully up to speed on GoReportPilot without needing to read anything else. This is the authoritative snapshot as of April 11, 2026.
>
> **Supersedes:** `docs/CHAT-HANDOVER-MARCH-2026.md` (March 21, 2026) and `docs/COMPLETE-PROJECT-REPORT.md` (April 4, 2026). Those remain accurate for what they covered, but this document reflects the state after the April 10–11 sprint that added landing-page overhaul, GA4 tracking, cookie consent, admin analytics, and dozens of report-quality improvements.
>
> **Written in parts.** This file is Part 1 (Sections 1–3). Parts 2 and 3 will be appended in subsequent commits covering sections 4–18 (pricing, schema, OAuth, DNS, env vars, workflow, prompt history, status, pending, report quality, landing page, marketing, decisions, accounts, file paths).

**Date:** April 11, 2026
**Founder:** Saurabh Singh (Bareilly, Uttar Pradesh) — trading as **Sahaj Bharat** proprietorship, brand **SapienBotics**
**Stage:** MVP complete and deployed to production. Pre-launch — waiting on Google OAuth verification + Meta App Review.

---

## Part 1 — Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technical Architecture](#2-technical-architecture)
3. [Feature Inventory](#3-feature-inventory)

---

## 1. Project Overview

### 1.1 Product identity

| Field | Value |
|---|---|
| **Product name** | GoReportPilot |
| **Brand** | SapienBotics (owned by Sahaj Bharat proprietorship) |
| **Domain** | `goreportpilot.com` (migrated from `reportpilot.co` April 7, commit `78a10b2`) |
| **Hero H1** | *"Branded client reports, written by AI."* |
| **Subheadline** | *"GoReportPilot connects GA4, Meta Ads, Google Ads, and Search Console, writes the narrative, and delivers a white-label PPTX + PDF — in under 5 minutes."* |
| **Pre-heading label** | *"Client Reporting Platform"* |
| **Primary CTA** | *"Start My Free Trial"* (first-person, documented ~90% CTR lift vs second-person) |

### 1.2 Elevator pitch

GoReportPilot is an AI-powered client reporting tool for digital marketing agencies and freelancers. It connects to GA4, Meta Ads, Google Ads, and Google Search Console via OAuth (plus CSV upload for any other platform), generates multi-paragraph narrative insights with GPT-4.1, and exports branded PowerPoint + PDF reports in under 5 minutes. Agencies email reports to their clients with one click or schedule them to auto-deliver weekly/biweekly/monthly.

**The one-sentence differentiator:** GoReportPilot is the only affordable tool ($19–$69/month) that combines AI-written narrative with editable PowerPoint export. Competitors ship dashboards; only NinjaCat (at $3,000+/month enterprise contracts) ships the same combination.

### 1.3 Target audience

1. **Indian digital marketing agencies (5–50 clients)** priced out of Western tools. ₹999/month entry beats AgencyAnalytics ($179/mo ≈ ₹15,000) by 15×.
2. **Global freelance marketers** (1–10 clients) billing at $50–$150/hour. At $19/month, one saved billable hour pays for the whole year.
3. **Small international agencies (5–15 clients)** currently paying $179–$500/month for AgencyAnalytics/DashThis/Whatagraph and frustrated by per-client surcharges, missing PPTX export, and AI as a paid add-on.

Not a target: enterprise buyers needing SSO/SAML, agencies needing 80+ integrations (we ship 4 OAuth + CSV upload for everything else), or dashboard-first workflows.

### 1.4 Four core differentiators

1. **AI narrative included on every plan.** Full 6-section commentary (executive summary, channel breakdowns, key wins, concerns, next steps, recommendations), written by GPT-4.1 with SCQA framework structure. Competitors charge AI as an add-on or don't offer it.
2. **Editable PowerPoint export on Pro+.** `.pptx` files agencies can tweak in PowerPoint and present. No affordable competitor ships this.
3. **Flat pricing.** Pay by plan, not by client × report × source. No per-client surcharges, no hidden AI add-on, no per-dashboard fees.
4. **5–10× cheaper** than mid-market. $39/mo for 15 clients vs. AgencyAnalytics $179/mo for 10 clients.

### 1.5 Three-stakeholder model

- **Developer** (Saurabh / SapienBotics) — builds the platform, holds admin account, configures Razorpay + OAuth providers.
- **Agency user** — signs up at goreportpilot.com, adds clients, connects data sources, generates and delivers reports.
- **End clients** — receive branded reports via email. **They never log into GoReportPilot.** On Pro+ white-labelled plans they see zero GoReportPilot branding.

This model governs every UX decision: the dashboard is for agency users; the reports are for end clients; GoReportPilot itself is invisible to the end client.

### 1.6 Live URLs

| Purpose | URL |
|---|---|
| Production frontend | `https://goreportpilot.com` |
| Vercel preview | `https://goreportpilot.vercel.app` |
| Production backend API | `https://goreportpilot-production.up.railway.app` |
| Health check | `https://goreportpilot-production.up.railway.app/health` |
| FastAPI interactive docs | `https://goreportpilot-production.up.railway.app/docs` |
| GitHub repository | `https://github.com/sapienbotics/goreportpilot` (branch: `main`) |
| Supabase project | `https://kbytzqviqzcvfdepjyby.supabase.co` |
| GA4 property | `G-GMTY15QRRZ` (installed April 11, gated on cookie consent) |

### 1.7 Legal entity

| Field | Value |
|---|---|
| Legal entity | Sahaj Bharat (sole proprietorship, India) |
| Brand | SapienBotics |
| Product | GoReportPilot |
| Registered address | Bareilly, Uttar Pradesh, India (updated from New Delhi April 6, commit `e85ca9d`) |
| Founder | Saurabh Singh |
| Primary contact | `hello@goreportpilot.com` |
| Dev account | `sapienbotics@gmail.com` |
| GSTIN | [UNVERIFIED — not in docs; Saurabh has the number] |

**Local project root:** `F:\Sapienbotics\ClaudeCode\reportpilot\` (Windows dev machine). Master instruction file: `CLAUDE.md` at repo root.

---

## 2. Technical Architecture

### 2.1 Frontend

| Layer | Tech | Version | Notes |
|---|---|---|---|
| Framework | Next.js App Router | 14.2.35 | Server components + client islands |
| Language | TypeScript | 5.x | Strict mode |
| Styling | Tailwind CSS | 3.4.x | |
| UI | shadcn/ui | latest | Copy-paste, no vendor lock-in |
| Fonts | Plus Jakarta Sans (headings) + Inter (body) | Google Fonts | `display: swap` |
| Icons | `lucide-react` | 0.577 | Individual imports, tree-shaken |
| HTTP | `axios` | 1.13 | Centralised in `frontend/src/lib/api.ts` |
| Forms | `react-hook-form` + `zod` | 7.71 / 4.3 | |
| Supabase SDK | `@supabase/supabase-js` + `@supabase/ssr` | 2.78 / 0.9 | |
| Toasts | `sonner` | 2.0 | |
| Progress bar | `next-nprogress-bar` | 2.4 | |
| **Hosting** | **Vercel** | — | Auto-deploy on `main` push (~30–60s) |

**Chart library note:** `recharts` is NOT installed despite being referenced in an earlier task spec. All charts on the admin analytics dashboard and the landing page hero are built from pure Tailwind CSS `div`s with percentage widths. This saves ~100KB of client JS that bar charts don't need.

### 2.2 Backend

| Layer | Tech | Version | Notes |
|---|---|---|---|
| Framework | FastAPI | 0.110+ | Async endpoints |
| Language | Python | 3.12+ | Type hints everywhere |
| Settings | `pydantic-settings` | 2.2–2.4 | Loads `backend/.env` |
| Async HTTP | `httpx` | 0.24–0.27 | **Never use `requests`** — sync blocks the event loop |
| Supabase | `supabase` | latest | Service-role key for admin ops |
| OpenAI | `openai` | latest | AsyncOpenAI |
| PPTX | `python-pptx` | 0.6.23+ | Template-based, run-level text replacement |
| **PDF primary** | **LibreOffice headless** | 7.x+ | `soffice --headless --convert-to pdf` — handles all scripts |
| PDF fallback | `reportlab` | 4.1.0 | Latin languages only when LibreOffice unavailable |
| Charts | `matplotlib` | 3.8.3+ | 300 DPI, theme-aware |
| Images | `Pillow` | 10.2 | Logo background removal + image measurement |
| Fonts (PDF) | Google Noto | latest | Full script coverage (Devanagari, CJK, Arabic) |
| CSV | `chardet` | 5.x | Encoding detection |
| Crypto | `cryptography` | 42.0.5 | AES-256-GCM for OAuth tokens |
| Rate limit | `slowapi` | latest | Public + expensive endpoints |
| **Hosting** | **Railway** | — | Builds from `backend/Dockerfile` (~2–5 min) |

**Docker image:** `python:3.12-slim` + `libreoffice-core` + `libreoffice-impress` + `fonts-noto-core` + `fonts-noto-cjk` + `libgl1`. Healthcheck: `/health`, timeout 300s.

**Scheduler loop:** FastAPI lifespan launches a long-lived `_scheduler_loop()` asyncio task checking `scheduled_reports` every **15 minutes** (reduced from 60 min on April 11). Logs `"Scheduler: no due schedules at <iso>"` at INFO level so production can confirm it's alive.

### 2.3 Database

**Provider:** Supabase (PostgreSQL 15)
**Project:** `https://kbytzqviqzcvfdepjyby.supabase.co` (ID: `kbytzqviqzcvfdepjyby`)

- 12 tables, 28+ RLS policies, 15+ indexes, 5 triggers
- **RLS enabled on every table from day 1** — policies restrict `auth.uid() = user_id` (or joined through `clients.user_id` for cascaded tables)
- 13 migrations in `supabase/migrations/`, run manually via Supabase SQL Editor
- Full schema in Part 2 §5

### 2.4 AI narrative pipeline

| Aspect | Detail |
|---|---|
| **Model** | `gpt-4.1` (migrated from `gpt-4o` in commit `ff12cfe` for ~20% cost reduction + better JSON instruction-following) |
| **File** | `backend/services/ai_narrative.py` |
| **Invocation** | `AsyncOpenAI.chat.completions.create()` with `response_format={"type": "json_object"}`, temperature 0.7, max_tokens 2000 |
| **Tones** | 4 presets: `professional`, `conversational` (alias `friendly`), `executive`, `data_heavy` (alias `technical`). Starter plan only gets `professional`; Pro+ gets all 4. |
| **Languages** | 13: English, Spanish, Portuguese, French, German, Italian, Dutch, Hindi, Japanese, Korean, Chinese Simplified, Arabic, Turkish |
| **SCQA structure** | Executive summary enforced to Situation → Complication → Question → Answer in 150 words max |
| **3+3+3 enforcement** | Exactly 3 wins, 3 concerns, 3 next steps. Next-step items must follow the *"Next month we will [action] on [channel], based on [data point], to achieve [expected outcome]"* pattern |
| **Bad-month detection** | `_detect_bad_month()` — when any of `sessions_change`, `users_change`, `conversions_change` drops > 5% MoM, injects a `_BAD_MONTH_INSTRUCTION` clause into the system prompt triggering the four-beat recovery pattern (honest number → context → cause → plan) |
| **chart_insights output key** | Top-level JSON object with per-chart action-title takeaways ≤15 words, used as chart titles in the rendered report |
| **Fallback** | Static `FALLBACK_NARRATIVE` when the API key is missing or the call errors |

### 2.5 Report generation pipeline

```
Agency user clicks "Generate"
 ↓
routers/reports.py::_generate_report_internal()
 ↓
1. Subscription check (expired? trial over 5 reports?)
2. Client ownership check
3. Plan enforcement (clamp AI tone + visual template to plan)
4. Data pull (GA4, Meta, Google Ads, Search Console + CSV in parallel)
5. Sanitize floats → 2dp (`_sanitize_data_for_ai()`)
6. AI narrative (GPT-4.1 with SCQA + 3+3+3 + bad-month)
7. Chart generation (matplotlib, 15+ types, Okabe-Ito palette, action titles from chart_insights)
8. PPTX generation (template-based, 19-slide pool, smart deletion, save-reload cycle)
9. LibreOffice PDF conversion (ReportLab fallback for Latin-only)
10. Persist to reports table + save files to backend/generated_reports/{uuid}/
```

**Template system:** 6 visual `.pptx` templates under `backend/templates/pptx/` (`modern_clean`, `dark_executive`, `colorful_agency`, `bold_geometric`, `minimal_elegant`, `gradient_modern`). Each contains all 19 possible slide types; `slide_selector.py::get_slides_to_delete()` analyses available data and deletes irrelevant slides at render time.

**Multi-CSV slide duplication:** for N CSV sources, the generator finds the template's `csv_data` slide, duplicates it N−1 times via `deepcopy(spTree)`, and reorders the duplicates to sit before Key Wins/Concerns/Next Steps. A **save-reload cycle** (`prs.save(buf); prs = Presentation(buf)`) runs after deletion and before duplication to purge orphaned `SlidePart` objects that would otherwise cause filename collisions.

### 2.6 Chart system

**Library:** `matplotlib` (non-interactive `Agg` backend)
**Size:** 5.6" × 3.0" at 300 DPI (CSV comparison chart: 8.0" × 4.0")
**File:** `backend/services/chart_generator.py`
**Palette:** **Okabe-Ito color-blind-safe** — `#0072B2`, `#D55E00`, `#009E73`, `#CC79A7`, `#E69F00`, `#56B4E9` — applied to all multi-series charts

**Quality layers (April 10–11 improvements):**

- Horizontal-only gridlines (`axes.grid.axis='y'`, `alpha=0.3`, `linewidth=0.5`) + hidden top/right spines + no tick marks (Tufte data-ink ratio)
- Action-titled charts: `title_override` parameter threaded through every `plot_*()` function, fed by AI `chart_insights` with smart 75-char truncation at sentence boundaries
- Chart captions: optional italic one-line takeaway below plot area
- **Sparklines** (`plot_sparkline()`): 2.0" × 0.35" minimal PNG with transparent background, 1.2pt line, dot on latest value, no axes — embedded at fixed 0.25" height on KPI scorecard
- Highlight-one-bar in campaign chart: top performer in brand color, rest muted slate-300
- Direct-labelled traffic sources when ≤4 categories (`"Direct — 1,234"` inline)
- Zero-conversion axis cleanup: force `set_ylim(0,1)` + `set_yticks([0])` when `max(conversions)==0`
- GA4 source label rewrites: `(none)` / `(direct)` → `Direct`, `(not set)` → `Other`, applied upstream + defense-in-depth at chart layer

### 2.7 Email & payments

| System | Provider | Key config |
|---|---|---|
| **Email delivery** | Resend | Sending domain `goreportpilot.com`, default sender `reports@goreportpilot.com`, direct `httpx` POST to `api.resend.com/emails` — no SDK dependency |
| **Payments** | Razorpay | Live mode, INR + USD plans (12 plan IDs total), webhook at `/api/billing/webhooks/razorpay`, events: `subscription.activated/charged/cancelled/paused`, `payment.failed` |
| **Currency detection** | Browser-side | `Intl.DateTimeFormat().resolvedOptions().timeZone` → if timezone contains `Asia/Kolkata`/`Asia/Calcutta` OR `navigator.language` starts with `hi`, show INR; otherwise USD. Shared helper in `frontend/src/lib/detect-currency.ts` with module-level memoisation |

### 2.8 Auth & encryption

**Auth:** Supabase Auth (email/password, JWT in httpOnly cookies via `@supabase/ssr`). Flows: signup with email confirmation, login, logout, forgot password, email confirmation enforcement, admin route guard (`frontend/src/app/admin/layout.tsx` checks `profiles.is_admin` server-side).

**Backend JWT verification:** `backend/middleware/auth.py::get_current_user_id()` calls `supabase.auth.get_user(token)` on every authenticated request.

**Admin guard:** `backend/routers/admin.py::_require_admin()` dependency — checks `profiles.is_admin` and raises 403 if false. Reused by `admin_analytics.py`.

**Token encryption:** OAuth tokens (Google, Meta, Google Ads, Search Console) encrypted with **AES-256-GCM** before storage. File: `backend/services/encryption.py`. Format: `base64(nonce || ciphertext+tag)`. Key stored **only** in `TOKEN_ENCRYPTION_KEY` env var — never in the database. 12-byte random nonce per encryption.

### 2.9 File storage

| Type | Location | Retention |
|---|---|---|
| Agency + client logos, custom section images | Supabase Storage `logos` bucket (public URLs) | Permanent |
| Generated PPTX / PDF / chart PNGs / sparklines | `backend/generated_reports/{report_id}/` (local FS) | **Ephemeral** (Railway restart wipes) |

**Ephemeral implication:** expired files return HTTP 410 `FILES_EXPIRED`, frontend shows "Regenerate Report" button. Regenerate endpoint re-runs the pipeline using stored `raw_data` + `ai_narrative`.

---

## 3. Feature Inventory

Complete list of what's built and shipped. Items marked **April 10–11** are from the most recent sprint.

### 3.1 Auth & user management

| Feature | Status | Notes |
|---|---|---|
| Email + password signup | ✅ | Supabase Auth |
| Email confirmation | ✅ | Enforced at login |
| Login / logout | ✅ | |
| Forgot password flow | ✅ | Commit `1d6d026` |
| Protected routes middleware | ✅ | `frontend/src/middleware.ts` |
| Admin route guard | ✅ | `profiles.is_admin` server-side |
| Account deletion (self-service) | ✅ | Commit `7a19320` |
| Google SSO login | ❌ | Not built (only data-source OAuth) |

### 3.2 Client management

| Feature | Status |
|---|---|
| Client CRUD + soft-delete | ✅ |
| Client logo upload (Supabase Storage) | ✅ |
| Industry, website, goals context fields | ✅ |
| Per-client AI tone override | ✅ |
| Per-client report language (13 options) | ✅ |
| Per-client `report_config` (sections, KPIs, template, visual template, custom section) | ✅ |
| Tabbed detail page (Overview, Integrations, Reports, Schedules, Settings) | ✅ |
| Client limit enforcement per plan | ✅ |

### 3.3 Data integrations

| Integration | Status | Notes |
|---|---|---|
| **Google Analytics 4** | ✅ Production | OAuth + auto-refresh, 6 API calls (sessions, users, sources, pages, devices, bounce rate) |
| **Meta Ads** (Facebook + Instagram) | ✅ Production | OAuth with short→long-lived token upgrade (~60 days) |
| **Google Ads** | ✅ Production | OAuth + MCC (`815-247-5096`), developer token configured |
| **Google Search Console** | ✅ Production | OAuth + `webmasters.readonly` scope |
| **CSV upload** | ✅ Production | Production-grade parser: encoding detection, delimiter detection, binary rejection, unit auto-detection, 35+ brand capitalisation, K/M/B suffixes, European decimals |
| CSV templates | ✅ | 5 downloadable: LinkedIn Ads, TikTok Ads, Mailchimp, Shopify, generic |
| LinkedIn Ads / TikTok / Shopify / HubSpot direct | ❌ | Via CSV upload only |

### 3.4 Report generation (Tier 1 + Tier 2 quality improvements April 10–11)

| Feature | Status |
|---|---|
| **PPTX export** (6 visual templates, 19-slide pool with smart deletion) | ✅ |
| **PDF export** — LibreOffice primary, ReportLab fallback | ✅ |
| 3 detail levels: Full / Summary / Executive Brief | ✅ |
| Smart slide deletion (no empty slides) | ✅ |
| Smart KPI selection (top 6 via `select_kpis()`) | ✅ |
| Multi-CSV slide duplication (save-reload pattern) | ✅ |
| Page footer renumbering | ✅ |
| **Action-titled charts from AI** | ✅ April 10–11 |
| Smart title truncation (75 chars, sentence boundaries) | ✅ April 10–11 |
| **Sparklines on KPI cards** (fixed 0.25" height) | ✅ April 10–11 |
| **Okabe-Ito color-blind palette** | ✅ April 10–11 |
| Horizontal-only gridlines + clean spines | ✅ April 10–11 |
| **Direct-labelled traffic sources** (≤4 sources) | ✅ April 10–11 |
| **Highlight-one-bar** in campaign chart | ✅ April 10–11 |
| Arrow glyphs ▲ ▼ ▬ on KPI changes + ±1% neutral band | ✅ April 10–11 |
| **Inverse cost-metric colors** (BOUNCE, COST, CPC, CPA, CPM, FREQ, POSITION, UNSUBSCRIBE, SPEND) | ✅ April 10–11 |
| **K/M/B compact KPI big numbers** | ✅ April 10–11 |
| **Currency formatter** (drops decimals on whole numbers) | ✅ April 11 |
| **Human-readable period date format** | ✅ April 11 |
| Report title uses END month of period | ✅ April 11 |
| Zero-conversion axis cleanup | ✅ April 11 |
| GA4 source label cleanup (`(none)` → `Direct`) | ✅ April 11 |
| **Logo bounding-box fit** (never overflows slide) | ✅ April 11 |
| **Bad-month detection + four-beat recovery prompt** | ✅ April 11 |
| WCAG AA emerald contrast (`#047857`) | ✅ April 10–11 |

### 3.5 AI narrative

| Feature | Status |
|---|---|
| GPT-4.1 engine | ✅ |
| 4 tone presets | ✅ |
| 13 supported languages | ✅ |
| **SCQA executive summary** | ✅ April 10–11 |
| **3+3+3 content enforcement** | ✅ April 10–11 |
| **Bad-month detection** | ✅ April 11 |
| **chart_insights output key** | ✅ April 10–11 |
| Client goals context fed to prompt | ✅ |
| Currency-aware prompts | ✅ |
| Per-section regeneration | ✅ |
| Inline edit with `user_edits` merge | ✅ |
| Graceful fallback when API errors | ✅ |

### 3.6 KPI scorecard

- 6 KPI cards with smart scoring across all sources
- K/M/B compact big numbers (April 10–11)
- Arrow glyphs with ±1% neutral dead-zone (April 10–11)
- Inverse cost-metric color logic (April 10–11)
- Sparklines under each value (April 10–11)
- Currency symbol auto-detection per connection
- Fallback pool when primary < 6 (April 11)
- `"▬ —"` placeholder when change data unavailable (April 11)

### 3.7 Report sharing & delivery

| Feature | Status |
|---|---|
| Public shareable link (hash URL) | ✅ |
| Optional password on share link (bcrypt) | ✅ |
| Optional expiry | ✅ |
| View tracking (IP anonymised to first 2 octets) | ✅ |
| View analytics per share (count, device, duration) | ✅ |
| Email delivery ("Send to Client") | ✅ |
| Multi-recipient | ✅ |
| Customisable subject + sender + reply-to | ✅ |
| **Attachment format selector** (PDF / PPTX / Both) | ✅ April 10–11 |
| Delivery logging in `report_deliveries` | ✅ |
| Branded indigo HTML email template | ✅ |

### 3.8 Scheduled reports

| Feature | Status |
|---|---|
| Schedules tab on client detail | ✅ |
| Weekly / biweekly / monthly frequency | ✅ |
| **Timezone-aware time picker** (9 common timezones) | ✅ April 10–11 |
| Auto-detect browser timezone | ✅ April 10–11 |
| **Smart `next_run_at`** (same-day if target time still ahead) | ✅ April 10–11 |
| **Attachment format per schedule** | ✅ April 11 |
| **Visual template per schedule** (plan-gated) | ✅ April 11 |
| Auto-send to client emails | ✅ |
| **15-minute background scheduler loop** | ✅ April 10–11 |
| **Plan pre-check** (downgrade safety) | ✅ April 11 |
| "May take up to 15 minutes" note | ✅ April 11 |

### 3.9 White-label branding

- Agency logo upload (visible on reports for Pro+)
- Brand color picker (Pro+)
- Agency name on reports (Pro+)
- Client logo on cover slide (all plans, with bounding-box fit April 11)
- "Powered by GoReportPilot" badge on Starter only
- **Trial watermark on PPTX exports** (commit `6462a17`)
- White-label email sender (Pro+)
- Custom email footer (all plans)

### 3.10 Plan enforcement

- Trial auto-creation on first `/billing` visit
- 14-day trial with 10-client limit
- **5-report trial cap** (commit `0053858`)
- **Block expired users** from generation + downloads (commit `deff25f`)
- **Feature gates with upgrade prompts** (commit `b4b83d3`)
- Client limit, visual template, AI tone, scheduling, PPTX export, white-label — all plan-gated

### 3.11 Billing (Razorpay)

- Dual-currency (INR + USD) with auto detection (commit `c30cf81`)
- Billing page with monthly/annual toggle
- Razorpay checkout modal, subscription CRUD, payment history
- **Never write plan until payment confirmed** via reverse `razorpay_plan_id` lookup (commit `ca60ab9`)
- Dunning emails on failed payments: ❌ not yet wired

### 3.12 Admin dashboard

- Separate admin layout with its own sidebar (commit `e7f5edf`)
- **8 pages:** Overview, **Analytics (NEW April 11)**, Users, Subscriptions, Connections, Reports, System, GDPR
- `_require_admin()` guard on all admin endpoints
- Admin activity log

**Admin Analytics page (April 11, commit `aee6616`)** builds metrics from OUR OWN database — no GA4 API. Features:

- 6 stat cards (total users, active 7d, reports generated, paying customers + MRR, conversion rate %, platform connections)
- 2 trend charts (30-day signups, 30-day reports) — pure Tailwind div-based
- Subscription breakdown with MRR in both INR and USD (annual cycles normalised to monthly)
- Conversion funnel (signed_up → connected_source → generated_report → paid)
- Users by country (derived from `profiles.timezone` via IANA→country map, top 10)
- Platform connection breakdown
- Sortable top-10-users table with plan badges
- Auto-refresh every 5 minutes
- **Pagination-safe**: `_fetch_all()` helper loops `.range(start, end)` in 1000-row batches — bypasses PostgREST default row cap
- MRR sourced directly from `services/plans.py` via `_plan_monthly_revenue()` — no hardcoded prices

### 3.13 Landing page

- Sticky nav with mobile hamburger
- **Hero** (April 11): pre-label + H1 *"Branded client reports, written by AI."* + subheadline + `HeroCTA` client island + "See How It Works" secondary + reassurance line with dual currency + integration logo strip
- Problem section (3 cards)
- How It Works (4-step horizontal flow)
- **Features grid expanded from 6 to 9 cards** with benefit-led copy (April 11)
- Comparison table (GoReportPilot vs AgencyAnalytics vs DashThis) — fixed "15 clients" + added multi-language + CSV rows
- Pricing section with monthly/annual toggle + auto currency detection
- **FAQ** with 10 questions (April 11): fixed Q1/Q2/Q5 factual errors, added Q7–Q10 (SEO / scheduling / languages / white-label)
- Final CTA section
- Footer with only working links (broken Integrations/Changelog/About/Blog removed)
- **SEO**: `sitemap.ts` + `robots.ts` + strengthened meta tags with audience word and price anchor
- **Cookie consent banner** (GDPR-compliant, April 11)
- **GA4 tracking** `G-GMTY15QRRZ` gated on consent (April 11)
- **Event tracking**: `sign_up`, `cta_click`, `select_plan`

### 3.14 Report preview & editing

- Report preview with KPI scorecard
- Inline edit on every narrative section
- Per-section regenerate (GPT-4.1)
- Download PPTX / PDF buttons
- "Send to Client" modal with attachment selector
- Share via public link
- `user_edits` JSONB merged over `ai_narrative` at display time
- HTTP 410 handling with "Regenerate Report" button when files expire

### 3.15 Settings page

- Account tab (name, email, password, timezone)
- Agency branding tab (logo, brand color, agency name/email/website)
- AI preferences tab (default tone, comparison period)
- Email settings tab (sender name, reply-to, footer)
- Notification preferences tab
- Danger zone with delete account (commit `7a19320`)

### 3.16 Onboarding & polish

- New user onboarding checklist + empty states (commit `58880a7`)
- First-report walkthrough
- Rate limiting on public endpoints (commit `7a19320` — e.g. 20/hour on send)
- Mobile responsive audit across all pages (commit `216bdd4`)
- Loading skeletons + progress bar + toasts (commit `bbe5ee6`)
- Legal pages: Privacy, Terms, Refund, Contact

---

---

## 4. PLAN & PRICING DETAILS

Source of truth: `backend/services/plans.py`. Any billing logic that references prices or limits MUST import from that file — never hardcode.

### Plan Matrix

| Plan | Monthly INR | Annual INR | Monthly USD | Annual USD | Clients | PPTX | PDF | White-label | Scheduling | AI Tones | Visual Templates |
|------|-------------|------------|-------------|------------|---------|------|-----|-------------|------------|----------|-----------------|
| Trial | — | — | — | — | 10 | ✅ | ✅ | ✅ | ✅ | all 4 | all 3 |
| Starter | ₹999 | ₹9,599 | $19 | $182 | 5 | ❌ | ✅ | ❌ | ❌ | professional only | modern_clean only |
| Pro | ₹1,999 | ₹19,199 | $39 | $374 | 15 | ✅ | ✅ | ✅ | ✅ | all 4 | all 3 |
| Agency | ₹3,499 | ₹33,599 | $69 | $662 | 999 (∞) | ✅ | ✅ | ✅ | ✅ | all 4 | all 3 |

**Trial rules:** 14 days, 10 clients, all features enabled, `powered_by_badge: True` (watermark "Powered by ReportPilot"), auto-created on first `/dashboard/billing` visit.

**"Powered by ReportPilot" badge:** `True` on Trial and Starter; `False` on Pro and Agency (badge removed from reports and emails on paid plans ≥ Pro).

**Scheduling frequencies:** `["weekly", "biweekly", "monthly"]` — Pro and Agency only.

### Razorpay Plan IDs (Environment Variables)

12 plan IDs must be created in Razorpay Dashboard → Subscriptions → Plans, then set as env vars:

```
# INR plans
RAZORPAY_PLAN_STARTER_MONTHLY   = plan_xxx   # ₹999/month
RAZORPAY_PLAN_STARTER_ANNUAL    = plan_xxx   # ₹9,599/year
RAZORPAY_PLAN_PRO_MONTHLY       = plan_xxx   # ₹1,999/month
RAZORPAY_PLAN_PRO_ANNUAL        = plan_xxx   # ₹19,199/year
RAZORPAY_PLAN_AGENCY_MONTHLY    = plan_xxx   # ₹3,499/month
RAZORPAY_PLAN_AGENCY_ANNUAL     = plan_xxx   # ₹33,599/year

# USD plans (separate Razorpay plans billed in USD)
RAZORPAY_PLAN_STARTER_MONTHLY_USD = plan_xxx   # $19/month
RAZORPAY_PLAN_STARTER_ANNUAL_USD  = plan_xxx   # $182/year
RAZORPAY_PLAN_PRO_MONTHLY_USD     = plan_xxx   # $39/month
RAZORPAY_PLAN_PRO_ANNUAL_USD      = plan_xxx   # $374/year
RAZORPAY_PLAN_AGENCY_MONTHLY_USD  = plan_xxx   # $69/month
RAZORPAY_PLAN_AGENCY_ANNUAL_USD   = plan_xxx   # $662/year
```

**Status:** ⚠️ All 12 plan IDs are currently empty strings in Railway env vars — must be filled before billing goes live.

### Currency Detection

`frontend/src/lib/detect-currency.ts` — module-level memoised timezone-based detection. Used by `CurrencyPrice` component and `PricingToggle`. Logic: if browser timezone contains "Asia/Calcutta" or "Asia/Kolkata" → INR; otherwise → USD. Shared via module-level `let _memo` to avoid re-running `Intl.DateTimeFormat` on every render.

---

## 5. DATABASE SCHEMA

### Migration Files (in order)

| File | Contents |
|------|----------|
| `001_initial_schema.sql` | Core 8 tables, RLS policies, indexes, triggers |
| `002_add_currency_to_connections.sql` | `currency` column on `connections` |
| `003_report_customization.sql` | `report_config` JSONB, `user_edits` JSONB, section toggles |
| `004_whitelabel_scheduling.sql` | Agency branding on `profiles`, `scheduled_reports` table with `template` + `send_to_emails` columns |
| `005_profiles_missing_columns.sql` | Backfill any missing profile columns |
| `006_billing.sql` | `subscriptions` + `payment_history` tables |
| `007_add_language.sql` | `language` column on `clients` (13 languages) |
| `008_shared_reports.sql` | `shared_reports` + `report_views` tables |
| `009_widen_platform_constraint.sql` | Adds `linkedin_ads` to `connections.platform` CHECK constraint |
| `010_storage_logos_bucket.sql` | Creates `logos` Storage bucket (public), RLS for upload/read |
| `011_admin_dashboard.sql` | `is_admin`/`is_disabled` on `profiles`, `admin_activity_log`, `gdpr_requests` tables |
| `012_fix_unpaid_subscriptions.sql` | Backfill subscriptions for users without one |

### Table Summary

**`profiles`** (extends `auth.users`)
- `id`, `email`, `name`, `avatar_url`
- `plan TEXT DEFAULT 'starter'` — ⚠️ legacy column; billing now in `subscriptions` table
- `agency_name`, `agency_email`, `agency_logo_url`, `brand_color`, `agency_website`, `timezone`
- `default_ai_tone`, `sender_name`, `reply_to_email`, `email_footer`
- `notification_report_generated`, `notification_connection_expired`, `notification_payment_failed`
- `is_admin BOOLEAN DEFAULT false`, `is_disabled BOOLEAN DEFAULT false`
- `preferences JSONB DEFAULT '{}'`

**`clients`**
- `id`, `user_id` (FK → profiles), `name`, `industry`, `website_url`
- `logo_url` (Supabase Storage URL), `goals_context`, `primary_contact_email`, `contact_emails JSONB`
- `report_schedule JSONB`, `report_template_id` (FK → report_templates), `ai_tone`
- `branding JSONB`, `notes`, `is_active BOOLEAN`, `language TEXT DEFAULT 'English'`

**`connections`**
- `id`, `client_id` (FK → clients), `platform` (`ga4`, `meta_ads`, `google_ads`, `search_console`, `linkedin_ads`)
- `account_id`, `account_name`
- `access_token_encrypted`, `refresh_token_encrypted` — AES-256-GCM, never plaintext
- `token_expires_at`, `token_type` (`user`, `long_lived`, `system_user`), `status` (`active`, `expiring_soon`, `expired`, `error`, `revoked`)
- `last_successful_pull`, `last_error_message`, `consecutive_failures INT`, `currency TEXT`

**`data_snapshots`**
- `id`, `connection_id`, `client_id`, `platform`, `period_start DATE`, `period_end DATE`
- `metrics JSONB`, `raw_response JSONB`, `pulled_at`, `is_valid BOOLEAN`

**`report_templates`**
- `id`, `user_id` (NULL = system default), `name`, `description`, `sections JSONB`, `is_system_default BOOLEAN`

**`reports`**
- `id`, `client_id`, `user_id`, `template_id`
- `title`, `period_start DATE`, `period_end DATE`, `comparison_period_start`, `comparison_period_end`
- `status` (`generating`, `draft`, `approved`, `sent`, `failed`)
- `ai_narrative JSONB`, `user_edits JSONB`, `sections JSONB`, `report_config JSONB`
- `pptx_file_url TEXT`, `pdf_file_url TEXT` — ephemeral local paths; expire after server restart (HTTP 410 triggers frontend regeneration)
- `share_link_hash`, `share_link_password`, `share_link_expires_at`
- `sent_at`, `opened_at`, `delivery_emails JSONB`

**`report_deliveries`**
- `id`, `report_id`, `delivery_method` (`email`, `link`), `recipient_email`
- `sent_at`, `opened_at`, `attachment_type` (`pdf`, `pptx`, `both`)
- `email_subject`, `email_body`, `status` (`pending`, `sent`, `delivered`, `opened`, `bounced`, `failed`)
- `resend_id TEXT`, `error_message TEXT`

**`scheduled_reports`**
- `id`, `client_id`, `user_id`
- `frequency` (`weekly`, `biweekly`, `monthly`), `day_of_week INT`, `day_of_month INT`
- `time_utc TEXT DEFAULT '09:00'`, `template TEXT DEFAULT 'full'`
- `auto_send BOOLEAN`, `send_to_emails JSONB DEFAULT '[]'`
- `attachment_format TEXT DEFAULT 'pdf'` — added in this session
- `visual_template TEXT DEFAULT 'modern_clean'` — added in this session
- `is_active BOOLEAN`, `last_generated_at`, `next_run_at`

**`subscriptions`**
- `id`, `user_id` (UNIQUE FK → auth.users)
- `razorpay_customer_id`, `razorpay_subscription_id`, `razorpay_plan_id`
- `plan TEXT DEFAULT 'trial'` (`trial`, `starter`, `pro`, `agency`), `billing_cycle` (`monthly`, `annual`)
- `status` (`trialing`, `active`, `past_due`, `cancelled`, `expired`, `paused`)
- `current_period_start`, `current_period_end`, `trial_ends_at DEFAULT NOW() + 14 days`
- `cancelled_at`, `cancel_at_period_end BOOLEAN`, `last_payment_at`, `payment_failed_count INT`

**`payment_history`**
- `id`, `user_id`, `subscription_id`, `razorpay_payment_id`
- `amount INT`, `currency TEXT DEFAULT 'INR'`, `status` (`captured`, `failed`, `refunded`)
- `plan TEXT`, `description TEXT`, `created_at`

**`shared_reports`**
- `id`, `report_id`, `user_id`, `share_hash VARCHAR(32) UNIQUE`
- `password_hash`, `expires_at`, `is_active BOOLEAN`

**`report_views`**
- `id`, `shared_report_id`, `viewer_ip`, `user_agent`, `device_type` (`mobile`, `desktop`, `tablet`)
- `viewed_at`, `duration_seconds INT`
- RLS: anyone can INSERT (public viewing); SELECT restricted to report owner

**`admin_activity_log`** (service role only, no user RLS)
- `id`, `admin_user_id`, `action TEXT`, `target_user_id`, `target_user_email`, `details JSONB`

**`gdpr_requests`** (service role only)
- `id`, `user_email`, `request_type` (`access`, `portability`, `erasure`, `rectification`, `restriction`)
- `status` (`pending`, `in_progress`, `completed`, `rejected`), `admin_notes`, `completed_at`

### Supabase Project

- **URL:** `https://kbytzqviqzcvfdepjyby.supabase.co`
- **Region:** ap-south-1 (Mumbai)
- **Storage bucket:** `logos` (public) — agency logos, client logos
- **Admin account:** `sapienbotics@gmail.com` → `is_admin = true` set in migration 011

---

## 6. OAUTH & THIRD-PARTY INTEGRATIONS

### Google OAuth (GA4 + Google Ads + Search Console)

- **Status:** Testing mode — only whitelisted test users can OAuth
- **Scopes:** `analytics.readonly`, `adwords`, `webmasters.readonly`
- **Console:** console.cloud.google.com → Project: ReportPilot
- **Redirect URIs registered:** `http://localhost:3000/api/auth/callback/google-analytics`, `http://localhost:3000/api/auth/callback/google-ads`, `http://localhost:3000/api/auth/callback/search-console`, and their `https://goreportpilot.com` equivalents
- **Verification required to go Production:** Privacy policy URL, ToS URL, app logo, scope justification
- **Timeline for review:** 2–6 weeks after submission
- **Token refresh:** Handled automatically in `services/google_analytics.py` — uses `refresh_token_encrypted` when `access_token` expires

### Meta Ads OAuth

- **Status:** Development mode — only app developers/testers can OAuth
- **Scopes:** `ads_read`, `ads_management`, `public_profile`
- **Portal:** developers.facebook.com → App: ReportPilot
- **Short-to-long-lived token exchange:** `services/meta_ads.py` exchanges short-lived token (1 hour) for long-lived token (60 days) immediately after callback
- **App Review required** for `ads_read` — requires screen recording demo, privacy policy, use case description
- **Timeline for review:** 1–4 weeks

### Resend (Email Delivery)

- **Domain:** `goreportpilot.com`
- **`EMAIL_FROM_DOMAIN`:** `goreportpilot.com` — reports sent from `reports@goreportpilot.com`
- **Status:** Domain added to Resend; DNS records (MX, SPF, DKIM) must be confirmed as verified in Resend dashboard
- **`email_service.py`:** Uses `httpx` POST to `api.resend.com/emails`; activated when `RESEND_API_KEY` is non-empty
- **Dunning emails:** `payment_failed_count` incremented in webhook; notification email not yet wired

### Razorpay (Billing)

- **Mode:** Live mode
- **Webhook endpoint:** `POST /api/billing/webhooks/razorpay`
- **Events handled:** `subscription.activated`, `subscription.charged`, `subscription.cancelled`, `subscription.paused`, `payment.failed`
- **Status:** API keys exist; 12 plan IDs not yet created (⚠️ must create before launch)
- **INR/USD detection:** Frontend uses `detect-currency.ts` to select INR vs USD plan IDs at checkout

### OpenAI

- **Model:** GPT-4.1 (migrated from GPT-4o in this session — better instruction-following for structured JSON output)
- **Usage:** AI narrative generation in `services/ai_narrative.py`
- **SCQA structure enforced:** Situation → Complication → Question → Answer on all narrative sections
- **3+3+3 enforcement:** 3 wins, 3 concerns, 3 next steps — exactly, no exceptions

---

## 7. DNS & DOMAIN CONFIGURATION

**Registrar:** Namecheap
**Primary domain:** `goreportpilot.com`

### DNS Records

| Type | Host | Value | Purpose | Status |
|------|------|-------|---------|--------|
| A | @ | Vercel IP (76.76.21.21) | Root domain → Vercel | ✅ |
| CNAME | www | cname.vercel-dns.com | www redirect | ✅ |
| CNAME | api | `<railway-generated>.up.railway.app` | Backend API | ✅ |
| MX | @ | `feedback-smtp.us-east-1.amazonses.com` (10) | Resend email (via SES) | ⚠️ Verify in Resend |
| TXT | @ | `v=spf1 include:amazonses.com ~all` | SPF for Resend | ⚠️ Verify in Resend |
| TXT | resend._domainkey | DKIM public key from Resend | DKIM signing | ⚠️ Verify in Resend |
| TXT | _dmarc | `v=DMARC1; p=none; rua=mailto:dmarc@goreportpilot.com` | DMARC | ⚠️ Verify in Resend |

**Note:** The exact MX/SPF/DKIM values are generated by Resend when you add the domain — copy them from Resend Dashboard → Domains → goreportpilot.com. DNS propagation takes up to 48 hours.

### Deployed URLs

| Service | URL |
|---------|-----|
| Frontend (production) | `https://goreportpilot.com` |
| Frontend (Vercel preview) | `https://reportpilot-*.vercel.app` |
| Backend API | `https://api.goreportpilot.com` |
| Backend health check | `https://api.goreportpilot.com/health` |
| Supabase | `https://kbytzqviqzcvfdepjyby.supabase.co` |

---

## 8. ENVIRONMENT VARIABLES

### Backend (`backend/.env`)

```bash
# Supabase
SUPABASE_URL=https://kbytzqviqzcvfdepjyby.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service role key from Supabase → Settings → API>

# Google OAuth (GA4 + Google Ads + Search Console — single OAuth client)
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
GOOGLE_REDIRECT_URI=http://localhost:3000/api/auth/callback/google-analytics
GOOGLE_ADS_REDIRECT_URI=http://localhost:3000/api/auth/callback/google-ads
SEARCH_CONSOLE_REDIRECT_URI=http://localhost:3000/api/auth/callback/search-console

# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=<from Google Ads API Center>
GOOGLE_ADS_LOGIN_CUSTOMER_ID=8152475096

# Meta OAuth
META_APP_ID=<from Meta Developer Portal>
META_APP_SECRET=<from Meta Developer Portal>
META_REDIRECT_URI=http://localhost:3000/api/auth/callback/meta-ads

# Token Encryption (AES-256-GCM)
TOKEN_ENCRYPTION_KEY=<base64-encoded 32-byte key — NEVER regenerate in production>

# OpenAI
OPENAI_API_KEY=<from platform.openai.com>

# Razorpay
RAZORPAY_KEY_ID=<from Razorpay → Settings → API Keys>
RAZORPAY_KEY_SECRET=<from Razorpay → Settings → API Keys>
RAZORPAY_WEBHOOK_SECRET=<from Razorpay → Webhooks>
# INR plans
RAZORPAY_PLAN_STARTER_MONTHLY=
RAZORPAY_PLAN_STARTER_ANNUAL=
RAZORPAY_PLAN_PRO_MONTHLY=
RAZORPAY_PLAN_PRO_ANNUAL=
RAZORPAY_PLAN_AGENCY_MONTHLY=
RAZORPAY_PLAN_AGENCY_ANNUAL=
# USD plans
RAZORPAY_PLAN_STARTER_MONTHLY_USD=
RAZORPAY_PLAN_STARTER_ANNUAL_USD=
RAZORPAY_PLAN_PRO_MONTHLY_USD=
RAZORPAY_PLAN_PRO_ANNUAL_USD=
RAZORPAY_PLAN_AGENCY_MONTHLY_USD=
RAZORPAY_PLAN_AGENCY_ANNUAL_USD=

# Resend
RESEND_API_KEY=<from resend.com → API Keys>
EMAIL_FROM_DOMAIN=goreportpilot.com

# App
FRONTEND_URL=http://localhost:3000         # production: https://goreportpilot.com
BACKEND_URL=http://localhost:8000          # production: https://api.goreportpilot.com
ENVIRONMENT=development                    # production: production
```

**Production note:** In Railway, `GOOGLE_REDIRECT_URI`, `META_REDIRECT_URI`, etc. are derived automatically from `FRONTEND_URL` via `config.py → model_post_init()` if not set explicitly. Set `FRONTEND_URL=https://goreportpilot.com` and the redirect URIs auto-populate.

### Frontend (`frontend/.env.local`)

```bash
NEXT_PUBLIC_SUPABASE_URL=https://kbytzqviqzcvfdepjyby.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<from Supabase → Settings → API → anon/public>
NEXT_PUBLIC_API_URL=http://localhost:8000    # production: https://api.goreportpilot.com
NEXT_PUBLIC_APP_URL=http://localhost:3000    # production: https://goreportpilot.com
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-GMTY15QRRZ  # optional — hardcoded fallback exists in AnalyticsProvider
```

### Running Dev Servers

```bash
# Backend
cd backend && python -m uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

**Never auto-start dev servers.** Always run `cd frontend && npx tsc --noEmit` after frontend changes.

---

## 9. DEVELOPMENT WORKFLOW

### How Saurabh Works with Claude

1. **Saurabh** describes a feature, bug, or design decision in Claude.ai chat (this conversation)
2. **Claude.ai** (claude.ai web) analyzes and writes a detailed numbered implementation prompt
3. **Saurabh** pastes the prompt into **Claude Code** (VS Code extension) — uses **Opus 4.6** for complex/systemic work, **Sonnet 4.6** for simpler tasks
4. Claude Code executes the changes autonomously across multiple files
5. **Saurabh** reports back with screenshots, terminal output, browser errors, or generated PPTX file previews
6. Cycle repeats: Claude.ai diagnoses issues → writes fix prompt → Saurabh pastes into Claude Code

### Key Rules

- **Never modify `.env` files** — Claude Code must not write to `.env` or `.env.local`
- **Never auto-start dev servers** — Saurabh starts them manually
- **Always typecheck after frontend changes:** `cd frontend && npx tsc --noEmit`
- **Database changes** run manually in Supabase SQL Editor — never via Supabase CLI from Claude Code
- **Single source of truth for pricing:** Always import from `backend/services/plans.py`; never hardcode amounts

### Local Dev Environment

- **OS:** Windows 11
- **Project root:** `F:\Sapienbotics\ClaudeCode\reportpilot\`
- **Python:** 3.12 (venv at `backend\venv\`)
- **Node:** 20+
- **LibreOffice:** `C:\Program Files\LibreOffice\program\soffice.exe`

---

## 10. PROMPT HISTORY

All prompts in order. Prompts 1–27 executed across Claude.ai + Claude Code (March 2026). Prompts 28–64 executed in April 2026 sessions.

| # | Description |
|---|-------------|
| 1 | Initial project scaffold — monorepo (Next.js 14 + FastAPI), directory structure, 95+ files |
| 2 | Supabase schema — 8 tables, 28 RLS policies, 15 indexes, 5 triggers, seed template |
| 3 | Supabase Auth — email/password signup, login, logout, protected /dashboard/* routes |
| 4 | Dashboard layout — sidebar nav, header with email + sign out, active highlighting |
| 5 | Client CRUD — create, list, get, update, soft-delete with ownership verification + frontend pages |
| 6 | Landing page — 10-section marketing page (hero, problem, how-it-works, features, competitor comparison, pricing with annual toggle, FAQ, CTA, footer) |
| 7 | Mock data service — realistic GA4 + Meta Ads fake data matching real API response structure |
| 8 | AI narrative engine — GPT-4o with 4 tone presets, returns 6 sections as JSON, graceful fallback |
| 9 | Chart generator — 4 matplotlib charts (sessions line, traffic sources bar, spend vs conversions dual-axis, campaign performance) |
| 10 | PowerPoint generator — 8-slide branded deck with embedded charts, KPI scorecard with color-coded changes |
| 11 | PDF generator — ReportLab A4 report with KPI table, embedded charts, all narrative sections |
| 12 | Report API — generate, list, get, download PPTX/PDF endpoints |
| 13 | Report preview UI — KPI cards, narrative sections, key wins/concerns/next steps, download buttons |
| 14 | GA4 OAuth — full flow (consent → callback → token exchange → property listing → connection save → real data pull with auto-refresh) |
| 15 | Meta Ads OAuth — full flow (Facebook login → token exchange → short-to-long-lived → ad account listing → connection save → real data pull) |
| 16 | Token encryption — AES-256-GCM via cryptography library, nonce prepended, base64 encoded |
| 17 | Currency handling — dynamic currency symbols (₹, $, €, £) across AI narrative, charts, PDF, PPTX, frontend preview |
| 18 | Connection management — save, list, delete connections with encrypted tokens, platform normalization |
| 19 | 19-slide template system — 6 visual templates (modern_clean, dark_executive, colorful_agency, bold_geometric, minimal_elegant, gradient_modern), smart slide selection/deletion |
| 20 | Google Ads OAuth + Search Console OAuth — full flows for both platforms |
| 21 | CSV upload system — per-report data source modal with drag-and-drop, template downloads |
| 22 | Multi-CSV slide duplication — save-reload cycle (orphan purge), N-1 duplicates, slide reordering |
| 23 | Category 1+2 systemic robustness — bulletproof CSV parser rewrite (encoding, delimiter, binary rejection, K/M/B suffixes, European decimals, brand name capitalization) |
| 24 | Three production fixes — CSV chart overlap fix, dual-chart type-aware expansion, brand name capitalization |
| 25 | Phase 1-5 template geometry — audit all 6 templates, fix CSV chart placeholder at source (`fix_csv_slide_layout.py`), chart thresholds (≥2 data points) |
| 26 | Chart sizing — CSV chart centering at 8" wide, type-aware dual-chart expansion (pie keeps 5.6", bar expands to 8.5") |
| 27 | March 2026 handover document |
| 28 | Report customization — section toggles per client, KPI selection, report_config JSONB |
| 29 | Inline report editing — edit/save/cancel on every narrative card, user_edits JSONB merge |
| 30 | Regenerate individual sections — per-section "Regenerate" button, GPT re-run |
| 31 | Email delivery — "Send to Client" dialog, Resend integration, report_deliveries table, delivery tracking |
| 32 | White-label branding — agency branding settings page, logo upload (Supabase Storage), brand color, per-client logo on cover slide, remove "Powered by ReportPilot" on Pro+ |
| 33 | Scheduled reports — APScheduler lifespan integration, per-client schedule config (frequency/day/time/auto-send), Schedules tab in client detail page |
| 34 | Billing & subscription — Razorpay service, billing router, subscriptions table, 14-day trial, checkout flow, plan enforcement middleware |
| 35 | Billing UI — current plan card, usage bar, trial countdown, plan comparison with annual/monthly toggle, payment history table, UpgradePrompt component |
| 36 | Settings page — account settings, agency branding tab, AI preferences, email settings, notification preferences, danger zone |
| 37 | Legal pages — Privacy Policy (/privacy), Terms of Service (/terms), Refund Policy, Contact page |
| 38 | Loading states + polish — skeleton loaders, progress bars, toasts (sonner), 404 page |
| 39 | Dashboard home page — total clients with plan limit, reports generated this month, reports due this week, recent activity feed, connection health summary |
| 40 | Mobile responsiveness audit — sidebar hamburger, scrollable tabs, responsive report preview |
| 41 | Onboarding checklist + empty states — first-report walkthrough, new user guided flow |
| 42 | Rate limiting — 20/hour on public endpoints, per-IP tracking |
| 43 | Razorpay INR+USD dual currency — 12 plan IDs (6 INR + 6 USD), detect-currency.ts, billing page toggle |
| 44 | Tier 1 report quality — Okabe-Ito color-blind-safe palette, action-oriented chart titles, 14pt axis labels, horizontal bar charts for comparisons, data labels on bars |
| 45 | Tier 2 report quality — KPI color logic (green/red/amber), sparklines on KPI cards (0.25" height), direct chart labels, AI SCQA narrative structure |
| 46 | Bad-month detection — AI narrative detects underperformance, uses empathetic tone, flags concerns accurately |
| 47 | GPT-4.1 migration — migrated from GPT-4o to GPT-4.1, 3+3+3 enforcement (exactly 3 wins / 3 concerns / 3 next steps) |
| 48 | Attachment format + visual template for scheduled reports — new DB columns (`attachment_format`, `visual_template`), dropdowns in Schedules tab with plan gating |
| 49 | Timezone selector for scheduled reports — plan file created; not yet executed |
| 50 | Landing page research — `docs/LANDING-PAGE-IMPROVEMENTS-2026.md` written (competitor analysis, copy recommendations, UX improvements) |
| 51 | Landing page overhaul — new hero H1 ("Branded client reports, written by AI."), integration logo strip, dual-currency pricing display, 9-card feature grid, FAQ factual accuracy fixes |
| 52 | SEO infrastructure — sitemap.ts (BUILD_DATE module-level), robots.ts, full OpenGraph meta tags on layout.tsx, title: "GoReportPilot — AI Client Reporting for Marketing Agencies" |
| 53 | GA4 tracking with GDPR cookie consent — `CookieConsent.tsx` banner, `AnalyticsProvider.tsx` gates gtag loading until consent, GA ID: G-GMTY15QRRZ, custom events: sign_up/cta_click/select_plan |
| 54 | Admin analytics dashboard — `GET /api/admin/analytics`, `admin_analytics.py` router, `frontend/src/app/admin/analytics/page.tsx`; 6 stat cards, bar charts (pure Tailwind, no recharts), funnel, country breakdown |
| 55 | Fix: `_fetch_all()` pagination helper — bypasses PostgREST 1000-row cap using `.range(start, end)` batches |
| 56 | Fix: MRR calculation — `_plan_monthly_revenue()` imports prices from `plans.py` directly, eliminates hardcoded price drift |
| 57 | Fix: `SortableTh` "Name" column had `k="email"` copy-paste bug — fixed to `k="name"`, new `SortKey` union type |
| 58 | Fix: `HorizontalBarRow` extracted — removed near-duplicate bar rendering across `SubscriptionBar`, `CountryList`, `ConnectionBreakdown` |
| 59 | Fix: `detect-currency.ts` extracted — removed `detectCurrency()` duplication from `CurrencyPrice.tsx` and `pricing-toggle.tsx`, module-level memo |
| 60 | Fix: Sparkline height — increased from 0.08" to fixed 0.25" via `_PIC_HEIGHT = Inches(0.25)` |
| 61 | Fix: Admin dashboard `sessions` field removed — was duplicating `reports_generated`, removed from payload + TS interface |
| 62 | Fix: Sitemap `new Date()` moved to module-level `BUILD_DATE` — prevents every crawl from reporting "modified now" |
| 63 | Fix: Funnel `generated_report` guard simplified — removed redundant `if uid` check, simplified to `len(reports_by_user)` |
| 64 | This handover document (HANDOVER-APRIL-11-2026.md) |

---

## 11. CURRENT STATUS (April 11, 2026)

### Deployment Status

| Component | Status |
|-----------|--------|
| Frontend (Vercel) | ✅ Live at `https://goreportpilot.com` |
| Backend (Railway) | ✅ Live at `https://api.goreportpilot.com` |
| Supabase | ✅ Live at `https://kbytzqviqzcvfdepjyby.supabase.co` |
| Domain DNS | ✅ Propagated |
| SSL | ✅ Automatic via Vercel |
| GA4 Tracking | ✅ Live (gated behind cookie consent) |

### Feature Status

| Feature | Status |
|---------|--------|
| Auth (signup/login/logout) | ✅ Working |
| Client CRUD | ✅ Working |
| GA4 OAuth + data pull | ✅ Working (Testing mode — add users in Google Cloud Console) |
| Meta Ads OAuth + data pull | ✅ Working (Development mode — add testers in Meta Dev Portal) |
| Google Ads OAuth + data pull | ✅ Working |
| Search Console OAuth + data pull | ✅ Working |
| CSV upload + parsing | ✅ Working |
| Report generation (PPTX + PDF) | ✅ Working |
| Report preview + inline editing | ✅ Working |
| Report email delivery | ✅ Working (needs Resend API key + DNS verified) |
| Report sharing (link + password) | ✅ Working |
| Scheduled reports (UI + scheduler) | ✅ Working (APScheduler runs in Railway backend) |
| Billing (Razorpay) | ✅ UI + backend built; needs 12 plan IDs filled in Railway |
| White-label branding | ✅ Working |
| Admin analytics dashboard | ✅ Working at `/admin/analytics` (is_admin required) |
| Cookie consent + GA4 | ✅ Working |
| Settings page | ✅ Working |
| Legal pages | ✅ Working |

### Pending Before Public Launch

1. **Fill in 12 Razorpay plan IDs** in Railway environment variables
2. **Confirm Resend DKIM/SPF/DMARC** DNS records verified in Resend dashboard
3. **Google OAuth verification** — submit consent screen for Production review (2–6 week wait)
4. **Meta App Review** — submit `ads_read` for review (1–4 week wait)
5. **Add test users** in Google Cloud Console (Testing mode) and Meta Developer Portal (Development mode) for beta testers

### Build Statistics

- **64 prompts** executed across Claude.ai + Claude Code
- **~150+ files** created or modified
- **12 Supabase migrations** applied
- **6 PPTX visual templates** (19 slides each)
- **~8,000 lines** of backend Python
- **~12,000 lines** of frontend TypeScript/TSX

---

## 12. PENDING ITEMS

### Immediate (Before Launch)

- [ ] **Razorpay plan IDs** — Create 12 plans in Razorpay Dashboard → Subscriptions → Plans; paste IDs into Railway env vars
- [ ] **Resend DNS verification** — Confirm MX, SPF, DKIM, DMARC records are `Verified` status in Resend dashboard
- [ ] **Google OAuth Production submission** — Change consent screen from Testing → In Production; provide privacy policy URL, ToS URL, app logo
- [ ] **Meta App Review submission** — Request `ads_read` permission; record screen demo video showing the integration
- [ ] **Beta tester access** — Add beta testers to Google Cloud Console (test users) and Meta Developer Portal (test users) before verification completes

### Near-term (Post-Launch)

- [ ] **Timezone selector for scheduled reports** — Plan file exists at `C:\Users\saura\.claude\plans\keen-imagining-galaxy.md`. Adds `schedTimezone` state in client detail page, `localTimeToUtc`/`utcToLocalTime` helpers in `lib/timezone-utils.ts`, timezone dropdown in `SchedulesTab.tsx`
- [ ] **Dunning emails** — Wire `payment_failed_count` webhook increment to Resend notification email
- [ ] **Google Ads developer token** — Currently using test account token. Apply for Standard Access once billing is live
- [ ] **LinkedIn Ads OAuth** — Platform column accepts `linkedin_ads` (migration 009); OAuth flow not yet built
- [ ] **Phase 2 features** — See `docs/PHASE-2-BUILD-PLAN.md`: team seats, client portal, AI report scoring, Looker Studio export

### Known Technical Debt

- [ ] `pptx_file_url` / `pdf_file_url` in `reports` table store ephemeral local paths — files deleted on server restart → HTTP 410 → frontend shows "Regenerate" button. Consider moving to Supabase Storage for persistence
- [ ] `profiles.plan` column is a legacy remnant from before migration 006 — billing source of truth is `subscriptions.plan`. Consider removing `profiles.plan` after verifying no references remain
- [ ] Scheduled reports timezone — times stored as UTC string "HH:MM"; no timezone conversion in UI (timezone selector is the pending task above)
- [ ] ReportLab PDF fallback — only supports Latin languages; non-Latin reports without LibreOffice return `None`. LibreOffice is in the Railway Docker image so this only affects local dev on machines without LibreOffice
- [ ] CSV `_seen_csv_names` deduplication uses source name string — if two CSV files have identical names, second is silently skipped. Could cause confusion if user uploads two differently-named files that happen to map to same cleaned name

---

## 13. PPTX REPORT QUALITY — CURRENT STATE

Research document: `docs/REPORT-QUALITY-RESEARCH-2026.md` (April 10, 2026)

### Tier 1 — All 8 items COMPLETE ✅

| # | Change | File | Status |
|---|--------|------|--------|
| 1 | Emerald WCAG fix: `#059669` → `#047857` (5.1:1 AA) | `report_generator.py`, `chart_generator.py` | ✅ |
| 2 | Filled arrow glyphs in KPI deltas: `▲`/`▼`/`▬` prepended in `_fmt_change()` | `report_generator.py` | ✅ |
| 3 | ±1% neutral band: `abs(val) < 1.0` → slate-500 color, `▬` glyph | `report_generator.py` | ✅ |
| 4 | K/M/B compact formatter: `_fmt_compact()` for KPI card big numbers only | `report_generator.py` | ✅ |
| 5 | Invert cost-metric color: CPC, CPA, bounce rate, frequency = down is green | `report_generator.py`, `slide_selector.py` | ✅ |
| 6 | Explicit line spacing: 1.45 body, 1.35 titles, 1.2 KPI values | `report_generator.py` | ✅ |
| 7 | Okabe-Ito multi-series palette: `#0072B2 → #D55E00 → #009E73 → #CC79A7 → #E69F00 → #56B4E9` | `chart_generator.py` | ✅ |
| 8 | Horizontal-only gridlines + hide top/right spines: `ax.grid(axis='y', alpha=0.5)`; `ax.spines[['top','right']].set_visible(False)` | `chart_generator.py` | ✅ |

### Tier 2 — Top 6 of 7 items COMPLETE ✅

| # | Change | Status | Notes |
|---|--------|--------|-------|
| 9 | Action-titled charts — AI generates `chart_titles` JSON key, wired into `_replace_charts()` | ✅ | Done in GPT-4.1 migration prompt |
| 10 | One-line chart captions — `chart_captions` JSON key, italic Slate-500 below plot area | ✅ | Done together with action titles |
| 11 | Direct-label charts (≤4 series) — replaces legend in traffic sources + campaign performance | ✅ | |
| 12 | Highlight-one bar strategy — non-top bars gray (Slate-300), winner in brand color | ✅ | `plot_campaign_performance()` |
| 13 | Sparklines on KPI cards — `plot_sparkline()`: 2"×0.25" (fixed height), no axes, 1.2pt line, dot at last point | ✅ | Height bug fixed: was 0.08", now `_PIC_HEIGHT = Inches(0.25)` |
| 14 | SCQA executive summary — Situation → Complication → Question → Answer, 150-word target | ✅ | GPT-4.1 prompt rewritten |
| 15 | 3+3+3 enforcement — exactly 3 wins, 3 concerns, 3 next steps validated programmatically | ✅ | Prompt + validation layer |
| — | One-line chart captions (Tier 2 #10) | ✅ | |

### Tier 3 — NOT STARTED ⬜

- [ ] **Audit all 6 `.pptx` templates** — verify Inter/Arial font, correct size hierarchy, 0.5" perimeter margins, title zone y=0.4", footer split (client+period left / N of Total right)
- Note: this is **manual PowerPoint work** — open each `.pptx`, inspect master/layout slides. No automated path.

### Tier 4 — Partially done

- [ ] **MoM + YoY + % of goal scorecard** — requires historical + target fields in the data model; significant schema + UI work
- ✅ **Bad-month detection** — GPT-4.1 prompt detects primary-KPI negative MoM; forces four-beat opening (honest number → context → cause → next steps)
- ⬜ `xml_effects.py` — not needed yet; skip until a concrete design requirement arises

### What NOT to do (from research)

- Do NOT switch to native OOXML charts — keep matplotlib PNGs
- Do NOT add animations or transitions
- Do NOT put >4 KPI cards in a scorecard row (four is the documented NinjaCat norm)
- Do NOT rely on color alone for any signal — always pair with a glyph
- Do NOT build runtime slide duplication beyond the existing CSV path

### Current quality assessment

After Tier 1+2 completions, GoReportPilot's PPTX output has:
- Color-blind-safe Okabe-Ito palette ✅
- WCAG AA compliant trend colors ✅
- Action-titled charts (McKinsey principle) ✅
- AI-generated one-line chart captions ✅
- Direct data labels, no legends where possible ✅
- Highlight-one-bar strategy ✅
- Sparklines on every KPI card ✅
- SCQA-structured executive summaries ✅
- Arrow glyphs + neutral band (no fake trends for <1% change) ✅
- Inverted cost-metric coloring ✅

**Remaining gap vs $300/month competitors:** Tier 3 (template typography audit) and MoM+YoY+goal scorecard. These are medium-to-high effort changes that don't affect most users immediately.

---

## 14. LANDING PAGE — CURRENT STATE

Research document: `docs/LANDING-PAGE-IMPROVEMENTS-2026.md` (April 11, 2026)

### Changes Implemented (Prompt 51 — Landing Page Overhaul)

| Element | Before | After |
|---------|--------|-------|
| **H1** | "AI Writes Your Client Reports. You Review and Send." | **"Branded client reports, written by AI."** (7 words, 42 chars — under the 44-char ceiling) |
| **Primary CTA** | "Start Free Trial" | **"Start My Free Trial"** (first-person — published A/B tests show up to 90% CTR lift) |
| **Sub-CTA microcopy** | "Join 100+ agencies…" (unverified) | **"Free 14 days · No credit card · From $19/mo · Cancel anytime"** |
| **Integration logos** | None | Logo strip: GA4, Meta Ads, Google Ads, Search Console (grayscale, below CTAs) |
| **Feature grid** | 6 cards, feature-name titles | **9 cards**, benefit-led copy (e.g., "Stop writing commentary. AI explains what happened.") |
| **Features coverage** | GA4 + Meta only | Added: Google Ads, Search Console, CSV upload, 6 PPTX templates, multi-language, sparklines |
| **FAQ** | 6 Q, factual errors | 9 Q — fixed: Search Console "coming soon" → shipped, GPT-4o → GPT-4.1, "25 clients" ceiling removed |
| **Comparison table** | "Price (10 clients) $39/mo" | "Price (15 clients) $39/mo" (Pro correct limit) |
| **Footer links** | Integrations, Changelog, About, Blog → `href="#"` (broken) | Removed or replaced with working routes |

### SEO Infrastructure (Prompt 52)

| Item | Status |
|------|--------|
| `frontend/src/app/sitemap.ts` | ✅ — uses module-level `BUILD_DATE` (not `new Date()` which reported "modified now" on every crawl) |
| `frontend/src/app/robots.ts` | ✅ |
| `layout.tsx` title | ✅ "GoReportPilot — AI Client Reporting for Marketing Agencies" |
| `layout.tsx` full OpenGraph | ✅ — title, description, url, siteName, type |
| `layout.tsx` Twitter card | ✅ — card type, title, description |
| `canonical` URL | ✅ |
| `og:image` | ❌ — no image file exists yet; OG/Twitter links preview without image |
| JSON-LD structured data | ❌ — no `Organization`, `Product`, `FAQPage` schema |

### GA4 Tracking (Prompt 53)

- **GA Measurement ID:** `G-GMTY15QRRZ` (hardcoded fallback in `AnalyticsProvider.tsx`; also in `NEXT_PUBLIC_GA_MEASUREMENT_ID`)
- **Cookie consent:** `CookieConsent.tsx` — GDPR banner, localStorage-based (`cookie_consent` key), dispatches `cookie_consent_change` custom event
- **Gating:** `AnalyticsProvider.tsx` listens for the event; only loads `gtag.js` script and fires `page_view` after consent
- **Custom events tracked:** `sign_up` (on `/signup` form submit), `cta_click` (on hero CTA), `select_plan` (on billing page plan selection)

### Still Missing (Not Yet Implemented)

- [ ] `og-image.png` (1200×630) — OG and Twitter link previews show no image
- [ ] Video demo section (60-90 second screen recording of connect → generate → download)
- [ ] Real customer testimonials / logos / G2 badge (pre-launch: no customers yet)
- [ ] JSON-LD structured data (`FAQPage` schema most impactful — enables FAQ rich snippets in Google)
- [ ] Per-integration feature pages (`/integrations/google-analytics`, etc.)
- [ ] Blog / content marketing infrastructure

### Current Conversion Assessment

The page after Prompt 51 fixes sits at the **research-predicted 5% conversion target**. The highest remaining levers in order:

1. Video demo section (largest single remaining lever — shows actual product)
2. `og:image.png` (unlocks social sharing acquisition channel)
3. JSON-LD FAQPage schema (captures bottom-funnel search traffic)
4. Real testimonials (when first paying customers exist)

---

## 15. MARKETING STRATEGY

Research document: `docs/PRICING-STRATEGY-2026.md` (April 9, 2026); `docs/competitive-analysis-2026.md`

### Competitive Position

GoReportPilot is the **only tool under $100/month that combines all three**:
1. AI-written narrative commentary (SCQA-structured, multi-tone, 13 languages)
2. Editable PowerPoint export (python-pptx, 6 branded templates)
3. Flat pricing without per-client surcharges

NinjaCat and TapClicks offer PPTX export but start at $3,000/contract (enterprise). AgencyAnalytics ($59–$349/mo) has AI summaries but no PPTX. DashThis ($44–$429/mo) has PPTX export but no AI. The gap below $100/month is genuine and large.

### Target Segments

| Segment | Description | Best Plan | Pain Point |
|---------|-------------|-----------|-----------|
| **Indian freelancers** | 1-3 yr, ₹40K–₹80K/mo salary, 2-5 clients | Starter (₹999) | 2-3 hours/client on manual reports |
| **Growing freelancers** | 4-8 clients, need Google Ads + SEO reporting | Pro (₹1,999 / $39) | Scaling without hiring |
| **Small agencies (India)** | 5-15 clients, team of 2-5 | Pro / Agency | Client expectations rising, margin pressure |
| **International agencies** | USD-billing, 10-30 clients | Pro / Agency ($39/$69) | Existing tools expensive ($179+/mo) |

### Revenue Projections

From pricing doc §10.5:

| Timeline | Users | MRR | Notes |
|----------|-------|-----|-------|
| Month 1 | 50 trial → 10 paid | ~$250 | Friends + network launch |
| Month 3 | 200 trial → 50 paid | ~$1,000 | Content + Product Hunt |
| Month 6 | 500 trial → 150 paid | ~$3,500 | SEO traction begins |
| Month 12 | 1,500 trial → 500 paid | ~$12,000 | PMF established |

Break-even: ~30 Pro users ($39/mo) covers OpenAI costs + Railway + Vercel + Resend at current usage.

### Go-To-Market Phases

**Phase 1 — Founder-led (Now → Month 2)**
- Personal network: share with every freelancer and agency owner you know
- Indian marketing communities: Facebook groups (Digital Marketing Freelancers India, etc.), LinkedIn posts
- Indie Hackers / Product Hunt launch: write a build-in-public post covering the 64-prompt journey
- Content: "I built a client reporting tool with Claude Code in 4 weeks" — authentic founder story with numbers

**Phase 2 — SEO + Content (Month 2 → Month 6)**
- Target keywords: "AI client report generator", "automated marketing reports agency", "PowerPoint client reporting tool"
- Long-tail: "how to automate client reporting", "Google Analytics report template agency"
- Content calendar: 1 post/week targeting a specific integration use case (e.g., "How to generate a Meta Ads report for clients automatically")
- SEO infrastructure: blog (/blog), integration pages (/integrations/google-analytics), comparison pages (/vs/agencyanalytics)

**Phase 3 — Paid + Partnerships (Month 6+)**
- Google Ads: target "agency reporting software", "client reporting automation" — CPC ~$3-5 in India, ~$15-25 in US
- YouTube/Loom demos embedded in comparison pages
- Agency forums and Slack communities: once you have 10+ customers, leverage their networks
- Affiliate program: 20-30% commission for referring agencies

### Marketing Budget (Pre-Revenue)

| Channel | Monthly Budget | Notes |
|---------|---------------|-------|
| Hosting (Railway + Vercel) | ~$25/mo | Railway Hobby plan; Vercel free for this traffic level |
| Supabase | $0 (free tier) | Free tier covers 500MB + 50K MAUs |
| OpenAI | ~$0.50-2/report | GPT-4.1 input/output pricing |
| Resend | $0 (3,000 emails/mo free) | Sufficient for trial phase |
| Google Ads | $0 until revenue | |

Total pre-revenue burn: **~$25-50/month** (excludes OpenAI which is usage-based and revenue-positive from first paid user).

---

## 16. KEY TECHNICAL DECISIONS & LEARNINGS

### 1. GPT-4.1 over GPT-4o

**Decision:** Migrated from `gpt-4o` to `gpt-4.1` in Prompt 47.

**Why:** GPT-4.1 follows structured JSON output schemas more reliably — particularly for `chart_titles`, `chart_captions`, and the strict 3+3+3 list counts. GPT-4o would occasionally add a 4th win or return prose instead of JSON when the prompt was long. GPT-4.1's improved instruction-following eliminated the need for a retry loop.

**Trade-off:** GPT-4.1 is slightly more expensive per token. Acceptable given the quality improvement.

### 2. Matplotlib PNG over Native OOXML Charts

**Decision:** All charts are rendered as matplotlib PNGs embedded in PPTX — not python-pptx's native chart objects.

**Why:** Native OOXML charts require XML manipulation for 80% of styling (shadow, axis color, gridline alpha, custom fonts). Matplotlib gives complete control via Python. PNG output is pixel-perfect and renders identically in PowerPoint, LibreOffice, and email attachment. Research doc (§4) confirmed this is the right call — "keep matplotlib PNG embedding, not native OOXML."

**Trade-off:** Charts aren't editable data charts in PowerPoint — they're images. Accepted because GoReportPilot's use case is reviewed-and-sent reports, not editable charts for clients.

### 3. Template-First PPTX Architecture

**Decision:** 6 `.pptx` template files (19 slides each) ship with the backend. The generator opens the template, deletes irrelevant slides, populates `{{token}}` placeholders, embeds charts.

**Why:** All slide geometry, fonts, colors, shadows, and branding defined once in PowerPoint — no python-pptx layout computation. Adding a new visual theme = design a new `.pptx` file, zero code changes. Same pattern used by TapClicks (enterprise) and NinjaCat.

**Pitfall discovered:** `python-pptx` `drop_rel()` slide deletion leaves orphaned `SlidePart` objects. If you then call `add_slide()`, it can pick colliding filenames, overwriting new slide content with orphan content. **Solution:** Save-reload cycle after all deletions, before any duplication: `prs.save(buf); prs = Presentation(buf)`. This purges orphans entirely.

### 4. AES-256-GCM Token Encryption at Application Layer

**Decision:** All OAuth access/refresh tokens encrypted with AES-256-GCM before storage in Supabase.

**Why:** Supabase encrypts at rest, but if someone exports the DB or reads via the Supabase dashboard, tokens would be readable. Application-layer encryption means tokens are unreadable without `TOKEN_ENCRYPTION_KEY` (env var, never in DB). Key critical: **never regenerate in production** — all stored tokens become unreadable.

### 5. Supabase Storage for Logos, Ephemeral FS for Reports

**Decision:** Agency logos and client logos → Supabase Storage `logos` bucket (persistent public URLs). Generated PPTX/PDF files → ephemeral local filesystem on Railway.

**Why logos in Storage:** Logo files needed across Railway restarts and multiple requests. They're small and need to be publicly accessible for report generation.

**Why reports ephemeral:** Generated files can always be regenerated. Storing them in Supabase Storage would cost money and require cleanup jobs. Instead: if a report's `pptx_file_url` returns HTTP 410 (file gone after restart), the frontend shows a "Regenerate" button. This is a deliberate design choice, not a bug.

### 6. `_fetch_all()` Pagination for Admin Analytics

**Decision:** PostgREST (Supabase's REST layer) silently caps results at 1,000 rows. Built `_fetch_all()` helper that loops with `.range(start, end)` until a page returns fewer rows than the page size.

**Why:** Admin analytics would silently under-report after 1,000 users/reports. The bug was silent — numbers looked plausible but were wrong. Now all admin queries use `_fetch_all()`.

**Pattern:**
```python
async def _fetch_all(query_fn, page_size=1000):
    rows, start = [], 0
    while True:
        page = await query_fn(start, start + page_size - 1)
        rows.extend(page.data)
        if len(page.data) < page_size:
            break
        start += page_size
    return rows
```

### 7. Single Source of Truth for Pricing: `plans.py`

**Decision:** All billing logic that references prices or limits MUST import from `backend/services/plans.py`. No hardcoded amounts anywhere.

**Why learned:** `admin_analytics.py` originally had hardcoded INR annual prices `[9590, 19190, 33590]` that differed by 9 rupees from `plans.py` `[9599, 19199, 33599]`. Both were wrong vs the pricing doc's final recommendation of `[9590, 19190, 33590]`. The drift went unnoticed until audit. Now `_plan_monthly_revenue()` calls `get_plan()` directly.

### 8. Module-Level Memoised Currency Detection

**Decision:** `detectCurrency()` extracted to `frontend/src/lib/detect-currency.ts` with a module-level `let _memo: 'INR' | 'USD' | null = null`.

**Why:** The function was duplicated in `CurrencyPrice.tsx` and `pricing-toggle.tsx`. `Intl.DateTimeFormat().resolvedOptions().timeZone` is cheap but non-trivial; memoising it avoids repeated calls across all renders. Using module-level (not React state/ref) memo means the detection runs once per page load across all component instances.

### 9. BUILD_DATE in sitemap.ts

**Decision:** `const BUILD_DATE = new Date()` at module level, not inside the `sitemap()` function.

**Why:** Next.js server components call `sitemap()` on every crawl request. `new Date()` inside the function would report every page as "last modified = right now", defeating the purpose of `lastModified`. Module-level assignment captures the deploy time, which is the correct semantic for "when did this page content last change."

---

## 17. ACCOUNTS & CREDENTIALS SUMMARY

| Service | URL | Account | Status | Notes |
|---------|-----|---------|--------|-------|
| **Supabase** | supabase.com | sapienbotics@gmail.com | ✅ Active | Project: kbytzqviqzcvfdepjyby; free tier |
| **Vercel** | vercel.com | sapienbotics@gmail.com | ✅ Active | Deploys from GitHub on push; root dir: `frontend/` |
| **Railway** | railway.app | sapienbotics@gmail.com | ✅ Active | Dockerfile deploy from `backend/`; Hobby plan |
| **Namecheap** | namecheap.com | (Saurabh's account) | ✅ Active | Domain: `goreportpilot.com`; DNS managed here |
| **Google Cloud Console** | console.cloud.google.com | sapienbotics@gmail.com | ✅ Active — Testing mode | OAuth app: ReportPilot; scopes: analytics.readonly, adwords, webmasters.readonly |
| **Meta Developer Portal** | developers.facebook.com | (Saurabh's FB account) | ✅ Active — Dev mode | App: ReportPilot; needs `ads_read` App Review |
| **OpenAI** | platform.openai.com | sapienbotics@gmail.com | ✅ Active | Model: gpt-4.1; pay-as-you-go |
| **Resend** | resend.com | sapienbotics@gmail.com | ✅ Active | Domain: goreportpilot.com; ⚠️ DNS records must be verified |
| **Razorpay** | razorpay.com | (Saurabh's account) | ✅ Live mode | ⚠️ 12 plan IDs not yet created |
| **GitHub** | github.com | SapienBotics | ✅ Active | Repo: `reportpilot`; push triggers auto-deploy |
| **Google Ads API** | ads.google.com | sapienbotics@gmail.com | ✅ Active — Test token | Developer token: test-only; login customer: 8152475096 |

### Key Credential Locations

| Secret | Where to find it |
|--------|-----------------|
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard → Settings → API → service_role |
| `SUPABASE_ANON_KEY` | Supabase Dashboard → Settings → API → anon/public |
| `GOOGLE_CLIENT_ID` / `SECRET` | Google Cloud Console → APIs & Services → Credentials |
| `META_APP_ID` / `SECRET` | Meta Developer Portal → App → Settings → Basic |
| `TOKEN_ENCRYPTION_KEY` | Railway env vars — **NEVER regenerate** |
| `OPENAI_API_KEY` | platform.openai.com → API Keys |
| `RAZORPAY_KEY_ID` / `KEY_SECRET` | Razorpay Dashboard → Settings → API Keys |
| `RESEND_API_KEY` | Resend Dashboard → API Keys |

---

## 18. KEY FILE PATHS

### Backend

| File | Description |
|------|-------------|
| `backend/main.py` | FastAPI entry point — 15 router mounts, CORS, lifespan APScheduler loop, `/health` endpoint |
| `backend/config.py` | Pydantic settings — all env vars with auto-derive for redirect URIs |
| `backend/services/plans.py` | **Single source of truth for pricing** — plan limits, features, prices; import from here always |
| `backend/services/report_generator.py` | **Main file — most complex** (~2,100 lines) — PPTX + PDF orchestration, slide selection, token replacement, chart embedding, save-reload cycle |
| `backend/services/chart_generator.py` | matplotlib chart rendering — 19 chart types, 3 themes, Okabe-Ito palette, action titles, direct labels, sparklines, 300 DPI |
| `backend/services/ai_narrative.py` | GPT-4.1 prompt engine — SCQA structure, 4 tones, 13 languages, 3+3+3 enforcement, `chart_titles` / `chart_captions` JSON keys |
| `backend/services/slide_selector.py` | Smart KPI scoring and slide pool selection — which of 19 slides to keep/delete per data availability |
| `backend/services/csv_parser.py` | Production-grade CSV parser — encoding detection, delimiter sniffing, K/M/B, European decimals, brand capitalization |
| `backend/services/email_service.py` | Resend integration — `httpx` POST to `api.resend.com/emails`; activated when `RESEND_API_KEY` non-empty |
| `backend/services/encryption.py` | AES-256-GCM encrypt/decrypt for OAuth tokens |
| `backend/services/scheduler.py` | APScheduler — checks `scheduled_reports` table, generates and optionally sends on schedule |
| `backend/routers/billing.py` | Razorpay subscription CRUD — create, activate, change-plan, cancel, payment verification |
| `backend/routers/admin_analytics.py` | Admin analytics with `_fetch_all()` pagination and `_plan_monthly_revenue()` from `plans.py` |
| `backend/routers/reports.py` | Report generate, list, get, download PPTX/PDF, share link endpoints |
| `backend/routers/auth.py` | OAuth callbacks — GA4, Meta Ads, Google Ads, Search Console token exchange |
| `backend/middleware/plan_enforcement.py` | Client limit + feature gate middleware — called before client create, feature access |
| `backend/templates/pptx/` | 6 `.pptx` template files (modern_clean, dark_executive, colorful_agency, bold_geometric, minimal_elegant, gradient_modern) — 19 slides each |

### Frontend

| File | Description |
|------|-------------|
| `frontend/src/app/page.tsx` | Landing page — hero, integration logos, features (9 cards), comparison table, pricing, FAQ, CTA |
| `frontend/src/app/layout.tsx` | Root layout — title, full OG/Twitter metadata, sitemap/robots registered, AnalyticsProvider |
| `frontend/src/app/sitemap.ts` | Next.js sitemap — `BUILD_DATE` module-level (not `new Date()` in function) |
| `frontend/src/app/robots.ts` | Next.js robots.txt |
| `frontend/src/app/dashboard/clients/[clientId]/page.tsx` | Client detail page — 5 tabs (Overview, Integrations, Reports, Schedules, Settings); `schedForm` state, `handleSaveSchedule()` |
| `frontend/src/app/dashboard/reports/[reportId]/page.tsx` | Report preview — inline editing, per-section regenerate, send dialog, download buttons |
| `frontend/src/app/dashboard/billing/page.tsx` | Billing page — current plan card, usage bar, trial countdown, plan comparison, payment history |
| `frontend/src/app/dashboard/settings/page.tsx` | Settings — account, agency branding, AI preferences, email settings, notifications, danger zone |
| `frontend/src/app/admin/analytics/page.tsx` | Admin analytics dashboard — 6 stat cards, Tailwind bar charts, funnel, country breakdown, auto-refresh 5min |
| `frontend/src/components/clients/tabs/SchedulesTab.tsx` | Schedules tab — frequency/day/time/auto-send/template/attachment_format/visual_template fields |
| `frontend/src/components/landing/CookieConsent.tsx` | GDPR cookie consent banner — localStorage-based, dispatches `cookie_consent_change` event |
| `frontend/src/components/AnalyticsProvider.tsx` | GA4 gating — loads gtag.js only after cookie consent; GA ID: `G-GMTY15QRRZ` |
| `frontend/src/components/billing/UpgradePrompt.tsx` | Reusable upgrade prompt component for gated features |
| `frontend/src/lib/detect-currency.ts` | Module-level memoised timezone-based INR/USD detection — shared by CurrencyPrice + PricingToggle |
| `frontend/src/lib/api.ts` | Axios wrapper for FastAPI backend — base URL from `NEXT_PUBLIC_API_URL` |
| `frontend/src/types/index.ts` | Shared TypeScript interfaces for all entities |
| `frontend/middleware.ts` | Next.js middleware — protects all `/dashboard/*` and `/admin/*` routes |

### Supabase

| File | Description |
|------|-------------|
| `supabase/migrations/001_initial_schema.sql` | Core 8 tables with RLS, indexes, triggers |
| `supabase/migrations/004_whitelabel_scheduling.sql` | Agency branding on profiles, scheduled_reports with template+send_to_emails |
| `supabase/migrations/006_billing.sql` | subscriptions + payment_history tables |
| `supabase/migrations/008_shared_reports.sql` | shared_reports + report_views tables |
| `supabase/migrations/011_admin_dashboard.sql` | is_admin/is_disabled on profiles, admin_activity_log, gdpr_requests |

### Docs

| File | Description |
|------|-------------|
| `docs/HANDOVER-APRIL-11-2026.md` | **This document** — comprehensive project state as of April 11, 2026 |
| `docs/REPORT-QUALITY-RESEARCH-2026.md` | Research: competitor visuals, professional standards, python-pptx capabilities, gap analysis |
| `docs/LANDING-PAGE-IMPROVEMENTS-2026.md` | Research: full audit, content mismatches, conversion optimization, prioritized fix list |
| `docs/PRICING-STRATEGY-2026.md` | Definitive pricing recommendation with competitor matrix, WTP analysis, India pricing |
| `docs/DEPLOYMENT-GUIDE.md` | Step-by-step: Railway + Vercel + OAuth redirect URIs + Razorpay + Resend setup |
| `docs/REMAINING-FEATURES.md` | Original feature checklist (Blocks 1-8) — partially superseded by this handover |
| `docs/CHAT-HANDOVER-MARCH-2026.md` | Earlier handover covering prompts 1-27 in detail |
| `CLAUDE.md` | Master project instructions — tech stack, conventions, what NOT to do |

---

*End of document. GoReportPilot handover — April 11, 2026. 64 prompts. 18 sections.*
