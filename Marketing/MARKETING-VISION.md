# GoReportPilot Marketing Automation — Vision & Execution Brief v2

**For:** Claude Code (executor)
**From:** Saurabh Singh (founder, sole operator)
**Date:** April 27, 2026 (v2 — replaces v1 dated April 26)
**Status:** Pre-launch, Meta App Review pending, soft launch in 2 weeks

---

## What changed in v2

- Apollo free tier limitations discovered: search API is free + unlimited, but email enrichment is credit-gated (50/month). Adjusted WF1 to two-step approach.
- Directory scraping (Clutch, Sortlist, Agency Spotter, Google Maps) blocked by Cloudflare. Removed as sources. Apollo free search replaces all.
- Reddit API requires OAuth (unauthenticated JSON blocked). Reddit app registration in progress.
- Discord dropped as notification layer. Google Sheets only + Friday email digest via Resend.
- Added 4 new workflows (WF7-WF10) for inbound marketing: LinkedIn content, blog drafts, Product Hunt prep, directory submissions.
- Budget reality: $5-15/mo OpenAI + optionally $34/mo Hunter Starter for 500 emails/month. Without Hunter upgrade, LinkedIn-first outreach with 100 emails/month.

---

## Your role

You are the **execution lead** for GoReportPilot's marketing automation. You have full repo access, file system access, and n8n MCP access. You build and ship.

Saurabh provides:
- Strategic direction and vision (this document + ongoing prompts from Claude Web)
- Credentials in n8n UI (Apollo, OpenAI, Google Sheets, Hunter — these you cannot create)
- Manual checkpoints on customer-facing sends (cold emails, Reddit comments, LinkedIn posts, signup welcome)
- Final approval before any workflow goes live

You do everything else: design n8n workflows, write code, validate, test, deploy, document, iterate.

---

## What we're building

A comprehensive, n8n-orchestrated marketing automation stack covering **all channels** — outbound prospecting, inbound content, community engagement, competitive intelligence, conversion optimization, and retention:

### Outbound engine
1. **WF1: Prospect Harvester** — 30-50 ICP prospects/day from Apollo free search API
2. **WF2: Outreach Drafter** — 10 hyper-personalized cold emails + LinkedIn messages/day for human review

### Inbound engine
3. **WF7: LinkedIn Content Drafter** — daily post draft from competitor intel + community trends
4. **WF8: Weekly Blog Drafter** — 1500-word SEO article from week's intelligence
5. **WF9: Product Hunt Launch Prep** — one-time workflow generating all PH assets
6. **WF10: Directory Submission Tracker** — tracks submission status across Capterra, G2, SaaSWorthy, AlternativeTo, GetApp

### Community engagement
7. **WF5: Reddit + HN Listener** — twice daily, surfaces engagement opportunities with draft comments

### Intelligence
8. **WF4: Competitor Monitor** — daily pricing/feature/positioning change detection

### Conversion
9. **WF3: Signup Lead Enrichment** — instant research on every new signup (post Meta approval)

### Retention
10. **WF6: Churn Early-Warning** — daily at-risk customer detection (after 5 paid customers)

**Total target spend: ~$5-15/month in OpenAI credits. Optionally $34/month for Hunter Starter (500 email enrichments/month). Everything else free.**

---

## Product context (read first)

GoReportPilot is a B2B SaaS reporting tool for digital marketing agencies. Pulls GA4 + Meta Ads + Google Ads + Search Console data, generates AI-narrated PPTX/PDF client reports.

**Production stack:**
- Frontend: Next.js 14 on Vercel (`goreportpilot.com`)
- Backend: FastAPI on Railway
- DB/Auth: Supabase (project `kbytzqviqzcvfdepjyby`)
- AI: GPT-4.1
- Reports: python-pptx, matplotlib, LibreOffice
- Billing: Razorpay (12 plans, INR + USD)
- Email: Resend + Zoho Mail

