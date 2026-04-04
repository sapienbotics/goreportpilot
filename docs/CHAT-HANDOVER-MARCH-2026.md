# ReportPilot — Chat Handover Document (March 2026)

## 1. PROJECT VISION

ReportPilot is an AI-powered client reporting tool for digital marketing agencies and freelancers.

**Core workflow:** Connect client data sources → ReportPilot pulls data → GPT-4o writes narrative insights → Generates branded PowerPoint + PDF report → Agency emails to client.

**Three-stakeholder model:**
- **Developer (Saurabh/SapienBotics):** Builds and maintains the platform
- **Agency user:** Logs into ReportPilot, manages their clients, generates and sends reports
- **End clients:** Receive polished branded reports via email. They NEVER interact with ReportPilot directly.

**Competitive positioning:** Only affordable tool combining AI narrative generation + editable PPTX export under the ₹5,000/month threshold. Competitors (AgencyAnalytics, DashThis, Whatagraph) charge $100–500/month USD and don't produce editable PowerPoint files with AI-written narrative context.

**Revenue model (Razorpay subscriptions):**
- Starter: ₹1,599/month (up to 5 clients, 10 reports/month)
- Pro: ₹3,299/month (up to 20 clients, unlimited reports)
- Agency: ₹5,799/month (unlimited clients, white-label, custom templates)

