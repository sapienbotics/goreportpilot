# GoReportPilot — Comprehensive Project Handover
**Date:** 2026-04-22
**Author:** Claude Code (Opus 4.7, xhigh) on behalf of Saurabh Singh / SapienBotics
**Purpose:** Self-contained handover for any future Claude session (web + code) to resume with **zero context loss**. No TLDR shortcuts — every relevant detail recorded and cross-verified against the live repository at `F:\Sapienbotics\ClaudeCode\GoReportPilot\`.
**Repo verified against:** 143 commits on `main`, HEAD = `c79c406` ("feat: shared UnreadCommentsProvider keeps badges live", 2026-04-21 20:02 IST).

---

## 1. EXECUTIVE SUMMARY

**GoReportPilot** is an AI-powered client-reporting SaaS for digital marketing agencies and freelancers. Users connect their clients' marketing accounts (GA4, Meta Ads, Google Ads, Search Console) + upload CSVs; the backend pulls the data, GPT-4.1 writes diagnostic narrative in one of 13 languages and 4 tones, and a report generator exports a branded PowerPoint deck + PDF via LibreOffice. Reports can be emailed to clients, shared via public link (password + expiry + comments), or scheduled on a recurring cadence.

**Current phase:** LIVE in production, pre-launch. All core features shipped. Awaiting Google OAuth verification + Meta App Review, then GTM.

**Critical blockers at a glance:**
1. **Google OAuth production verification** — demo video submitted ([YouTube](https://youtu.be/YJ1KYOAIxQA)), awaiting Google review.
2. **Meta App Review** — **REJECTED on 2026-04-21**. 6 of 7 requested permissions denied (see §10 for details). Need to rebuild the review submission with clearer justification, enhanced screencasts, and better app-state reproduction.
3. **Razorpay KYC** — still needs final sign-off for INR international card settlement.
4. **Email infrastructure finalization** — Resend sending works; Zoho receiving on `support@` / `info@` needs final routing confirmation.
5. **Auth UX polish** — forgot password / email confirmation work functionally, Supabase emails still need Saurabh's branded sender templates in the Supabase dashboard.
6. **LinkedIn banner upload** — pending.

**Project trajectory:** MVP is in a launchable state. The team must unblock Meta + Google before paid customers can onboard their GA4 + Meta accounts without encountering the "unverified app" scare screen.

---

## 2. PROJECT ORIGIN & RESEARCH

### 2.1 Market research summary
Agencies (2-15 clients) and freelance marketers spend 4-8 hours per client/month on monthly reporting. Industry primary research (summarised in `docs/USER-RESEARCH-APRIL-2026.md` and `docs/REPORT-QUALITY-RESEARCH-2026.md`) revealed three dominant pain points:
1. **Data aggregation is manual** — copy/paste from GA4, Meta Ads Manager, Google Ads, Search Console, plus CSVs.
2. **Narrative writing is generic** — junior staff write vague "traffic went up" sentences that don't diagnose *why* or prescribe *what to do*.
3. **Visual polish is costly** — incumbents charge by client or by dashboard, making annual cost painful for small agencies.

### 2.2 Competitor analysis conclusions
Detailed in `docs/COMPETITOR-FEATURE-MATRIX-2026.md` (12 tools × 7 dimensions). Highlights:
- **AgencyAnalytics** — strong integrations, weak AI narrative, priced per client (expensive at scale).
- **DashThis** — interactive dashboards, no automated narrative, priced per dashboard.
- **Whatagraph** — decent reports + Whatagraph IQ "AI insights" but the AI reads like a KPI recap, not a diagnosis.
- **Swydo** — modest AI features, clean brand, mid-market pricing.
- **Looker Studio** — free but zero narrative, zero automation, zero branding.

**Positioning gap:** No incumbent combines **(a) AI narrative with actual campaign-level attribution**, **(b) branded PPT/PDF output (not an interactive dashboard)**, and **(c) simple client-count pricing with unlimited reports**. GoReportPilot occupies that intersection.

### 2.3 Why GoReportPilot's positioning was chosen
- **"Agency's senior strategist in software form."** Not a dashboard, not a template — the product writes the diagnostic that a junior would take 2 hours to write, in 30 seconds.
- **PowerPoint + PDF deliverables**, not interactive dashboards — mirrors how agencies actually hand off work to clients.
- **Client-count pricing with unlimited reports** — flipping the industry norm.

### 2.4 Pricing strategy rationale (client-count moat vs report-count)
Research in `docs/PRICING-STRATEGY-2026.md` + `docs/COMPETITOR-FEATURE-MATRIX-2026.md`:
- Every competitor of note meters on either clients, dashboards, or data pulls. Report generation is free to them too; they ration access via client seat.
- **GoReportPilot meters only on client count.** Reports per client are unlimited. Freelancers running 5 clients can regenerate a report 20× if they want and pay $19/mo flat.
- **The moat:** report unit economics are ~₹1.50/report (GPT-4.1 cost per narrative + marginal Railway/matplotlib CPU). Even an agency user generating 5 reports × 15 clients × 10 refreshes/mo = 750 reports at ₹1.50 = ₹1,125 AI cost at ₹3,499 plan revenue → ≈68% gross margin. Users cannot burn us on compute.
- **Reversed psychology:** By removing the "limit worry", acquisition is frictionless — the user doesn't have to calculate whether a plan "covers" their usage.

### 2.5 Unit economics (~₹1.50/report)
- GPT-4.1 per narrative: input ≈ 3-4K tokens + output ≈ 1-2K tokens → ~₹0.90 per report at 2026 OpenAI pricing.
- matplotlib + python-pptx + LibreOffice CPU: ≈ ₹0.20 per report (Railway compute amortised).
- Supabase row writes + file upload: negligible.
- Total delivered cost ≈ ₹1.10-₹1.60 → rounding to **~₹1.50/report**.

### 2.6 Reference docs informing decisions
In `docs/`:
- `PRICING-STRATEGY-2026.md` — full pricing rationale with competitor data.
- `COMPETITOR-FEATURE-MATRIX-2026.md` — 12 tools × 7 dimensions.
- `USER-RESEARCH-APRIL-2026.md` — qualitative interviews + top-10 pain points.
- `REPORT-QUALITY-RESEARCH-2026.md` — why narratives fail + diagnostic fix pattern.
- `LANDING-PAGE-IMPROVEMENTS-2026.md` — 2026 conversion benchmarks.
- `HANDOVER-APRIL-11-2026.md` — earlier handover doc, prompts 1-70.
- `CHAT-HANDOVER-MARCH-2026.md` — prompts 1-48 from the March build sprint.
- `COMPLETE-PROJECT-REPORT.md` — full project report.
- `DEPLOYMENT-GUIDE.md` — Railway + Vercel + Supabase deploy recipe.
- `DESIGN-SYSTEM-PLAN.md` — precursor to Phase A/B theme unification.
- `REMAINING-FEATURES.md` — pre-MVP checklist.

In `.claude/tasks/` (phase completion docs — every phase is reviewable):
- `phase-roadmap.md` — master roadmap (Phase 1 → 7).
- `phase-1-completion.md`, `phase-1b-completion.md`, `phase-1-snapshot-audit.md`
- `phase-2-completion.md`, `phase-2-fix-completion.md`
- `phase-3-completion.md` + 5 fix/parity variants
- `phase-4-completion.md` (Diagnostic Narrative v2)
- `phase-A-completion.md`, `phase-B-completion.md` (Design System Option F)

---

## 3. FOUNDER & BUSINESS CONTEXT

| Item | Value |
|---|---|
| Founder | Saurabh Singh (CEO, SapienBotics) |
| Location | Bareilly, Uttar Pradesh, India |
| Legal entity | Sahaj Bharat (sole proprietorship under Richa Singh) |
| GSTIN | 09CYVPS3328G1ZQ |
| Trade brand (tech) | SapienBotics |
| Product brand | GoReportPilot |
| Founder email | sapienbotics@gmail.com |
| Test account (primary) | biotaction.saurabh@gmail.com |
| Test account UUID | 5a91226a-6cef-41cc-894e-5055a25a7dea |
| Test client name | Videogenie |
| Test client UUID | 5dfa44ea-b73b-4e15-b21f-139eebd7164f |

**Working style note (for future Claude):** Saurabh pushes back firmly when reasoning is lazy or when the fix is narrow instead of systemic. Treat him as a product-expert peer, not a beginner. Always prefer *generic/systemic* fixes over *targeted patches*, and split risky work into safe incremental prompts.

---

## 4. INFRASTRUCTURE — COMPLETE INVENTORY

| Layer | Service | URL / Identifier | Notes |
|---|---|---|---|
| Frontend hosting | Vercel | `goreportpilot.vercel.app` → `goreportpilot.com` | Auto-deploy from `main` branch |
| Backend hosting | Railway | `goreportpilot-production.up.railway.app` | Docker image built from `backend/Dockerfile`, LibreOffice baked in |
| Database | Supabase (PostgreSQL) | `kbytzqviqzcvfdepjyby.supabase.co` | RLS on every user-data table |
| Auth | Supabase Auth | email/password + Google SSO | JWTs via httpOnly cookies (no localStorage) |
| Source | GitHub | `sapienbotics/goreportpilot` | |
| Local dev root | `F:\Sapienbotics\ClaudeCode\GoReportPilot\` | Windows 11 | Python venv at `backend/venv/` |
| Email (outbound) | Resend | `reports@goreportpilot.com` | DKIM verified |
| Email (inbound) | Zoho Mail (free tier) | `support@`, `info@` aliases | Final routing config pending |
| Payments | Razorpay | 12 plans — 3 tiers × 2 currencies × 2 cycles | KYC in progress |
| AI | OpenAI | GPT-4.1 (model: `gpt-4.1`) | Migrated from GPT-4o in commit `ff12cfe` (2026-03-30) |
| GA4 tracking | Google Analytics | `G-GMTY15QRRZ` | Gated on GDPR cookie consent |
| DNS | Namecheap → Vercel | `goreportpilot.com` | Domain migrated 2026-04-05 (commit `78a10b2`) |
| File storage | Supabase Storage | `logos` bucket (public) + `cover_heroes/` subfolder | Agency + client logos + Phase 3 cover heroes |
| Report files | Local FS (Railway) | `backend/generated_reports/` | Ephemeral; 410 → regenerate pattern (commit `94d4f8d`) |
| Token encryption | `cryptography` 42.x | AES-256-GCM | Key in `TOKEN_ENCRYPTION_KEY` env var |

**LibreOffice inside Docker:** `backend/Dockerfile` installs LibreOffice 7.x + Noto font family (Devanagari, CJK, Arabic, etc.) so PPTX→PDF works across all 13 translation languages.

---

## 5. TECH STACK (COMPLETE)

### 5.1 Frontend (`frontend/package.json`)
```
next                14.2.35
react / react-dom   ^18
typescript          ^5
tailwindcss         ^3.4.1
@supabase/ssr       ^0.9.0
@supabase/supabase-js ^2.78.0
axios               ^1.13.6
react-hook-form     ^7.71.2
@hookform/resolvers ^5.2.2
zod                 ^4.3.6
class-variance-authority  ^0.7.1
clsx                ^2.1.1
tailwind-merge      ^3.5.0
tw-animate-css      ^1.4.0
lucide-react        ^0.577.0
sonner              ^2.0.7
next-nprogress-bar  ^2.4.7
next-themes         ^0.4.6
@base-ui/react      ^1.3.0
shadcn              ^4.0.8
```
DevDependencies: `@types/node ^20`, `@types/react ^18`, `eslint ^8`, `eslint-config-next 14.2.35`, `postcss ^8`.

### 5.2 Backend (`backend/requirements.txt`)
```
fastapi==0.110.0
uvicorn[standard]==0.27.1
httpx>=0.24,<0.28
python-dotenv==1.0.1
pydantic>=2.6,<2.8
pydantic-settings>=2.2,<2.5
supabase==2.7.4
openai==1.14.0              # GPT-4.1 model id
python-pptx==0.6.23
reportlab==4.1.0            # Latin-only PDF fallback
matplotlib==3.8.3           # 19 chart types, 300 DPI
cryptography==42.0.5        # AES-256-GCM token encryption
python-multipart==0.0.9
pillow==10.2.0
facebook-business==19.0.0   # Meta Marketing API
google-analytics-data==0.18.5
google-ads==24.1.0          # MCC: 815-247-5096
google-auth==2.28.1
google-auth-httplib2==0.2.0
resend==0.8.0
stripe==8.4.0               # Present but unused — Razorpay is primary
razorpay==2.0.1             # See commit 0683f9c for pkg_resources fix
slowapi==0.1.9              # Rate limiting on public endpoints
setuptools>=69.0.0          # Needed by razorpay (pkg_resources)
chardet>=5.0,<6.0
```
**Excluded / deprecated** — `Make.com`, `n8n`-runtime-as-service, and Stripe (present in requirements but not wired; do not re-enable). `backend/services/mock_data.py` exists for pre-integration dev — production uses only real data (commit `a7e8ad8`).

### 5.3 Runtime binaries inside backend Docker
- LibreOffice 7.x+ (headless; primary PPTX→PDF path; supports all Unicode scripts).
- Noto font family (Devanagari, CJK, Arabic, Hebrew, Thai, etc.).
- `libgl1` replaced `libgl1-mesa-glx` for Debian Trixie (commit `d602a03`).

### 5.4 Local dev
- Windows 11, Python 3.12 venv at `backend/venv/`, Node 20+.
- LibreOffice at `C:\Program Files\LibreOffice\program\soffice.exe`.
- Local URL: `http://localhost:3000` (Next dev) + `http://localhost:8000` (FastAPI).
- **Claude Code must never auto-start dev servers.** Saurabh runs them manually.