**Pricing model differentiator:** limited by client count (Starter 2, Pro 10, Agency 50), unlimited reports per client. Competitors limit reports — we don't. This is core positioning.

**Reference docs in repo:**
- `PROJECT-HANDOVER-APRIL-22-2026.md` — full state of product
- `Marketing/context/` — brand voice, ICP definition, competitor matrix, outreach templates

---

## ICP — explicitly NOT India this phase

**Target geographies (priority order):**
1. United States
2. United Kingdom
3. Canada
4. Australia
5. Singapore
6. UAE
7. Germany, Netherlands, Ireland (English-friendly EU)

**Explicitly excluded:**
- India (despite founder being in India — INR pricing exists for inbound, not outbound prospecting)
- Non-English-primary markets
- Enterprise companies
- In-house marketing teams

**Target firmographics:**
- Digital marketing agencies, 2-30 employees
- Managing 5-50 clients
- Tech stack visible: GA4, Meta Ads, Google Ads
- Pain signals: complaints about Looker Studio, AgencyAnalytics pricing, manual PPTX work

---

## Architecture

```
n8n (self-hosted, MCP access confirmed)
├── Schedule triggers + webhook triggers
├── OpenAI (gpt-4o-mini bulk, gpt-4o for outreach/content)
├── Apollo free API (search = unlimited, enrichment = 50 credits/month)
├── Hunter.io (free 50/month OR Starter $34/mo for 500/month)
├── Reddit OAuth API (authenticated, reliable)
├── HN Algolia API (free, no auth)
├── Google Sheets (Prospect-Pipeline + log sheets)
├── Google Drive (draft documents — Outreach, Leads, Engage, Winback, Content)
├── Resend (Friday digest email)
└── Supabase webhooks (signup enrichment trigger)
```

**Primary prospect source:** Apollo free People API Search
- Endpoint: `POST /api/v1/mixed_people/api_search` — free, unlimited, no credits consumed
- Returns: name, title, company, LinkedIn URL, website, country, employee count
- Does NOT return email (requires separate enrichment)

**Email enrichment strategy (two-tier):**
- Tier 1: Hunter.io domain-search (free 50/month or Starter 500/month)
- Tier 2: Apollo People Enrichment (50 free credits/month)
- Budget: enrich top-scored prospects first, LinkedIn-outreach the rest
- Daily email budget: 2-4/day (free) or 20/day (Hunter Starter)

**Directory scraping: REMOVED.** Clutch, Sortlist, Agency Spotter, Google Maps all blocked by Cloudflare. Apollo API replaces all directory sources.

**Skip permanently:**
- Apify (cost overruns)
- Apollo Pro ($79/mo — free API search is sufficient)
- Firecrawl Hobby ($19/mo)
- Anthropic API (use OpenAI from existing wallet credits)
- Claude Routines (n8n via MCP is better)
- Make.com (explicitly excluded)
- Directory scraping (Cloudflare-blocked)

---

## Google Drive structure (created, live)

