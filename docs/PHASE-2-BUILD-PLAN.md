# ReportPilot — Phase 2 Build Plan

**Created:** March 24, 2026
**Scope:** PPTX Quality Overhaul + 5 Priority Features
**Timeline:** 3 Build Days (via Claude Code)

---

## Table of Contents

1. [PPTX Quality Audit — Issues Found](#1-pptx-quality-audit)
2. [Design Specification — Target Quality](#2-design-specification)
3. [Feature Specifications — 5 Priority Features](#3-feature-specifications)
4. [Build Sequence — Day-by-Day Plan](#4-build-sequence)
5. [Effort Estimates](#5-effort-estimates)
6. [Risk Assessment](#6-risk-assessment)

---

## 1. PPTX Quality Audit

### 1.1 Current State Assessment

**Template Generation:** 3 visual templates built with pptxgenjs (JavaScript):
- `modern_clean.pptx` — Light, corporate, consulting-firm style
- `dark_executive.pptx` — Dark navy, Bloomberg-terminal aesthetic
- `colorful_agency.pptx` — Vibrant coral/purple/teal, Stripe-style

**Population Engine:** python-pptx opens the template, replaces `{{placeholder}}` text, embeds chart PNGs, colorizes KPI changes, embeds logos, deletes unused slides.

**Chart Engine:** matplotlib generates 4 chart types as PNG at 200 DPI:
- Sessions over time (area line chart)
- Traffic sources (horizontal bar)
- Spend vs conversions (dual-axis bar + line)
- Campaign performance (grouped bars)

**Audit Results (March 24, 2026):**
- All 3 templates: **PASS** — 0 critical, 0 warnings
- No leftover placeholders
- Charts properly embedded (2 per data slide)
- KPI colors correctly applied (green/red/gray)
- Slide count: 8 (custom section auto-deleted when empty)

### 1.2 Issues Found — Categorized

#### CATEGORY A: Chart-on-Dark-Background Problem (CRITICAL)

**Issue:** All 4 charts are rendered with `#FAFAFA` (near-white) background. On the `dark_executive` template (background `#0F172A`), this creates jarring white rectangles on dark slides. The chart image background clashes severely with the slide background.

**Evidence:** Audit confirmed all 4 chart PNGs on the dark template show light backgrounds against dark card fills (`#1E293B`).

**Impact:** The dark executive template — arguably the most "premium" looking option — is visually broken for the chart slides.

**Fix Required:**
- `chart_generator.py` must accept a `theme` parameter: `"light"` (default) or `"dark"`
- Dark theme: `figure.facecolor = "#1E293B"`, `axes.facecolor = "#1E293B"`, text/label colors flip to light (`#CBD5E1`), grid lines use `#334155`, spines use `#475569`
- Chart colors (primary series) need to be more vivid on dark backgrounds for contrast
- The `generate_all_charts()` function needs a `dark_mode=True` parameter
- `report_generator.py` must pass `dark_mode=True` when `visual_template == "dark_executive"`

#### CATEGORY B: Chart Resolution and Sizing Issues (MEDIUM)

**Issue B1: DPI is 200 — should be 300**
Charts at 200 DPI look acceptable on screen but pixelated when printed or presented on high-resolution displays (4K monitors, projectors). Professional reports should use 300 DPI minimum.

**Issue B2: Chart figsize is 10×4.2" but embedded at 5.6×3.0"**
The matplotlib figure is larger than the PPTX slot, causing downscaling. This wastes file size and can introduce anti-aliasing artifacts. Charts should be generated at the exact dimensions they'll be displayed.

**Issue B3: Chart fonts don't match template fonts**
Charts use `Arial/DejaVu Sans` at 11pt base. Templates use `Calibri/Calibri Light`. This creates a visible typography mismatch between slide text and chart labels.

**Fix Required:**
- Increase DPI to 300
- Match figsize to PPTX slot: generate at 5.6×3.0" (left charts) and 5.7×3.0" (right charts) — or standardize to 5.6×3.0"
- Switch chart font to `Calibri` (available on Windows; fallback to `Arial` on Linux)
- Adjust font sizes: chart title 13pt, axis labels 10pt, tick labels 9pt (scaled down from current since figsize is smaller)

#### CATEGORY C: Typography Consistency Issues (MEDIUM)

**Issue C1: 10 different font sizes used across slides**
Sizes found: 8, 9, 10, 11, 12, 13, 16, 28, 30, 42pt. This is too many — professional decks use 4-5 sizes maximum.

**Issue C2: Calibri is functional but not premium**
Calibri is the default Microsoft font since 2007. While readable, it doesn't convey "premium tool" quality. However, python-pptx can only use fonts installed on the system, so we must stick with widely-available fonts.

**Recommended type scale (reduce to 5 sizes):**

| Role | Current | Proposed | Rationale |
|------|---------|----------|-----------|
| Slide title | 28pt Calibri Bold | 28pt Calibri Bold | Keep — good size |
| Cover client name | 42pt Calibri Bold | 40pt Calibri Bold | Slight reduction, cleaner |
| KPI value | 30pt Calibri Bold | 32pt Calibri Bold | Slightly larger for impact |
| Body text | 12-13pt Calibri Light | 12pt Calibri Light | Standardize |
| KPI label | 10pt Calibri Bold | 10pt Calibri Bold | Keep |
| Footer | 8pt Calibri Light | 8pt Calibri Light | Keep |
| Cover subheading | 16pt Calibri Light | 14pt Calibri Light | Tighten |

**Fix: Standardize to 6 sizes: 8, 10, 12, 14, 28, 32pt**

#### CATEGORY D: Narrative Text Handling (MEDIUM)

**Issue D1: Long narratives are plain text with no formatting**
The AI generates multi-paragraph narratives, but `_replace_placeholders_in_slide()` puts everything into the first run of the first paragraph. This means:
- No paragraph breaks (all text becomes one block)
- No bullet points for list items (key_wins, concerns, next_steps)
- No bold/italic emphasis

**Issue D2: List items on slides 6-8 have no bullet formatting**
Key wins, concerns, and next steps are newline-separated text. They render as plain paragraphs with no visual hierarchy.

**Fix Required:**
- For narrative slides (exec summary, website, ads): split on `\n\n` and create separate paragraphs with proper spacing
- For list slides (key wins, concerns, next steps): split on `\n` and add bullet character (`•`) prefix or use proper bullet formatting
- New helper function: `_populate_text_frame_formatted()` that handles paragraph splitting, bullet formatting, and preserves font attributes from the template

#### CATEGORY E: Cover Page Design (LOW-MEDIUM)

**Issue E1: Empty logo placeholder areas visible**
When no agency/client logo is provided, the placeholder areas show as empty white space with no visual element. This looks incomplete.

**Issue E2: No visual separator between report metadata**
The report period, type, and agency attribution are stacked with minimal spacing. Adding a subtle divider or color accent would improve hierarchy.

**Fix Required:**
- When logos are absent, either: (a) remove the placeholder shapes entirely, or (b) add a subtle decorative element (monogram, initials)
- Add a small accent line or icon before "Prepared by {{agency_name}}"

#### CATEGORY F: Slide Visual Variety (LOW)

**Issue F1: Content slides 2-5 are structurally identical**
Executive Summary, Website Performance, and Meta Ads Performance all follow the same pattern: title at top, content below. This creates visual monotony in the middle of the deck.

**Issue F2: No slide numbering in the deck**
While footers show "Page N", there's no visual progress indicator showing deck position.

**Fix Required (Low Priority):**
- Consider adding a small "1/8" indicator in footers
- The structural similarity is acceptable for MVP — the color-coded wins/concerns/next steps slides already provide variety

### 1.3 Issues Summary

| Category | Severity | Issue | Fix Effort |
|----------|----------|-------|------------|
| A | CRITICAL | Charts have light bg on dark template | 2 hours |
| B1 | MEDIUM | Chart DPI too low (200→300) | 15 min |
| B2 | MEDIUM | Chart figsize mismatch | 30 min |
| B3 | MEDIUM | Chart fonts don't match template | 30 min |
| C1 | MEDIUM | Too many font sizes (10→6) | 1 hour |
| C2 | LOW | Calibri is functional but not premium | No fix needed |
| D1 | MEDIUM | Narrative text has no paragraph formatting | 2 hours |
| D2 | MEDIUM | List items have no bullet formatting | 1 hour |
| E1 | LOW | Empty logo areas look incomplete | 30 min |
| E2 | LOW | No visual separator on cover | 15 min |
| F1 | LOW | Middle slides structurally similar | Defer |
| F2 | LOW | No slide number indicator | 15 min |

**Total estimated fix time: ~8 hours (1 build day)**

---

## 2. Design Specification

### 2.1 Typography Specification

**Font Stack (system-safe, no embedding needed):**
- **Headings:** Calibri Bold (Windows) / Arial Bold (fallback)
- **Body:** Calibri Light (Windows) / Arial (fallback)
- **KPI Values:** Calibri Bold
- **Chart text:** Calibri (matches slides)

**Type Scale (6 sizes only):**

| Token | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `display` | 40pt | Bold | 1.1 | Cover: client name |
| `h1` | 28pt | Bold | 1.2 | Slide titles |
| `h2` | 14pt | Regular | 1.3 | Cover: report period, section subheadings |
| `kpi-value` | 32pt | Bold | 1.0 | KPI scorecard numbers |
| `body` | 12pt | Light/Regular | 1.4× | Narrative text, list items |
| `caption` | 10pt | Bold | 1.2 | KPI labels, chart annotations |
| `footer` | 8pt | Regular | 1.0 | Footer text |

### 2.2 Color Specification Per Template

#### Modern Clean

| Token | Hex | Usage |
|-------|-----|-------|
| `bg` | `#FAFAFA` | Slide background |
| `primary` | `#4338CA` | Accent bar, headers, primary chart color |
| `card-bg` | `#FFFFFF` | Card backgrounds, chart containers |
| `text-primary` | `#0F172A` | Headings, KPI values |
| `text-body` | `#334155` | Body text |
| `text-muted` | `#64748B` | Labels, secondary text |
| `text-light` | `#94A3B8` | Footers, placeholders |
| `border` | `#E2E8F0` | Dividers, card borders |
| `success` | `#059669` | Positive KPI changes, Key Wins accent |
| `warning` | `#D97706` | Concerns accent |
| `danger` | `#BE123C` | Negative KPI changes (bumped from `#E11D48` for WCAG AA compliance — 5.5:1 vs 4.4:1) |
| `chart-bg` | `#FAFAFA` | Chart figure background (matches slide) |

#### Dark Executive

| Token | Hex | Usage |
|-------|-----|-------|
| `bg` | `#0F172A` | Slide background |
| `bg-deep` | `#020617` | Cover background |
| `primary` | `#06B6D4` | Accent lines, teal highlights |
| `card-bg` | `#1E293B` | Card backgrounds |
| `text-primary` | `#F8FAFC` | Headings, KPI values |
| `text-body` | `#CBD5E1` | Body text |
| `text-muted` | `#64748B` | Labels |
| `text-dim` | `#475569` | Footers |
| `border` | `#334155` | Dividers |
| `success` | `#10B981` | Positive changes |
| `warning` | `#F59E0B` | Concerns |
| `danger` | `#F87171` | Negative changes (brighter red for dark bg) |
| `chart-bg` | `#1E293B` | Chart figure background (matches cards) |
| `chart-grid` | `#334155` | Chart gridlines |
| `chart-text` | `#CBD5E1` | Chart labels, tick marks |

#### Colorful Agency

| Token | Hex | Usage |
|-------|-----|-------|
| `bg` | `#F8FAFC` | Slide background |
| `accent-1` | `#F97316` | Coral — cover, website performance |
| `accent-2` | `#8B5CF6` | Purple — exec summary, meta ads |
| `accent-3` | `#14B8A6` | Teal — KPI, next steps |
| `card-bg` | `#FFFFFF` | Card backgrounds |
| `text-primary` | `#0F172A` | Headings |
| `text-body` | `#334155` | Body text |
| `success` | `#059669` | Positive changes |
| `warning` | `#D97706` | Concerns |
| `chart-bg` | `#FFFFFF` | Chart figure background |

### 2.3 Layout Specification

**Slide dimensions:** 13.33" × 7.5" (Widescreen 16:9)

**Margins:**
- Left margin: 0.8" (from content to slide edge)
- Right margin: 0.53" (W - 1.6" total content width = 11.73")
- Top margin to title: 0.45"
- Title height: 0.7" (bottom of title at 1.15")
- Content starts at: 1.5" from top
- Footer at: 7.12" (y = H - 0.38)
- Bottom safe area: 0.5" (below footer)

**KPI Card Grid (3×2):**
- Card width: 3.5"
- Card height: 2.2"
- Horizontal gap: 0.35"
- Vertical gap: 0.35"
- Grid starts: x=0.8", y=1.55"
- Total grid width: 3 × 3.5 + 2 × 0.35 = 11.2" ✓ (within 11.73" content width)

**Chart Areas:**
- Left chart: x=0.8", y=1.5", w=5.6", h=3.0"
- Right chart: x=6.8", y=1.5", w=5.7", h=3.0"
- Gap between charts: 0.4"
- Narrative below charts: x=0.8", y=4.8", h=2.0"

### 2.4 Chart Design Specification

**General:**
- DPI: 300
- figsize: 5.6 × 3.0 inches (exact match to PPTX slot)
- Font: Calibri (fallback: Arial, DejaVu Sans)
- Base font size: 10pt
- Title: 12pt bold
- No chart background border
- Transparent chart areas where possible (use slide background color as facecolor)

**Light theme charts (modern_clean, colorful_agency):**
- facecolor: `#FAFAFA` (modern_clean) or `#FFFFFF` (colorful_agency)
- Grid: `#E2E8F0` at alpha 0.3
- Axis text: `#475569`
- Spine color: `#CBD5E1`
- Title color: `#0F172A`

**Dark theme charts (dark_executive):**
- facecolor: `#1E293B` (matches card background)
- Grid: `#334155` at alpha 0.4
- Axis text: `#CBD5E1`
- Spine color: `#475569`
- Title color: `#F8FAFC`
- Primary series: `#06B6D4` (teal, more vivid)
- Secondary series: `#10B981` (emerald, brighter)
- Accent: `#F59E0B` (amber)

---

## 3. Feature Specifications

### 3.1 Feature 1: Google Ads Integration

#### Overview
Add Google Ads data pull via the Google Ads API, integrated into the existing OAuth flow and report generation pipeline.

#### OAuth Setup
- **Scope to add:** `https://www.googleapis.com/auth/adwords`
- **Reuse existing Google OAuth:** Yes — same Google Cloud project, same client ID/secret. Just add the scope to the consent screen
- **Developer token:** Required. Apply via Google Ads Manager Account. Start with Basic access (up to 15,000 operations/day). Application process takes 1-5 business days
- **Environment variable to add:** `GOOGLE_ADS_DEVELOPER_TOKEN` in `backend/.env`

#### Library
- **Package:** `google-ads` (official Google Ads Python client library, gRPC-based)
- **Current version:** 29.2.0 (released Feb 2026, supports API v22, Python 3.9-3.14)
- **Install:** `pip install google-ads` (note: large package due to gRPC dependencies)
- **Add to:** `backend/requirements.txt`
- **Configuration:** Use `GoogleAdsClient.load_from_dict()` (best for FastAPI integration)
- **Query method:** Use `search_stream()` for reporting queries (streams results, more efficient than `search()`)

#### Data to Pull (GAQL Queries)

**Campaign Performance Report:**
```sql
SELECT
  campaign.id,
  campaign.name,
  campaign.status,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions,
  metrics.conversions_value,
  metrics.cost_per_conversion,
  metrics.ctr,
  metrics.average_cpc,
  segments.date
FROM campaign
WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
  AND campaign.status != 'REMOVED'
ORDER BY metrics.cost_micros DESC
```

**Account-level summary:**
```sql
SELECT
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions,
  metrics.conversions_value,
  metrics.ctr,
  metrics.average_cpc,
  metrics.search_impression_share
FROM customer
WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
```

**Search Terms Report (Top 20):**
```sql
SELECT
  search_term_view.search_term,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions
FROM search_term_view
WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
ORDER BY metrics.impressions DESC
LIMIT 20
```

#### Data Structure (Output)
```python
{
    "google_ads": {
        "currency": "USD",
        "summary": {
            "impressions": 150000,
            "clicks": 4500,
            "spend": 3200.00,  # cost_micros / 1_000_000
            "conversions": 120,
            "conversion_value": 12000.00,
            "ctr": 3.0,
            "avg_cpc": 0.71,
            "roas": 3.75,
            "cost_per_conversion": 26.67,
            "search_impression_share": 0.45,
            # Period comparisons
            "spend_change": 8.5,
            "conversions_change": 15.2,
            "clicks_change": 12.0,
        },
        "campaigns": [
            {"name": "Brand Search", "spend": 1200, "clicks": 2100, "conversions": 65, "ctr": 8.2},
            # ...
        ],
        "daily": [
            {"date": "2026-02-01", "spend": 115.00, "clicks": 160, "conversions": 4},
            # ...
        ],
        "search_terms": [
            {"term": "buy product x online", "impressions": 3200, "clicks": 180, "conversions": 12},
            # ...
        ],
    }
}
```

#### Report Integration
- **New slide:** "Paid Advertising — Google Ads" (same layout as existing Meta Ads slide)
- **New charts:** Spend vs conversions (reuse existing dual-axis) + campaign performance (reuse existing grouped bar)
- **Slide position:** After Meta Ads slide (slide index 5, pushing remaining slides down)
- **Template update:** All 3 template scripts need a new slide 6
- **AI narrative:** Add `google_ads_performance` section to AI prompt
- **KPI scorecard:** Add Google Ads metrics to KPI options (gads_spend, gads_conversions, gads_roas, gads_cpa)

#### Developer Token Access Levels (Critical for Launch)

| Level | How to Get | Timeline | Daily Ops | Notes |
|---|---|---|---|---|
| Test Account | Automatic on API signup | Instant | 15,000 | Fake data only — can't read real accounts |
| Explorer | Automatic (since Oct 2025) | Instant | 2,880 | **Real production access** — sufficient for MVP launch (~50-100 accounts/day) |
| Basic | Application + review | Weeks to months (backlog as of Feb 2026) | 15,000 | Full production — apply in parallel |
| Standard | Application + review | Longer | Unlimited | Large-scale tools |

**MVP strategy:** Use Explorer Access for launch (instant, real data). Apply for Basic immediately since review is backlogged. Explorer's 2,880 ops/day supports ~50-100 client reports daily.

#### Rate Limits
- Operations per day: depends on access level (see above)
- Per-second: Token Bucket algorithm per (customer_id + developer_token) pair — not a fixed QPS
- Paginated requests with valid page tokens do NOT count against quota
- For read-only reporting, unlikely to hit limits at Explorer or Basic level

#### Account Hierarchy
- Need to handle MCC (Manager Account) → Client Account hierarchy
- Use `CustomerService.ListAccessibleCustomers()` to list accounts (no customer_id needed for this call)
- For MCC drill-down: query `customer_client` resource to get child accounts
- **Must store `login_customer_id` (MCC ID)** alongside the connection record when user connects via manager account
- Store `customer_id` in connections table alongside existing `property_id` field

#### Important Implementation Notes
- **Monetary values in micros:** All cost fields (cost_micros, etc.) must be divided by 1,000,000
- **ROAS not a direct metric on campaign resource:** Must calculate: `ROAS = conversions_value / (cost_micros / 1_000_000)`
- **Developer token is per-app, not per-user:** Store as env var, used for ALL API calls
- **OAuth is separate from GA4:** Same client ID/secret, different scope. Needs its own consent prompt with `prompt=consent&access_type=offline`
- **Data freshness:** Clicks/impressions delayed <3 hours. Non-last-click conversions delayed up to 15 hours. Conversions can update retroactively up to 30 days. Consider ending report date 2-3 days before today.

#### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/services/google_ads.py` | CREATE | Google Ads API client service |
| `backend/routers/connections.py` | MODIFY | Add Google Ads account listing + connection save |
| `backend/routers/auth.py` | MODIFY | Add Google Ads scope to OAuth flow |
| `backend/services/ai_narrative.py` | MODIFY | Add Google Ads section to prompt |
| `backend/services/chart_generator.py` | MODIFY | Generate charts from Google Ads data |
| `backend/services/report_generator.py` | MODIFY | New slide for Google Ads |
| `backend/services/mock_data.py` | MODIFY | Add mock Google Ads data |
| `backend/requirements.txt` | MODIFY | Add `google-ads` package |
| `scripts/create_*.js` (all 3) | MODIFY | Add Google Ads slide template |
| `frontend/.../connections/page.tsx` | MODIFY | Add Google Ads connection UI |
| `backend/config.py` | MODIFY | Add `GOOGLE_ADS_DEVELOPER_TOKEN` |

**Estimated complexity:** HIGH — 12 files, ~800 lines of code

---

### 3.2 Feature 2: Google Search Console Integration

#### Overview
Add Google Search Console (GSC) data pull for SEO performance metrics. Reuses existing Google OAuth flow.

#### OAuth Setup
- **Scope to add:** `https://www.googleapis.com/auth/webmasters.readonly`
- **Reuse existing Google OAuth:** Yes — just add scope
- **No additional API key needed** (unlike Google Ads, no developer token required)

#### Library
- **Package:** `google-api-python-client` (already likely a dependency from GA4 setup)
- **Service:** `searchconsole` v1 (not the old `webmasters` v3) → `searchanalytics.query()`
- **Service construction:** `build('searchconsole', 'v1', credentials=credentials)`
- **Install:** `pip install google-api-python-client google-auth google-auth-httplib2` (if not already present)

#### Data to Pull

**Search Analytics — Top Queries (by clicks):**
```python
service.searchanalytics().query(
    siteUrl='https://example.com',
    body={
        'startDate': '2026-02-01',
        'endDate': '2026-02-28',
        'dimensions': ['query'],
        'rowLimit': 20,
        'type': 'web',
    }
).execute()
```

**Search Analytics — Top Pages (by clicks):**
```python
service.searchanalytics().query(
    siteUrl='https://example.com',
    body={
        'startDate': '2026-02-01',
        'endDate': '2026-02-28',
        'dimensions': ['page'],
        'rowLimit': 20,
        'type': 'web',
    }
).execute()
```

**Daily Performance:**
```python
service.searchanalytics().query(
    siteUrl='https://example.com',
    body={
        'startDate': '2026-02-01',
        'endDate': '2026-02-28',
        'dimensions': ['date'],
        'type': 'web',
    }
).execute()
```

#### Data Structure (Output)
```python
{
    "search_console": {
        "summary": {
            "clicks": 8500,
            "impressions": 125000,
            "ctr": 6.8,
            "average_position": 12.3,
            # Period comparisons
            "clicks_change": 15.2,
            "impressions_change": 22.0,
            "ctr_change": -1.5,
            "position_change": -0.8,  # negative = improved
        },
        "top_queries": [
            {"query": "buy product x", "clicks": 450, "impressions": 3200, "ctr": 14.1, "position": 3.2},
            # ... top 20
        ],
        "top_pages": [
            {"page": "/products/x", "clicks": 1200, "impressions": 8500, "ctr": 14.1, "position": 5.1},
            # ... top 20
        ],
        "daily": [
            {"date": "2026-02-01", "clicks": 280, "impressions": 4100, "ctr": 6.8, "position": 12.5},
            # ...
        ],
    }
}
```

#### Report Integration
- **New slide:** "SEO Performance" — shows clicks trend, top queries table, top pages
- **New charts:**
  - Clicks & impressions over time (dual-axis line chart)
  - Top 10 queries horizontal bar chart (by clicks)
- **AI narrative:** Add `seo_performance` section to prompt
- **KPI scorecard:** Add GSC metrics (clicks, impressions, CTR, avg position)

#### Site Verification
- Use `sites.list()` to get verified sites for the authenticated user
- Support both URL prefix (`https://example.com/`) and domain properties (`sc-domain:example.com`)
- Store `site_url` in connections table

#### Rate Limits
- 200 requests/minute per site for `searchAnalytics.query`
- 1,200 queries/minute per project overall
- 25,000 rows per query (rowLimit); use `startRow` for pagination
- Data available with 2-3 day delay (not real-time)
- Max historical data: ~16 months
- ReportPilot needs ~6 API calls per report (aggregate current, aggregate previous, top queries, top pages, device breakdown, daily trend) — well within limits

#### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/services/search_console.py` | CREATE | GSC API client service |
| `backend/routers/connections.py` | MODIFY | Add GSC site listing + connection save |
| `backend/routers/auth.py` | MODIFY | Add GSC scope to OAuth flow |
| `backend/services/ai_narrative.py` | MODIFY | Add SEO section to prompt |
| `backend/services/chart_generator.py` | MODIFY | SEO charts (clicks trend, top queries bar) |
| `backend/services/report_generator.py` | MODIFY | New SEO slide |
| `backend/services/mock_data.py` | MODIFY | Add mock GSC data |
| `scripts/create_*.js` (all 3) | MODIFY | Add SEO slide template |
| `frontend/.../connections/page.tsx` | MODIFY | Add GSC connection UI |

**Estimated complexity:** MEDIUM — 10 files, ~500 lines of code

---

### 3.3 Feature 3: CSV Upload for Custom Data Sources

#### Overview
Allow users to upload CSV files containing data from platforms we don't directly integrate with (LinkedIn Ads, TikTok Ads, Mailchimp, etc.). The data flows into reports as a custom data section.

#### User Flow
1. User navigates to Client → Connections → "Add Data Source" → "Upload CSV"
2. User selects a CSV file from their computer
3. System parses the CSV and shows a preview (first 5 rows)
4. User maps columns: which column is "date", which is "metric name", which is "value"
5. User names the data source (e.g., "LinkedIn Ads", "TikTok Ads")
6. System saves the data as a connection of type `csv_upload`
7. Data appears in report generation as an additional section

#### CSV Format Options

**Option A: Simple KPI Format (recommended for MVP)**
```csv
metric_name,current_value,previous_value,unit
Followers,12500,11200,number
Engagement Rate,4.2,3.8,percent
Reach,85000,72000,number
Link Clicks,2300,1900,number
```

**Option B: Time-Series Format (future enhancement)**
```csv
date,metric_name,value
2026-02-01,followers,12340
2026-02-01,engagement_rate,4.1
2026-02-02,followers,12380
```

**MVP: Start with Option A** — simple KPI pairs that generate a scorecard-style section in the report.

#### Downloadable Templates
Provide pre-formatted CSV templates for popular platforms:
- `linkedin_ads_template.csv` — Impressions, Clicks, Spend, Leads, CTR, CPC
- `tiktok_ads_template.csv` — Impressions, Video Views, Clicks, Spend, Conversions
- `mailchimp_template.csv` — Emails Sent, Open Rate, Click Rate, Unsubscribes, Revenue
- `generic_kpi_template.csv` — Blank template with instructions

#### Backend Implementation

**Upload endpoint:**
```
POST /api/connections/csv-upload
Content-Type: multipart/form-data
Body: file (CSV), client_id, source_name
```

**Processing:**
1. Parse CSV with Python `csv` module
2. Validate: max 20 rows, required columns present
3. Compute period-over-period changes from current_value vs previous_value
4. Store parsed data as JSON in `data_snapshots` table
5. Create a connection record with `platform = "csv_{source_name}"`

**Report integration:**
- Generate a KPI-style section (similar to existing scorecard)
- AI narrative includes CSV data in the prompt context
- New slide: "{Source Name} Performance" with KPI cards

#### Frontend Implementation

**Upload UI:** Modal dialog triggered from Connections page
1. Drag-and-drop file zone (accepts .csv only)
2. Column mapping dropdown (auto-detect common names)
3. Preview table showing parsed data
4. "Source Name" text input
5. "Save" button

**Components needed:**
- `CSVUploadDialog.tsx` — Modal with file drop zone
- `CSVPreviewTable.tsx` — Shows parsed data preview
- `CSVColumnMapper.tsx` — Column name → role mapping

#### Database Changes
No schema changes needed — CSV data fits existing tables:
- `connections` table: `platform = "csv_linkedin_ads"`, `connection_metadata = {columns, source_name}`
- `data_snapshots` table: `platform_data` JSON stores the parsed CSV data

#### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/routers/csv_upload.py` | CREATE | CSV upload + parsing endpoint |
| `backend/services/csv_parser.py` | CREATE | CSV validation and parsing service |
| `backend/services/report_generator.py` | MODIFY | Render CSV data section in report |
| `backend/services/ai_narrative.py` | MODIFY | Include CSV data in AI prompt |
| `backend/templates/csv_templates/` | CREATE | 4 downloadable CSV template files |
| `frontend/.../connections/page.tsx` | MODIFY | Add "Upload CSV" button |
| `frontend/components/clients/CSVUploadDialog.tsx` | CREATE | Upload modal |
| `frontend/components/clients/CSVPreviewTable.tsx` | CREATE | Data preview |

**Estimated complexity:** MEDIUM — 8 files, ~600 lines of code

---

### 3.4 Feature 4: Multi-Language AI Narratives

#### Overview
Allow AI-generated narrative to be written in languages other than English. Critical for agencies serving non-English-speaking clients.

#### Priority Languages (by market size)
1. **Spanish** — Latin America + Spain (huge freelancer market)
2. **Portuguese** — Brazil (large digital marketing industry)
3. **French** — France, Quebec, West Africa
4. **German** — Germany, Austria, Switzerland
5. **Hindi** — India (ReportPilot's home market)
6. **Arabic** — Middle East (growing digital ad market)
7. **Japanese** — Japan
8. **Italian** — Italy

#### Implementation

**Approach:** Add a `language` parameter to the GPT-4o prompt. GPT-4o natively supports all target languages with high quality.

**Prompt modification in `ai_narrative.py`:**
```python
# Current
system_prompt = "You are a digital marketing analyst..."

# New
language_instruction = ""
if language and language != "en":
    language_names = {
        "es": "Spanish", "pt": "Portuguese", "fr": "French",
        "de": "German", "hi": "Hindi", "ar": "Arabic",
        "ja": "Japanese", "it": "Italian",
    }
    lang_name = language_names.get(language, language)
    language_instruction = f"\n\nIMPORTANT: Write ALL narrative content in {lang_name}. "
    "Use natural, professional {lang_name} — not machine-translated English. "
    "Keep metric names and abbreviations in English (KPI, CTR, CPC, ROAS) "
    "but write all commentary, analysis, and recommendations in {lang_name}."
```

**What gets translated:**
- ✅ Executive summary narrative
- ✅ Website performance narrative
- ✅ Paid advertising narrative
- ✅ Key wins, concerns, next steps
- ❌ KPI labels (stay in English: "SESSIONS", "AD SPEND")
- ❌ Chart axis labels (stay in English)
- ❌ Footer text (stays in English)
- ❌ Report title ("Performance Report" stays English)

**UI: Per-client language setting**
- Add `report_language` field to `clients` table (default: "en")
- Dropdown on client settings page: English, Spanish, Portuguese, French, German, Hindi, Arabic, Japanese, Italian
- Passed to AI narrative generation

**Potential issue: AI hallucination in non-English**
GPT-4o's quality varies by language. Spanish, French, German, Portuguese are excellent. Hindi, Arabic, Japanese are good but may need more explicit prompt instructions to maintain professional register.

#### Chart Label Translation (Deferred)
For MVP, chart labels stay in English. Future enhancement: add a `chart_labels` dict per language that maps "Sessions Over Time" → "Sesiones a lo Largo del Tiempo", etc.

#### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/services/ai_narrative.py` | MODIFY | Add language parameter to prompt |
| `backend/routers/reports.py` | MODIFY | Pass language from client config |
| `backend/routers/clients.py` | MODIFY | Accept report_language in client update |
| `backend/models/schemas.py` | MODIFY | Add report_language to ClientUpdate |
| `supabase/migrations/007_add_language.sql` | CREATE | Add report_language column |
| `frontend/.../[clientId]/page.tsx` | MODIFY | Language dropdown in client settings |
| `frontend/components/clients/LanguageSelector.tsx` | CREATE | Language dropdown component |

**Estimated complexity:** LOW-MEDIUM — 7 files, ~200 lines of code

---

### 3.5 Feature 5: Report Link Sharing with View Tracking

#### Overview
Generate shareable URLs for reports that can be sent to clients or stakeholders. Track when and how reports are viewed.

#### User Flow
1. User generates a report and views the preview
2. User clicks "Share" button (next to existing Download/Send buttons)
3. Share dialog opens with options:
   - Auto-generated link: `https://app.reportpilot.co/shared/r/{hash}`
   - Password protection toggle (optional)
   - Expiry date picker (7 days, 30 days, 90 days, never)
   - Copy link button
4. Client/stakeholder opens the link → sees a read-only report view
5. Agency user can see view analytics: opens, unique viewers, time, devices

#### Database Schema

**New table: `shared_reports`**
```sql
CREATE TABLE shared_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    share_hash VARCHAR(32) NOT NULL UNIQUE,  -- short unique identifier
    password_hash VARCHAR(255),  -- bcrypt hash if password-protected
    expires_at TIMESTAMPTZ,  -- NULL = never expires
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- RLS: owner only
ALTER TABLE shared_reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own shared reports"
    ON shared_reports FOR ALL
    USING (auth.uid() = user_id);
```

**New table: `report_views`**
```sql
CREATE TABLE report_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shared_report_id UUID NOT NULL REFERENCES shared_reports(id) ON DELETE CASCADE,
    viewer_ip VARCHAR(45),  -- IPv4 or IPv6
    user_agent TEXT,
    device_type VARCHAR(20),  -- 'desktop', 'mobile', 'tablet'
    country VARCHAR(2),  -- from IP geolocation (optional)
    viewed_at TIMESTAMPTZ DEFAULT now(),
    duration_seconds INTEGER  -- time on page (via beacon API)
);

-- RLS: accessible via shared_report → user_id
ALTER TABLE report_views ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users view own report views"
    ON report_views FOR SELECT
    USING (
        shared_report_id IN (
            SELECT id FROM shared_reports WHERE user_id = auth.uid()
        )
    );

-- No insert policy for report_views — inserts happen via service role
```

#### Backend Implementation

**Endpoints:**
```
POST   /api/reports/{report_id}/share       — Create share link
GET    /api/reports/{report_id}/share        — Get share links for report
DELETE /api/shared/{share_hash}              — Revoke share link
GET    /api/shared/{share_hash}              — Public: get report data (no auth)
POST   /api/shared/{share_hash}/verify       — Public: verify password
POST   /api/shared/{share_hash}/view         — Public: log view event
GET    /api/reports/{report_id}/analytics    — Get view analytics
```

**Share hash generation:**
```python
import secrets
share_hash = secrets.token_urlsafe(16)  # 22-character URL-safe string
```

**Public report view endpoint (no auth required):**
- Checks share_hash exists and is active
- Checks expiry date
- If password-protected, requires prior verification
- Returns report data (narrative, KPIs, chart URLs) but NOT raw API tokens
- Logs view event via service role key

#### Frontend Implementation

**Share Dialog Component:**
```
<ShareReportDialog>
  ├── Link display with copy button
  ├── Password toggle + input
  ├── Expiry date selector
  ├── "Create Link" / "Update" button
  └── Active share links list with revoke buttons
</ShareReportDialog>
```

**Public Report View Page:**
- Route: `/shared/[hash]` (public, no auth required)
- Password gate: if password-protected, show password input first
- Read-only report view: KPI cards, narratives, charts (reuse existing preview components)
- No edit/download functionality (drives users to sign up)
- Footer: "Report generated by ReportPilot — Create your own at reportpilot.co"

**View Analytics Panel:**
- Added to existing report preview page
- Shows: total views, unique viewers, last viewed, device breakdown
- Simple table/chart of views over time

#### View Tracking Implementation
```javascript
// On public report page load
fetch(`/api/shared/${hash}/view`, {
    method: 'POST',
    body: JSON.stringify({
        user_agent: navigator.userAgent,
        device_type: detectDevice(),
    }),
});

// On page unload (duration tracking)
navigator.sendBeacon(`/api/shared/${hash}/view`, JSON.stringify({
    duration_seconds: Math.round((Date.now() - pageLoadTime) / 1000),
}));
```

#### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `supabase/migrations/008_shared_reports.sql` | CREATE | shared_reports + report_views tables |
| `backend/routers/shared.py` | CREATE | Share CRUD + public view endpoints |
| `backend/models/schemas.py` | MODIFY | Add share-related Pydantic models |
| `frontend/src/app/shared/[hash]/page.tsx` | CREATE | Public report view page |
| `frontend/components/reports/ShareReportDialog.tsx` | CREATE | Share dialog |
| `frontend/components/reports/ViewAnalytics.tsx` | CREATE | View tracking display |
| `frontend/.../reports/[reportId]/page.tsx` | MODIFY | Add Share button + analytics |

**Estimated complexity:** HIGH — 8 files, ~700 lines of code

---

## 4. Build Sequence

### Day 1: PPTX Quality Overhaul (8 hours)

**Morning — Chart Engine Overhaul (4 hours)**

| Step | File | Task | Time |
|------|------|------|------|
| 1.1 | `backend/services/chart_generator.py` | Add `theme` parameter ("light"/"dark") to `_setup_chart_style()`. Dark theme uses `#1E293B` background, `#CBD5E1` text, `#334155` grid. | 45 min |
| 1.2 | `backend/services/chart_generator.py` | Increase DPI from 200 to 300. Change figsize from (10, 4.2) to (5.6, 3.0) for all chart functions. | 30 min |
| 1.3 | `backend/services/chart_generator.py` | Switch font to Calibri (with Arial/DejaVu Sans fallback). Adjust font sizes: title 12pt, labels 10pt, ticks 9pt. | 30 min |
| 1.4 | `backend/services/chart_generator.py` | Update `generate_all_charts()` to accept `dark_mode` and `visual_template` params. Pass theme colors to each chart function. | 30 min |
| 1.5 | `backend/services/chart_generator.py` | For colorful_agency: use coral/purple/teal as chart primary colors instead of indigo. | 20 min |
| 1.6 | `backend/services/report_generator.py` | Pass `visual_template` to chart generation so dark_executive gets dark charts. | 15 min |
| 1.7 | Generate + audit | Re-generate all 3 template reports. Run audit. Verify dark charts on dark background. | 30 min |

**Afternoon — Template + Text Formatting (4 hours)**

| Step | File | Task | Time |
|------|------|------|------|
| 1.8 | `backend/services/report_generator.py` | Create `_populate_text_frame_formatted()` helper that splits text on `\n\n` into paragraphs with proper spacing, preserving template font attributes. | 60 min |
| 1.9 | `backend/services/report_generator.py` | Create `_populate_bullet_list()` helper that splits text on `\n`, adds `•` prefix, creates separate paragraphs. | 45 min |
| 1.10 | `backend/services/report_generator.py` | Replace `_replace_placeholders_in_slide()` usage for narrative/list slides with formatted population functions. | 45 min |
| 1.11 | `scripts/create_modern_clean.js` | Standardize font sizes to 6-size scale. Adjust cover subheading from 16pt to 14pt. KPI value from 30pt to 32pt. | 20 min |
| 1.12 | `scripts/create_dark_executive.js` | Same font standardization. | 15 min |
| 1.13 | `scripts/create_colorful_agency.js` | Same font standardization. | 15 min |
| 1.14 | `backend/services/report_generator.py` | Handle empty logo placeholders: remove shape entirely when no logo URL provided. | 20 min |
| 1.15 | Re-generate templates | Run `node scripts/create_all_templates.js` to rebuild templates. | 5 min |
| 1.16 | Final audit | Generate all 3 reports. Run full audit. Open in PowerPoint to visually verify. | 30 min |

---

### Day 2: Google Ads + Google Search Console (8 hours)

**Morning — Google Ads Integration (5 hours)**

| Step | File | Task | Time |
|------|------|------|------|
| 2.1 | `backend/requirements.txt` | Add `google-ads>=25.0.0` | 5 min |
| 2.2 | `backend/config.py` | Add `GOOGLE_ADS_DEVELOPER_TOKEN` setting | 5 min |
| 2.3 | `backend/services/google_ads.py` | CREATE — Google Ads API client: auth setup, campaign report query, account summary query, search terms query. Period comparison logic. Token refresh reuse from existing Google OAuth. | 120 min |
| 2.4 | `backend/services/mock_data.py` | Add mock Google Ads data matching the data structure spec above | 20 min |
| 2.5 | `backend/routers/auth.py` | Add Google Ads scope to OAuth consent URL. Add account listing endpoint. | 30 min |
| 2.6 | `backend/routers/connections.py` | Add Google Ads connection save (customer_id + connection) | 20 min |
| 2.7 | `backend/routers/data_pull.py` | Add Google Ads data pull to the aggregation endpoint | 15 min |
| 2.8 | `scripts/create_*.js` (all 3) | Add "Google Ads Performance" slide template (same layout as Meta Ads slide) | 30 min |
| 2.9 | `backend/services/report_generator.py` | Add Google Ads slide population, chart embedding, slide map update | 30 min |
| 2.10 | `backend/services/chart_generator.py` | Add Google Ads chart functions (reuse spend_vs_conversions and campaign patterns) | 20 min |
| 2.11 | `backend/services/ai_narrative.py` | Add Google Ads section to AI prompt | 15 min |

**Afternoon — Google Search Console Integration (3 hours)**

| Step | File | Task | Time |
|------|------|------|------|
| 2.12 | `backend/services/search_console.py` | CREATE — GSC API client: query search analytics, list sites, period comparison | 60 min |
| 2.13 | `backend/services/mock_data.py` | Add mock GSC data | 15 min |
| 2.14 | `backend/routers/auth.py` | Add GSC scope to Google OAuth consent URL | 10 min |
| 2.15 | `backend/routers/connections.py` | Add GSC site listing + connection save | 20 min |
| 2.16 | `scripts/create_*.js` (all 3) | Add "SEO Performance" slide template | 30 min |
| 2.17 | `backend/services/chart_generator.py` | Add SEO charts: clicks/impressions trend, top queries bar | 30 min |
| 2.18 | `backend/services/report_generator.py` | Add SEO slide population | 20 min |
| 2.19 | `backend/services/ai_narrative.py` | Add SEO section to prompt | 10 min |
| 2.20 | Frontend connections page | Add Google Ads + GSC connection buttons to connections UI | 30 min |

---

### Day 3: CSV Upload + Multi-Language + Report Sharing (8 hours)

**Morning — CSV Upload + Multi-Language (3.5 hours)**

| Step | File | Task | Time |
|------|------|------|------|
| 3.1 | `backend/services/csv_parser.py` | CREATE — CSV parsing, validation, column mapping | 45 min |
| 3.2 | `backend/routers/csv_upload.py` | CREATE — Upload endpoint, template download endpoint | 30 min |
| 3.3 | `backend/templates/csv_templates/` | CREATE — 4 template CSV files | 15 min |
| 3.4 | `backend/services/report_generator.py` | Render CSV data as KPI section in report | 30 min |
| 3.5 | `frontend/components/clients/CSVUploadDialog.tsx` | CREATE — Upload dialog with preview | 45 min |
| 3.6 | `frontend/.../connections/page.tsx` | Add "Upload CSV" button | 15 min |
| 3.7 | `supabase/migrations/007_add_language.sql` | CREATE — Add report_language column to clients | 5 min |
| 3.8 | `backend/services/ai_narrative.py` | Add language parameter to prompt | 20 min |
| 3.9 | `backend/routers/reports.py` | Pass language from client config | 10 min |
| 3.10 | `frontend/components/clients/LanguageSelector.tsx` | CREATE — Language dropdown | 15 min |
| 3.11 | `frontend/.../[clientId]/page.tsx` | Add language selector to client settings | 10 min |

**Afternoon — Report Link Sharing (4.5 hours)**

| Step | File | Task | Time |
|------|------|------|------|
| 3.12 | `supabase/migrations/008_shared_reports.sql` | CREATE — shared_reports + report_views tables with RLS | 20 min |
| 3.13 | `backend/routers/shared.py` | CREATE — Share CRUD, public view, password verify, view logging | 90 min |
| 3.14 | `backend/models/schemas.py` | Add share-related Pydantic models | 15 min |
| 3.15 | `frontend/src/app/shared/[hash]/page.tsx` | CREATE — Public report view (read-only, no auth) | 60 min |
| 3.16 | `frontend/components/reports/ShareReportDialog.tsx` | CREATE — Share dialog with options | 45 min |
| 3.17 | `frontend/components/reports/ViewAnalytics.tsx` | CREATE — View tracking display | 30 min |
| 3.18 | `frontend/.../reports/[reportId]/page.tsx` | Add Share button + analytics panel | 15 min |

---

## 5. Effort Estimates

### Summary by Feature

| Feature | Files Created | Files Modified | Est. Lines | Complexity | Time |
|---------|-------------|----------------|-----------|------------|------|
| PPTX Quality Overhaul | 0 | 6 | ~400 | MEDIUM | 8 hours |
| Google Ads Integration | 1 | 10 | ~800 | HIGH | 5 hours |
| Google Search Console | 1 | 7 | ~500 | MEDIUM | 3 hours |
| CSV Upload | 6 | 4 | ~600 | MEDIUM | 3.5 hours |
| Multi-Language | 2 | 4 | ~200 | LOW | 1.5 hours |
| Report Link Sharing | 5 | 3 | ~700 | HIGH | 4.5 hours |
| **TOTAL** | **15** | **34** | **~3,200** | — | **25.5 hours** |

### Database Migrations

| Migration | Tables | Columns | RLS Policies |
|-----------|--------|---------|-------------|
| `007_add_language.sql` | 0 new | 1 added (clients.report_language) | 0 new |
| `008_shared_reports.sql` | 2 new | 14 total | 2 new |

### Dependencies to Install

| Package | Version | Used For |
|---------|---------|----------|
| `google-ads` | >=29.0.0 | Google Ads API (large package — includes gRPC) |
| `google-api-python-client` | latest | Search Console API (may already be installed) |
| `google-auth` | latest | OAuth credentials (may already be installed) |
| `google-auth-httplib2` | latest | HTTP transport for google-auth |

---

## 6. Risk Assessment

### High Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Google Ads developer token approval delay** | Can't test with real accounts at Basic level | **Mitigated:** Explorer Access (2,880 ops/day) is instant and provides real production access. Use this for MVP launch. Apply for Basic Access in parallel — review backlog is weeks-to-months as of Feb 2026. |
| **Chart font rendering on Linux/Docker** | Calibri not available on Linux (Railway deployment) | Include font fallback chain: Calibri → Arial → DejaVu Sans. Test on Railway before launch. |
| **python-pptx text formatting limitations** | Complex formatting (bullets, bold within paragraph) may not render correctly | Test extensively in actual PowerPoint. Keep formatting simple. |

### Medium Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Google Ads MCC hierarchy complexity** | Account selection UI may need multiple levels | Start with single-account selection. Add MCC drill-down later. |
| **CSV parsing edge cases** | Malformed CSVs, encoding issues, delimiter confusion | Strict validation. Show preview before saving. Support UTF-8 only. |
| **Multi-language AI quality** | Some languages may produce less professional narrative | Add language-specific prompt tuning. Allow manual editing. Test with native speakers before launch. |
| **Shared report security** | Public URLs could be brute-forced | Use 22-character cryptographic hashes (secrets.token_urlsafe). Rate limit the public endpoint. |

### Low Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Chart background color mismatch** | Slight color difference between chart bg and slide bg | Use exact hex values from template spec. Generate comparison screenshots. |
| **GSC data delay (2-3 days)** | Report shows stale SEO data | Display "Data as of {date}" label. Document in UI. |
| **View tracking accuracy** | sendBeacon may not fire on all browsers | Duration tracking is best-effort. View count (page load) is reliable. |

### Blockers (Must Resolve Before Build)

1. **Google Ads Developer Token** — Apply NOW via Google Ads Manager Account → API Center (`https://ads.google.com/aw/apicenter`). Explorer Access is instant (real production data, 2,880 ops/day). Apply for Basic Access in parallel — review backlog is weeks-to-months.
2. **Railway font availability** — Verify Calibri/Arial availability on Railway's Docker image. May need to include fonts in the Docker image or use a Google Font that's pre-installed.
3. **pptxgenjs installed** — Verify `node scripts/create_all_templates.js` runs successfully before starting Day 1.

---

## Appendix A: Current File Inventory

### Files That Will Be Modified (Day 1 — PPTX Overhaul)

```
backend/services/chart_generator.py    — Dark mode, DPI, fonts, figsize
backend/services/report_generator.py   — Formatted text, logo handling
scripts/create_modern_clean.js         — Font standardization
scripts/create_dark_executive.js       — Font standardization
scripts/create_colorful_agency.js      — Font standardization
scripts/audit_pptx.py                  — Update for new slide count
```

### Files That Will Be Created (Days 2-3)

```
backend/services/google_ads.py         — Google Ads API client
backend/services/search_console.py     — GSC API client
backend/services/csv_parser.py         — CSV parsing service
backend/routers/csv_upload.py          — CSV upload endpoints
backend/routers/shared.py              — Share link endpoints
backend/templates/csv_templates/*.csv  — 4 template files
supabase/migrations/007_add_language.sql
supabase/migrations/008_shared_reports.sql
frontend/src/app/shared/[hash]/page.tsx
frontend/components/clients/CSVUploadDialog.tsx
frontend/components/clients/CSVPreviewTable.tsx
frontend/components/clients/LanguageSelector.tsx
frontend/components/reports/ShareReportDialog.tsx
frontend/components/reports/ViewAnalytics.tsx
```

## Appendix B: Key Design Principles Applied

Based on professional presentation design research (McKinsey/BCG methodology + WCAG accessibility):

### Core Layout Rules
1. **60-30-10 Color Rule:** 60% white/background, 30% dark text, 10% brand accent
2. **One idea per slide.** Never mix two unrelated concepts.
3. **Minimum contrast ratio:** 4.5:1 for body text, 3:1 for large text (WCAG AA)
4. **Content safe zone:** 0.5" minimum on all edges → usable area = 12.33" × 6.5"
5. **Max 60-70% fill:** Never fill more than 70% of a slide with content
6. **Gestalt proximity:** Related items 0.1-0.15" apart, unrelated groups 0.3-0.5" apart

### Typography Rules
7. **Stick to system fonts:** Calibri/Arial only — python-pptx cannot embed fonts
8. **Maximum 5-6 font sizes** per deck (not 10+ like current state)
9. **Avoid Light/Thin weights:** Render poorly at small sizes, especially in PDF export
10. **Line spacing:** 1.2-1.5× for body text, 1.0-1.15× for titles

### Content Rules (McKinsey Pyramid Principle)
11. **Action titles, not topic titles:** "Sessions peaked in week 3 driven by email campaign" (good) vs "Sessions Over Time" (weak)
12. **Lead with the conclusion** then support with evidence
13. **Max 4 lines of text per paragraph on a slide** — if longer, split across slides
14. **Max 3-5 bullets per list** on any slide
15. **Max 5-7 KPIs per scorecard slide**

### Chart Rules
16. **DPI:** 300 for print-quality reports (our use case)
17. **Match chart background to slide background** — no jarring white boxes
18. **Remove top and right spines** — only left and bottom
19. **Chart titles as slide text boxes** (not in-chart) for font consistency
20. **9-10pt minimum for chart text** — smaller is unreadable

### Color Contrast Verification (WCAG AA)
| Combination | Ratio | Status |
|---|---|---|
| `#0F172A` on `#FFFFFF` | 15.4:1 | ✅ AAA |
| `#4338CA` on `#FFFFFF` | 6.5:1 | ✅ AA |
| `#64748B` on `#FFFFFF` | 4.6:1 | ✅ AA |
| `#059669` on `#FFFFFF` | 4.6:1 | ✅ AA |
| `#E11D48` on `#FFFFFF` | 4.4:1 | ⚠️ Borderline — use bold or bump to `#BE123C` (5.5:1) |
| `#F8FAFC` on `#0F172A` | 15.1:1 | ✅ AAA (dark template) |
| `#CBD5E1` on `#0F172A` | 9.8:1 | ✅ AAA (dark template body) |

### python-pptx Specific Constraints
- Cannot embed fonts — must use system-installed fonts
- Cannot insert images into table cells — use overlaid positioned shapes
- No gradient fill API — use pre-rendered gradient images if needed
- No animation/transition support (fine for reports)
- Chart support exists but limited in styling — render in matplotlib + embed as PNG
- Text box internal margins default to 0.1" — override via XML when needed for tight layouts

Sources:
- [McKinsey Presentation Structure - SlideModel](https://slidemodel.com/mckinsey-presentation-structure/)
- [Professional PowerPoint Design Guide 2026 - PrzntPerfect](https://www.przntperfect.com/post/professional-powerpoint)
- [60-30-10 Color Rule - Wix](https://www.wix.com/wixel/resources/60-30-10-color-rule)
- [WCAG Contrast Minimum - W3C](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- [python-pptx Documentation](https://python-pptx.readthedocs.io/en/latest/)
- [Font Size Guide for Presentations - Superchart](https://www.superchart.io/blog/presentation-font-size)
- [Data Visualization Best Practices - 24slides](https://24slides.com/presentbetter/presenting-data-in-powerpoint-in-visual-and-effective-ways)