---

## 6. FEATURE INVENTORY (EXHAUSTIVE)

### 6.1 Auth & Onboarding
- **Supabase Auth** — email/password signup, email confirmation enforcement, forgot password + reset, Google SSO, account deletion self-service.
- **Admin guard** — `profiles.is_admin` flag, checked in `frontend/src/app/admin/layout.tsx` + `backend/routers/admin.py`.
- **Onboarding checklist** — `frontend/src/components/dashboard/onboarding-checklist.tsx` prompts new users through "add client → connect integration → generate first report" (commit `58880a7`, 2026-04-09).
- **Forgot password / reset pages** — `frontend/src/app/forgot-password/`, `frontend/src/app/reset-password/`.
- **Confirm-email page** — `frontend/src/app/confirm-email/`.
- **Branded auth flow** — commit `1d6d026`. Supabase email templates still need dashboard-side update.

### 6.2 Client management
- **Client CRUD** — `backend/routers/clients.py` + `frontend/src/app/dashboard/clients/`.
- **Logo upload** — Supabase storage `logos` bucket, persistent (commit `94d4f8d` fix).
- **AI tone** — one of `professional | conversational | executive | data_heavy`.
- **Language** — 13 supported (commit `d9578db` completed multi-language coverage end-to-end).
- **Report config** — JSONB column, stores per-client section enable/disable + customization.
- **Business context field** — `frontend/src/components/clients/BusinessContextField.tsx` + AI-assist + quality indicator (commit `edff2d4`, 2026-04-21). Feeds `context_enhancer.py` which injects business context into the narrative prompt.
- **Client detail page** — 7 tabs: Overview, Integrations, Reports, Schedules, Design, Goals, Settings (`frontend/src/components/clients/tabs/`).

### 6.3 Integrations
- **GA4** — `backend/services/google_analytics.py` (341 LOC). 6 API calls per pull. OAuth at `/api/auth/google-analytics`. Scope: `analytics.readonly`.
- **Meta Ads** — `backend/services/meta_ads.py` (242 LOC). Short-lived → long-lived token exchange. Scope: `ads_read, ads_management, business_management, pages_read_engagement, pages_show_list, public_profile`. **6 of 7 denied 2026-04-21.**
- **Google Ads** — `backend/services/google_ads.py` (443 LOC). MCC: `815-247-5096`. Scope: `adwords`. Wired into production pull in commit `1557a1f` (Phase 1b — discovered it was defined-but-unused).
- **Search Console** — `backend/services/search_console.py` (395 LOC). Scope: `webmasters.readonly`. Also wired in Phase 1b.
- **Unified Google OAuth callback** — single route handles GA4, Google Ads, Search Console (commit `e85eead8`). Phase 3 fix `a757873` resolved duplicate connections + false "expiring_soon" status.
- **CSV upload** — `backend/services/csv_parser.py` (670 LOC). 5 templates. Production-grade. `backend/routers/csv_upload.py` + `frontend/src/components/clients/CSVUploadDialog.tsx` + `CSVPreviewTable.tsx`.
- **Connection health monitor (Phase 2)** — `backend/services/health_check.py` (777 LOC). 6-hour cadence via scheduler. Alert emails on broken/expiring. `frontend/src/components/dashboard/connection-health-widget.tsx`. Pre-generation gate: reports blocked (HTTP 422) if relevant connection is broken/expiring_soon.
- **Dedupe** — migration `015_dedupe_connections.sql` cleaned duplicate rows introduced by early OAuth flow bugs.

### 6.4 Report generation pipeline
- Entry point: `POST /api/reports/generate` in `backend/routers/reports.py` (1883 LOC — the largest router).
- Orchestration in `_generate_report_internal`: pull data (GA4 + Meta + Google Ads + SC + CSVs) → compute top_movers → AI narrative → chart_generator → report_generator (PPTX) → LibreOffice (PDF) → Supabase snapshot save.
- Regenerate: `POST /api/reports/{id}/regenerate`. Mirror of _generate path with same snapshot hooks (Phase 1 made this idempotent).
- Expired file handling: 410 response triggers frontend to call regenerate (commit `94d4f8d`).
- Trial: 5-report limit + blocked for expired trials (commits `0053858`, `deff25f`, `e19d30e`).
- Scheduler: `backend/services/scheduler.py` (291 LOC) — 15-minute APScheduler tick, smart `next_run_at` computation (commit `70e14bc`).