**Supabase project:** https://kbytzqviqzcvfdepjyby.supabase.co
**Project root:** `F:\Sapienbotics\ClaudeCode\reportpilot\`

---

## 2. TECH STACK

| Layer | Technology | Version | Notes |
|---|---|---|---|
| Frontend | Next.js (App Router) | 14.x | Vercel deployment |
| Frontend Lang | TypeScript | 5.x | Strict mode |
| CSS | Tailwind CSS | 3.x | |
| UI Components | shadcn/ui | latest | |
| Backend | FastAPI | 0.110+ | Railway deployment |
| Backend Lang | Python | 3.11+ | (running 3.12 locally) |
| Database | Supabase (PostgreSQL) | latest | |
| Auth | Supabase Auth | included | |
| AI | OpenAI GPT-4o | latest | Narrative generation |
| PPTX | python-pptx | 0.6.23+ | |
| PDF (primary) | LibreOffice headless | 7.x+ | All scripts including Hindi/CJK |
| PDF (fallback) | ReportLab | 4.x | Latin languages only |
| Charts | matplotlib | 3.8+ | 300 DPI, theme-aware |
| Fonts | Google Noto | latest | Non-Latin PDF rendering |
| Email | Resend | latest | NOT YET CONFIGURED |
| Billing | Razorpay | latest | NOT YET CONFIGURED |
| Token Encrypt | cryptography (AES-256-GCM) | 42.x+ | |
| Scheduling | APScheduler | latest | Built but needs continuous backend |
| Encoding detect | chardet | 5.x | CSV parser |

**LibreOffice local path (Windows):** `C:\Program Files\LibreOffice\program\soffice.exe`

---

## 3. PROJECT FILE STRUCTURE

```
reportpilot/
├── CLAUDE.md                          # Master project instructions
├── docs/
│   ├── PROJECT-HANDOFF.md            # Setup guide
│   ├── REMAINING-FEATURES.md         # Feature backlog
│   ├── CHAT-HANDOVER-MARCH-2026.md   # THIS FILE
│   ├── reportpilot-deep-dive.md      # Business case
│   ├── reportpilot-feature-design-blueprint.md
│   └── reportpilot-auth-integration-deepdive.md
│
├── frontend/
│   ├── src/app/
│   │   ├── layout.tsx                # Root layout
│   │   ├── page.tsx                  # Landing page (marketing)
│   │   ├── pricing/page.tsx
│   │   ├── login/page.tsx
│   │   ├── signup/page.tsx
│   │   └── dashboard/
│   │       ├── layout.tsx            # Dashboard shell (sidebar + header)
│   │       ├── page.tsx              # Dashboard home
│   │       ├── clients/
│   │       │   ├── page.tsx
│   │       │   └── [clientId]/
│   │       │       ├── page.tsx      # Tabbed: Overview/Integrations/Reports/Schedules/Settings
│   │       │       ├── reports/page.tsx
│   │       │       └── connections/page.tsx
│   │       ├── reports/
│   │       │   ├── page.tsx          # Reports list with filters
│   │       │   └── [reportId]/
│   │       │       ├── page.tsx      # Report preview
│   │       │       └── deliver/page.tsx
│   │       ├── integrations/page.tsx  # Platform connections with client selector
│   │       └── settings/page.tsx
│   ├── src/components/
│   │   ├── ui/                        # shadcn/ui base components
│   │   ├── dashboard/                 # Widgets, stat cards
│   │   ├── clients/                   # Client cards, forms, detail views
│   │   ├── reports/
│   │   │   ├── CSVUploadForReport.tsx # CSV upload modal (used in report generation)
│   │   │   └── ShareReportDialog.tsx  # Share link modal
│   │   └── layout/                    # Sidebar, Header, Footer, Nav
│   └── src/lib/
│       ├── supabase/client.ts
│       ├── supabase/server.ts
│       ├── api.ts                     # Axios wrapper for FastAPI
│       └── utils.ts
│
├── backend/
│   ├── main.py                        # FastAPI app entry, CORS, routers
│   ├── config.py                      # Pydantic Settings (loads .env)
│   ├── requirements.txt               # Python dependencies (includes chardet>=5.0,<6.0)
│   ├── Dockerfile                     # Includes LibreOffice + Noto fonts
│   ├── railway.toml
│   ├── routers/
│   │   ├── auth.py                    # OAuth callbacks (GA4, Meta, Google Ads, Search Console)
│   │   ├── clients.py                 # Client CRUD
│   │   ├── connections.py             # Connection management + CSV parse endpoint
│   │   ├── reports.py                 # Report generation, list, download, share
│   │   ├── data_pull.py               # Manual data pull trigger
│   │   └── webhooks.py                # Razorpay webhooks
│   ├── services/
│   │   ├── google_analytics.py        # GA4 Data API client — added device_breakdown (6th API call)
│   │   ├── meta_ads.py                # Meta Marketing API client
│   │   ├── google_ads.py              # Google Ads API client
│   │   ├── search_console.py          # Search Console API client
│   │   ├── ai_narrative.py            # GPT-4o prompt engine (4 tones, 13 languages)
│   │   ├── report_generator.py        # PPTX + PDF orchestration (MAIN FILE — most modified)
│   │   ├── chart_generator.py         # matplotlib chart rendering (19 types, 3 themes)
│   │   ├── slide_selector.py          # Smart slide/KPI selection logic
│   │   ├── text_formatter.py          # Custom section rich text parsing
│   │   ├── csv_parser.py              # Production-grade CSV parser (fully rewritten)
│   │   ├── email_service.py           # Resend SDK wrapper (not yet active)
│   │   ├── encryption.py              # AES-256-GCM token encryption
│   │   ├── mock_data.py               # Realistic GA4 + Meta Ads fake data
│   │   └── scheduler.py               # APScheduler for scheduled reports
│   ├── templates/
│   │   └── pptx/                      # 6 PPTX visual templates (19 slides each)
│   │       ├── modern_clean.pptx      # FIXED: CSV chart placeholder repositioned
│   │       ├── dark_executive.pptx    # FIXED: CSV chart placeholder repositioned
│   │       ├── colorful_agency.pptx   # FIXED: CSV chart placeholder repositioned
│   │       ├── bold_geometric.pptx    # FIXED: CSV chart placeholder repositioned
│   │       ├── minimal_elegant.pptx   # FIXED: CSV chart placeholder repositioned
│   │       └── gradient_modern.pptx   # FIXED: CSV chart placeholder repositioned
│   └── scripts/                       # Audit and fix scripts
│       ├── audit_templates.py         # Full template geometry dump
│       ├── audit_csv_slide.py         # Focused CSV slide diagnosis
│       ├── fix_csv_slide_layout.py    # Template CSV slide position fix (ALREADY RUN on all 6)
│       ├── verify_report.py           # End-to-end report generation test (3 CSV sources)
│       ├── verify_chart_sizing.py     # Chart sizing verification (CSV + solo chart)
│       ├── verify_pie_centering.py    # Pie chart solo centering verification
│       └── diagnose_slides.py         # Detailed slide content dump
│
├── supabase/
│   └── migrations/                    # 001-009 all executed
│
└── docker-compose.yml
```

---

## 4. DEVELOPMENT WORKFLOW

1. **Saurabh** describes requirements/issues in Claude.ai chat
2. **Claude.ai** writes detailed numbered prompts (PROMPT-17, PROMPT-18, etc.)
3. **Saurabh** pastes prompts into Claude Code (**Opus 4.6** for complex/systemic work, Sonnet 4.6 for simpler tasks)
4. **Saurabh** reports back with screenshots, terminal output, and generated PPTX files
5. **Claude.ai** diagnoses issues and writes fix prompts
6. **Dev servers** run manually:
   - Backend: `cd backend && python -m uvicorn main:app --reload --port 8000`
   - Frontend: `cd frontend && npm run dev`
7. **Database changes** run manually in Supabase SQL Editor
8. **For complex/systemic issues**, Opus 4.6 model is preferred in Claude Code

**IMPORTANT:** Never modify `.env` files. Never start dev servers automatically. Always run `cd frontend && npx tsc --noEmit` after frontend changes.

---

## 5. WHAT IS COMPLETE

### Authentication & OAuth
- ✅ Supabase Auth (email/password signup, login, logout, protected routes)
- ✅ GA4 OAuth — tested with real data, auto-refresh tokens
- ✅ Meta Ads OAuth — tested with real data, short→long-lived token exchange
- ✅ Google Ads OAuth — flow works, no test ad accounts on sapienbotics@gmail.com
- ✅ Search Console OAuth — connected to sc-domain:videogenie.tech
- ✅ Token encryption (AES-256-GCM) for all OAuth tokens in Supabase

### Report Generation Pipeline
- ✅ **6 PPTX visual templates:** modern_clean, dark_executive, colorful_agency, bold_geometric, minimal_elegant, gradient_modern
- ✅ **19 slide types** in each template:
  - cover, executive_summary, kpi_scorecard
  - website_traffic, website_engagement, website_audience, bounce_rate_analysis
  - meta_ads_overview, meta_ads_audience, meta_ads_creative
  - google_ads_overview, google_ads_keywords
  - seo_overview
  - csv_data (duplicated per source)
  - conversion_funnel
  - key_wins, concerns, next_steps, custom_section
- ✅ **Smart slide selection** — analyzes available data, deletes irrelevant slides
- ✅ **Smart KPI scoring** — picks best 6 KPIs from GA4/Meta/Google Ads/SEO/CSV
- ✅ **3 detail levels:** Full Report, Summary, Executive Brief
- ✅ **AI narrative via GPT-4o** — 4 tones (professional/conversational/executive/data-heavy), 13 languages
- ✅ **19 chart types** — 3 themes (light/dark/colorful), 300 DPI, dual-chart expansion
- ✅ **Chart minimum threshold:** < 2 data points → no chart generated (all 10 list-based functions)
- ✅ **Type-aware chart centering:**
  - Pie/donut charts (device breakdown): keep original ~5.60" width, center horizontally
  - Bar/line charts: expand to max 8.5" width, center horizontally
- ✅ **CSV comparison chart:** figsize(8, 4), max 8.0" wide, centered on slide (3.1:1 aspect ratio)
- ✅ **PDF via LibreOffice** — all languages including Hindi, Japanese, CJK, Arabic
- ✅ **PDF fallback via ReportLab** — Latin languages only when LibreOffice unavailable
- ✅ **Multi-CSV support** — multiple CSV sources per report, each gets its own slide
- ✅ **CSV slide duplication** — template slide duplicated N-1 times; save-reload cycle prevents part name collisions
- ✅ **Slide reordering** — CSV slides placed before Key Wins/Concerns/Next Steps
- ✅ **Page renumbering** — runs as LAST step before save, after all slide operations
- ✅ **Template geometry fixed** — all 6 templates: chart placeholder 0.20" below last KPI card bottom
- ✅ **Data sanitization** — `_sanitize_data_for_ai()` rounds all floats to 2dp before passing to GPT-4o
- ✅ **Deduplication guard** — `_seen_csv_names` set prevents duplicate CSV slides from same source
- ✅ **PDF exception logging** — FileNotFoundError / TimeoutExpired / CalledProcessError each logged distinctly

### CSV Parser (Production-Grade — Full Rewrite)
- ✅ Encoding: UTF-8-sig → UTF-8 → chardet (≥70% confidence) → Latin-1 fallback
- ✅ Delimiter: csv.Sniffer auto-detect (comma/semicolon/tab/pipe)
- ✅ Binary rejection: Excel (.xlsx/.xls), PDF, JPEG, PNG, GIF with actionable error messages
- ✅ Flexible column aliases (metric_name/metric/name/kpi/indicator, current_value/current/value/actual, etc.)
- ✅ Number parsing: K/M/B suffixes, European decimal (1.234,56), space-as-thousands, currency symbols
- ✅ Unit auto-detection from value symbols ($, ₹, %) and metric name keywords (spend→currency, rate→percent)
- ✅ Filename cleaning: strip date prefix, iterative junk suffix stripping (template/data/report/export/v2/etc.)
- ✅ Brand name capitalization: TikTok, LinkedIn, YouTube, HubSpot, WhatsApp, WooCommerce, etc.

### UI/UX
- ✅ Tabbed client detail page (Overview, Integrations, Reports, Schedules, Settings)
- ✅ Full-width dashboard layout (max-w-7xl)
- ✅ Mobile responsive (hamburger sidebar, scrollable tabs)
- ✅ Report filters (date range, status, search, client filter)
- ✅ Language selector in client Settings tab (13 languages)
- ✅ CSV upload in report generation form (modal with drag-and-drop, template downloads)
- ✅ Share report dialog (centered modal, active shareable links)
- ✅ Report link sharing with view tracking
- ✅ Integrations page with client selector and live connection status
- ✅ Error messages from CSV parser shown with actionable fix suggestions

### Infrastructure
- ✅ Dockerfile for backend (LibreOffice + Noto fonts included)
- ✅ Dockerfile for frontend
- ✅ docker-compose.yml for local testing
- ✅ Railway deployment configs (`backend/railway.toml`)
- ✅ LibreOffice installed locally (Windows)

---

## 6. WHAT NEEDS TESTING

- ✅ Report sharing: link generation and incognito viewing
- ✅ Multi-language: Hindi tested
- ⬜ Other languages (Japanese, Arabic, Chinese) need testing
- ⬜ CSV upload with custom (non-template) files — edge cases
- ⬜ Rich text custom sections with image upload
- ⬜ Report email delivery (needs Resend API key + domain)
- ⬜ Scheduled reports (APScheduler built, needs continuous backend)
- ⬜ Visual verification of latest chart sizing fixes (8" centered CSVs, type-aware expansion)

---

## 7. WHAT IS PENDING (Before Deployment)

1. **Resend email setup** — Need API key + verified sender domain. `email_service.py` is written, endpoint exists, just needs real keys.

2. **Razorpay account setup** — Need Razorpay account + API keys + create 6 subscription plans (Starter monthly/annual, Pro monthly/annual, Agency monthly/annual). Subscribe buttons currently show error.

3. **Domain purchase** — reportpilot.co or similar. After purchase:
   - Update `FRONTEND_URL` and `BACKEND_URL` env vars
   - Update Google OAuth redirect URIs in Google Cloud Console
   - Update Meta OAuth redirect URIs in Meta Developer Portal
   - Update CORS origins in `backend/main.py`

4. **Deploy:**
   - Frontend → Vercel (connect GitHub repo, set root to `frontend/`, add env vars)
   - Backend → Railway (connects to `backend/Dockerfile`, add env vars)

5. **Google Cloud OAuth consent screen** — Currently "Testing" mode (limited to test users). Must submit for verification to go Production. Required docs: privacy policy URL, terms of service URL, app logo.

6. **Meta App Review** — Currently in Development mode. Must submit `ads_read` permission for Meta review. Required: screen recording demo, privacy policy, use case description.

7. **Chart quality visual verification** — Latest chart sizing fixes need visual check in generated PPTX:
   - CSV chart: should be ~8" wide, centered on slide, aspect ratio ~3:1
   - Website Engagement with only sessions chart: bar should expand to ~8.5", centered
   - Website Engagement with both charts: pie keeps ~5.6" width, centered; bar stays right-side

---

## 8. KNOWN ISSUES / QUIRKS

- **React Strict Mode double-mount:** OAuth callbacks use `useRef(false)` guard to prevent double execution in development.
- **Google Ads `invalid_grant`:** Expected when user's Google account has no Ads accounts linked — handled gracefully.
- **python-pptx orphan parts:** `drop_rel()` slide deletion leaves orphaned `SlidePart` objects. `add_slide()` can then pick colliding filenames during save, causing new slide content to be overwritten by orphan. **SOLVED:** Save-reload cycle (`prs.save(buf); prs = Presentation(buf)`) after all deletions, before any duplication — purges orphans entirely.
- **LibreOffice not in PATH on Windows:** Backend tries explicit path `C:\Program Files\LibreOffice\program\soffice.exe` in addition to `soffice` and `libreoffice` commands.
- **Field name mismatches historically:** `report_language`, `url` vs `site_url` have caused silent data drops. Always verify frontend/backend field names match DB schema exactly.
- **PPTX template geometry — now fixed:** modern_clean and dark_executive previously had chart placeholder overlapping KPI cards by 0.13–0.20". Fixed in all 6 templates via `scripts/fix_csv_slide_layout.py` — all templates now have 0.20" clearance between last KPI card bottom and chart top.
- **CSV chart `metrics` variable shadowing:** `generate_csv_comparison_chart` previously had `metrics = metrics_raw[:6]` shadowing the threshold check. Resolved by explicitly using `metrics_raw` for the `len() < 2` guard.
- **Currency display for small values:** `_fmt_csv_value()` uses 2 decimal places when `num < 10` (e.g., ₹0.24 not ₹0). Format: `{:,.2f}` for < 10, `{:,.0f}` for ≥ 10.
- **top_pages threshold:** Was `>= 3` pages required to render chart. Lowered to `>= 2` so the Website Engagement dual-chart slot renders even with minimal page data.

---

## 9. CRITICAL CODE AREAS

### `backend/services/report_generator.py` — Key Functions

| Function | Purpose |
|---|---|
| `generate_pptx_report()` | Main orchestrator — opens template, runs all population steps, saves |
| `_reorder_slides(prs, order)` | Manipulates `prs.slides._sldIdLst` lxml elements to physically reorder slides |
| `_duplicate_slide(prs, src_idx)` | `add_slide()` + `deepcopy(spTree)` — creates copy of a slide |
| `_populate_csv_slide(slide, source, chart_path)` | Fills `{{csv_*}}` tokens, embeds chart capped at 8.0" wide centered |
| `_replace_charts(slide, charts, data)` | Embeds chart images; dual-chart expansion with type detection |
| `_renumber_slide_footers(prs)` | Updates page X of Y tokens — runs LAST before save |
| `_sanitize_data_for_ai(data)` | Deep copy + round all floats to 2dp — called before GPT-4o |
| `generate_pdf_report()` | Wraps PPTX generation + LibreOffice conversion with detailed exception logging |

### Save-Reload Cycle (Critical Pattern)
```python
# After deleting unused slides, BEFORE any duplication:
_buf = io.BytesIO()
prs.save(_buf)
_buf.seek(0)
prs = Presentation(_buf)
# Now safe to duplicate slides — no orphaned parts
```

### Type-Aware Dual-Chart Centering
```python
_PIE_CHART_HINTS = {"device", "pie", "donut", "breakdown"}
_DUAL_PAIRS = {
    "{{sessions_chart}}": "{{top_pages_chart}}",
    # ...
}
_MAX_BAR_W = int(8.5 * 914400)  # 8.5 inches in EMU