```
GoReportPilot-Marketing/ (1IqoA6XJsrm8Iw69-LQ9dbeP3yI6GrARj)
├── Outreach/        (1SB11BM-q5VAVJtlohxr8eCzGFwvUP_Xu) — WF2 email drafts
├── Leads/           (17Q56xdzyG5HAr97ZBg8bDICYTvr8pcHG) — WF3 signup enrichment
├── Engage/          (1y-bimMAnsrfCUd0v3CILtAb37xHpUQMy) — WF5 Reddit/HN drafts
├── Winback/         (1VyanVPNewmZU-RlOjohbvg48kExa6fe7) — WF6 churn drafts
├── Content/         (TO CREATE) — WF7 LinkedIn + WF8 blog drafts
├── Launch/          (TO CREATE) — WF9 Product Hunt assets
├── Snapshots/       (1sgCklwLyVrIbn_OZwk6GZmVs37G0BDTN) — WF4 competitor snapshots
├── context/         (1FpOBOAVVM2-k7kjecUUjBp8sYsM1dGhZ) — brand voice, templates
├── Prospect-Pipeline (sheet: 1sOtDT4OXPu2pVcmLepDyippa0vMXezr9EIsXMcP8iP0)
├── Competitor-Changelog (sheet: 10eUXlTpu0_9MnsbXF_SJqYBkGxDhX5lyALTuotx4wcM)
├── Harvester-Log    (sheet: 1pBPuJQK4WYvSepqvzHGAN3CBsXxzRvCkw5R5ZFsyHYs)
├── Drafter-Log      (sheet: 1F-m3p1BbgFjTmWpwad8wqlFt6LDyM9X53MR06Uc-90w)
└── Listener-Log     (sheet: 1iXiV_DFS5v7z7LNHcRfJIbQFP2O_K7CfCtjy3Ll0JX0)
```

---

## n8n environment

**Project:** `saurabh singh <sapienbotics@gmail.com>` (ID `6rX1MdQ6SZiPyO6q`)
**Folder:** `GoReportPilot` (ID `qtlBJqfotG6NXIJK`) — all marketing workflows here

**Existing workflows:**
- WF4: `0sU9XMFAHSCHkCpt` — Competitor Monitor (ACTIVE, production)
- WF1: `YGMtaRA9YvYqBC0B` — Prospect Harvester (needs Apollo endpoint fix)
- WF2: `kgXMHPgseTchGz4o` — Outreach Drafter (ACTIVE, awaits WF1 prospects)
- WF5: `lYCSDKm6vTw7W9wi` — Reddit HN Listener (ACTIVE, Reddit blocked pending OAuth)

**Existing credentials (bound):**
- Google Sheets: `Sapienbotics_Google Sheets account` (UrVcm7cFfj89uKrF)
- Google Drive: bound in WF4
- OpenAI: `OpenAi account_Begig_ActivumSG` (xTBe7w8R45tum5PI)
- Apollo: bound as Header Auth (x-api-key)
- Hunter: bound as Query Auth (api_key)

**Build pattern (refined from v1):**
1. Search n8n nodes + get type definitions (never guess parameters)
2. Write workflow SDK code
3. Validate via `n8n:validate_workflow`
4. Create via `n8n:create_workflow_from_code`
5. **ALWAYS publish_workflow immediately after create/update** (draft vs active distinction — critical lesson from v1)
6. Test with pinned data OR live execution
7. Save canonical SDK to `Marketing/workflows/`
8. Update `Marketing/RUNBOOK.md`
9. Saurabh binds any new credentials via n8n Settings → Credentials (NOT workflow editor)
10. **NEVER save workflow from n8n UI after MCP update** (stale tab overwrites fix)

---

## The 10 workflows (complete plan)

### OUTBOUND ENGINE

#### WF1: Prospect Harvester (Daily)
- **Schedule:** daily 6am IST, skip Sunday
- **Source:** Apollo free People API Search (`/api/v1/mixed_people/api_search`) — unlimited, no credits
- **Filters:** person_titles = Founder/CEO/Owner/Co-Founder/Managing Director, organization keywords = marketing agency/digital agency/performance marketing/PPC agency, employee ranges 1-50, locations = US/UK/CA/AU/SG/AE/DE/NL/IE
- **Page rotation:** (dayOfYear % 10) + 1 — cycles pages 1-10
- **Per prospect:** name, title, company, LinkedIn URL, website, country, employee count from Apollo
- **Email enrichment:** top 2-4/day via Hunter.io (tracks daily budget), rest marked status=new_no_email
- **Website scrape:** homepage best-effort for services, client logos, tech signals
- **Scoring:** OpenAI gpt-4o-mini, 1-10 fit score
- **Dedup:** against Prospect-Pipeline by website domain
- **Output:** append to Prospect-Pipeline sheet, log to Harvester-Log
- **Target:** 30-50 prospects/day, 900-1500/month

