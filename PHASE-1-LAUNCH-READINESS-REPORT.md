# Phase 1 Launch Readiness Report — GoReportPilot

**Audit date:** 2026-04-28
**Audited by:** Claude (Opus, full-effort marketing + technical audit)
**Inputs:** CLAUDE.md, COMPLETE-PROJECT-REPORT.md, PROJECT-HANDOVER-APRIL-22-2026.md, HANDOVER-APRIL-11-2026.md, REMAINING-FEATURES.md, ADMIN-DASHBOARD-BLUEPRINT.md, PRICING-STRATEGY-2026.md, full git log (last 60 days, ~90 commits), live frontend code, live `/pricing` HTTP response, DNS records.

> **Note:** No `PROMPT-*.md` files exist in the project root. The user's spec referenced them but they aren't filed in the repo. Git log + handover docs cover the same ground.

---

## A. Executive Summary — Top 5 Launch Blockers (ranked by impact)

| # | Blocker | Severity | Root cause | Owner |
|---|---|---|---|---|
| **1** | **`/pricing` route is a "Coming soon" stub on production** | 🔴 Critical | `frontend/src/app/pricing/page.tsx` returns one-line placeholder. Nav links + footer point at it. Verified live: `curl https://goreportpilot.com/pricing` returns "Coming soon". | Claude (copy + page) |
| **2** | **Landing page advertises "6 visual templates" for Pro, but code ships only 3** | 🔴 Critical | `backend/services/plans.py` lines 58, 78 set `visual_templates: ["modern_clean", "dark_executive", "colorful_agency"]` for Pro/Agency. The other 3 templates exist as files (bold_geometric.pptx, minimal_elegant.pptx, gradient_modern.pptx) but aren't enabled. Either (a) enable them in plans.py, or (b) change landing page to "3 visual templates". | Saurabh decides A vs B; Claude implements |
| **3** | **No `og:image` set anywhere** — every social share will render a blank preview | 🟠 High | `frontend/src/app/layout.tsx` declares Open Graph metadata but no `image` field. Twitter card declared `summary_large_image` but no image to render. | Saurabh creates 1200×630 image; Claude wires it into metadata |
| **4** | **PPTX polish items still failing** — sparklines invisible, agency logo overflow, zero-conversion legend artifact, traffic label inconsistency between chart and narrative | 🟠 High | Each has a specific root cause traced in Section F. Surgical fixes (1-3 lines each). | Claude (this audit applies the fixes) |
| **5** | **Meta App Review + Google OAuth verification both pending** — Meta Ads + GA4 OAuth currently work for Saurabh's own account but will block any new user from connecting | 🟠 High | Awaiting external review (Meta ~14 days post-submission, Google ~2-6 weeks). Cannot be fixed in code — Saurabh follows up. | Saurabh |

**Other blockers worth knowing about** (lower priority, listed in section F):
- No `/features` dedicated route (SEO + nav opportunity loss)
- No customer testimonials / social proof anywhere on landing page
- No real product screenshots in `/public` — only `favicon.svg`. Hero is a CSS mockup, not real UI.
- "Multi-language reports" sold as Pro+ on landing but is actually all-tiers in the code (no plan check anywhere). Intentional or oversight?
- Email-delivery limits (Starter 50/mo, Pro 200/mo) advertised in PRICING-STRATEGY-2026.md but **not enforced in code**. If a Starter user blasts 500 scheduled reports, nothing stops them.
- Forgot-password and self-service account-deletion flows: routes exist (`/forgot-password`, `/reset-password`) but completeness needs verification.

---

## B. Marketing Surface — Feature-by-Feature Audit

Grouped by category. **"On Landing"** = the feature is mentioned by name on the public landing page hero/features/comparison/FAQ. **"On Pricing"** = the feature is mentioned in the per-plan feature list on the pricing toggle. **"On /features"** = a dedicated /features page mentions it (none exist; this column is "—"). **Gap action** = what to do.

### B.1 Data integrations

| Feature | Shipped | On Landing | On Pricing | On /features | Gap action |
|---|---|---|---|---|---|
| GA4 OAuth + 6-call data pull | ✅ | ✅ ("Google Analytics 4") | ✅ all tiers | — | None |
| Meta Ads OAuth + Marketing API v21 | ✅ (pending Meta review) | ✅ ("Meta Ads") | ✅ all tiers | — | None |
| Google Ads OAuth + MCC | ✅ (pending Google verification) | ✅ ("Google Ads") | ✅ all tiers | — | None |
| Search Console OAuth + Search API | ✅ | ✅ ("Search Console") | ✅ all tiers | — | None |
| CSV upload (5 templates, 35-brand capitalization, K/M/B suffixes, encoding/delimiter detection) | ✅ | ✅ "Any Data Source via CSV" feature card | ✅ Starter feature line "CSV upload for any other data source" | — | **Marketing under-sells this.** Card mentions LinkedIn/TikTok/Shopify/HubSpot but doesn't mention the production-grade parser (35-brand capitalization, auto-detection). Add 1-line specifics. |

### B.2 Report generation