### 6.5 PPTX / PDF generation
- `backend/services/report_generator.py` — **2662 LOC, by far the largest file**. Orchestrates 6 visual templates × 19 slides each.
- 6 Canva-derived templates, all in `backend/templates/pptx/`:
  - `modern_clean.pptx`, `dark_executive.pptx`, `colorful_agency.pptx`, `bold_geometric.pptx`, `minimal_elegant.pptx`, `gradient_modern.pptx`.
- Template creation scripts in `scripts/create_*.js` (6 files + `create_all_templates.js`) + audit at `scripts/audit_pptx.py`.
- Chart generator: `backend/services/chart_generator.py` (1434 LOC). 19 chart types, 3 themes, 300 DPI.
- Slide selector: `backend/services/slide_selector.py` (501 LOC). KPI-scored smart selection based on data availability.
- PPTX→PDF:
  - Primary: LibreOffice headless (all Unicode scripts).
  - Fallback: ReportLab (Latin-only, commit `9254aec`).
- Recent fixes: sparklines on KPIs + direct-label charts + bad-month detection (commit `89e9b88`); logo overflow + campaign axis (commit `79e3012`); smarter title truncation (commit `353d3c4`); date format + zero-conv axis (commit `86a8da2`); KPI color inversion (commit `e562464`).

### 6.6 AI narrative (Phase 4 — Diagnostic Upgrade)
- `backend/services/ai_narrative.py` (477 LOC). GPT-4.1, 4 tones, 13 languages, 6 primary sections + 3 supplementary.
- **Phase 4 (commit `c50c865`, 2026-04-21)** — critical quality upgrade. Before Phase 4 the AI wrote generic filler ("paid advertising improved this month"); after Phase 4 it names specific campaigns, queries, pages as drivers.
- New module: `backend/services/top_movers.py` (475 LOC). Pure function — extracts ranked campaigns/queries/pages/sources/devices from already-pulled data. Injects them as a `TOP MOVERS` block into the user prompt.
- System prompt gained **DIAGNOSTIC STANDARD** + **RECOMMENDATION STANDARD** clauses rejecting vague causal filler.
- Call tuning: `max_tokens 2000→3500`, `temperature 0.7→0.6`.
- Verification script at `backend/scripts/verify_diagnostic_narrative.py`.
- Known Phase 4 deferrals: `{text, evidence[]}` schema change deferred; "Show reasoning" UI deferred; numeric-validator post-processor deferred; change-based movers (vs last period) deferred until Phase 1 snapshots accumulate.
- Business context enhancer: `backend/services/context_enhancer.py` (72 LOC) — Phase 4.5 layer injecting business-context into narrative (commit `edff2d4`).

### 6.7 Design system (Phase 3 / Phase A-B — 6 themes)
- Migration `017_design_system.sql` — unified "cover_design_preset" + "visual_template" into a single `clients.theme` column governing the whole deck.
- 6 themes: `modern_clean`, `dark_executive`, `colorful_agency`, `bold_geometric`, `minimal_elegant`, `gradient_modern`.
- `backend/services/theme_layout.py` (231 LOC).
- Cover customization: migration `014_cover_customization.sql` + `backend/services/cover_customization.py` (548 LOC). Columns `cover_headline`, `cover_subtitle`, `cover_hero_image_url`, `cover_design_preset`.
- `DesignTab.tsx` in client detail page consolidates theme + cover overrides (Phase B, commit `54ff14d`).
- `Phase 3 v2.1` (commit `f61118e`) fixed alignment + "subtitle as tagline" + CSS-preview parity.
- Phase 3 had ~10 iterative fixes (commits `a39948f` → `dc8c4c8`) as template parity was tuned.
- THUMBNAIL_VERSION bumped to `v2-2` for cache-bust (commit `f86ab67`).

### 6.8 Scheduling
- Migration `004_whitelabel_scheduling.sql`.
- `backend/routers/scheduled_reports.py` (281 LOC) + `backend/services/scheduler.py` (291 LOC).
- APScheduler runs every 15 min. Smart `next_run_at` calc (commit `70e14bc`).
- Frequencies: weekly, biweekly, monthly. Timezone selector (commit `ce02029`).
- Attachment format + visual template per schedule (commit `d80e752`).
- `frontend/src/components/clients/tabs/SchedulesTab.tsx` — scheduler timing note added for UX clarity (commit `8135da0`).

### 6.9 White-label branding
- Agency logo, brand color, client logo, "Powered by GoReportPilot" badge (on Starter only, removed on Pro+).
- Agency name on cover slide (commit `ff3a463`).
- Starter plan: `powered_by_badge: true`; Pro + Agency: `false`.
- Migration `004_whitelabel_scheduling.sql` + `005_profiles_missing_columns.sql`.

### 6.10 Sharing & public reports (Phase 5)
- Migration `008_shared_reports.sql` — `shared_reports` + `report_views` tables. Optional password + expiry + view tracking.
- Phase 5A backend (commit `c8c56d5`): `backend/routers/comments.py` (575 LOC) + migration `019_report_comments.sql`. New `report_comments` table: slide_number (nullable) + section_key (nullable) + resolve workflow.
- Phase 5B frontend (commit `2a670b9`): `frontend/src/components/shared/CommentsPanel.tsx` + `frontend/src/app/shared/[hash]/` enhanced.
- Granular comment badges + fixed view-analytics (commit `0009eff`).
- Unresolved-comment badge on All Reports list rows (commit `090d473`).
- Shared `UnreadCommentsProvider` keeps badges live (commit `c79c406`, HEAD).
- Anti-spam: `slowapi` rate limiting + honeypot + length guard.
- Public shared viewer at `frontend/src/app/shared/[hash]/page.tsx` — no auth required.

### 6.11 Billing & subscriptions
- `backend/routers/billing.py`, `backend/services/razorpay_service.py` (123 LOC), `backend/routers/webhooks.py`.
- Migration `006_billing.sql` + `012_fix_unpaid_subscriptions.sql`.
- 12 Razorpay plans: Starter / Pro / Agency × Monthly / Annual × INR / USD.
- Currency detection: `frontend/src/lib/detect-currency.ts` — `Asia/Kolkata` timezone → INR; else USD. No toggle (commit `8874cc7`).
- **Critical fix (commit `ca60ab9`)**: Never write plan name to DB until Razorpay payment is verified — reverse-lookup from `razorpay_plan_id` only. Prevents wrong-plan assignment on failed payments.
- Webhook-based subscription lifecycle management.
- Payment history table + admin view.
- Delivery policy added to Terms page for Razorpay international compliance (commit `10bbb37`).

### 6.12 Goals & Alerts (Phase 6)
- Migration `018_goals_alerts.sql` — `client_goals` table + `alerts_sent` JSONB + `alert_emails` override.
- Phase 6A backend (commit `06e0773`): `backend/services/goal_checker.py` (443 LOC) + `backend/routers/goals.py` (265 LOC).
- Phase 6B frontend (commit `93b4e72`): `frontend/src/components/clients/tabs/GoalsTab.tsx` + trial limit override (triallers get 3 goals — Pro limits — so they can evaluate the feature).
- Metric targets per-client: operator + value + period (weekly / monthly).
- Idempotent breach emails (once per streak) + resolution emails when back above target.
- Phase 2 integration — goals skip evaluation if the client's relevant connection is broken/warning.
- Per-plan gates: Starter = **1** goal/client, Pro = **3**, Agency = **999** (effectively unlimited). Source: `backend/services/plans.py::get_goal_limit`.

### 6.13 Client Comments (Phase 5) — see §6.10

### 6.14 Business Context AI enhancement
- Migration — no schema change; lives on `clients.business_context` (added earlier).
- `backend/services/context_enhancer.py` (72 LOC) — injects business context into AI narrative prompt.
- Quality indicator surfaces in UI at `BusinessContextField.tsx` (commit `edff2d4`). AI-assist button rewrites the raw text into structured context.

### 6.15 Settings, legal, polish
- **Settings page** — 5 tabs (Account, Branding, AI, Email, Notifications) at `frontend/src/app/dashboard/settings/page.tsx`.
- **Admin dashboard** — `/admin` with overview, users, subscriptions, connections, reports, system, GDPR (commit `82bebb4`). Admin analytics dashboard (commit `aee6616`) with metrics, charts, funnel, country breakdown.
- **Cookie consent** — `frontend/src/components/CookieConsent.tsx` + `AnalyticsProvider.tsx` gates GA4 tracking (commit `d9781f0`).
- **Navigation progress bar** — `next-nprogress-bar` + loading skeletons (commit `bbe5ee6`).
- **Legal pages** — `/privacy`, `/terms`, `/contact`, `/refund`.
- **Domain migration** — `reportpilot.app` → `goreportpilot.com` (commit `78a10b2`).
- **Mobile responsive** — full audit in commit `216bdd4`.
- **Rate limiting** — `slowapi` on public endpoints (commit `7a19320`).
- **Self-service account deletion** — same commit.
- **Logo overflow / padding fixes** — commits `79e3012`, `353d3c4`.

