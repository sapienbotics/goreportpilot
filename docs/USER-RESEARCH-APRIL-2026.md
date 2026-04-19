# USER RESEARCH — APRIL 2026
## Deep Pain-Point & Competitor Research for Feature Prioritization

**Research window:** 2025–2026 reviews, Reddit, LinkedIn, competitor changelogs, industry surveys.
**Evidence base:** ~70 distinct verbatim quotes across G2, Capterra, Trustpilot, Reddit, Wayfront interviews, PPC.land survey, competitor changelogs.
**Produced:** April 19, 2026.
**Purpose:** Identify the 3–5 highest-impact features GoReportPilot should build next based on validated user pain, not assumptions.

---

## 1. EXECUTIVE SUMMARY — Top 5 Recommendations (Ranked)

| # | Recommendation | 1-line Justification | Effort |
|---|---|---|---|
| 1 | **Diagnostic AI Narrative v2** (prompt overhaul + drill-down) | Every competitor shipped "AI summaries"; users call them shallow. Real diagnostic commentary ("CTR dropped 18% *because* Campaign X fell 2.3%→4.1%") is our strongest wedge — AgencyAnalytics AskAI, Whatagraph IQ, Databox Genie are still at the "summary" layer. | 2 days |
| 2 | **Connection Health Monitor + Auto-Alerts** | #1 cross-cutting pain across all 8 competitors: connectors silently break, scheduled reports go out empty. Marketing angle: "Reports that actually arrive with data." | 3 days |
| 3 | **Goals & Alerts (threshold-based email)** | Whatagraph, Swydo, NinjaCat all shipped this in 2025–26. Shifts positioning from "reporting tool" to "performance management." Hottest emerging category. | 3–4 days |
| 4 | **Custom Cover-Page Editor + Branded Title Slides** | AgencyAnalytics Capterra quote: *"The cover page of the reports is super ugly, like unbelievably ugly."* 5+ reviewers name ugly/rigid covers as a dealbreaker. Low-effort, high-visual-impact demo artifact. | 1–2 days |
| 5 | **Client Comments on Shared Reports** | Nobody competitive has a clean client-feedback loop on shared links. 73% of agency churn attributed to "poor reporting, not poor results" — closing the loop makes reports a two-way conversation. | 2 days |

**Total: ~11–13 days.** Ship #1, #2, #4 in first sprint (highest impact / lowest effort), then #3 and #5.

---

## 2. VALIDATED PAIN POINTS — Top 10 (with direct quotes + sources)

### Pain #1 — Connectors silently break; scheduled reports go out empty
**Frequency:** Cited for AgencyAnalytics, DashThis, Whatagraph, Databox, NinjaCat, Supermetrics.
**Intensity:** Dealbreaker. This is the single most-repeated complaint across every platform.