| Feature | Shipped | On Landing | On Pricing | On /features | Gap action |
|---|---|---|---|---|---|
| AI narrative — GPT-4.1 | ✅ | ✅ ("AI Writes the Commentary") | ✅ tier-gated by tones | — | Card says "GPT-4.1" nowhere. Worth keeping vague. ✅ no change. |
| AI tones — 4 (professional/conversational/executive/data_heavy) | ✅ | ⚠️ Mentioned in feature card but ambiguous | ✅ Starter 1 tone, Pro/Agency 4 tones | — | None |
| 13-language narrative (Spanish, Portuguese, French, German, Hindi, Arabic, Japanese, Italian, Korean, Chinese Simplified, Dutch, Turkish, English) | ✅ all tiers | ✅ "Reports in 13 Languages" feature card | ⚠️ Listed as Pro+ feature on Pro plan ("Multi-language reports (13 languages)") but **the code does NOT gate this by plan.** | — | **Marketing-vs-code mismatch.** Either (a) add a plan gate in code (`ai_narrative.py` checks `plan_features.languages`), or (b) move to Starter feature line. **Recommend (b)** — multi-language is a $0 marginal cost feature; gating it adds friction without saving anything. |
| 6 visual PPTX templates (modern_clean, dark_executive, colorful_agency, bold_geometric, minimal_elegant, gradient_modern) | ⚠️ **3 of 6 live; 3 files exist but disabled** | ❌ Landing #features card says "Six visual templates" | ❌ Pro plan line says "6 visual templates" — **wrong**, plans.py gives Pro only 3 | — | **Critical.** Either enable the other 3 in plans.py (after QA on those PPTX files) or change all marketing to "3 templates". See Sec C+D for diffs both ways. |
| 19 chart types | ✅ | ⚠️ Vague reference ("Charts That Tell the Story") | ❌ no exact count anywhere | — | Could mention "19 chart types" specifically — quantification is more credible. |
| AI-titled charts ("Sessions surged 23% as organic recovered") | ✅ | ✅ Feature card mentions this | ❌ Not on pricing | — | None |
| Sparklines on KPI cards | ⚠️ Code present but **rendering broken** (Section F item 1) | ✅ Mentioned in feature card | — | — | Fix code (Phase 4 of this audit). |
| Color-blind-safe palette | ✅ | ✅ Feature card mentions it | — | — | None |
| White-label (agency logo, brand color, client logo, custom footer) | ✅ Pro+ | ✅ "Your Brand, Not Ours" feature card | ✅ Pro feature line "White-label branding — no GoReportPilot badge" | — | None |
| "Powered by GoReportPilot" badge (visible on Starter, removed on Pro+) | ✅ | ⚠️ Indirectly implied | ✅ Starter feature line | — | None |
| PPTX export (Pro+ only — Starter PDF only) | ✅ Pro+ gated (`backend/routers/reports.py` returns 403 for Starter) | ✅ "Present in PowerPoint" feature card — **but doesn't mention PPTX is Pro+** | ✅ Pricing differentiates: Starter "PDF export", Pro "PPTX + PDF export" | — | **Landing feature card is misleading.** Reads as if PPTX is universal. Add 1 line: "Available on Pro+." |
| PDF export (LibreOffice + ReportLab fallback, all Unicode scripts) | ✅ all tiers | ⚠️ Implicit (mentioned alongside PPTX) | ✅ Starter "PDF export + email delivery" | — | None |
| Scheduled reports (weekly/biweekly/monthly, timezone-aware, auto-email) | ✅ Pro+ | ✅ "Reports That Send Themselves" feature card — doesn't say Pro+ | ✅ Pro feature line | — | Card should add "Available on Pro+." |
| Per-section regenerate | ✅ all tiers | ❌ Not mentioned anywhere | ❌ Not on pricing | — | Worth adding. Differentiator vs static-deck competitors. |
| Editable PPTX (vs flat PDF) | ✅ Pro+ | ⚠️ Implicit ("editable PPTX deck") | ⚠️ Implicit | — | This is a major differentiator vs AgencyAnalytics/Whatagraph (PDF-only). Make explicit. |
| Email delivery (Resend) | ✅ all tiers | ⚠️ Implicit | ✅ Starter "PDF export + email delivery" | — | None |
| Email-delivery rate limits (Starter 50/mo, Pro 200/mo, Agency unlimited) | ❌ **Not enforced in code** (claim in PRICING-STRATEGY-2026.md only) | ❌ Not advertised | ❌ Not on pricing | — | Either (a) implement in code, or (b) drop the limits from marketing. **Recommend dropping** — agencies sending more than 200 client reports/month are an edge case that becomes a sales conversation, not a code limit. |

### B.3 Plan-tier features

| Feature | Shipped | On Landing | On Pricing | On /features | Gap action |
|---|---|---|---|---|---|
| 14-day trial, no credit card | ✅ | ✅ Mentioned 5+ times | ✅ "All plans include a 14-day free trial" | — | None |
| Trial gives Pro-level features (full PPTX, 4 tones, 3 templates, white-label, scheduling) | ✅ per `plans.py` trial config | ❌ Not advertised | ❌ Not on pricing | — | **Worth adding to pricing footer:** "Trial unlocks Pro-tier features for 14 days." |
| Trial 5-report limit | ⚠️ `trial_reports_limit` field exists in subscriptions table; enforcement location unclear | ❌ Not advertised | ❌ Not on pricing | — | If enforced: advertise it ("5 reports during trial"). If not: implement or drop. |
| Trial 10-client limit | ✅ per `plans.py` trial config | ❌ Not advertised | ❌ Not on pricing | — | Worth a footer line. Generous trial is a selling point. |
| Trial watermark on exports ("Powered by") | ✅ | ❌ Not on landing | ❌ Not on pricing | — | None — implicit in "Pro+ removes badge" copy. |
| Plan client limits (5 / 15 / unlimited) | ✅ enforced in `plan_enforcement.py` | ✅ "Up to 5 / 15 / unlimited" on each plan | ✅ Each plan card | — | None |
| Goal limits per client (1 / 3 / unlimited) | ✅ enforced in `plan_enforcement.py` | ❌ Not on landing | ❌ Not on pricing | — | **Goals & alerts feature isn't shipped yet (per HANDOVER-APRIL-22). Don't advertise.** |