---

## 7. DATABASE SCHEMA — MIGRATIONS 001-019

Run manually in Supabase Dashboard → SQL Editor. Never via Supabase CLI.

| # | File | LOC | Purpose |
|---|---|---|---|
| 001 | `001_initial_schema.sql` | 426 | All core tables (profiles, clients, connections, reports, data_snapshots, report_templates) + RLS + triggers + seed default template |
| 002 | `002_add_currency_to_connections.sql` | 8 | Adds `currency` column to connections |
| 003 | `003_report_customization.sql` | 50 | Report template JSONB customization fields |
| 004 | `004_whitelabel_scheduling.sql` | 73 | `scheduled_reports` table + agency branding columns |
| 005 | `005_profiles_missing_columns.sql` | 14 | Agency name / brand color / phone / tz columns |
| 006 | `006_billing.sql` | 56 | `subscriptions` + `payment_history` tables |
| 007 | `007_add_language.sql` | 6 | `clients.language` default `en` |
| 008 | `008_shared_reports.sql` | 70 | `shared_reports` + `report_views` |
| 009 | `009_widen_platform_constraint.sql` | 21 | CHECK constraint widened for `csv_<slug>` platform values |
| 010 | `010_storage_logos_bucket.sql` | 43 | Create `logos` bucket + RLS |
| 011 | `011_admin_dashboard.sql` | 42 | `admin_activity_log`, `gdpr_requests`, `profiles.is_admin` |
| 012 | `012_fix_unpaid_subscriptions.sql` | 32 | Data hygiene — null plan on unpaid |
| 013 | `013_connection_health.sql` | 48 | `last_health_check_at`, `health_status`, `alerts_sent`, CHECK + index (Phase 2) |
| 014 | `014_cover_customization.sql` | 36 | 4 cover_* columns + CHECK on preset (Phase 3) |
| 015 | `015_dedupe_connections.sql` | 50 | De-dupes duplicate OAuth connection rows |
| 016 | `016_report_customization_expansion.sql` | 84 | Expanded customization fields |
| 017 | `017_design_system.sql` | 80 | `clients.theme` unifies cover preset + visual template (Phase A/B) |
| 018 | `018_goals_alerts.sql` | 107 | `client_goals` + alerts_sent + alert_emails (Phase 6) |
| 019 | `019_report_comments.sql` | 114 | `report_comments` + `profiles.comment_notifications_enabled` (Phase 5) |

**Total:** 1,360 lines of SQL across 19 migrations. RLS enabled on every user-data table.

### Key table purposes
- **profiles** — extends `auth.users`. Plan, agency branding, timezone, is_admin, `comment_notifications_enabled`.
- **clients** — belongs to agency user. Name, industry, logo, AI tone, language, theme, cover_*, business_context, report_config (JSONB).
- **connections** — OAuth per platform. Encrypted tokens, account IDs, `status`, `health_status` (ok / warning / broken / expiring_soon), `alerts_sent` (JSONB idempotency).
- **reports** — raw_data, ai_narrative, user_edits, metadata.
- **data_snapshots** — Phase 1 infra. Cached API data per report — **seeds Phase 7 MoM/YoY when it has 3+ months of history**.
- **subscriptions** — plan, status, razorpay_*, trial_ends_at, cancel_at_period_end.
- **payment_history** — audit trail.
- **shared_reports** — share_hash, password_hash, expires_at, enable_comments.
- **report_views** — view tracking for shared links (note: `avg_duration_seconds` always null — see §18).
- **report_comments** — per-slide / per-section / general. Resolve workflow.
- **scheduled_reports** — frequency, next_run_at, timezone, visual template.
- **client_goals** — metric, operator, value, period, alerts_sent.
- **admin_activity_log** + **gdpr_requests** — admin/compliance.

---

## 8. COMPLETE COMMIT HISTORY ON `main` — GROUPED BY PHASE

**143 commits total.** Oldest: `1f5db2e1` (initial scaffolding, 2026-03-17). Newest: `c79c406e` (shared UnreadCommentsProvider, 2026-04-21).

### Phase 0 — Scaffolding & Auth (March 17-18, 2026)
- `1f5db2e` initial project scaffolding — Next.js + FastAPI + directory structure
- `15f02a6` complete Supabase DB schema with RLS and triggers
- `d7948b0` Supabase auth — signup, login, logout, protected routes
- `bb51377`, `023b035`, `c0ed919` Tailwind, Server component, Input forwardRef fixes
- `916ebd1` resolve httpx/supabase dependency conflict
- `bb963b1` FastAPI backend + client CRUD + frontend client management

### Phase 1 — First report generation (March 20)
- `00f3c68` align client schema with DB
- `ee8d648` marketing landing page — hero, features, pricing, FAQ
- `f50e3d5` report generation — mock data, AI narrative (GPT-4o), charts, PPTX & PDF
- `9254aec`, `29d84fa`, `2c5e58a` narrative list/string handling fixes
- `193eed6` GA4 OAuth integration with real data pull + token encryption
- `71affb0` .env path fix + SettingsConfigDict upgrade
- `5c39df1`, `a4505cd`, `e4b0032`, `5bc3a53`, `a410710` DB schema + platform constraint alignment

### Phase 2 — PPTX templates & report customization (March 21-24)
- `b5eb336` CLAUDE.md + REMAINING-FEATURES.md
- `ab8b230` template-based report gen with 3 Canva templates
- `d2130ab` redesign PPTX templates with professional layouts
- `5f843e6` chart images, logo placeholders, KPI colors
- `d64d32c` complete Razorpay billing with plan enforcement + subscriptions + checkout
- `764081d` report customization, email delivery, scheduling, settings, Meta Ads, white-label
- `66b50c2` plans.py refactor
- `1159c0d`, `fa50f4d` None result handling + legal pages + dashboard metrics + loading + mobile meta tags
- `75a60e9`, `514f8d3` connections.is_active → status + UX navigation fixes
- `d511bb8` PPTX quality overhaul — dark charts, 300 DPI, formatted narratives
- `e4bc156` 6 PPTX templates + logo bg removal + demo reports + research
- `343d87f` enhanced PPTX research
- `4b0a69f` smart adaptive report system — 19 chart types + slide selection + KPI scoring
- `66101f5` adaptive generator with smart slide deletion + demo pipeline
- `b59702a` complete Phase 2 — CSV upload + multi-language + report sharing + Google Ads + Search Console + rich custom sections
- `1112c8d` wire Phase 2 components into client + integrations pages
- `eebc58e` csv_<slug> platform values + widen DB constraint
- `4e236bd` GOOGLE_ADS_LOGIN_CUSTOMER_ID config fix
- `e85eead` unified Google OAuth callback handles GA4 / Google Ads / Search Console
- `d459ae4` integrations page — client selector + direct connect/disconnect
- `97a93e0`, `f88b548`, `f59e43f` Google Ads await-on-sync + SearchConsole interface fixes
- `e52ca10` client page tab layout + full-width dashboard + mobile responsive
- `ff12cfe` **perf: GPT-4o → GPT-4.1 (20% cost reduction)** — 2026-03-30

### Phase 3 — First MVP deploy + production readiness (April 4-6)
- `31dd7cc` **initial commit: GoReportPilot MVP** (2026-04-04 17:50 — this is the repo-v1 commit, prior history is the scaffold branch)
- `d602a03` libgl1-mesa-glx → libgl1 for Debian Trixie
- `dd0e8f0` Dockerfile COPY paths for Railway
- `31ee867` Vercel build ESLint fixes
- `a1cc7ad`, `08b40f7` dashboard stats 500 fix + missing OAuth callback routes
- `0cfc07e` **docs: comprehensive project handover report** (the predecessor to this doc)
- `1d6d026` auth UX — forgot password + email confirmation + branded flow
- `ff3a463` agency name on cover + website engagement narrative
- `78a10b2` domain migration to goreportpilot.com + contact & refund pages
- `e85ca9d` address update New Delhi → Bareilly, Uttar Pradesh
- `bbcbf9e`, `0683f9c` Railway cache bust + setuptools/razorpay 2.0.1
- `94d4f8d` expired report files (410 + regenerate) & persistent logo storage
- `82bebb4` complete admin dashboard — overview, users, subs, connections, reports, system, GDPR
- `e7f5edf` separate admin layout + INR currency
- `faf22cd`, `2450648`, `0226ed9` admin dashboard endpoint + query + error-logging fixes
- `3ffc8b7` subscription payment verification + agency name display
- `bbe5ee6` **loading states, progress bar, skeletons, toasts — full UX polish**
- `3a82887` billing endpoint network error — CHECK constraint violation
- `216bdd4` complete mobile responsive audit