#### WF2: Outreach Drafter (Daily)
- **Schedule:** daily 9am IST, skip Sunday
- **Input:** top 10 prospects with status=new (has email) from Prospect-Pipeline
- **Per prospect:** scrape website, read brand-voice.md + outreach-templates.md from Drive
- **Draft:** OpenAI gpt-4o generates subject + 80-120 word body referencing one specific thing from their site
- **Output:** .txt file per prospect in Outreach/ folder, status updated to "drafted"
- **For prospects with status=new_no_email:** draft LinkedIn connection message instead of email
- **Log:** Drafter-Log sheet
- **Manual checkpoint:** Saurabh reviews every draft, edits ~30%, sends from Zoho mailbox or LinkedIn

### INBOUND ENGINE

#### WF7: LinkedIn Content Drafter (Daily) — NEW
- **Schedule:** daily 10am IST, skip Sunday
- **Input:** reads latest outputs from WF4 (competitor changes) + WF5 (Reddit/HN trends)
- **Logic:** OpenAI gpt-4o drafts 1 LinkedIn post (100-200 words) based on:
  - Today's competitor intel (if any changes detected)
  - Today's Reddit/HN engagement opportunities
  - Rotating content pillars: Mon=competitor comparison, Tue=agency pain point, Wed=product tip, Thu=industry trend, Fri=founder story
- **Brand voice:** reads brand-voice.md, applies strictly
- **Output:** .txt file in Content/LinkedIn/ subfolder, named `{date}-linkedin-draft.txt`
- **Log:** Content-Log sheet (columns: date, content_pillar, word_count, source_wf4, source_wf5, status)
- **Manual checkpoint:** Saurabh reviews, edits, posts manually from personal LinkedIn