### B.4 Account features

| Feature | Shipped | On Landing | On Pricing | On /features | Gap action |
|---|---|---|---|---|---|
| Email/password signup | ✅ | ✅ CTA flow | ❌ Not on pricing | — | None |
| Email confirmation enforcement | ⚠️ **Partial** — Supabase sends confirm email but login does NOT block unconfirmed users (known issue per COMPLETE-PROJECT-REPORT.md) | ❌ Not advertised | ❌ Not on pricing | — | **Saurabh: enable in Supabase Auth config.** Code change not needed. |
| Forgot-password flow | ⚠️ Routes exist (`/forgot-password`, `/reset-password`) — needs verification it's wired | ❌ Not advertised | ❌ Not on pricing | — | Verify by manually triggering reset on a test account. |
| Self-service account deletion | ⚠️ Admin can delete; user-initiated dashboard delete not yet built | ❌ Not advertised | ❌ Not on pricing | — | Add to dashboard settings → "Danger Zone" section. Required for GDPR/Razorpay compliance. |
| Per-agency branding settings (logo, brand color, name, email, website, footer text) | ✅ Pro+ | ✅ Implicit in white-label card | ✅ Pro feature line | — | None |
| Per-client AI tone, language, report config | ✅ all tiers | ❌ Not on landing | ❌ Not on pricing | — | Worth adding. "Per-client AI tone + language" is a real Pro differentiator. |

### B.5 Billing

| Feature | Shipped | On Landing | On Pricing | On /features | Gap action |
|---|---|---|---|---|---|
| Razorpay live mode | ✅ (live keys per CLAUDE.md) | ❌ Not on landing | ❌ Not on pricing | — | None — payment provider isn't a selling point. |
| Dual currency INR/USD with auto-detection | ✅ (`detect-currency.ts` checks `Asia/Kolkata` timezone or Hindi navigator language) | ✅ "Prices shown in [INR/USD]. International cards accepted." | ✅ Toggle visible | — | None |
| 12 plan IDs (3 tiers × 2 cycles × 2 currencies) | ✅ stored in env vars | — | — | — | None |
| Annual billing 20% off | ✅ | ✅ "Save 20%" badge in pricing toggle | ✅ Toggle | — | None |
| Cancellation flow | ✅ (cancel_at_period_end pattern) | ✅ "Cancel anytime" reassurance | ✅ Same | — | None |

### B.6 Admin features

(All admin features are internal — not on marketing surface, correct as-is.)

| Feature | Shipped | Notes |
|---|---|---|
| `/dashboard/admin` (8 stat cards + activity feed) | ✅ | Internal — Saurabh only |
| `/dashboard/admin/analytics` | ✅ | Internal |
| `/dashboard/admin/users` | ⚠️ Partial | Internal |
| User export (GDPR JSON) | ✅ | Internal |

### B.7 Recently shipped (last 60 days, per git log)

| Feature | Shipped | On Landing | Gap action |
|---|---|---|---|
| Comments on shared reports (Phase 5A backend + 5B frontend) | ✅ commits c8c56d5 + 2a670b9 | ❌ Not on landing | **Big differentiator nobody knows about.** Add a feature card: "Clients comment directly on shared reports — no login required." Also add to pricing (which tier gets it?). Currently no plan gate visible. |
| Comment badges on All Reports list (granular + view analytics fix) | ✅ commits 0009eff, 090d473 | ❌ | Same — bundle with the comments card. |
| Live unread-comment badges across tabs (UnreadCommentsProvider) | ✅ commit c79c406 | ❌ | Same — bundle. |
| Business context UX overhaul (with AI-assist + quality indicator) | ✅ commit edff2d4 | ❌ | Worth a feature card or one-line on pricing: "Per-client business context shapes AI narrative." |
| Trial limit override mechanism (Phase 6B) | ✅ commit 93b4e72 | ❌ | Internal mechanism, not a customer-facing feature. Skip. |
| Goals & alerts (Phase 6A backend, 6B frontend) | ✅ commits 06e0773, 93b4e72 | ❌ | **Don't advertise yet** — feature inventory agent flagged this as "design complete, build pending Phase 2.1" but git log shows it's actually shipped. Verify it works end-to-end before marketing. If working: add a "Goals & Alerts" feature card. If broken/half-built: leave off. |
| Diagnostic narrative with top movers attribution | ✅ commit c50c865 | ❌ | This is a meaningful AI improvement. Worth one line in the "AI Writes the Commentary" card: "...explains the **why**, not just the **what** — top metric movers and their attribution." |
| Custom cover page editor (Phase 3) | ✅ commit b0345fb (cover editor) + 11 follow-up fixes | ❌ Not advertised | Major Pro+ feature. Add a feature card: "Custom cover page per client — your design, their brand." |
| Connection health monitor (Phase 2) | ✅ commit ca38ba2 + bug fixes | ❌ Not on landing | Worth a feature card: "Auto-detect broken integrations before they break your reports." Also surfaces in admin dashboard. |
| Multi-language translation (slide titles, KPI labels, chart titles, footer, N/A indicators) | ✅ commit d9578db | ✅ ("13 languages" feature card) | Card should be more specific: "Translates **slide titles, KPI labels, chart axes, footer** — not just narrative." Currently sounds like AI-only translation. |