### Phase 4 — Pricing, trial, plan enforcement (April 7-9)
- `a7e8ad8` **remove mock data from production reports, require real connections**
- `ca60ab9` **never write plan until payment confirmed — reverse lookup from razorpay_plan_id**
- `7a19320` rate limiting on public endpoints + self-service account deletion
- `10bbb37` delivery policy on Terms (Razorpay international compliance)
- `af8ffe0`, `dedf80d`, `b092ea2` comprehensive pricing strategy + competitor matrix docs
- `c30cf81` **dual currency pricing (INR + USD), updated plans and client limits**
- `8874cc7` remove currency toggle — auto-detect only with footnote
- `b4b83d3` enforce all plan feature restrictions with upgrade prompts
- `dbd84cd` syntax error in settings.py + unused import in ReportsTab
- `deff25f`, `0053858`, `6462a17`, `e19d30e` block expired trials / 5-report limit / trial watermark / regenerate expired check
- `58880a7` new user onboarding checklist + empty states

### Phase 5 — Scheduler refinement (April 9-10)
- `e1462d4` EMAIL_FROM_DOMAIN default + scheduler log level
- `ce02029` timezone selector for scheduled reports
- `70e14bc` smart next_run_at calculation + 15min scheduler + frequency options
- `8135da0` scheduler timing note on schedules tab

### Phase 6 — Report quality Tier 1+2 (April 10)
- `97c7654` docs: report quality research
- `4005ca8` **report quality improvements — Tier 1+2 from research**
- `e562464` KPI color inversion, missing changes, chart title/label overflow
- `86a8da2` date format, zero-conv axis, line spacing, traffic labels, currency decimals
- `89e9b88` **sparklines on KPIs + direct-label charts + bad-month detection**
- `79e3012` logo overflow + sparklines + campaign axis + logo pad + label caps
- `353d3c4` logo pad removal + increased sparkline height + smarter title truncation
- `d80e752` attachment format + visual template selector for scheduled and manual report emails

### Phase 7 — Landing page overhaul + analytics (April 11)
- `e414aea`, `98844a1` landing page analysis + 2026 research benchmarks
- `07b41c9` **landing page overhaul — content fixes, hero rewrite, conversion boosters, SEO**
- `d9781f0` GA4 tracking + GDPR cookie consent banner
- `aee6616` admin analytics dashboard with user metrics, charts, funnel, country breakdown
- `dc5c04d` **docs: comprehensive project handover April 11, 2026**

### Phase 8 — Translations + Phase 1 infra (April 13, April 19)
- `b064093` remove trial watermark + navigation loading indicators
- `d9578db` **complete multi-language translation — slide titles + KPI labels + chart titles + footer + N/A indicators**
- `56f4021` **feat: phase 1 snapshot-saving infrastructure + research docs**
- `1557a1f` feat: wire Google Ads + Search Console data pulls (phase 1b / path A)

### Phase 9 — Connection health + Phase 3 cover (April 19)
- `ca37ba3` feat: phase 2 connection health monitor
- `b0345fb` feat: phase 3 custom cover page editor
- `77d7e18`, `c55b124`, `b020499`, `e035cca`, `a757873` reconnect flow fixes + deep-link scroll + health status + expiring_soon false positive
- `40ea06d` phase 3 cover bugs + unified report customization tab
- `548df15` lint: escape apostrophe
- `a39948f` → `dc8c4c8` — 10 iterative cover parity/fix commits (v2 → v10)

### Phase 10 — Design System Option F (April 20)
- `68d155d` feat: phase A — Design System Option F v1 (backend)
- `54ff14d` feat: phase B — Design System Option F v1 (frontend)
- `3cde04c` fix: phase 3 parity fix — chrome-only templates + exact-hex colour
- `430b726` fix: phase 3 parity v2 — accent reposition + agency attribution + minimal chrome
- `54ef062` docs: rebrand CLAUDE.md + planning docs + marketing workspace
- `f61118e` fix: phase 3 v2.1 — alignment + subtitle-as-tagline + preview parity
- `f86ab67` chore: bump THUMBNAIL_VERSION to v2-2

### Phase 11 — Diagnostic Narrative v2 + Goals + Comments (April 21)
- `c50c865` **feat: phase 4 — diagnostic narrative with top movers attribution**
- `06e0773` feat: phase 6A — goals & alerts backend
- `93b4e72` feat: phase 6B — goals & alerts frontend + trial limit override
- `edff2d4` feat: business context UX overhaul with AI-assist + quality indicator
- `c8c56d5` feat: phase 5A — client comments on shared reports (backend)
- `2a670b9` feat: phase 5B — client comments on shared reports (frontend)
- `0009eff` feat: granular comment badges + fix view analytics
- `090d473` feat: unresolved-comment badge on All Reports list rows
- `c79c406` feat: shared UnreadCommentsProvider keeps badges live **(HEAD)**

---

## 9. CURRENT DEVELOPMENT STATUS

### 9.1 Deployed to production (pushed to `main` → auto-deploy Railway + Vercel)
- All 143 commits. Latest deploy = HEAD commit `c79c406` (2026-04-21 20:02 IST).
- All 19 migrations executed in Supabase.

### 9.2 In-flight / being iterated
- Meta App Review resubmission (after 2026-04-21 rejection).
- Google OAuth verification (submitted; awaiting Google review).
- Marketing/GTM asset production (LinkedIn banner, explainer video, 30-day content calendar).

### 9.3 Deferred (with explicit reasons)
- **Phase 7 — MoM/YoY comparison charts:** blocked. `data_snapshots` needs ≥3 months of history. Earliest viable start: **June–July 2026**.
- **Change-based top movers** (biggest gainers/losers vs last period): same block.
- **`{text, evidence[]}` narrative schema** + "Show reasoning" UI + numeric-validator post-processor: Phase 5 was pivoted from these enhancements to client-comments instead. Still deferred.
- **Multi-agent coordination via Paperclip** + OpenClaw ops/intelligence agent on VPS: post-launch.

---

## 10. PRE-LAUNCH BLOCKERS (DETAILED)

### 10.1 Google OAuth production verification
- Demo video: https://youtu.be/YJ1KYOAIxQA
- Status: submitted, pending Google review.
- Risk: until verified, new users get the "Unverified app" scare screen when connecting GA4 / Google Ads / Search Console. Kills conversion.

### 10.2 Meta App Review — REJECTED 2026-04-21
- **6 of 7 requested permissions rejected.**
- Expected document: `docs/META-APP-REVIEW-REJECTION-APRIL-21-2026.md` — **NOTE: this file does not exist in the repo as of 2026-04-22.** Must be created / relocated from chat/notes. Placeholder action: next session should write this doc capturing exact rejection reasons from Meta + remediation plan.
- Scopes at stake: `ads_read, ads_management, business_management, pages_read_engagement, pages_show_list, public_profile`.
- Remediation likely requires: tighter screencast of each use case, cleaner app-state reproduction, clearer permission justification text, and possibly ripping out any scope we can't defend.

### 10.3 Razorpay KYC
- Entity Sahaj Bharat sole prop. KYC final sign-off pending.
- Blocks live international-card settlements.

### 10.4 Email infrastructure
- **Outbound (Resend):** DKIM verified for `reports@goreportpilot.com`. Working.
- **Inbound (Zoho free tier):** `support@`, `info@` aliases set. Final routing confirmation pending — test-send needed.

### 10.5 Auth UX polish
- Forgot password flow functional (commit `1d6d026`).
- Email confirmation enforced on signup.
- **Pending:** Supabase dashboard email templates need to be rewritten in GoReportPilot brand voice (current templates are generic "confirm your email" default).

### 10.6 LinkedIn banner upload
- Marketing asset pending.

---

## 11. DEFERRED FEATURES

| Feature | Reason | Earliest start |
|---|---|---|
| Phase 7 — MoM/YoY trend analysis | Needs 3 months of `data_snapshots` history | June-July 2026 |
| Change-based top movers (vs prev period) | Needs Phase 7 data | June-July 2026 |
| `{text, evidence[]}` narrative schema | Phase 5 pivoted to comments | Post-launch |
| "Show reasoning" UI toggle | Depends on `evidence[]` schema | Post-launch |
| Numeric-validator post-processor | Depends on `evidence[]` schema | Post-launch |
| Multi-agent Paperclip coordination | Not a launch requirement | Post-launch |
| OpenClaw ops/intelligence agent (VPS) | Post-launch ops infrastructure | Post-launch |
| Advanced validation layer (schema-level input validation) | Current Pydantic + slowapi sufficient for launch | Post-launch |

---

## 12. MARKETING & GO-TO-MARKET

### 12.1 Target ICP
Marketing agencies and freelance marketers managing **2-15 clients** — the band where manual reporting is the worst pain (too many to do manually, too few to justify enterprise tools).