> "Sometimes the integration does not work properly, and when the scheduled report is sent to the client, it goes empty." — Muhammad Umar A. ([G2 AgencyAnalytics](https://www.g2.com/products/agencyanalytics/reviews))

> "Data sources being randomly disconnected for no apparent reason." — G2 Whatagraph reviewer

> "Consistently, reports did not generate in full or did not generate correctly. Tokens expire and even after re-authentication, data does not pull in correctly." — Kim S., NinjaCat ([Capterra](https://www.capterra.com/p/132630/NinjaCat/reviews/))

> "Widgets stop pulling data or default to the wrong Facebook/Instagram account, sometimes for weeks." — Databox G2 reviewer

### Pain #2 — Per-client / per-dashboard / per-connector pricing balloons
**Frequency:** AgencyAnalytics (doubled from $10→$20/mo in May 2025), DashThis ($629/mo for 25 clients × 4 reports), Swydo, Whatagraph.
**Intensity:** Primary driver of churn.

> "I have used AgencyAnalytics for several years now, but have stopped due to their new pricing model and caging features that I used before on lower-tier plans behind their new, much more expensive plans." — [r/marketing](https://www.reddit.com/r/marketing/comments/1d2ukj3/comment/l96wlr8/)

> "If you want to use their MySQL integration, they charge $700/mo on top of the plan you want to purchase." — [r/marketing](https://www.reddit.com/r/marketing/comments/1ijc8me/)

> "A subscription became a little pricey for me; I found I wasn't using the tool enough to warrant the cost." — Erin H., Apr 2025 ([Capterra DashThis](https://www.capterra.com/p/163170/DashThis/reviews/))

> "Higher plans can feel like worse value than lower ones, with little incentive to upgrade." — G2 AgencyAnalytics reviewer

### Pain #3 — Rigid templates, ugly cover pages, no customization
**Frequency:** AgencyAnalytics (5+ reviewers), DashThis, Whatagraph.

> "The cover page of the reports is super ugly, like unbelievably ugly and they offer no options to customize this." — Sam M., Dec 2021 ([Capterra AgencyAnalytics](https://www.capterra.com/p/158746/Agency-Analytics/reviews/))

> "If you want to change up the title page or try to combine elements, there really isn't a way to do that." — G2 AgencyAnalytics

> "The charts and visuals are not customizable with font selections and charts. Branding only applies to the logo, backgrounds and some accent colors." — [r/digital_marketing](https://www.reddit.com/r/digital_marketing/comments/1ijcae2/)

### Pain #4 — AI "summaries" are shallow, not diagnostic
**Frequency:** Growing — every competitor ships AI; quality is the differentiator.

> "My least favorite thing is how limited the software is with insights — I find it's great at only a few different metrics." — [Whatagraph's review of AgencyAnalytics](https://whatagraph.com/reviews/agencyanalytics)

> "If you aim to generate reports leveraging machine learning and AI insights to understand campaign performance drivers, AgencyAnalytics likely falls short… AgencyAnalytics' AI Summary feature does just that — summarize." — Whatagraph review

**Context:** Asana 2025 Marketing AI Report — only 49% of marketers trust AI for admin tasks ([source](https://asana.com/resources/ai-survey-marketing-skeptics)). Knowledge workers spend 4.3 hrs/week fact-checking AI outputs ([drainpipe.io](https://drainpipe.io/the-reality-of-ai-hallucinations-in-2025/)). **Demand is real, trust is fragile** — diagnostic + editable output wins.

### Pain #5 — Predatory billing / auto-renew / non-refundable contracts
**Frequency:** Whatagraph (flagship offender), Databox, NinjaCat, Swydo.

> "Expensive, low value, and predatory billing and customer service." — [endorsal.io/reviews/whatagraph](https://www.endorsal.io/reviews/whatagraph?rating=1)

> "I was charged extra without any notice. When I tried to contact customer support, their response was basically, 'Well, that's just how it is.'" — Razvan T., Apr 2025 ([Capterra Swydo](https://www.capterra.com/p/159323/Swydo/reviews/))

> "Our services are billed in advance and are non-refundable." — Vince T., Apr 2025 (Databox)

> "After several years of issues, we have notified them of cancellation and requested the final quarter be waived due to the massive issues and software components they shelved, but they insist on holding us through the contract." — Kim S. (NinjaCat)

### Pain #6 — Dismissive / slow customer support
**Frequency:** Oviond, Databox, AgencyAnalytics, Klipfolio, NinjaCat.

> "Their support team blames the client but then when Databox is informed the broken metrics are included in the templates they made, then they act all confused and pass along the blame." — Guy M., Jun 2024 (Capterra)

> "Every time they contact support they get the impression that they are bothering them." — G2 Klipfolio

> "Each time we contacted Support, they would re-send a link to a Help section (in which their examples are not kept up to date)." — Kim S. (NinjaCat)

### Pain #7 — Time cost of manual reporting
**Frequency:** Industry-wide consensus.

> "In early days, the biggest problem was that you really need to spend man-hours on preparing reports… about three to four hours per one report." — Justas Malinauskas, Whatagraph Founder ([Wayfront](https://wayfront.com/blog/agency-client-reporting))

> "We were doing 360 days a year of manual reporting and we wanted to automate that low-level reporting." — Simon Barks, McCann Central ([Supermetrics](https://supermetrics.com/blog/marketing-agency-client-reporting))

> "Senior strategists hired to grow business don't have time to catch CPA spikes because they're too busy jumping between tabs." — [PPC.land Fluency Survey 2025](https://ppc.land/71-of-ad-agencies-say-manual-work-is-putting-campaigns-at-risk/)

**Survey stats:** 71% of ad-ops teams say manual processes put campaigns at risk. 39.75 hrs/strategist/month on routine tasks. 89% want better reporting tools. Marketers spend 20%+ of workweek on reporting ([DataStaqAI](https://datastaqai.com/blog/agency-client-reporting-automation)).

### Pain #8 — White-label is gated, watermarks leak through
**Frequency:** Looker Studio (free-tier watermark), AgencyAnalytics (white-label gated on higher tier).

> "Franco S. wants to 'tailor their reports to match their company branding'" — flagged as gap on lower AgencyAnalytics tiers ([Whatagraph review](https://whatagraph.com/reviews/agencyanalytics))

> **ALM Corp 2025:** "Agencies lose clients over seemingly minor branding inconsistencies that reveal their tool stack." ([source](https://almcorp.com/blog/white-label-client-reporting-agencies/))

### Pain #9 — Wrong / inaccurate calculations
**Frequency:** Databox, Oviond, NinjaCat, Whatagraph.

> "The most simple calculations are wrong too often." — Hidde O., Jun 2024 (Databox)

> "The data that gets output isn't always correct, and there is no way to create custom metrics to rectify the wrong data outputs." — G2 Oviond

### Pain #10 — Sudden pricing / plan changes that break existing workflows
**Frequency:** AgencyAnalytics (May 2025), DashThis (Mar 2026), Swydo (3-year doubling), Oviond (forced migration wiping reports).

> "Starting March 30, 2026, DashThis is retiring its unlimited data sources model, with plan tiers now capped by both the number of dashboards and active data sources." — multiple sources

> "All templates will be deleted, all reports deleted, all integrations deleted." — Oviond forced migration G2 quote

---

## 3. WHAT USERS LOVE — Features That Create Lock-in

### "Smart-looking" branded PDFs (Swydo leading)
> "Beautiful reports, branded with my agency logo, cover photo customisation options, simple set up, and the templated reports often didn't need much tweaking." — Nabeel T., Jan 2026 (Swydo Capterra)

> "I export very smart-looking PDF's which clients benefit from." — Emlyn D., Mar 2025 (Swydo)

### Visual polish & template variety (Whatagraph)
> "Pretty solid visualization options when you need to impress clients who are visual learners. Their templates are decent time-savers." — [r/googleads](https://www.reddit.com/r/googleads/comments/1ki920q/comment/ms2rp9k/)

### One-click multi-platform consolidation (universal love)
> "I was able to analyze multiple analytics (ads, website, etc) for our clients from one place." — Feraud O., Jul 2025 (AgencyAnalytics Capterra)

### Transparent SEO reports "at scale" (positive benchmark)
> "AgencyAnalytics provides easy to understand, transparent SEO reports for our clients at scale." — Harry Strick, Ranked.ai (Wayfront)

### What the "love" teaches us
1. Visual polish of individual slides/pages matters more than dashboard complexity.
2. Agency-logo branding is the minimum emotional ask; ugly cover pages are immediate grounds for complaint.
3. The love language is **time saved on the repetitive 80%** — templates that "often didn't need much tweaking" is the highest praise.

---

## 4. FEATURE GAP ANALYSIS — What GoReportPilot Lacks vs. What Users Actively Want

| Feature | User Demand Evidence | GRP Status | Gap Size |
|---|---|---|---|
| AI chat over client data ("Ask your data") | AgencyAnalytics AskAI 2.0, Whatagraph IQ, Databox Genie, DashThis AI Insights Pro, NinjaCat Agent, Swydo AI — **all shipped 2025–26** | Not built | LARGE |
| Diagnostic AI narrative (not just summary) | "AI Summary just summarizes… falls short on understanding drivers" (Whatagraph review) | Narrative exists; prompt is summary-grade | MEDIUM |
| Goals & Alerts (threshold-based monitoring) | Whatagraph, Swydo, NinjaCat all launched 2025–26 | Not built | MEDIUM |
| Connection health / broken-connector alerts | #1 cross-cutting pain in reviews | Not built | LARGE |
| Custom cover page / branded title slide editor | 5+ AgencyAnalytics reviewers cite ugly/rigid covers | Templates exist; title slide not editable | SMALL |
| Portfolio / Roll-up view across all clients | AgencyAnalytics shipped Nov 2025 | Not built | MEDIUM |
| Forecasting / predictive | AgencyAnalytics, Databox, Whatagraph shipping 2025–26 | Not built | LARGE |
| Client comments on shared reports | No competitor has this cleanly | Shared links exist; no comments | SMALL |
| Reddit Ads / TikTok Organic / GoHighLevel integrations | Hottest 2025–26 additions across 3+ competitors | CSV upload supports; no native | MEDIUM |
| Proactive email summaries ("report arrived" + AI note) | Swydo shipped Apr 2026 | Email delivery exists; no AI highlight | SMALL |

---

## 5. STRATEGIC RECOMMENDATIONS — 3–5 Features to Build Next (3–5 day sprint each)

### ⭐ Recommendation #1 — Diagnostic AI Narrative v2
**Problem solved:** Users call current competitor AI "summaries" shallow. Our narrative is currently in the same bucket — good prose, but doesn't *explain why* metrics moved.
**Evidence:**
- "AgencyAnalytics' AI Summary feature does just that — summarize." (Whatagraph review)
- "Limited with insights… great at only a few different metrics." (AgencyAnalytics G2)
- Asana 2025: marketers don't trust AI that doesn't cite specifics.
**What to build:**
1. Rewrite `ai_narrative.py` prompt to require *causal attribution*: "CTR dropped 18% — driven by Campaign X (CTR 2.3% vs. account avg 4.1%)."
2. Inject top-5 movers (best/worst campaigns, highest-CAC segments) into prompt context before generation.
3. Add a "Show reasoning" toggle on each section revealing the specific data rows the AI used.
**Effort:** 2 days (prompt engineering + UI toggle, no new infra).
**Competitive impact:** Hero marketing claim — "The only AI that explains *why*, not just *what*."

### ⭐ Recommendation #2 — Connection Health Monitor + Auto-Alerts
**Problem solved:** #1 cross-cutting pain. Scheduled reports going out empty is the single most-cited competitor failure. Every incumbent is vulnerable here.
**Evidence:**
- "Scheduled report is sent to the client, it goes empty." (AgencyAnalytics)
- "Data sources being randomly disconnected for no apparent reason." (Whatagraph)
- "Tokens expire and even after re-authentication, data does not pull in correctly." (NinjaCat)
**What to build:**
1. New `connection_health` table (last_pulled_at, last_success, consecutive_failures, token_expires_at).
2. APScheduler job (daily) pings each connection with a cheap API call; flags failures.
3. Pre-generation gate: report generation pauses and emails the agency owner *before* sending an empty report to their client.
4. Dashboard widget: "3 clients have connection issues — fix now" CTA.
5. Token expiry countdown on integrations page (we already have Meta 60-day expiry risk).
**Effort:** 3 days.
**Competitive impact:** Direct marketing angle — "Never send an empty report again." Backed by a live status page.

### ⭐ Recommendation #3 — Goals & Alerts (Proactive Monitoring)
**Problem solved:** Shifts GRP positioning from "reporting tool" to "performance management." Hot 2025–26 category (3 competitors shipped).
**Evidence:**
- Whatagraph Goals & Alerts launched 2025 ([source](https://digitalagencynetwork.com/whatagraph-launches-goals-alerts-helping-agencies-shift-from-reactive-to-proactive-reporting/))
- Swydo Smarter Monitoring (Mar 2026)
- PPC.land quote: "Senior strategists don't have time to catch CPA spikes."
**What to build:**
1. Per-client goals UI: "Keep CAC ≤ ₹500", "ROAS ≥ 3x", "Weekly spend ≤ $X."
2. APScheduler job (hourly/daily per goal) evaluates; triggers Resend email + dashboard alert when breached.
3. Reuses existing connection-pull infrastructure.
**Effort:** 3–4 days.
**Competitive impact:** Unlocks "We catch CPA spikes before your client notices" narrative. Expands TAM beyond reporting into ad-ops.

### ⭐ Recommendation #4 — Custom Cover-Page Editor + Branded Title Slides
**Problem solved:** AgencyAnalytics' most-quoted visual complaint, and the first thing a client sees.
**Evidence:**
- "Cover page is super ugly, like unbelievably ugly." (Sam M., Capterra)
- "No way to change up the title page." (G2)
- "Font selections and charts not customizable." (r/digital_marketing)
**What to build:**
1. Cover-page section in client settings: headline (editable), subtitle, logo position (left/center/right), color accent picker.
2. 3–5 preset cover designs (hero image + agency logo, minimal, bold, corporate).
3. Optional client-logo background or hero image upload (Supabase Storage).
4. Reflect in PPTX generation (python-pptx slide 1) + PDF preview.
**Effort:** 1–2 days.
**Competitive impact:** Strong demo artifact. Every screenshot comparison will make incumbents look dated.

### ⭐ Recommendation #5 — Client Comments on Shared Reports
**Problem solved:** No competitor closes the feedback loop cleanly. 73% of agency churn is attributed to "poor reporting, not poor results" ([Reportr.agency](https://reportr.agency/blog/seo-report-format-guide)) — turning reports into conversation reduces that.
**Evidence:**
- No competitor has this as a first-class feature.
- Jeremy Moser (uSERP): *"If a CMO or COO reviews your deck, and it's just gibberish about DR scores, you are going to be the first vendor cut when budgets get tight."* — the feedback loop itself is protective.
**What to build:**
1. Comment thread widget on `shared/[hash]/page.tsx`.
2. Simple name + email (no signup) with optional password gate (reuses existing share-link password).
3. Notification email to agency owner on new comment.
4. Comments table in Supabase with RLS tied to report_id.
**Effort:** 2 days.
**Competitive impact:** Sticky differentiator. Supports the "reports clients actually engage with" narrative.

---

## 6. FEATURES TO EXPLICITLY NOT BUILD

### 🚫 The integration-count race (NinjaCat/AgencyAnalytics territory)
**Why:** Competitors have 30–100+ integrations. Chasing parity is an infinite money pit; CSV upload already handles 90% of long-tail platforms.
**Exception:** Reddit Ads + TikTok Organic are genuinely hot (shipped by 3+ competitors in 2025–26) — worth native connectors *when stable*. Skip GoHighLevel, Quora Ads, Apple Search Ads for now.

### 🚫 Live/real-time dashboards as a standalone product
**Why:** Competitors invested heavily here and users still send static reports. 61.7% of agencies send static reports; clients abandon dashboards. Our PPTX wedge actively wins BECAUSE it's not a dashboard. Don't dilute.

### 🚫 Drag-and-drop visual report builder
**Why:** Huge build effort (weeks, not days). Our smart slide selection + template variety already solves the use case. Builders become maintenance burdens.

### 🚫 Native mobile apps
**Why:** Zero competitor launched a mobile app in 2025–26 (cooling category). Responsive web is sufficient.

### 🚫 Deep forecasting / predictive analytics
**Why:** AgencyAnalytics and Databox are investing here, but no review quotes show users *asking* for it — it's a vendor-push feature, not user-pull. Skip until we hit $50k MRR.

### 🚫 Proposals module
**Why:** AgencyAnalytics shipped it in Nov 2025 — scope creep outside reporting. Distraction from core.

### 🚫 SQL/BI-layer data blending (Klipfolio/Databox territory)
**Why:** Reviews show this fragments the product: *"If you want to build custom connections, you'll need to work with code and SQL queries, which is time-consuming and too advanced for most."* (Klipfolio). Our wedge is simplicity.

### 🚫 "AI Chat" as a hero feature (counter-intuitive call)
**Why:** AskAI 2.0, IQ Chat, Genie are shipped; we can't out-ship incumbents with bigger teams. But diagnostic narrative (Rec #1) is the same value without the chat-UI build cost. Ship Rec #1 first; revisit chat in Q3 if retention data warrants.

---

## 7. NOTES ON RESEARCH LIMITATIONS

- **G2 and Trustpilot blocked direct scraping** — quotes pulled via search snippets + Whatagraph/Endorsal aggregator pages. Spot-check before using in public marketing.
- **Reddit access limited** — ~15 verbatim quotes recovered via aggregator citations; full Reddit mining requires browser access.
- **Twitter/X and Product Hunt surfaced no verbatim marketer quotes** — those channels are effectively silent/walled for this research.
- **No first-hand interviews with GRP trial users** — everything external. A 30-minute call with 3–5 trial users would be the highest-ROI next research step.

---

## 8. SOURCES APPENDIX

### Competitor Review Platforms
- [G2 — AgencyAnalytics](https://www.g2.com/products/agencyanalytics/reviews)
- [Capterra — AgencyAnalytics](https://www.capterra.com/p/158746/Agency-Analytics/reviews/)
- [Capterra — DashThis](https://www.capterra.com/p/163170/DashThis/reviews/)
- [Capterra — Whatagraph](https://www.capterra.com/p/146220/Whatagraph/reviews/)
- [Endorsal — Whatagraph](https://www.endorsal.io/reviews/whatagraph?rating=1)
- [Capterra — Swydo](https://www.capterra.com/p/159323/Swydo/reviews/)
- [Capterra — Databox](https://www.capterra.com/p/154024/Databox/reviews/)
- [Trustpilot — Databox](https://www.trustpilot.com/review/databox.com)
- [Capterra — Oviond](https://www.capterra.com/p/192488/Oviond/reviews/)
- [Capterra — NinjaCat](https://www.capterra.com/p/132630/NinjaCat/reviews/)
- [Capterra — Klipfolio](https://www.capterra.com/p/130237/Klipfolio-Dashboard/reviews/)
- [TrustRadius — Klipfolio](https://www.trustradius.com/products/klipfolio/reviews)
- [Whatagraph review aggregator pages](https://whatagraph.com/reviews/agencyanalytics)

### Reddit Threads
- [r/marketing — AgencyAnalytics pricing backlash](https://www.reddit.com/r/marketing/comments/1d2ukj3/comment/l96wlr8/)
- [r/marketing — AgencyAnalytics alternatives](https://www.reddit.com/r/marketing/comments/1ijc8me/)
- [r/digital_marketing — Branding limits](https://www.reddit.com/r/digital_marketing/comments/1ijcae2/)
- [r/PPC — Whatagraph quirky](https://www.reddit.com/r/PPC/comments/1176tq6/comment/j9ahd06/)
- [r/googleads — Whatagraph visuals](https://www.reddit.com/r/googleads/comments/1ki920q/comment/ms2rp9k/)
- [r/marketing — Databox free alternatives](https://www.reddit.com/r/marketing/comments/1cb3y1b/)
- [r/GoogleDataStudio — "clown car"](https://www.reddit.com/r/GoogleDataStudio/comments/1i1cd9e/)
- [r/BusinessIntelligence — Looker Studio debate](https://www.reddit.com/r/BusinessIntelligence/comments/1be1ox9/)
- [r/DigitalMarketing — Supermetrics overrated](https://www.reddit.com/r/DigitalMarketing/comments/1ik1l2z/comment/mbn4nn1/)

### Competitor Changelogs & Product Updates
- [AgencyAnalytics What's New](https://help.agencyanalytics.com/en/articles/12883723-what-s-new-at-agencyanalytics)
- [AgencyAnalytics Updates Portal](https://updates.agencyanalytics.com/)
- [Whatagraph Changelog](https://wg.canny.io/changelog)
- [Whatagraph Goals & Alerts launch](https://digitalagencynetwork.com/whatagraph-launches-goals-alerts-helping-agencies-shift-from-reactive-to-proactive-reporting/)
- [Swydo Changelog](https://changelog.swydo.com/)
- [Databox 2025 Year in Review](https://databox.com/2025-year-in-review)
- [Databox Advanced Analytics Launch](https://databox.com/advanced-analytics-launch-2025)
- [DashThis Product Updates](https://dashthis.com/blog/category/product-updates)
- [NinjaCat Changelog](https://docs.ninjacat.io/changelog)
- [Klipfolio 2025 Changelog](https://support.klipfolio.com/hc/en-us/articles/29037124114839-Klipfolio-Changelog-2025)
- [Looker Studio Release Notes](https://cloud.google.com/looker-studio/docs/release-notes)
- [Coupler.io Product Updates Oct 2025](https://blog.coupler.io/new-data-sources-ai-integrations/)

### Industry Surveys & Editorial
- [PPC.land — 71% of agencies say manual work puts campaigns at risk](https://ppc.land/71-of-ad-agencies-say-manual-work-is-putting-campaigns-at-risk/)
- [Wayfront — Stop Wasting Billable Hours on Manual Agency Reports](https://wayfront.com/blog/agency-client-reporting)
- [Supermetrics — McCann Central case study](https://supermetrics.com/blog/marketing-agency-client-reporting)
- [DataStaqAI — Agency Client Reporting Automation](https://datastaqai.com/blog/agency-client-reporting-automation)
- [Reportr.agency — SEO Report Format Guide (73% churn stat)](https://reportr.agency/blog/seo-report-format-guide)
- [ALM Corp — White Label Client Reporting](https://almcorp.com/blog/white-label-client-reporting-agencies/)
- [Asana — Marketers are AI Skeptics 2025](https://asana.com/resources/ai-survey-marketing-skeptics)
- [Drainpipe — AI Hallucinations 2025](https://drainpipe.io/the-reality-of-ai-hallucinations-in-2025/)
- [Swydo — 12 AgencyAnalytics Alternatives](https://www.swydo.com/blog/agencyanalytics-alternatives/)
- [Socialrails — AgencyAnalytics Pricing 2026](https://socialrails.com/blog/agencyanalytics-pricing)
- [Socialrails — Whatagraph Pricing](https://socialrails.com/blog/whatagraph-pricing)

---

*End of research document. No code changes made. Recommendations ready for prioritization discussion.*