---

## C. Proposed Landing Page Copy Diffs

> **All diffs target `frontend/src/app/page.tsx` and components in `frontend/src/components/landing/`. Saurabh approves before applying.**

### C.1 Hero — sharper differentiator

The current headline is good but generic. The actual differentiator (multi-paragraph AI narrative + editable PPTX + client-count pricing) is buried in feature cards. Hoist the strongest specific into the subheadline.

**Before** (current hero copy, verbatim from `frontend/src/app/page.tsx` hero section):
```
Branded client reports, written by AI.
GoReportPilot connects GA4, Meta Ads, Google Ads, and Search Console, writes the narrative, and delivers a white-label PPTX + PDF — in under 5 minutes.
Free 14 days · No credit card · From $19/mo · Cancel anytime
```

**After** (proposed):
```
Branded client reports, written by AI.
Multi-paragraph narrative explaining what changed and why — not one-line summaries. White-label PPTX you can edit, plus PDF. Connects GA4, Meta Ads, Google Ads, Search Console + CSVs. From $19/mo, 14 days free.
14 days free · No credit card · From $19/mo · Cancel anytime
```

**Why:** "Multi-paragraph" specifically calls out the differentiator vs AgencyAnalytics/Whatagraph (which give 1-line summaries). "PPTX you can edit" is the other big differentiator (most tools give flat PDFs). "Plus CSVs" reminds prospects this isn't only Google/Meta-shaped agencies.

---

### C.2 Comparison table — add Whatagraph + Looker Studio, fix the "6 templates" claim if not enabling them

**Before** (current `#comparison` table, 3 columns):
```
| Feature                 | AgencyAnalytics | DashThis    | GoReportPilot |
| Price (15 clients)      | $179–239/mo     | $139/mo     | $39/mo ✓      |
| AI Narrative Insights   | Add-on only     | Add-on ($19/mo) | Included ✓ |
| PowerPoint Export       | ✗               | ✗           | Yes ✓         |
| Flat Pricing            | No (per-client) | No (per-dashboard) | Yes ✓  |
| White-Label             | Higher tiers    | Yes         | Pro+ ✓        |
| Multi-language Reports  | ✗               | ✗           | 13 languages ✓ |
| CSV Upload (Any Source) | ✗               | ✗           | Yes ✓         |
```

**After** (proposed — adds Whatagraph + Looker Studio columns, replaces template count with editable PPTX claim):
```
| Feature                  | AgencyAnalytics | Whatagraph    | Looker Studio | GoReportPilot |
| Price (15 clients)       | $179–239/mo     | $249–999/mo   | Free (DIY)    | $39/mo ✓      |
| AI multi-para narrative  | Add-on only     | Short summaries | None        | Included ✓    |
| Editable PPTX export     | ✗ (PDF only)    | ✗ (PDF only)  | ✗             | Yes ✓         |
| Pricing model            | Per client      | Per data src  | Free / setup  | Per client (flat) ✓ |
| White-label              | Higher tiers    | Yes           | DIY only      | Pro+ ✓        |
| 13-language reports      | ✗               | ✗             | DIY templates | Yes ✓         |
| CSV upload (any source)  | ✗               | Limited       | DIY           | Yes ✓         |
| Time to first report     | 30+ min setup   | 1+ hour       | Days (DIY)    | <5 min ✓      |
```

**Why:**
- Whatagraph is named in the brand voice doc as a primary competitor. It's the most comparable tool (AI summaries, agencies). Missing it from the comparison table is a credibility gap.
- Looker Studio is the elephant — every prospect has tried it. Comparing on cost-vs-time-to-set-up beats comparing on feature count.
- "Editable PPTX" is the single biggest hard-feature differentiator. Prospects can verify by trying.
- Drop "PowerPoint Export" wording (vague) for "Editable PPTX export" (specific).

---

### C.3 Pricing card #features section — fix the visual templates count

**Recommended path:** Enable all 6 templates in `plans.py` (with QA on bold_geometric.pptx, minimal_elegant.pptx, gradient_modern.pptx) and keep the "6 visual templates" claim. **If those 3 files have known issues**, drop the marketing claim to "3" instead.

**Diff for path A (enable 6, keep marketing):** code-level change in `backend/services/plans.py`:
```diff
  "pro": {
    ...
    "features": {
      ...
-     "visual_templates": ["modern_clean", "dark_executive", "colorful_agency"],
+     "visual_templates": ["modern_clean", "dark_executive", "colorful_agency",
+                          "bold_geometric", "minimal_elegant", "gradient_modern"],
    }
  },
  "agency": {
    ...
    "features": {
      ...
-     "visual_templates": ["modern_clean", "dark_executive", "colorful_agency"],
+     "visual_templates": [...same 6...],
    }
  },
  "trial": {
    ...
    "features": {
      ...
-     "visual_templates": ["modern_clean", "dark_executive", "colorful_agency"],
+     "visual_templates": [...same 6...],  // trial gets all
    }
  }
```