### 12.2 Channels planned
- **LinkedIn** — 15-20 connection requests/day to ICP, daily posts (content calendar), InMail for warm leads.
- **Reddit** — `r/digital_marketing`, `r/PPC`, `r/AgencyGrowth`. Value-first answers on weekly threads.
- **Content marketing** — SEO-tuned blog posts on "monthly client reporting", "AI for agency reports", etc.
- **Direct outreach** — cold email to small agencies (curated list in `Marketing/outreach-tracker.csv`).

### 12.3 Content strategy
`Marketing/CONTENT-CALENDAR-30DAY.md` + `Marketing/weekly-posts.md`. Day 1 post (commit queued, 2026-04-21): question post: *"Quick question for agency owners and freelance marketers: How long does it take you to build ONE client report from scratch?"*

### 12.4 Video assets planned
- **Real demos:** Playwright + `edge-tts` + ffmpeg — scripted flows through the product with synced narration. Source-controlled, reproducible.
- **Explainer video:** Remotion for the landing-page hero loop + how-it-works section.
- **Demo video (Google OAuth review):** https://youtu.be/YJ1KYOAIxQA (already submitted).

### 12.5 Ops / intelligence agent
- **OpenClaw** on VPS, post-launch. Handles monitoring (Railway logs + Resend webhooks + Razorpay webhooks), background triage, daily status reports.

### 12.6 Human review loop (brand protection)
Any outbound AI-generated content (LinkedIn posts, cold emails, client-facing narrative samples) is reviewed by Saurabh before publishing. This is **a feature, not a limitation** — marketing copy claims "AI writes it, humans review it" as a trust signal.

### 12.7 Marketing workspace
`Marketing/`:
- `GOREPORTPILOT-OUTREACH-PROJECT.md` — project KB.
- `CLAUDE-CODE-OUTREACH-GUIDE.md` — how Claude Code assists outreach.
- `CONTENT-CALENDAR-30DAY.md` — 30-day post calendar.
- `LINKEDIN-REALITY-CHECK.md` — LinkedIn expectations recalibration.
- `outreach-tracker.csv` — prospect list.
- `today-tasks.md` — daily outreach focus.
- `weekly-posts.md` — post drafts.

---

## 13. PRICING STRUCTURE

Source of truth: `backend/services/plans.py`. **Never hardcode amounts anywhere else.**

| Plan | Monthly USD | Annual USD (/mo eq.) | Monthly INR | Annual INR (/mo eq.) | Clients | Goals/client | PPTX | White-label | Scheduling |
|---|---|---|---|---|---|---|---|---|---|
| Trial | — | — | — | — | 10 (generous) | 3 (Pro match) | ✅ | ✅ | ✅ |
| Starter | $19 | $15.17 ($182/yr) | ₹999 | ₹799.92 (₹9,599/yr) | 5 | **1** | ❌ (PDF only) | ❌ | ❌ |
| Pro | $39 | $31.17 ($374/yr) | ₹1,999 | ₹1,599.92 (₹19,199/yr) | 15 | **3** | ✅ | ✅ | ✅ (weekly/biweekly/monthly) |
| Agency | $69 | $55.17 ($662/yr) | ₹3,499 | ₹2,799.92 (₹33,599/yr) | **999** (unlimited) | **999** (unlimited) | ✅ | ✅ | ✅ |

- **Trial:** 14 days, Pro-level access, 5-report generation limit, "Powered by GoReportPilot" badge shows by default. Gives 3 goals/client so triallers can evaluate Goals & Alerts.
- **Reports per client: unlimited** across all paid plans. This is the moat.
- **Powered-by badge:** Trial + Starter only; removed on Pro+.
- **AI tones:** Starter = `professional` only; Pro + Agency = all 4.
- **Visual templates:** Starter = `modern_clean` only; Pro + Agency = 3 (trial), full 6 (Pro+).
- **Currency detection:** via timezone — `Asia/Kolkata` → INR; else USD. No toggle (commit `8874cc7`).
- **12 Razorpay plans configured** — 3 tiers × 2 currencies × 2 billing cycles.

---

## 14. WORKFLOW: HOW CLAUDE WEB + CLAUDE CODE COORDINATE

**CRITICAL SECTION.** Respect this workflow exactly; it has been battle-tested across 71+ prompts.