# Detection:
is_pie = any(hint in placeholder_name.lower() for hint in _PIE_CHART_HINTS)
# Pie: keep original width, center. Bar: expand to _MAX_BAR_W, center.
```

### CSV Slide Duplication Pattern
```python
# 1. Find template slide index by scanning for {{csv_source_name}}
# 2. Save-reload to purge orphans
# 3. For N sources:
#    - Populate slide[_csv_tpl_idx] with sources[0]
#    - For sources[1..N-1]: duplicate, populate, track new indices
# 4. Reorder: move appended duplicates to follow original (before Key Wins)
```

---

## 10. ENVIRONMENT VARIABLES

### Backend (`backend/.env`)
```
# Supabase
SUPABASE_URL=https://kbytzqviqzcvfdepjyby.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service role key>

# Google OAuth (GA4 + Google Ads + Search Console)
GOOGLE_CLIENT_ID=<id>
GOOGLE_CLIENT_SECRET=<secret>
GOOGLE_REDIRECT_URI=http://localhost:3000/api/auth/callback/google-analytics

# Meta OAuth
META_APP_ID=<id>
META_APP_SECRET=<secret>
META_REDIRECT_URI=http://localhost:3000/api/auth/callback/meta-ads

# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=<token>
GOOGLE_ADS_LOGIN_CUSTOMER_ID=<id>