**Diff for path B (drop to 3, fix marketing):** 2 changes to landing components.

In the #features section feature card "Present in PowerPoint":
```diff
- Get a branded, editable PPTX deck your clients can open in PowerPoint — plus a PDF for quick sharing. Six visual templates to match any brand.
+ Get a branded, editable PPTX deck your clients can open in PowerPoint — plus a PDF for quick sharing. Three visual templates: clean, dark executive, and colorful agency.
```

In the Pro plan feature line on the pricing toggle:
```diff
- 6 visual templates
+ 3 visual templates (clean / dark executive / colorful agency)
```

**My recommendation:** Path A. Three more PPTX templates is a small QA task (open each, generate one report, verify it doesn't crash). The marketing claim sets a higher visual-variety bar that's defensible. Saurabh decides.

---

### C.4 Features section — add 4 missing feature cards

The git log shows shipped features that don't appear on the landing page. Add these 4 cards to the existing 9:

**New card — "Clients Comment on Reports":**
```
[icon: MessageSquare]
Clients Comment on Reports
Your clients can leave comments directly on shared report links — no login required. You see unread badges across the dashboard, get notified, reply, and resolve. Reports become a conversation, not a one-way deliverable.
```

**New card — "Custom Cover per Client":**
```
[icon: Image]
Custom Cover per Client
Design a unique cover page for each client. Your headline, your subtitle, hero image, your colors. Live preview before you generate. Available on Pro and Agency.
```

**New card — "Connection Health Monitor":**
```
[icon: Activity]
Connection Health Monitor
We probe your data connections weekly. Broken integration? Expiring token? You'll know before your next report runs — not after the client wonders why their numbers are missing.
```

**New card — "Per-Client Business Context":**
```
[icon: BookOpen]
Per-Client Business Context
Tell GoReportPilot what each client cares about: their goals, their seasonality, their key channels. The AI weaves that context into every narrative — so the report sounds like you wrote it for them, because it kind of did.
```

These 4 cards put the landing page at 13 feature cards total. That's a lot. Recommend deleting one of the weaker existing cards — "Set Up in 5 Minutes" overlaps with "How It Works" section and is the weakest unique claim.

---

### C.5 Add a small "Trial includes Pro-tier features" footer to the pricing toggle

**Before** (`frontend/src/components/landing/PricingToggle.tsx`, billing-note):
```
All plans include a 14-day free trial. No credit card required.
```

**After:**
```
All plans include a 14-day free trial. No credit card. Trial unlocks Pro-tier features (PPTX, all 4 tones, white-label, scheduling) so you can evaluate the full product before picking a plan.
```

**Why:** Removes the "what does the trial actually let me do?" question. Conversion-positive.

---

## D. Proposed Pricing Page (`/pricing`) — needs to be built from scratch

The current `/pricing` route is a one-line stub. Saurabh nav links + footer point at it. Anyone clicking "Pricing" in nav gets a broken-feeling page. **This is a launch blocker.**

### D.1 Recommended structure

The dedicated `/pricing` page should be **more detail-dense** than the landing page's `#pricing` section, not a duplicate.

**Sections (in order):**

1. **Hero strip:** "Pick a plan. Switch anytime. 14 days free, no credit card."
2. **Pricing toggle** (reuse the existing `<PricingToggle />` component from landing — same monthly/annual + currency display)
3. **Full feature comparison matrix** — every plan's every feature, side-by-side. The pricing toggle on landing only shows the "headline" features per plan; the dedicated page has space for the long list. Sample shape:

```
| Feature                                | Starter | Pro | Agency |
| Clients                                | 5       | 15  | Unlimited |
| Reports per month                      | Unlim.  | Unlim. | Unlim. |
| Data integrations (GA4, Meta, GAds, SC) | ✓     | ✓   | ✓ |
| CSV upload (any source)                | ✓       | ✓   | ✓ |
| AI narrative tones                     | 1 (Professional) | 4 | 4 |
| Languages (narrative + chart labels)   | 13      | 13  | 13 |
| PDF export                             | ✓       | ✓   | ✓ |
| PPTX export (editable)                 | —       | ✓   | ✓ |
| Visual templates                       | 1 (Modern Clean) | 6 | 6 |
| Custom cover per client                | —       | ✓   | ✓ |
| White-label branding                   | —       | ✓   | ✓ |
| "Powered by GoReportPilot" badge       | Shown   | —   | — |
| Scheduled reports (auto-send)          | —       | ✓   | ✓ |
| Email delivery                         | ✓       | ✓   | ✓ |
| Per-section regenerate                 | ✓       | ✓   | ✓ |
| Per-client AI tone + language          | ✓       | ✓   | ✓ |
| Per-client business context            | ✓       | ✓   | ✓ |
| Goals & alerts                         | 1/client | 3/client | Unlimited |
| Connection health monitoring           | ✓       | ✓   | ✓ |
| Comments on shared reports             | ✓       | ✓   | ✓ |
| Shared report links (password + expiry)| ✓       | ✓   | ✓ |
| API access                             | —       | —   | ✓ (planned) |
| Priority support                       | —       | —   | ✓ |
```

(Update `1 (Modern Clean)` and `6` once the Section C.3 plans.py path is decided. If 3-template path: change Pro/Agency to "3".)

4. **FAQ specific to pricing** (4-5 questions): "What happens at the end of the trial?", "Can I switch plans?", "How does the client limit work?", "Do scheduled reports count against any limit?", "What if I exceed the client limit on Starter?"
5. **"Still deciding?" CTA strip** — primary "Start free trial" button + secondary "Book a demo" link (or contact form link).

### D.2 Code change required

Replace `frontend/src/app/pricing/page.tsx` (currently a one-line stub) with a full page using the existing `<PricingToggle />` component plus the matrix above. New components needed: `PricingMatrix.tsx` (the comparison table), `PricingFAQ.tsx` (different from landing FAQ — pricing-specific). Estimate: ~250 lines of TSX, half a day.

**Also:** add page-level metadata to the new `/pricing/page.tsx`:
```tsx
export const metadata: Metadata = {
  title: "Pricing — GoReportPilot",
  description: "From $19/mo. 14-day free trial, no credit card. Flat pricing by client count, not by report volume — so weekly-cadence agencies don't get punished. Compare Starter, Pro, and Agency plans.",
  alternates: { canonical: "/pricing" },
};
```

(I haven't drafted full TSX here because the user said "do NOT edit files yet" for marketing copy. I'll generate the file when Saurabh approves.)

---

## E. Missing Pages or Sections — content drafts

### E.1 `/features` route — does NOT exist, recommend creating it

A dedicated `/features` page is high-leverage for SEO ("ga4 reporting tool", "automated marketing reports", "white-label client reports"). Each feature gets its own H2 + 200-400 words + a screenshot. This is what AgencyAnalytics and Whatagraph have — it ranks.

**Recommended structure** (12 sections, one per major feature, ~2,500 words total):

1. **The 5-minute report flow** — hero section, video or animated demo
2. **AI multi-paragraph narrative (4 tones, 13 languages)** — show side-by-side: input data → output narrative
3. **Editable PPTX export** — explain the differentiator vs PDF-only competitors
4. **6 visual templates** — gallery with screenshots of each (or 3 if we go path B in C.3)
5. **White-label branding** — show before/after with agency logo, brand color, custom footer
6. **Custom cover per client** — show 4-5 cover designs side-by-side
7. **Scheduled reports** — explain weekly/biweekly/monthly + timezone-aware delivery
8. **Comments on shared reports** — explain the no-login client comment flow + unread badges
9. **Connection health monitor** — explain the weekly probes + broken-connection alerts
10. **Per-client business context** — show how AI uses goals_context to shape narrative
11. **All-source CSV upload** — show the 5 templates (LinkedIn, TikTok, Mailchimp, generic) + brand-name capitalization
12. **13-language support** — show same report rendered in English, Hindi, Spanish, Japanese

**Estimated effort:** 1-2 days to write copy + capture 12 product screenshots. Saurabh writes copy (or AI-drafts); Saurabh captures screenshots.

### E.2 Open Graph image — does NOT exist, recommend creating

Currently no `og:image` is set, so social shares (Twitter, LinkedIn, Slack previews, WhatsApp) render with no preview image. This is a low-effort high-leverage fix.

**Recommended specs:**
- 1200×630px PNG, under 1MB
- Shows: GoReportPilot logo + tagline ("Branded client reports, written by AI") + a small product screenshot (a PPTX cover or KPI page)
- Save to `frontend/public/og-image.png`

**Code wiring** in `frontend/src/app/layout.tsx`:
```diff
  openGraph: {
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    type: "website",
    url: "https://goreportpilot.com",
    siteName: "GoReportPilot",
+   images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "GoReportPilot — AI client reporting for marketing agencies" }],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
+   images: ["/og-image.png"],
  },
```

### E.3 Testimonials / social proof section — currently zero on landing

Can't be drafted until Saurabh has actual customers. **Do NOT use placeholder/fake testimonials.** Recommend:
- After 5 paying customers, ask each for a 1-2 sentence quote + permission to use their name + agency
- After 10, capture customer logos
- Until then, leave the section out (no social proof beats fake social proof)

**Interim recommendation:** add a "Built for agency founders, by an agency founder" section with Saurabh's photo + 50-word origin story. Authenticity > nothing.

### E.4 Real product screenshots in `/public`

Currently `/public` only has `favicon.svg`. The hero is a CSS mockup. Replace with:
- `og-image.png` (Section E.2)
- `hero-product.png` — a real screenshot of the report dashboard or a generated PPTX cover
- `screenshot-pptx-cover.png`, `screenshot-pptx-kpi.png`, `screenshot-pptx-narrative.png` (3 PPTX page screenshots)
- `screenshot-dashboard.png`, `screenshot-pricing.png`

**See Section H** — this requires generating real screenshots, which is a Saurabh-action task (needs running app + login).

---

## F. Product Technical Readiness

| # | Item | Status | Action required | Owner |
|---|---|---|---|---|
| 1 | **Meta App Review (ads_read permission)** | ⚠️ Pending | Saurabh checks developers.facebook.com app dashboard. If pending >14 days, draft + send follow-up via the support form referencing the original submission ID. If approved, end-to-end test: signup → connect Meta Ads → generate report → verify Meta data flows. | **Saurabh** |
| 2 | **Google OAuth verification (production scopes)** | ⚠️ Pending | Saurabh checks Google Cloud Console > APIs & Services > OAuth consent screen for `report-pilot-490812` project. Verification typically 2-6 weeks. If approved: end-to-end test with fresh signup. | **Saurabh** |
| 3 | **Razorpay live mode end-to-end** | ⚠️ Untested | Saurabh runs a real Pro subscription ($39 USD) on a fresh test account → verify webhook fires (`payment.captured`) → verify `subscriptions.plan` written correctly → verify Resend sends receipt email → verify cancellation flow → verify `cancel_at_period_end` propagates and the subscription actually expires at next billing cycle. | **Saurabh** |
| 4 | **PPTX polish — sparklines invisible** | ❌ Bug confirmed | Code root cause: `chart_generator.py` sparkline function doesn't set `ax.patch.set_visible(False)`, leaving an opaque axes background that occludes the line. **Fix in Phase 4 of this audit (below).** | **Claude** |
| 5 | **PPTX polish — campaign chart legend artifact when conversions=0** | ❌ Bug confirmed | Code root cause: `chart_generator.py` line ~617 always passes `label="Conversions"` to `ax2.bar()`, so legend includes the entry even when all values are zero. **Fix in Phase 4.** | **Claude** |
| 6 | **PPTX polish — agency logo overflow** | ❌ Bug confirmed | Code root cause: `_fit_image_to_box()` correctly preserves aspect ratio, but no post-fit bounds check guarantees `pic_left + fit_w` stays inside slide width. Ultra-wide logos push past right edge. **Fix in Phase 4.** | **Claude** |
| 7 | **PPTX polish — traffic label capitalization mismatch** | ❌ Bug confirmed | Code root cause: `chart_generator._clean_source_label()` works correctly for charts. But `ai_narrative.py` reads raw GA4 traffic_sources without applying the same cleaner — so chart says "Direct" while narrative says "(none)". **Fix in Phase 4.** | **Claude** |
| 8 | **Reddit OAuth completion (for WF5 Reddit listener)** | ⚠️ Blocked on Reddit policy | Saurabh paused on Reddit's Responsible Builder Policy. Document exact blocker (which question stumped him, which app reviewer rejected it, etc.) in a follow-up. | **Saurabh** |
| 9 | **Zoho Mail MX verification** | ✅ DNS correct, ⚠️ verification incomplete | DNS check confirms: MX records point at `mx.zoho.in / mx2.zoho.in / mx3.zoho.in`, TXT record `zoho-verification=zb72962368.zmverify.zoho.in` is published, SPF includes `zoho.in`. **DNS is fine.** If Zoho still says "unverified", Saurabh needs to log into Zoho admin console > Domain settings > click "Verify Now" on the domain. If it still rejects: contact Zoho support and reference the verification token (it may have rotated). | **Saurabh** |
| 10 | **Domain SSL + DNS health (`goreportpilot.com`)** | ✅ All green | Verified: HTTPS valid, HSTS enabled (`max-age=63072000`), Vercel CDN serving, `/`, `/signup`, `/pricing` all return HTTP 200. Strict-Transport-Security header present. No mixed content. /signup loads in <500ms (cached). | **No action** |
| 11 | **`/pricing` is a "Coming soon" stub** | ❌ Launch blocker | Verified live: `curl https://goreportpilot.com/pricing` returns 200 with body containing "Coming soon" and "Pro" placeholder. **Build the full pricing page** per Section D. | **Claude** (when Saurabh approves the matrix) |
| 12 | **`og:image` not set, no real product screenshots in /public** | ❌ Launch blocker | Verified: `frontend/public/` contains only `favicon.svg`. No screenshots, no OG image. **See Section E.2 + E.4** | **Saurabh creates images, Claude wires metadata** |
| 13 | **Email confirmation not enforced at login** | ⚠️ Known | Per COMPLETE-PROJECT-REPORT.md: "Users can currently sign in without confirming their email." Supabase config issue, not code. | **Saurabh** (Supabase Auth settings) |
| 14 | **Multi-language sold as Pro+, but no plan check in code** | ⚠️ Mismatch | Marketing-vs-code mismatch. Recommend dropping the gate (free feature, no marginal cost) and moving language support to Starter feature line. | **Saurabh decides; Claude implements** |
| 15 | **Email-delivery rate limits advertised, not enforced** | ⚠️ Mismatch | PRICING-STRATEGY-2026.md mentions Starter 50/mo, Pro 200/mo. Code has no enforcement. Recommend dropping the limits from marketing rather than implementing them. | **Saurabh decides** |
| 16 | **`backend/services/plans.py` ships only 3 visual templates; landing page advertises 6** | ❌ Mismatch | See Section B.2 / Section C.3 — recommend Path A (enable all 6 + QA the 3 untested files). | **Saurabh decides; Claude implements** |
| 17 | **9 pre-/dashboard public routes verified** | ✅ All present | Verified: `/`, `/contact`, `/pricing` (stub), `/privacy`, `/refund`, `/terms`, `/login`, `/signup`, `/forgot-password`, `/reset-password`, `/confirm-email`. | **No action** |

---

## G. Recommended fix order

### Tier 1 — fix this week (launch blockers)

1. **Apply Phase 4 PPTX fixes** (this audit). Sparklines, campaign chart legend, logo overflow, traffic label cleaning. Code-only, no Saurabh action. (Claude does this immediately after this report — Phase 4 in the todos.)
2. **Build the real `/pricing` page** per Section D. Saurabh approves the comparison matrix; Claude builds the TSX.
3. **Saurabh creates `og-image.png` (1200×630)** — single PNG, can be done in Figma in 30 min. Claude wires it into layout metadata.
4. **Decide on visual_templates count** (Section C.3) — Saurabh says "test the 3 unused templates first" or "drop the marketing claim to 3". Claude implements either path.
5. **Saurabh enables email confirmation enforcement** in Supabase Auth dashboard. 1 toggle.

### Tier 2 — fix this month (high-impact gaps)

6. **Apply landing page copy diffs** (Sections C.1, C.2, C.5) — sharper hero subheadline, expanded comparison table with Whatagraph + Looker Studio, clarified trial terms.
7. **Add 4 missing feature cards** (Section C.4) — comments on shared reports, custom cover, connection health, per-client business context. Drop "Set Up in 5 Minutes" card to make room.
8. **Build the `/features` page** (Section E.1) — high SEO leverage, ~2,500 words + 12 screenshots. Saurabh writes the copy or AI-drafts it (recommend the latter; reuse WF8 blog drafter pattern).
9. **Drop email-delivery rate limits from marketing** (Section F item 15) and **drop multi-language plan gating from marketing** (Section F item 14) — both are cleaner-than-implementing.
10. **Saurabh follows up on Meta App Review + Google OAuth verification** if either is past 14 days with no response.

### Tier 3 — pre-launch sanity (when first 5 customers exist)

11. **Capture testimonials** (Section E.3) — wait for real customers, then ask each for a quote.
12. **Razorpay live-mode end-to-end test** (Section F item 3). Best done with a real first customer; until then it's a manual dry run on Saurabh's own card.
13. **Resolve Reddit OAuth blocker** (Section F item 8) for WF5. Lower priority than core launch.

---

## H. Marketing screenshot pack — STATUS AND BLOCKER

**The audit spec said:** "Generate a fresh marketing screenshot pack: real PPTX page screenshots, dashboard screenshot, pricing page screenshot. Save to /mnt/user-data/outputs/marketing-screenshots/."

**Status:** ❌ **NOT GENERATED — requires Saurabh action.**

**Why I can't:**
- Generating real PPTX screenshots requires running the backend FastAPI server, logging in as `sapienbotics@gmail.com`, generating a real report against a connected GA4/Meta/Google Ads account, and screen-capturing the resulting PPTX in a viewer. The CLAUDE.md project instructions explicitly forbid me from auto-starting dev servers ("NEVER auto-start dev servers — Saurabh starts them manually").
- The dashboard screenshot requires the same — running app + Saurabh's session.
- The pricing page screenshot will be most valuable AFTER Section D's full pricing page is built (current page is "Coming soon" stub — not worth screenshotting).

**Recommended Saurabh process:**
1. Start backend + frontend locally as per CLAUDE.md.
2. Log in with `sapienbotics@gmail.com`. Pick any client with connected data.
3. Generate one Pro-tier PPTX (use the `dark_executive` template — it's the most marketing-friendly visually). Open in PowerPoint.
4. Take screenshots of: cover slide, KPI overview slide (with sparklines!), first AI-narrative slide, one chart slide (campaign performance), final summary slide. Save as `screenshot-pptx-1-cover.png` … `screenshot-pptx-5-summary.png` in `frontend/public/`.
5. Take a dashboard screenshot at `/dashboard/clients` (with 3-5 clients listed) — save as `screenshot-dashboard.png`.
6. Take the pricing page screenshot AFTER the Section D rebuild lands — save as `screenshot-pricing.png`.
7. Generate the OG image (Section E.2) in Figma — save as `og-image.png`.

**Alternative:** I can attempt to script a Playwright-based capture of the LIVE site (`https://goreportpilot.com`) using `mcp__Claude_Preview` tools — but this only captures the LIVE site, which currently has the "Coming soon" pricing stub and no signed-in dashboard. It would only give the landing page screenshot, which Saurabh already sees daily. **Not worth the effort until the pricing page rebuild is live.**

---

## What this report did NOT cover

- **Dashboard UX audit** — out of scope. The signed-in product surface is internal; this audit was about the public marketing surface.
- **Backend API surface** — out of scope. No endpoint-by-endpoint review.
- **Database schema gaps** — out of scope. Sufficient signal in handover docs that schema is solid (12 migrations, RLS on all tables).
- **Cost-per-customer / unit economics** — out of scope. Handover docs cover this (~$0.022 per report; 99%+ margin even at Starter tier).
- **Competitor pricing freshness** — comparison table uses numbers from PRICING-STRATEGY-2026.md (April 2026). If competitor pricing changed since, those numbers need a refresh. Worth a quick look before applying Section C.2.

---

## Next action from Claude

Phase 4 of this audit: apply the 4 PPTX polish fixes (Section F items 4-7). Code-only changes, surgical, ~10 lines total across 2-3 files. Will report back with exact diffs applied + recommend Saurabh do a manual visual verification by generating one PPTX with his test account.

After Phase 4: wait for Saurabh's decisions on the 3 forks in this report:
- Section C.3: enable 6 templates or drop marketing to 3?
- Section F item 14: drop multi-language plan gate from marketing?
- Section F item 15: drop email-delivery limits from marketing?

— end of report —