### 14.1 Flow
1. **Requirements capture:** Saurabh describes requirements conversationally to Claude Web (claude.ai).
2. **Analysis + clarification:** Claude Web analyzes, asks clarifying questions, iterates until the spec is unambiguous. **Do not skip this** — generic prompts produce narrow fixes.
3. **Numbered PROMPT-N specs:** Claude Web drafts the implementation as `PROMPT-71: [title]` style numbered prompts. Each prompt is self-contained — it can be executed without Claude Web's context.
4. **Execution:** Saurabh copy-pastes the prompt into Claude Code running locally on `F:\Sapienbotics\ClaudeCode\GoReportPilot\`.
5. **Claude Code executes.** Changes files, runs tests/typecheck, commits when told to.
6. **Report-back:** Claude Code reports with:
   - Changed files + diffs (short summaries).
   - Commit SHAs.
   - Screenshots of generated outputs (PPTX slides, UI states).
   - Verification test results (pytest / ast.parse / tsc output).
7. **Visual review:** Saurabh shares screenshots/outputs back to Claude Web.
8. **Verification:** Claude Web verifies visually, flags issues, requests next iteration or marks as done.
9. **Model selection:** Complex / systemic work → Opus (4.6 / 4.7). Targeted simple changes → Sonnet (4.6).

### 14.2 Critical rules for Claude Code
- **NEVER auto-start dev servers** — Saurabh runs `uvicorn` and `npm run dev` manually.
- **NEVER modify `.env` / `.env.local` files** — manual only.
- **NEVER run DB migrations** — Saurabh runs them in Supabase Dashboard SQL Editor.
- **ALWAYS run `cd frontend && npx tsc --noEmit`** after frontend changes. Must pass with zero errors before commit.
- **Single source of truth for pricing:** import from `backend/services/plans.py`. Never hardcode amounts.
- **Systemic > narrow:** fix generic root causes, not targeted patches for specific instances.
- **MVP = production quality.** Any paying or prospect customer may evaluate at any time.
- **Risky changes → split into safe incremental prompts.**
- **Git commit after every change set** with descriptive message. Wait for Saurabh's approval on first commit of a phase.
- **Create `.claude/tasks/phase-N-completion.md`** after each phase, with:
  - §0 Executive summary
  - §1 New / modified files with LOC counts
  - §2 Design decisions
  - §3 Deviations from the master prompt (explicit)
  - §4 Evidence (output samples, A/B comparisons, verification runs)
  - §5 User's verification plan (step-by-step)
  - §6 What's NOT in scope
- **STOP for user review between phases.**

### 14.3 Anti-patterns (have caused real bugs — don't repeat)
- Skipping plan enforcement because "it'll work in the UI" → shipped wrong plans to DB. Fixed in `ca60ab9` with reverse-lookup rule.
- Mocking data in production report generator "temporarily" → shipped for 2 weeks undetected. Fixed in `a7e8ad8`.
- Patching cover-page bug narrowly without looking at the whole template system → 10 consecutive "phase 3 cover vN" commits until root-caused to template-parity in Phase A/B.
- Trusting DB constraint names from code instead of inspecting the schema → 5 consecutive schema-alignment fixes in March (`5c39df1` etc.).

---

## 15. KEY LEARNINGS & PRINCIPLES

1. **Production quality is the only standard; MVP is just the first checkpoint for real clients.** No "we'll polish it later" — any future prospect may evaluate at any time.
2. **Client-count limits = pricing moat.** No competitor does this. Report unit economics (~₹1.50) make it safe.
3. **Currency detection via timezone** (`Asia/Kolkata` → INR; else USD). No toggle. Clear footnote on landing page.
4. **Payment bug pattern:** plan name must be derived via reverse lookup *after* Razorpay verifies payment, never written optimistically (commit `ca60ab9`).
5. **Human review loop in marketing is brand protection, not a limitation.** Pitch it as a feature.
6. **Report unit economics favor aggressive usage patterns.** Unlimited reports is safe; don't rate-limit paid users.
7. **Diagnostic narrative needs entity-level data injection, not prompt rewriting.** Phase 4 proof: same model, same temperature, same prompt skeleton — adding TOP MOVERS block fixed the quality problem.
8. **Idempotent snapshots + idempotent alerts.** Breach emails use `alerts_sent` JSONB keyed by `(period, alert_type)`.
9. **Always prefer generic fixes.** If you see a pattern of 3 similar bugs, root-cause the system instead of patching each.
10. **Split risky fixes into safe incremental prompts.** Especially true for PPTX rendering, cover customization, and OAuth flows.
11. **Translations are full-stack, not just copy.** Slide titles, KPI labels, chart titles, footer, N/A indicators — all 13 languages (commit `d9578db`).
12. **LibreOffice is non-negotiable for multi-script PDFs.** ReportLab is Latin-only fallback.
13. **`data_snapshots` is the long-term foundation.** Every report save must hit the snapshot table (Phase 1 infra) — even if Phase 7 is 3 months away.

---

## 16. CONTACT & ACCESS INFO (what credentials exist — NOT the values)

| Service | Account / owner | Where credentials live |
|---|---|---|
| Supabase project URL | `kbytzqviqzcvfdepjyby.supabase.co` | `backend/.env` SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY; `frontend/.env.local` NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY |
| GitHub org | `sapienbotics/goreportpilot` | Saurabh's GitHub account |
| Vercel project | goreportpilot | Vercel dashboard under `sapienbotics@gmail.com` |
| Railway project | `goreportpilot-production` | Railway dashboard under `sapienbotics@gmail.com` |
| OpenAI | GPT-4.1 | `backend/.env` OPENAI_API_KEY |
| Razorpay | Sahaj Bharat prop account | `backend/.env` RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET |
| Resend | `reports@goreportpilot.com` | `backend/.env` RESEND_API_KEY; DKIM verified in Resend dashboard |
| Zoho Mail (free tier) | `support@`, `info@` aliases | Zoho admin console under `sapienbotics@gmail.com` |
| Google Cloud (OAuth) | Project under `sapienbotics@gmail.com` | `backend/.env` GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET |
| Meta Developer | App under `sapienbotics@gmail.com` | `backend/.env` META_APP_ID, META_APP_SECRET |
| Google Ads MCC | 815-247-5096 | `backend/.env` GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_LOGIN_CUSTOMER_ID |
| Domain registrar | Namecheap | `sapienbotics@gmail.com` |
| Token encryption key | AES-256-GCM | `backend/.env` TOKEN_ENCRYPTION_KEY — must never be rotated without re-encrypting all stored tokens |

**Do not ever write actual secret values to memory, docs, commits, or chat transcripts.**

---

## 17. FILE LOCATIONS REFERENCE

```
F:\Sapienbotics\ClaudeCode\GoReportPilot\
├── CLAUDE.md                                     # Project instructions (OVERRIDES default behavior)
├── README.md
├── ADMIN-DASHBOARD-BLUEPRINT.md
├── package.json / package-lock.json              # Root-level (shadcn CLI; repo-wide dev deps)
├── docker-compose.yml
│
├── .claude/
│   ├── tasks/
│   │   ├── PROJECT-HANDOVER-APRIL-22-2026.md     # THIS FILE
│   │   ├── phase-roadmap.md                      # Master phase plan
│   │   ├── phase-1-completion.md                 # Phase 1 snapshot infra
│   │   ├── phase-1-snapshot-audit.md
│   │   ├── phase-1b-completion.md                # Google Ads + Search Console wire-up
│   │   ├── phase-2-completion.md / phase-2-fix-completion.md
│   │   ├── phase-3-completion.md / phase-3-fix-completion.md / phase-3-fix-v2.md / phase-3-fix-v3.md
│   │   ├── phase-3-parity-analysis.md / phase-3-parity-fix-completion.md / phase-3-parity-v2-*.md
│   │   ├── phase-3-v2-concerns-analysis.md
│   │   ├── phase-4-completion.md                 # Diagnostic Narrative v2
│   │   ├── phase-A-completion.md                 # Design System Option F backend
│   │   └── phase-B-completion.md                 # Design System Option F frontend
│
├── docs/
│   ├── HANDOVER-APRIL-11-2026.md                 # Earlier handover
│   ├── CHAT-HANDOVER-MARCH-2026.md               # March handover
│   ├── COMPLETE-PROJECT-REPORT.md
│   ├── COMPETITOR-FEATURE-MATRIX-2026.md
│   ├── PRICING-STRATEGY-2026.md
│   ├── USER-RESEARCH-APRIL-2026.md
│   ├── REPORT-QUALITY-RESEARCH-2026.md
│   ├── LANDING-PAGE-IMPROVEMENTS-2026.md
│   ├── REMAINING-FEATURES.md
│   ├── DEPLOYMENT-GUIDE.md
│   ├── DESIGN-SYSTEM-PLAN.md
│   ├── PHASE-1-2-REFINED-PLAN.md
│   ├── PHASE-2-BUILD-PLAN.md
│   ├── PROJECT-HANDOFF.md
│   ├── competitive-analysis-2026.md
│   ├── pptx-research-findings.md
│   └── reportpilot-auth-integration-deepdive.md
│
├── supabase/
│   └── migrations/  (001 … 019 — all 19 files executed)
│
├── backend/
│   ├── Dockerfile                                # Python 3.12-slim + LibreOffice + Noto fonts
│   ├── main.py                                   # FastAPI app + CORS + router includes
│   ├── config.py                                 # Pydantic Settings
│   ├── requirements.txt
│   ├── railway.toml
│   ├── routers/    (auth, clients, connections, reports, scheduled_reports, csv_upload,
│   │                settings, dashboard, billing, webhooks, admin, admin_analytics,
│   │                comments, goals, shared, data_pull)
│   ├── services/   (google_analytics, meta_ads, google_ads, search_console,
│   │                ai_narrative, top_movers, context_enhancer, report_generator,
│   │                chart_generator, slide_selector, cover_customization, theme_layout,
│   │                csv_parser, text_formatter, translations, email_service,
│   │                encryption, logo_processor, scheduler, snapshot_saver,
│   │                goal_checker, health_check, razorpay_service, plans,
│   │                supabase_client, demo_data, mock_data)
│   ├── middleware/ (auth, plan_enforcement)
│   ├── models/     (schemas)
│   ├── utils/
│   ├── templates/pptx/  (6 .pptx visual templates)
│   ├── scripts/    (audit, verification, demo seed)
│   └── static/
│
├── frontend/
│   ├── package.json
│   ├── middleware.ts                             # Route protection
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx / page.tsx             # Landing
│   │   │   ├── sitemap.ts / robots.ts
│   │   │   ├── login/ signup/ forgot-password/ reset-password/ confirm-email/
│   │   │   ├── privacy/ terms/ contact/ refund/ pricing/
│   │   │   ├── shared/[hash]/page.tsx            # Public report viewer
│   │   │   ├── api/auth/callback/
│   │   │   ├── dashboard/
│   │   │   │   ├── layout.tsx / page.tsx / loading.tsx / error.tsx
│   │   │   │   ├── clients/ / clients/[clientId]/ (7 tabs)
│   │   │   │   ├── reports/ / reports/[reportId]/
│   │   │   │   ├── integrations/
│   │   │   │   ├── billing/
│   │   │   │   └── settings/
│   │   │   └── admin/  (overview, analytics, users, etc.)
│   │   ├── components/
│   │   │   ├── ui/                               # shadcn base components
│   │   │   ├── dashboard/  (connection-health-widget, onboarding-checklist, upgrade-prompt)
│   │   │   ├── clients/    (BusinessContextField, CSVPreviewTable, CSVUploadDialog,
│   │   │   │                LanguageSelector, RichTextEditor, add-client-dialog, tabs/)
│   │   │   │   └── tabs/   (DesignTab, GoalsTab, IntegrationsTab, OverviewTab,
│   │   │   │                ReportsTab, SchedulesTab, SettingsTab)
│   │   │   ├── reports/    (CSVUploadForReport, CommentsSection, ShareReportDialog, ViewAnalytics)
│   │   │   ├── shared/     (CommentsPanel)
│   │   │   ├── landing/    (CurrencyPrice, HeroCTA, faq-accordion, mobile-nav, pricing-toggle)
│   │   │   ├── admin/
│   │   │   ├── layout/
│   │   │   ├── providers.tsx / AnalyticsProvider.tsx / CookieConsent.tsx
│   │   ├── lib/  (api.ts — axios wrapper, detect-currency.ts, supabase/)
│   │   └── types/
│
├── Marketing/
│   ├── GOREPORTPILOT-OUTREACH-PROJECT.md
│   ├── CLAUDE-CODE-OUTREACH-GUIDE.md
│   ├── CONTENT-CALENDAR-30DAY.md
│   ├── LINKEDIN-REALITY-CHECK.md
│   ├── outreach-tracker.csv
│   ├── today-tasks.md
│   └── weekly-posts.md
│
├── scripts/   (create_*_template.js × 6, create_all_templates.js,
│               audit_pptx.py, generate_demo_reports.py, seed_test_data.py,
│               setup_supabase.sh)
│
├── n8n/workflows/                                # Present; not in runtime use
├── demo_reports/
├── test_generated_pptx/
└── PPTX_template/                                # Canva-source PPTX inputs
```

### File size highlights (top 10 backend)
```
2662  backend/services/report_generator.py      # THE BIG ONE — orchestrates all 6 templates
1883  backend/routers/reports.py                # Largest router; generate + regenerate + send + share
1434  backend/services/chart_generator.py       # 19 chart types
 777  backend/services/health_check.py          # Phase 2 connection monitor
 691  backend/services/translations.py          # 13-language dictionary
 670  backend/services/csv_parser.py            # Production-grade parser
 608  backend/routers/shared.py                 # Public report endpoints
 575  backend/routers/comments.py               # Phase 5 comments
 548  backend/services/cover_customization.py
 501  backend/services/slide_selector.py        # KPI-scored smart selection