# Token Encryption
TOKEN_ENCRYPTION_KEY=<base64-encoded 32-byte key>

# OpenAI
OPENAI_API_KEY=<key>

# Razorpay (NEEDS ACCOUNT SETUP)
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
RAZORPAY_PLAN_STARTER_MONTHLY=
RAZORPAY_PLAN_STARTER_ANNUAL=
RAZORPAY_PLAN_PRO_MONTHLY=
RAZORPAY_PLAN_PRO_ANNUAL=
RAZORPAY_PLAN_AGENCY_MONTHLY=
RAZORPAY_PLAN_AGENCY_ANNUAL=

# Resend (NEEDS SETUP)
RESEND_API_KEY=

# App URLs
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
ENVIRONMENT=development
```

### Frontend (`frontend/.env.local`)
```
NEXT_PUBLIC_SUPABASE_URL=https://kbytzqviqzcvfdepjyby.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

---

## 11. PROMPT HISTORY

| Prompt | Description |
|---|---|
| PROMPT-1 | Initial project scaffold (monorepo, Next.js 14, FastAPI) |
| PROMPT-2 | Supabase schema and RLS policies |
| PROMPT-3 | Supabase Auth (signup, login, logout, protected routes) |
| PROMPT-4 | Dashboard layout (sidebar, header, navigation) |
| PROMPT-5 | Client CRUD (create, list, get, update, soft-delete) |
| PROMPT-6 | Landing page (10 sections: hero, problem, features, pricing, FAQ, CTA) |
| PROMPT-7 | Mock data service (GA4 + Meta Ads realistic fake data) |
| PROMPT-8 | AI narrative engine (GPT-4o, 4 tones, structured JSON output) |
| PROMPT-9 | Chart generator (matplotlib, 19 chart types, 3 themes, 300 DPI) |
| PROMPT-10 | PowerPoint generator (python-pptx, 8-slide branded deck) |
| PROMPT-11 | PDF generator (ReportLab fallback) |
| PROMPT-12 | Report API endpoints (generate, list, get, download PPTX/PDF) |
| PROMPT-13 | Report preview UI (KPI cards, narrative sections, download buttons) |
| PROMPT-14 | GA4 OAuth (consent → callback → token exchange → property listing → real data) |
| PROMPT-15 | Meta Ads OAuth (Facebook login → token exchange → ad account listing) |
| PROMPT-16 | Token encryption (AES-256-GCM) |
| PROMPT-17 | Currency handling (dynamic symbols ₹/$/ €/£ across AI, charts, PDF, PPTX) |
| PROMPT-18 | Connection management (save, list, delete, platform normalization) |
| PROMPT-19 | 19-slide template system with slide pool architecture |
| PROMPT-20 | Google Ads OAuth + Search Console OAuth |
| PROMPT-21 | CSV upload system (per-report data source, modal with templates) |
| PROMPT-22 | Multi-CSV slide duplication system (save-reload cycle, slide reordering) |
| PROMPT-23 | Category 1+2: Systemic robustness + bulletproof CSV parser rewrite |
| PROMPT-24 | Three production fixes: CSV chart overlap, dual-chart expansion, brand names |
| PROMPT-25 | Phase 1-5: Template geometry audit, fix at source, chart thresholds |
| PROMPT-26 | Chart sizing: CSV chart centering (8"), type-aware dual-chart expansion |
| PROMPT-27 | THIS HANDOVER DOCUMENT |

---

## 12. KEY ARCHITECTURE DECISIONS

### Slide Pool Architecture
Templates contain ALL 19 possible slides. The generator analyzes available data sources and deletes irrelevant slides before population. This means:
- GA4 slides deleted when no GA4 connection
- Meta Ads slides deleted when no Meta connection
- CSV slides kept (and duplicated) when CSV sources provided
- Key Wins/Concerns deleted when narrative sections are empty

### Template-Based PPTX (Not Code-Drawn)
Pre-designed `.pptx` files with `{{placeholder}}` tokens. Python opens the template, replaces tokens with real values, embeds chart images. This produces professional-looking slides without complex drawing code. Templates are in `backend/templates/pptx/`.

### Multi-CSV Slide Duplication
For N CSV sources:
1. Delete unused slides (including CSV slide if no CSV data, or keep 1 if CSV present)
2. **Save-reload cycle** to purge orphaned parts from deletion
3. Find the single `{{csv_source_name}}` template slide by scanning
4. Duplicate it N-1 times with `add_slide()` + `spTree` deep copy
5. Populate each slide with its source's data and chart
6. Reorder: move appended duplicates to after the original, before Key Wins/Concerns/Steps

### Three-Stakeholder Model
- Developer configures the system
- Agency user: Logs in, adds clients, connects data sources, generates/sends reports
- End clients: Only ever see the PDF/PPTX they receive via email — never interact with ReportPilot

### Smart KPI Scoring
`select_kpis()` in `slide_selector.py` scores all available metrics across all connected sources by priority (conversions > sessions > spend > others), picks top 6, never shows N/A or zero-value KPIs.

### Theme-Aware Charts
`dark_executive` template → matplotlib dark theme. `colorful_agency` → colorful theme. Others → light theme. Chart images are generated to match the slide background.

### CSV as Per-Report Data
CSV uploads are NOT persistent connections. They're uploaded during report generation, flow through the pipeline as `data["csv_sources"]` list, generate slides + contribute to KPI scorecard + inform AI narrative. They do not appear in the Integrations page.

### LibreOffice for PDF (Primary)
`subprocess.run(["soffice", "--headless", "--convert-to", "pdf", ...])` converts PPTX to PDF. Handles all Unicode scripts. ReportLab is a Latin-only fallback when LibreOffice unavailable. Non-Latin languages WITHOUT LibreOffice return `None` (frontend shows "Download PPTX" instead).

### Save-Reload After Deletion (Critical Fix)
`drop_rel(rId)` removes the relationship but the `SlidePart` stays in memory. `add_slide()` picks names based on existing rels (not in-memory parts), so it can reuse a deleted slide's filename. During `prs.save()`, the orphan overwrites the new slide. Fix: `buf=io.BytesIO(); prs.save(buf); prs=Presentation(buf)` after deletion — only reachable parts are written, orphans are discarded.

---

## 13. SUPABASE DATABASE

**Project URL:** https://kbytzqviqzcvfdepjyby.supabase.co

### Key Tables
| Table | Purpose |
|---|---|
| `users` | Extends `auth.users` (agency users, plan, branding settings) |
| `clients` | Agency's clients (name, website, logo, report config, language) |
| `connections` | OAuth tokens for GA4/Meta/Google Ads/Search Console (AES-256-GCM encrypted) |
| `reports` | Generated reports (PPTX/PDF file paths, narrative, status) |
| `shared_reports` | Shareable links (token, view count, expiry) |
| `report_views` | Link view tracking |
| `scheduled_reports` | APScheduler configs per client |

### RLS Policies
All tables have Row-Level Security enabled. Users can only access their own data (enforced at DB level, not just application code).

### Migrations
Migrations 001 through 009 all executed. Run via Supabase Dashboard SQL Editor.

### Test Account
- **Login:** sapienbotics@gmail.com
- **Client:** "Videogenie"
  - GA4: Connected (property linked to sapienbotics@gmail.com)
  - Meta Ads: Connected (test ad account)
  - Search Console: Connected (sc-domain:videogenie.tech)

---

## 14. BUGS FIXED IN THIS SESSION

| Bug | Root Cause | Fix |
|---|---|---|
| CSV KPI units showing as blank | `_TEMPLATES` in csv_parser.py used `%`/`$` symbols instead of `percent`/`currency`/`number` | Updated all templates + added `_CSV_UNIT_ALIASES` safety net in report_generator.py |
| Duplicate narrative text on slides 4+5 | `_NARRATIVE_SLIDES` mapped slides 4,5,6 all to `{{website_narrative}}` | Removed those from the map; leftover cleanup clears remaining tokens |
| Only 1 CSV slide from N uploads | Architecture only handled first source | Full multi-slide duplication system with save-reload cycle |
| Source name shows "TikTok Ads Template" | `_clean_source_name` didn't strip `_template` | Added `_TRAILING_JUNK_RE` iterative suffix stripping |
| ₹0 instead of ₹0.24 for small currency | `_fmt_csv_value()` always used `{:,.0f}` | Use `{:,.2f}` when `num < 10` |
| CSV slide content corruption (Key Wins showing wrong data) | python-pptx orphaned SlidePart name collision on `prs.save()` | Save-reload cycle after all deletions, before any duplication |
| Website Engagement blank right side | `top_pages` chart skipped when < 3 pages (threshold too high) | Lowered threshold to `>= 2` |
| PDF always "unavailable" | Silent exception swallowing, no visibility into LibreOffice errors | Per-exception logging (FileNotFoundError / TimeoutExpired / CalledProcessError) |
| CSV chart too wide (11.7") / wrong ratio | Template placeholder was full-slide width | Cap at 8.0" EMU, center: `left = (SLIDE_W - chart_w) // 2` |
| Pie chart stretched when solo on slide | Old expansion code merged both bounding boxes | Type detection via `_PIE_CHART_HINTS`: pie keeps original width, bar expands |
| Chart overlapping KPI cards in templates | modern_clean + dark_executive chart started 0.13–0.20" ABOVE KPI card bottom | Fixed all 6 templates at source via `fix_csv_slide_layout.py` |