#### WF8: Weekly Blog Drafter (Monday)  — NEW
- **Schedule:** Monday 6am IST
- **Input:** aggregates full week of WF4 competitor diffs + WF5 engagement data + WF1 prospect signal notes
- **Logic:** OpenAI gpt-4o generates:
  - Topic recommendation (based on what's trending in the data)
  - 1500-word SEO-optimized article draft with H2/H3 structure
  - Meta description + 5 target keywords
  - 3 internal linking suggestions to goreportpilot.com features
- **Brand voice:** reads brand-voice.md
- **Output:** .txt file in Content/Blog/ subfolder, named `{date}-blog-draft.txt`
- **Log:** Content-Log sheet
- **Manual checkpoint:** Saurabh reviews, edits, publishes on blog

#### WF9: Product Hunt Launch Prep (One-time) — NEW
- **Trigger:** manual execution (not scheduled)
- **Logic:** OpenAI gpt-4o generates complete PH launch kit:
  - Tagline (max 60 chars)
  - Description (max 260 chars)
  - Maker comment (500 words — story of why built, who for, what's different)
  - 5 first-day comment responses for common questions
  - Launch checklist with timing recommendations
  - Social announcement drafts (LinkedIn, Twitter, Reddit)
- **Input:** reads brand-voice.md, icp-definition.md, competitor-matrix.md, product handover docs
- **Output:** all assets in Launch/ subfolder as individual .txt files
- **Manual checkpoint:** Saurabh reviews all assets, schedules launch day

#### WF10: Directory Submission Tracker (Weekly) — NEW
- **Schedule:** weekly Monday 9am IST
- **Logic:**
  - Maintains a Google Sheet with target directories: Capterra, G2, SaaSWorthy, AlternativeTo, GetApp, Product Hunt, SaaSHub, BetaList
  - Columns: directory, submission_url, status (not_started/submitted/live/rejected), submitted_date, live_url, notes
  - For status=not_started: generates submission copy (description, category, screenshots list) via OpenAI
  - For status=submitted: HTTP checks the listing URL to detect if it went live
  - Updates status automatically when listing detected
- **Output:** updated Directory-Submissions sheet, alerts on status changes
- **Manual checkpoint:** Saurabh submits manually (most directories require human form fill), workflow tracks status

### COMMUNITY ENGAGEMENT

#### WF5: Reddit + HN Listener (2x Daily)
- **Schedule:** twice daily 8am IST + 7pm IST, runs 7 days
- **Sources:**
  - HN Algolia API (free, no auth) — working
  - Reddit OAuth API (authenticated via script app) — in progress, currently blocked on unauthenticated
- **Keywords:** "client reporting", "looker studio alternative", "AgencyAnalytics", "Whatagraph", "automate reports", "white label report", "agency reporting tool", "marketing report automation"
- **Scoring:** OpenAI gpt-4o-mini batch scores all posts 1-10, filters >= 7
- **Draft comments:** 30-60 words, value-first, never pitch GoReportPilot in opening sentence
- **Output:** .txt files in Engage/ folder, log to Listener-Log sheet
- **Manual checkpoint:** Saurabh rewrites every comment in own voice, posts from real account. NEVER paste AI verbatim.

### INTELLIGENCE

#### WF4: Competitor Monitor (Daily) — ACTIVE IN PRODUCTION
- **Schedule:** daily 8am IST
- **Targets:** AgencyAnalytics, Whatagraph, Swydo, NinjaCat — /pricing, /features, homepage (12 URLs)
- **Snapshots:** .txt files in Drive Snapshots/ folder, Drive versioning = change history
- **Diff:** OpenAI gpt-4o-mini compares old vs new, outputs JSON with has_meaningful_change, summary, categories
- **Output:** Competitor-Changelog sheet, silent if no changes
- **Feeds:** WF7 (LinkedIn drafts) + WF8 (blog topics)

### CONVERSION

#### WF3: Signup Lead Enrichment (Event-driven) — POST META APPROVAL
- **Trigger:** Supabase webhook on `auth.users` insert → POST to n8n webhook
- **Logic:** skip personal domains (gmail/yahoo/hotmail/outlook), Apollo lookup by domain, Hunter fallback, scrape website
- **Output:** intelligence summary + welcome email draft + 3 talking points in Leads/ folder
- **Manual checkpoint:** Saurabh sends welcome email within 2 hours

### RETENTION

#### WF6: Churn Early-Warning (Daily) — AFTER 5 PAID CUSTOMERS
- **Schedule:** daily 11pm IST
- **Logic:** Supabase query for paid users with last_login >7 days OR report-generation dropped >50% week-over-week
- **Output:** personal re-engagement email draft in Winback/ folder
- **Manual checkpoint:** Saurabh edits heavily, sends personally

---

## Marketing Operations Dashboard (Admin Panel)

All marketing data must be visible and actionable from the existing admin dashboard at `/admin/`. No separate tool, no Google Sheets checking — everything in one place.

### Location
New tab in existing admin panel: `/admin/marketing/` — sits alongside the existing analytics tab.

### Existing admin infrastructure (reuse)
- `frontend/src/app/admin/` — admin layout with route guard (`profiles.is_admin`)
- `backend/routers/admin.py` + `admin_analytics.py` — existing admin API patterns
- Supabase RLS with admin flag — already enforced
- Auto-refresh pattern (5 min) — already built in admin analytics

### Data source decision
Migrate marketing data from Google Sheets to **Supabase tables** for tight integration with existing admin backend. Workflows write to both Sheets (backup/portability) AND Supabase (dashboard reads). Tables:
- `marketing_prospects` — mirrors Prospect-Pipeline sheet
- `marketing_outreach_drafts` — email/LinkedIn drafts with copy-to-clipboard
- `marketing_engage_opportunities` — Reddit/HN threads with draft comments
- `marketing_competitor_changes` — changelog entries
- `marketing_content_drafts` — LinkedIn posts, blog drafts
- `marketing_directory_submissions` — submission tracker
- `marketing_workflow_logs` — unified log across all workflows

### Dashboard sections

#### 1. Overview (top cards)
- Prospects today / this week / this month
- Outreach drafted / sent / replied
- Reddit/HN opportunities found / engaged
- Competitor changes detected
- Content drafted / published
- Pipeline health score (prospects → outreach → reply → customer conversion funnel)

#### 2. Prospect Pipeline
- Full table: company, founder, email, LinkedIn, website, country, fit score, status, date
- Filters: by status (new, new_no_email, drafted, sent, replied, converted), by score, by country, by date
- Actions per row:
  - **Copy email draft** (one-click clipboard for Zoho)
  - **Copy LinkedIn message** (one-click clipboard)
  - **Mark as sent** (updates status)
  - **Mark as replied** (updates status)
  - **Skip** (removes from outreach queue)
  - **Open website** (new tab)
  - **Open LinkedIn** (new tab)

#### 3. Outreach Drafts
- Today's drafts: subject, body preview, prospect name, fit score
- **Copy to clipboard** button per draft (formatted for email or LinkedIn)
- **Edit inline** before copying
- Status tracking: drafted → sent → replied → converted
- Reply rate metric prominent

#### 4. Reddit/HN Engagement
- Today's qualified threads: title, URL, score, source, draft comment
- **Copy draft comment** (one-click)
- **Open thread** (new tab, opens Reddit/HN directly)
- **Mark as posted** (updates status)
- Engagement rate metric

#### 5. Competitor Intel
- Latest changes: competitor, page, what changed, when
- Historical timeline view
- **Use in outreach** button — copies change summary as outreach ammunition

#### 6. Content Queue
- LinkedIn drafts: today's draft, copy button, mark as posted
- Blog drafts: this week's draft, copy button, mark as published
- Product Hunt assets: all PH materials, copy buttons
- Directory submissions: status board

#### 7. Workflow Health
- All 10 workflows: last run time, status (success/error), next scheduled run
- Error alerts prominent
- Run logs expandable per workflow
- Manual trigger button per workflow (calls n8n API)

### Build approach
- **Phase 5 in build order** — after basic marketing is running, before "optimize"
- Backend: new `backend/routers/marketing.py` with Supabase queries
- Frontend: new `/admin/marketing/` page with sub-tabs
- n8n workflows updated to dual-write (Sheets + Supabase) via HTTP Request to backend API
- Reuse existing admin UI patterns (stat cards, tables, Tailwind bar charts)

---

## Context files (the brain)

Stored in Drive at `context/` folder (1FpOBOAVVM2-k7kjecUUjBp8sYsM1dGhZ) and in repo at `Marketing/context/`. Every workflow reads from Drive at runtime.

### `brand-voice.md` (Drive: 10YMhbTYBSbJp5hqyh3FBok7u4cZ4bFHf)
Tone: confident, technical, direct, zero fluff. Sound like a founder who used to spend 6 hours/month making client reports and got fed up. Banned phrases: "leverage", "synergy", "in today's fast-paced world", "revolutionary", "AI-powered", "game-changer", "seamless", "robust", "cutting-edge". Always: name competitors, use specific numbers, write like a person not a brand. Lengths: emails 80-120 words, LinkedIn posts 100-200, comments 30-60, blog 1500.

### `icp-definition.md`
Primary: digital marketing agencies, 2-30 employees, managing 5-50 clients. Geography: US/UK/CA/AU/SG/AE/DE/NL/IE — NOT India. Tech: GA4, Meta Ads, Google Ads. Pain: Looker Studio time cost, AgencyAnalytics pricing, manual PPTX. Disqualifiers: in-house teams, <5 clients, enterprises, India.

### `competitor-matrix.md`
Live comparison: AgencyAnalytics, Whatagraph, Swydo, NinjaCat, Looker Studio. Auto-updated by WF4.

### `outreach-templates.md` (Drive: 1YYh8G00Zxroya7ybs2utBfhh-zjNi9ve)
Template structures for: cold email, LinkedIn connection message, LinkedIn post, signup welcome, churn winback, Reddit comment frame, blog outline.

---

## Manual checkpoints (non-negotiable)

1. **Cold emails** — read each, edit ~30%, send from Zoho. ~15 min/day for 10 emails.
2. **LinkedIn messages** — review AI draft, personalize, send from LinkedIn. ~15 min/day.
3. **LinkedIn posts** — review daily draft, edit tone, post manually. ~5 min/day.
4. **Reddit/HN comments** — never paste verbatim, rewrite in real voice. ~10 min/day.
5. **Signup welcome emails** — review intelligence, edit, send within 2 hours. ~5 min/signup.
6. **Blog posts** — review weekly draft, edit heavily, publish. ~30 min/week.
7. **Product Hunt launch** — review all assets, execute launch day manually. One-time.
8. **Directory submissions** — fill forms manually, workflow tracks status. ~15 min/week.
9. **Churn winback** — heavy edit, personal send. ~5 min/customer.
10. **Friday review** — read weekly digest, update context files. ~30 min/week.

**Total manual time: ~60-75 min/day weekdays + 1 hour Friday.**

---

## Success criteria — first 30 days post-launch

### Outbound
- 900-1500 ICP prospects in pipeline (30-50/day × 30)
- 200 personalized outreach sent (cold email + LinkedIn combined)
- 5% reply rate = 10 replies, 2-3 demos, 1-2 paying customers

### Inbound
- 20 LinkedIn posts published (1/weekday)
- 4 blog posts published (1/week)
- Product Hunt launch completed with 50+ upvotes
- Listed on 5+ directories (Capterra, G2, SaaSWorthy, AlternativeTo, GetApp)

### Community
- 30-50 Reddit/HN comments posted (real, value-first)
- 5+ threads where GoReportPilot mentioned naturally

### Intelligence
- Competitor changes tracked daily, 5-10 actionable intel pieces

### Conversion
- Every signup enriched within 60 seconds (post Meta approval)
- 30-50 trial signups from all channels combined

### Revenue target
- 1-2 paying customers by day 30
- 3-5 paying customers by day 60

If reply rate <2% after 100 outreach: pause volume, fix targeting/copy, then resume.

---

## Build order

### Phase 1: Fix + verify (this week)
- [ ] Fix WF1 with Apollo free search endpoint (`/api/v1/mixed_people/api_search`)
- [ ] Fix WF5 with Reddit OAuth (app registration in progress)
- [ ] Verify WF1 → WF2 pipeline produces real prospects → real draft emails
- [ ] Verify WF4 runs clean for 3 consecutive days
- [ ] Verify WF5 produces real HN results

### Phase 2: Inbound engine (next week)
- [ ] Build WF7: LinkedIn Content Drafter
- [ ] Build WF8: Weekly Blog Drafter
- [ ] Build WF9: Product Hunt Launch Prep (one-time)
- [ ] Build WF10: Directory Submission Tracker

### Phase 3: Conversion + retention (post Meta approval)
- [ ] Build WF3: Signup Lead Enrichment
- [ ] Build WF6: Churn Early-Warning (after 5 paid customers)

### Phase 4: Marketing Operations Dashboard (week 3-4)
- [ ] Create Supabase marketing tables (marketing_prospects, marketing_outreach_drafts, etc.)
- [ ] Build `backend/routers/marketing.py` API endpoints
- [ ] Build `/admin/marketing/` dashboard page with all 7 sections
- [ ] Update all n8n workflows to dual-write (Sheets + Supabase)
- [ ] Add copy-to-clipboard, mark-as-sent, inline-edit actions
- [ ] Add workflow health monitoring with manual trigger buttons

### Phase 5: Optimize (week 4-5)
- [ ] Tune OpenAI prompts based on reply rates
- [ ] Add LinkedIn message drafting to WF2 for no-email prospects
- [ ] Implement cross-run dedup for WF5 (reduce duplicate drafts)
- [ ] Add email warm-up tracking
- [ ] Friday email digest workflow via Resend

---

## Working principles

- **Validate before create.** Always `n8n:validate_workflow` first.
- **ALWAYS publish after create/update.** Draft vs active distinction is real. Schedule runs active version only.
- **Never save from n8n UI after MCP update.** Stale tab overwrites. Refresh tab before any UI interaction.
- **Bind credentials via Settings → Credentials, not workflow editor.**
- **Set + autoMapInputData for all Sheets operations.** Shape data in Set/Code node first.
- **CSV upload for sheet creation** (pre-seeded headers, Drive auto-converts, tab = filename).
- **No Google Docs for storage.** .txt files only. Drive versions both equally well.
- **Don't guess node parameters.** Always `n8n:search_nodes` then `n8n:get_node_types`.
- **Prefer dedicated nodes** over HTTP Request when n8n has them.
- **Idempotent re-runs.** Dedupe by domain/URL before insert.
- **No silent failures.** Every workflow logs to its own sheet. Every error captured.
- **Cost discipline.** Log OpenAI token usage. Target <$0.50/day total across all workflows.
- **Identity awareness.** Every API key is Saurabh's personal account.
- **Document as you go.** Update `Marketing/RUNBOOK.md` after every workflow ships.

---

## What NOT to do

- Don't auto-send cold emails. Drafts only.
- Don't auto-post to Reddit/HN. Drafts only.
- Don't auto-post to LinkedIn. Drafts only.
- Don't auto-publish blog posts. Drafts only.
- Don't target India in any prospect query.
- Don't use Apify, Anthropic API, or Make.com.
- Don't scrape Clutch/Sortlist/Agency Spotter/Google Maps (Cloudflare-blocked).
- Don't use Apollo /people/search or /mixed_people/search (paid only). Use /mixed_people/api_search (free).
- Don't burn the prospect list with bad outreach. Pause at <2% reply rate.
- Don't create workflows outside the `GoReportPilot` folder.
- Don't save workflows from n8n UI after MCP updates.

---

## Communication protocol

- **Saurabh writes prompts in Claude Web.** They get pasted into Claude Code.
- **Claude Code executes.** Read repo, write code, build workflows, validate, test, ship.
- **Report back via Google Sheets + repo commits.** No Discord.
- **When stuck, ask precise questions.** Don't guess credentials or business context.
- **Flag risks proactively.** Brand damage, list burning, API limit exhaustion — surface before building.
- **Update this doc.** When vision shifts, edit `Marketing/VISION.md` and commit.

---

## What success looks like in 6 weeks

- All 10 workflows running in production
- Prospect pipeline at 1,500+ ICP agencies
- 200+ personalized outreach sent (email + LinkedIn combined)
- 20+ LinkedIn posts published, growing follower base
- 4+ blog posts published, indexed by Google
- Product Hunt launched with 50+ upvotes
- Listed on 5+ SaaS directories
- 50+ Reddit/HN engagements
- 3-5 paying customers acquired
- Every signup enriched within 60 seconds
- Brand voice + ICP refined based on what's converting
- Friday digest emails reaching Saurabh's inbox
- Saurabh spending ≤75 min/day on marketing manual work
- **Marketing Operations Dashboard live at `/admin/marketing/`** — all prospect, outreach, engagement, competitor, content data visible and actionable from one screen
- Total monthly spend: under $50 (with Hunter Starter) or under $20 (free only)

This is a complete, multi-channel, mostly-automated marketing machine for a solo founder pre-launch. No channel left unaddressed. No context-switching between Google Sheets, Drive, and n8n — everything controlled from the admin dashboard.