```

---

## 18. KNOWN ISSUES / GOTCHAS

1. **`report_views.avg_duration_seconds` is always null.** Documented trade-off. The public viewer doesn't instrument dwell-time reliably enough across the comment-badge-polling states. The field is kept for forward compatibility but any UI showing it should handle null gracefully. Commit `0009eff` confirms the trade-off.
2. **Meta App Review 6/7 permissions rejected** (see §10.2). Missing rejection-analysis doc at `docs/META-APP-REVIEW-REJECTION-APRIL-21-2026.md` — must be written.
3. **Google OAuth "Unverified app" scare screen** still shown to new users until Google completes verification.
4. **Stripe package present but unused** (`stripe==8.4.0` in requirements.txt). Remove or hide in next cleanup prompt — Razorpay is primary.
5. **`backend/services/mock_data.py` still shipped.** Production reports don't use it (commit `a7e8ad8` enforced real data), but the file exists for dev scaffolding. Do not re-enable for production paths.
6. **THUMBNAIL_VERSION constant** (`v2-2`) is a cache-bust hack — when updating report thumbnail rendering, bump the constant to force regeneration (pattern in commit `f86ab67`).
7. **10 iterative Phase 3 cover commits** (`a39948f` → `dc8c4c8`) show the system was over-engineered before Phase A/B unified it via `clients.theme`. The `cover_design_preset` column is deprecated — left NULLable for historical reads; new writes come from `theme` per migration `017`.
8. **GPT-4o is retired** — migration to GPT-4.1 in commit `ff12cfe` dropped costs ~20%. Don't regress.
9. **Razorpay `pkg_resources` import** needs `setuptools` (commit `0683f9c`) — if you upgrade razorpay don't drop setuptools from requirements.
10. **Debian Trixie GL library** is `libgl1`, not `libgl1-mesa-glx` (commit `d602a03`) — if you change the Dockerfile base image, verify this.
11. **Scheduler uses 15-min cadence** (not hourly) — health check runs every 6h via `_last_health_check_ts` timer in scheduler.py (not modulo on ticks).
12. **CSV platform values** are `csv_<slug>` (not `csv`) — DB CHECK constraint widened in migration `009`. Enforced in commit `eebc58e`.
13. **`n8n/` directory is present but not wired** — Saurabh has explicitly ruled out Make.com and n8n-as-runtime-service. Don't re-introduce.
14. **Currency toggle was removed** (commit `8874cc7`). Don't re-add — timezone detection + footnote is the official UX.

---

## 19. HANDOVER CHECKLIST FOR NEXT SESSION

On day 1, the next Claude Web session should do exactly this:

1. **Read this document end-to-end** (`.claude/tasks/PROJECT-HANDOVER-APRIL-22-2026.md`).
2. **Read (or if absent, reconstruct) `docs/META-APP-REVIEW-REJECTION-APRIL-21-2026.md`.** As of 2026-04-22 this file doesn't exist yet — if missing, ask Saurabh for the Meta rejection reasons and write the doc.
3. **Read `CLAUDE.md` at repo root** — overrides default Claude behavior.
4. **Read the latest phase completion doc** in `.claude/tasks/` to understand most-recent state. Currently that's `phase-4-completion.md` (Diagnostic Narrative v2, 2026-04-20).
5. **Read `docs/HANDOVER-APRIL-11-2026.md`** for context on prompts 1-70.
6. **Check `git log`** for commits since `c79c406` (2026-04-21 20:02 IST — HEAD of this handover).
7. **Verify deployment status:** check Vercel latest deploy + Railway latest deploy both match the current `main` HEAD.
8. **Check Supabase migrations:** confirm `supabase/migrations/019_report_comments.sql` was executed manually by Saurabh (Phase 5 schema).
9. **Ask Saurabh** what the current top-priority workstream is:
   - Remediating Meta App Review rejection?
   - Google OAuth verification follow-up?
   - Razorpay KYC final sign-off?
   - Marketing asset production (LinkedIn banner + explainer video)?
   - New feature work?
10. **Confirm model selection** — Opus 4.7 for systemic/complex; Sonnet 4.6 for targeted simple fixes.
11. **Re-read §14 (Workflow)** before issuing any Claude Code prompt.

### Pre-flight checks before starting any new work
- [ ] Repo on `main`, clean working tree, up to date with `origin/main`.
- [ ] `cd frontend && npx tsc --noEmit` passes with zero errors.
- [ ] Latest migration number known; new migration (if any) gets next sequential number.
- [ ] No `.env` edits planned.
- [ ] No auto-start of dev servers planned.

---

## APPENDIX A — Quick reference: key commands

```bash
# Run backend
cd backend && python -m uvicorn main:app --reload --port 8000

# Run frontend
cd frontend && npm run dev

# Type check frontend (MANDATORY after changes)
cd frontend && npx tsc --noEmit

# Inspect production logs (Railway)
# → Railway dashboard → project goreportpilot-production → Deployments → Logs

# Dry-run Phase 4 diagnostic narrative (no API cost)
python backend/scripts/verify_diagnostic_narrative.py

# Live A/B (costs ~$0.10)
OPENAI_API_KEY=sk-...  python backend/scripts/verify_diagnostic_narrative.py --live

# Audit generated PPTX
python scripts/audit_pptx.py backend/generated_reports/<file>.pptx
```

---

## APPENDIX B — File counts (verified via repo scan 2026-04-22)

- Migrations: **19** (001-019, 1,360 LOC total)
- Backend routers: **16** files (3 of them — `data_pull.py`, `webhooks.py` — are tiny stubs)
- Backend services: **28** files (20,143 LOC total — `report_generator.py` alone is 2,662)
- PPTX templates: **6** files in `backend/templates/pptx/`
- Frontend app routes: 17 top-level directories
- Frontend components: 10 category directories
- Commits on `main`: **143**
- Total phase completion docs: **19** files in `.claude/tasks/` (including this handover)
- Docs in `docs/`: **18** `.md` files
- Marketing workspace: **7** files in `Marketing/`

---

## APPENDIX C — Referenced commit SHA quick-lookup

Keep this table updated as new milestones land:

| Milestone | SHA | Date |
|---|---|---|
| Initial scaffold | `1f5db2e1` | 2026-03-17 |
| Supabase schema + auth | `15f02a6`, `d7948b0` | 2026-03-18 |
| First report generation (GPT-4o) | `f50e3d5` | 2026-03-20 |
| Phase 2 complete | `b59702a` | 2026-03-24 |
| GPT-4o → GPT-4.1 | `ff12cfe` | 2026-03-30 |
| MVP initial commit | `31dd7cc` | 2026-04-04 |
| Domain migration to goreportpilot.com | `78a10b2` | 2026-04-05 |
| Admin dashboard | `82bebb4` | 2026-04-06 |
| Mock data removed from production | `a7e8ad8` | 2026-04-08 |
| Reverse-lookup plan from razorpay_plan_id | `ca60ab9` | 2026-04-09 |
| Dual currency pricing | `c30cf81` | 2026-04-09 |
| Report quality Tier 1+2 | `4005ca8` | 2026-04-10 |
| Landing page overhaul | `07b41c9` | 2026-04-11 |
| GA4 tracking + GDPR | `d9781f0` | 2026-04-11 |
| Admin analytics | `aee6616` | 2026-04-11 |
| First handover doc | `dc5c04d` | 2026-04-11 |
| Full multi-language translation | `d9578db` | 2026-04-13 |
| Phase 1 snapshot infra | `56f4021` | 2026-04-19 |
| Phase 1b wire Google Ads + SC | `1557a1f` | 2026-04-19 |
| Phase 2 connection health | `ca37ba3` | 2026-04-19 |
| Phase 3 custom cover editor | `b0345fb` | 2026-04-19 |
| Phase A/B design system Option F | `68d155d`, `54ff14d` | 2026-04-20 |
| Phase 3 v2.1 parity | `f61118e` | 2026-04-20 |
| **Phase 4 diagnostic narrative** | `c50c865` | 2026-04-21 |
| Phase 6A/6B goals & alerts | `06e0773`, `93b4e72` | 2026-04-21 |
| Business context UX | `edff2d4` | 2026-04-21 |
| Phase 5A/5B client comments | `c8c56d5`, `2a670b9` | 2026-04-21 |
| Comment badges + view analytics | `0009eff`, `090d473`, `c79c406` | 2026-04-21 |

---

**End of handover.**

*This document is a snapshot as of 2026-04-22. For anything that may have moved since, check `git log` against `c79c406` (this handover's HEAD) first.*
