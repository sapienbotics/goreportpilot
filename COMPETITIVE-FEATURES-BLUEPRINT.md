# COMPETITIVE-FEATURES-BLUEPRINT

**Phase 0 output — discovery, verification, and design. No production code written.**

Context date: 2026-08-22
Author: Claude Code (Opus, Phase 0 discovery run)
Status: **Decisions recorded 2026-08-22 (see Section F). Phase 1 = D-0 + Track A, in progress.**

> **Scope locked for this cycle (~12 days, then stop for customer validation):**
> D-0 (2d) → Track A (6d) → Track C1 (3.5d) → Track E copy (0.5d).
> Deferred until agency feedback: C2, Stripe + remaining connectors, MCP server,
> YouTube Analytics. Not doing: Shopify, LinkedIn, GBP, integration-count parity.

---

## Executive summary (read this first)

Three findings change the plan materially:

1. **There is no integration abstraction seam.** Every data source is bespoke, and the
   per-source pull logic is *copy-pasted into two functions* in `routers/reports.py`.
   Adding a source today costs ~180 lines across two call sites plus five other files.
   Track B as written ("implement against the abstraction contract") has no contract to
   implement against. A ~2-day adapter refactor must land before Tracks A and B, or both
   tracks bake the duplication in permanently.

2. **The PPTX generator is index-and-token based, not layout-and-placeholder based.**
   It opens a fixed 19-slide `.pptx`, addresses slides by integer index, and does
   `{{token}}` string substitution inside pre-positioned shapes. It never touches
   `slide_layouts` or `placeholders`. Track C as specified ("map our 19 slide types onto
   their arbitrary layouts") is not a feature on top of this architecture — it is a
   rewrite of it. Section D-C proposes three scoped alternatives; the recommended MVP
   delivers most of the strategic value in ~8 days instead of ~4 weeks.

3. **Track D cannot use "API key per user."** Claude.ai's custom-connector UI accepts
   OAuth client credentials, not bearer tokens. A key-only MCP server would be
   installable from Cursor and the API but not from the surface agencies actually use.
   Conformant remote MCP as of the 2026-07-28 spec revision means being an OAuth 2.1
   resource server with RFC 9728 metadata. That is not a Sonnet-scale task.

The strategic thesis itself survives contact with the codebase. Universal CSV (Track A)
is genuinely unblocked and genuinely high-value. Agency template upload is genuinely
uncopiable — just not in the form the prompt assumes.

---

## A. Current integration architecture

### A.1 End-to-end trace: GA4 from OAuth to rendered slide

| Step | File | Symbol / line | What happens |
|---|---|---|---|
| 1. OAuth initiation | `frontend/src/app/dashboard/integrations/page.tsx` | `PLATFORMS[]` :33 | Static registry of 4 platforms. Stores `clientId` in `sessionStorage` under `ga4_connect_client_id`, redirects to backend authorize URL. |
| 2. Authorize + callback | `backend/routers/auth.py` | :1–526 | Google consent (`prompt=consent&access_type=offline`), code exchange. |
| 3. Callback landing | `frontend/src/app/api/auth/callback/google-analytics/route.ts` | — | Next.js route hands back to `/dashboard/integrations/google-callback`. |
| 4. Token storage | `backend/services/encryption.py` | `encrypt_token` :1–66 | AES-256-GCM. Written to `connections.access_token_encrypted` / `refresh_token_encrypted`. |
| 5. Connection row | `supabase/migrations/001_initial_schema.sql` | `connections` :60–79 | `platform`, `account_id`, both encrypted token columns, `token_expires_at`, `status`, `consecutive_failures`. |
| 6. Health gate | `backend/routers/reports.py` | :331–356 | Blocks generation if any connection is `broken` or `expiring_soon` (bypassed when `csv_sources` supplied). |
| 7. Connection lookup | `backend/routers/reports.py` | :363–374 | Hardcoded `.eq("platform", "ga4")` query, hardcoded column list. |
| 8. Token refresh | `backend/services/google_analytics.py` | `_get_valid_access_token` :53–90 | Refreshes 60s before expiry, writes the new token back to Supabase inline. |
| 9. API pull | `backend/services/google_analytics.py` | `pull_ga4_data` :252–341 | Six `runReport` calls via `asyncio.gather` (current, previous, daily, sources, pages, devices). |
| 10. Normalisation | `backend/services/google_analytics.py` | `_parse_ga4_responses` :127–245 | Hand-written mapping into a GA4-specific dict. |
| 11. Snapshot persist | `backend/services/snapshot_saver.py` | `save_snapshot` | Writes `data_snapshots` row keyed by `connection_id` + period. Non-fatal on failure. |
| 12. Assembly | `backend/routers/reports.py` | :581–599 | `raw_data["ga4"] = ga4_data` — flat namespace keyed by platform string. |
| 13. Narrative | `backend/services/ai_narrative.py` | `generate_narrative` :220; prompt build :296–432 | Reads `data["ga4"]["summary"]` by literal key. Section list assembled by `if data.get("<platform>")` checks at :270–281. |
| 14. Charts | `backend/services/chart_generator.py` | `generate_all_charts` :1261 | Dispatches to ~19 named generator functions, each reading its own platform key. |
| 15. Slide selection | `backend/services/slide_selector.py` | `SLIDE_POOL` :67, `select_slides` :112 | Predicate per slide, e.g. `_has_ga4` :46. |
| 16. Slide deletion | `backend/services/slide_selector.py` | `get_slides_to_delete` :172 | Returns `set(range(19)) - keep_indices`. |
| 17. Render | `backend/services/report_generator.py` | `generate_pptx_report` :1671 | Opens the template, substitutes tokens, swaps chart placeholders, deletes unselected slides, renumbers footers. |
| 18. PDF | `backend/services/report_generator.py` | `generate_pdf_report` :2138 | LibreOffice headless; ReportLab fallback :2255. |

**Adding one new source today touches:** `routers/reports.py` (×2 blocks),
`services/<new>.py`, `services/ai_narrative.py` (2 places), `services/chart_generator.py`,
`services/slide_selector.py` (predicate + `SLIDE_POOL` + `SLIDE_INDEX`),
`services/report_generator.py` (`_replace_charts` map), all six `.pptx` template files
(new slides), `frontend/.../integrations/page.tsx`, `services/goal_checker.py`
(`METRIC_REGISTRY`), and a migration to widen the platform CHECK.

### A.2 The abstraction seam — there isn't one

There is no base class, no `Protocol`, no registry. The four pull functions do not even
share a signature:

```python
# services/google_analytics.py:252  — async, needs supabase + connection_id to self-heal tokens
async def pull_ga4_data(access_token_encrypted, refresh_token_encrypted,
                        token_expires_at, property_id, period_start, period_end,
                        connection_id, supabase) -> dict

# services/meta_ads.py:20           — async, no refresh at all, takes currency
async def pull_meta_ads_data(account_id, access_token_encrypted,
                             period_start, period_end,
                             connection_id=None, currency="USD") -> dict

# services/google_ads.py:121        — SYNCHRONOUS, wrapped in asyncio.to_thread by the caller
def pull_google_ads_data(access_token_encrypted, refresh_token_encrypted,
                         customer_id, period_start, period_end, token_expires_at) -> dict

# services/search_console.py:143    — async, returns {} (not None) on failure
async def pull_search_console_data(access_token_encrypted, refresh_token_encrypted,
                                   site_url, period_start, period_end, token_expires_at) -> dict
```

Three different failure conventions (raise / return `{}` / return `None`), two different
concurrency models, three different credential-argument shapes, and token refresh
implemented independently in three files.

The caller compensates with ~90 lines of near-identical boilerplate per platform — and
that boilerplate exists **twice**:

- `_generate_report_internal` — `routers/reports.py:363–580`
- `regenerate_report` — `routers/reports.py:1490–1700`

The two copies have already drifted. `_generate_report_internal` accepts `csv_sources`
and honours the caller's `visual_template`; `regenerate_report` accepts no CSV and
hardcodes `"modern_clean"` (`reports.py:1747`). Any new source added without first
collapsing these will drift the same way.

> **This is the single most important finding in Phase 0.** Track B's premise — "implement
> against the abstraction contract defined in the blueprint" — requires that contract to be
> built first. It is specified in D-0 below.

### A.3 Slide-pool architecture

`SLIDE_INDEX` (`slide_selector.py:21`) is a literal dict mapping 19 slide IDs to integer
positions 0–18. Every one of the six `.pptx` files must contain exactly those 19 slides
in exactly that order. `TOTAL_TEMPLATE_SLIDES = 19` is hardcoded at :43.

Selection is a list of `(slide_id, predicate, [detail_levels])` tuples (:67–110). CSV is
the one dynamic case: `select_slides` emits one pseudo-ID per source
(`csv_data_<source_name>`, :137–140), and `generate_pptx_report` duplicates template
slide 13 N times via `_duplicate_slide` (`report_generator.py:1492`), populating each
with `_populate_csv_slide` (:1518).

**Registering a new source's slides means editing `SLIDE_INDEX`, shifting every index
above the insertion point, and rebuilding all six .pptx files.** Appending at index 19+
is safe; inserting in the middle is not.

The CSV duplication mechanism is the escape hatch: a new source can reuse the `csv_data`
slide with zero template edits. This is what makes Track A cheap and Track B moderate.

### A.4 PPTX generation layer — coupling assessment

```python
# services/report_generator.py:209
VISUAL_TEMPLATES = {"modern_clean": <path>, "dark_executive": <path>, ...}
# :1709
prs = Presentation(template_path)
```

Then:

- **Text** — `_replace_placeholders_in_slide` (:574) walks `slide.shapes`, finds
  `{{token}}` substrings in paragraph runs, rewrites run 0 and blanks the rest.
- **Charts** — `_replace_charts` (:639) finds *text boxes* whose text is `{{chart_sessions}}`
  etc., deletes the shape, and inserts a PNG at the shape's saved position. The mapping is a
  literal dict of 17 token→chart-key pairs (:651–678), plus hardcoded dual-chart pairing
  and pie-vs-bar width rules.
- **Geometry** — `services/theme_layout.py:62` `THEME_LAYOUT` is a per-theme dict of
  absolute inch coordinates (cover header band, logo boxes, accent bars). `VALID_THEMES`
  is derived from its keys (:216).
- **Cover** — `services/cover_customization.py` is documented as "the SOLE writer of cover
  text + colour overrides"; it *draws new text boxes at the theme's known coordinates*
  because the cover slide has no placeholder shapes at all.
- **Chart colours** — `chart_generator.py:58` `CHART_THEMES` (3 themes) and :104
  `_VISUAL_TO_THEME` map each visual template to `light` / `dark` / `vibrant`.

**Coupling verdict: very tight.** The generator does not use PowerPoint's layout or
placeholder model anywhere. It assumes (a) exactly 19 slides in a known order, (b) shapes
pre-positioned by us, (c) our `{{token}}` vocabulary present in the file, (d) theme
geometry pre-registered in a Python dict. An arbitrary agency deck satisfies none of these.

### A.5 CSV path as it exists today

`services/csv_parser.py:405` `parse_kpi_csv(file_content, filename) -> dict`.

It is **not** a general CSV importer. It accepts exactly one shape — a long-format KPI list:

```
metric_name, current_value, previous_value, unit
```

Alias tolerance is generous (`_COL_ALIASES`, :28 — 12 aliases for `metric_name`, 13 for
`current_value`). Number parsing is genuinely good: K/M/B suffixes, European decimals,
currency symbols, space thousands separators (`_parse_number` :202). Encoding detection is
UTF-8-BOM → UTF-8 → chardet → Latin-1 (:147). Binary rejection is explicit and actionable
(:78–127) — including a friendly "this is an .xlsx, export as CSV" message, because **xlsx
is not supported**.

The "5 templates" (`routers/csv_upload.py:23`) — `linkedin_ads`, `tiktok_ads`, `mailchimp`,
`shopify`, `generic` — are **not parsers**. They are five downloadable sample CSVs
(`csv_parser.py:594` `_TEMPLATES`) with identical column structure and different example
rows. There is no per-template parsing logic whatsoever.

Hard limits: `MAX_METRICS = 20` (:26), `MAX_FILE_SIZE = 1 MB` (`csv_upload.py:24`),
`.csv` extension only (:57), six KPIs rendered per slide (`report_generator.py:1537`).

**What it would take to make it schema-free:** the parser is not the obstacle — its number
and encoding handling should be kept verbatim. The obstacles are (a) the fixed 4-column
contract, (b) no wide→long reshaping, (c) no date/time-series concept at all, (d) no xlsx.
Track A is therefore *additive*: a new mapping layer that produces the existing
`{"source_name", "metrics": [...]}` structure, with the current parser retained as the
fast path.

---

## B. Canonical internal data schema

**There is no canonical schema.** `raw_data` is a flat dict keyed by platform string, and
each platform's sub-dict has an independently invented shape. Documenting what actually
exists:

```python
raw_data = {
    "client_name": str,
    "period_start": "YYYY-MM-DD",
    "period_end":   "YYYY-MM-DD",

    "ga4": {                                    # google_analytics.py:236-245
        "summary": {
            "sessions": int, "sessions_change": float|None,
            "users": int, "users_change": float|None,
            "pageviews": int,
            "conversions": int, "conversions_change": float|None,
            "bounce_rate": float, "avg_session_duration": float,
        },
        "daily":           [{"date": "YYYY-MM-DD", "sessions": int, "users": int}],
        "traffic_sources": {label: sessions},   # NB: a dict, not a list
        "top_pages":       [{"page": str, "sessions": int, "pageviews": int}],
        "device_breakdown":[{"device": str, "sessions": int, "users": int, "bounce_rate": float}],
    },

    "meta_ads": {                               # meta_ads.py:205-242
        "platform": "meta_ads",                 # only meta carries this
        "currency": "USD",                      # only meta carries this
        "period":   {"start": str, "end": str}, # only meta carries this
        "summary": {
            "spend": float, "prev_spend": float, "spend_change": float|None,
            "impressions": int, "prev_impressions": int,
            "clicks": int, "prev_clicks": int,
            "ctr": float, "prev_ctr": float, "cpc": float, "prev_cpc": float, "cpm": float,
            "conversions": int, "prev_conversions": int, "conversions_change": float|None,
            "cost_per_conversion": float, "prev_cost_per_conversion": float,
            "revenue": float, "roas": float, "prev_roas": float,
        },
        "daily":     [{"date","spend","conversions","impressions","clicks"}],
        "campaigns": [{"name","spend","impressions","clicks","conversions","cpc","roas"}],
    },

    "google_ads":     { "summary": {...}, "daily": [...], "campaigns": [...], "search_terms": [...] },
    "search_console": { "summary": {...}, "daily": [...], "top_queries": [...] },

    "csv_sources": [                            # csv_parser.py:405 contract
        {"source_name": str,
         "metrics": [{"name": str, "current_value": float,
                      "previous_value": float|None,
                      "unit": "currency"|"percent"|"number",
                      "change": float|None}]}
    ],
}
```

### Observed inconsistencies

| Issue | Evidence |
|---|---|
| Change fields: GA4 uses `<m>_change` only; Meta uses both `prev_<m>` and `<m>_change` | `google_analytics.py:157` vs `meta_ads.py:214` |
| `traffic_sources` is `dict[str,int]`; every other breakdown is `list[dict]` | `google_analytics.py:208` |
| Only Meta carries `platform`, `currency`, `period` | `meta_ads.py:206–208` |
| Currency is re-stamped by the caller after the pull | `reports.py:591` |
| Failure signalling differs per source (raise / `{}` / `None`) | see A.2 |
| CSV metrics have no time dimension at all | `csv_parser.py:405` |

### Proposed canonical envelope (target for D-0)

Additive; existing keys stay so nothing breaks:

```python
{
  "source_id":   "ga4" | "meta_ads" | "stripe" | "csv:<slug>",
  "source_label":"Google Analytics",     # display name, translatable
  "kind":        "analytics"|"ads"|"seo"|"ecommerce"|"email"|"calls"|"custom",
  "currency":    "USD",
  "period":      {"start": "...", "end": "...", "prev_start": "...", "prev_end": "..."},
  "summary":     {metric_key: {"current": float, "previous": float|None,
                               "change_pct": float|None, "unit": str,
                               "direction": "higher_is_better"|"lower_is_better"}},
  "series":      {"daily": [{"date": "...", metric_key: float, ...}]},
  "breakdowns":  {"campaigns": [...], "top_pages": [...], ...},
  "warnings":    [str],
}
```

Rationale for the nested `summary` value objects: it collapses the `prev_x` / `x_change`
inconsistency, makes `METRIC_REGISTRY` (`goal_checker.py:40`) derivable rather than
hand-maintained, and gives Track A's mapped CSV data a first-class place to live without a
synthetic identity hack.

---

## C. External access verification (August 2026)

Verified against live documentation on 2026-08-22. **GREEN** = ship now, no external gate.
**AMBER** = gated but achievable solo; timeline stated. **RED** = not viable pre-revenue.

| Source | Auth | Gate? | Timeline | Verdict |
|---|---|---|---|---|
| **Stripe** | User-generated **restricted API key** (read-only), pasted into our UI | **None.** Stripe's review requirement applies only to publishing in the Stripe App Marketplace, not to a customer pasting their own RAK into a third-party tool | 0 days | 🟢 **GREEN** |
| **Klaviyo** | Private API key from user's account | None. OAuth is required only for Klaviyo's App Marketplace listing | 0 days | 🟢 **GREEN** |
| **WooCommerce** | Consumer key/secret, generated at *WooCommerce → Settings → Advanced → REST API* with **Read** permission | None — entirely merchant-side | 0 days | 🟢 **GREEN** |
| **CallRail** | API key, `Authorization: Token token="…"`. Keys are user-scoped, never expire, no OAuth flow exists | None | 0 days | 🟢 **GREEN** |
| **Plausible** | Bearer API key from account settings. 600 req/hour default | None | 0 days | 🟢 **GREEN** |
| **Matomo** | `token_auth` static token (OAuth 2.0 also offered) | None | 0 days | 🟢 **GREEN** |
| **Fathom** | API token — docs not confirmed in this pass | Unknown | — | ⚪ **UNVERIFIED** — defer, tiny market |
| **Mailchimp** | OAuth 2.0. App registration is **self-serve**: *Account → Extras → API keys → Register an App* returns client_id/secret immediately | None for function. Partner Program / Marketplace listing is optional and separate | 0 days | 🟢 **GREEN** |
| **Shopify** | ⚠️ **Changed in 2026.** Shopify docs now state plainly: *"You can no longer create new admin-created custom apps. Existing apps are unaffected and continue to work."* New merchant-side apps go through the Dev Dashboard / CLI, whose `client_credentials` tokens are short-lived (~24h) rather than static `shpat_` | Merchant must use Dev Dashboard, or we publish a public app with custom distribution | 2–5 days build; no Shopify approval for custom distribution | 🟡 **AMBER** |
| **YouTube Analytics v2** (`yt-analytics.readonly`) | Google OAuth, **sensitive** scope | ⚠️ **Adding it re-opens verification.** Google: *"your app needs to be verified and approved for these scopes before your app can start to call these APIs"*, and *"we strongly recommend you get your app verified and approved for the new scopes before making code changes."* Using it early triggers the unverified-app screen and a **100-user cap**. No new security assessment is required if one is already complete | Sensitive-scope review documented as **3–5 business days** typically (community reports up to ~10) | 🟡 **AMBER** — *not* the 6-week task feared, **but see F-1**: submitting a consent-screen change while our existing verification is still in flight risks resetting that review |
| **Google Business Profile Performance API** | Google OAuth **plus a separate access-request form**, then a separate quota-increase request | Form gate still mandatory in 2026; approval is discretionary, requires a verified GBP active 60+ days, starts on a small quota | Weeks, unpredictable | 🔴 **RED** for this cycle |
| **Microsoft Advertising** | Developer token + Entra ID app + OAuth | Production developer token needs Microsoft approval — *"up to five business days"* for agency / tool-provider requests | 5 business days, **plus** the SOAP→REST migration: v13 SOAP feature-freezes **2026-10-01**, decommissioned **2027-01-31**, so we would have to build REST-first | 🟡 **AMBER** — defer past this cycle |
| **LinkedIn Ads** | — | Excluded by strategy | — | 🔴 **RED** (unchanged) |

**GREEN set for Track B: Stripe, Klaviyo, Mailchimp, WooCommerce, CallRail, Plausible, Matomo.**
Shopify is a near-miss that needs a design decision (F-3).

Sources:
[Google — changes to an approved app](https://support.google.com/cloud/answer/13464018?hl=en) ·
[Google — sensitive scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification) ·
[Stripe — restricted API keys](https://docs.stripe.com/keys/restricted-api-keys) ·
[Klaviyo — authenticate API requests](https://developers.klaviyo.com/en/docs/authenticate_) ·
[Mailchimp — OAuth 2 guide](https://mailchimp.com/developer/marketing/guides/access-user-data-oauth-2/) ·
[Shopify — admin-created custom app tokens](https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/generate-app-access-tokens-admin) ·
[WooCommerce — REST API authentication](https://developer.woocommerce.com/docs/apis/rest-api/authentication/) ·
[CallRail API v3](https://apidocs.callrail.com/) ·
[Plausible Stats API](https://plausible.io/docs/stats-api) ·
[Matomo — API token authentication](https://matomo.org/faq/general/faq_114/) ·
[Google Business Profile — prerequisites](https://developers.google.com/my-business/content/prereqs) ·
[Microsoft Advertising — get started](https://learn.microsoft.com/en-us/advertising/guides/get-started?view=bingads-13) ·
[MCP — authorization spec](https://modelcontextprotocol.io/specification/draft/basic/authorization) ·
[Anthropic — custom connectors via remote MCP](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp) ·
[Meta — Ads MCP Server overview](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/ads-mcp-server-overview)

---

## D. Per-track technical design

### D-0 — PREREQUISITE: the source-adapter seam (~2 days)

Not in the original prompt. Tracks A and B both depend on it, and skipping it is the
single largest source of wasted work in this roadmap.

**1. Uniform adapter protocol** — `backend/services/sources/base.py`:

```python
class SourceAdapter(Protocol):
    source_id: str                      # "ga4", "stripe", "csv"
    kind: str                           # "analytics" | "ads" | "ecommerce" | ...
    credential_type: Literal["oauth", "api_key", "key_pair", "none"]
    required_fields: list[CredentialField]   # drives the generic credential UI
    async def pull(self, ctx: PullContext) -> SourceResult: ...
    async def probe(self, ctx: PullContext) -> HealthResult: ...
```

`PullContext` carries the decrypted credential bundle, `period_start/end`, `currency`,
`connection_id`, and the supabase handle. `SourceResult` is the canonical envelope from
Section B. **One failure convention: raise `SourceError`.** Never return `{}` / `None`.

**2. Registry** — `backend/services/sources/__init__.py` maps `source_id → adapter`.
Existing modules become thin adapter wrappers; **`pull_ga4_data` et al. keep their current
signatures and bodies** so nothing regresses.

**3. Collapse the duplication.** Replace both hand-written pull blocks
(`reports.py:363–580` and `:1490–1700`) with one loop over active connections that
dispatches through the registry and does snapshot persistence once. This is the change
that makes every subsequent integration cheap. It also fixes the drift bug where
`regenerate_report` ignores `visual_template` and drops CSV sources (see G-7).

**4. Generic OAuth token refresh** — lift `_get_valid_access_token`
(`google_analytics.py:53`) into `services/sources/oauth_refresh.py`; Google Ads and Search
Console currently reimplement it.

**Risk:** this touches the highest-traffic code path in production. Mitigation — ship it
in three commits (add adapters alongside; switch `_generate_report_internal`; switch
`regenerate_report`), each independently revertible, with a golden-output check that a
GA4+Meta report produces identical slide selection before and after.

---

### D-A — Universal CSV/XLSX ingestion with AI column mapping

**Strategic value: highest. Confidence: high. External gates: none. Estimate: 5–6 days.**

#### Pipeline

```
upload → format detect → sheet/table extraction → profiling → AI mapping proposal
       → user confirmation UI → normalisation → canonical envelope → existing pipeline
       → save as reusable mapping template
```

**Format handling.** Add `openpyxl` (not currently a dependency — only `chardet`, no
`pandas`). Deliberately avoid `pandas`: a large wheel to do work the existing hand-rolled
parser already does better for this data. Keep `csv_parser._detect_encoding`,
`_detect_delimiter`, `_parse_number` verbatim — they are the strongest part of the current
code. Replace the xlsx *rejection* at `csv_parser.py:78` with xlsx *handling*.

**Sampling for the LLM** (answers "without blowing context"): never send the file. Send a
**column profile**, which is bounded regardless of file size:

- For each column: header text, position, non-null count, distinct count, inferred
  primitive type, min/max, and **8 sample values chosen as first-2 + last-2 + 4 stratified
  by row position** (catches trailing totals rows and mid-file format changes that
  head-N sampling misses).
- Plus: sheet names, detected header row index, detected totals-row index, row count.

Cost bound: ~120 tokens/column × ≤60 columns ≈ 7k tokens whether the file has 1 row or
500,000.

**Mapping prompt output contract** — strict JSON, validated with Pydantic, one retry on
schema violation:

```json
{
  "table_shape": "long_kpi | wide_timeseries | wide_entity | unknown",
  "source_label": "LinkedIn Ads",
  "date_column": {"name": "Day", "format": "%Y-%m-%d", "confidence": 0.95},
  "entity_column": {"name": "Campaign name", "confidence": 0.9},
  "columns": [
    {"source_column": "Impressions", "target_metric": "impressions",
     "unit": "number", "direction": "higher_is_better",
     "confidence": 0.97, "reasoning": "exact canonical name match"}
  ],
  "ignored_columns": [{"name": "Currency code", "reason": "constant metadata"}],
  "ambiguities": [{"column": "Cost", "candidates": ["spend", "revenue"],
                   "question": "Is 'Cost' money you spent or money you earned?"}]
}
```

The LLM classifies and names; it **never sees or transforms the values**. All parsing,
locale handling, and arithmetic stay in deterministic Python. This is the design decision
that keeps the feature trustworthy — an AI that hallucinated a number into a client report
is an unrecoverable trust failure.

**Detection details.**
- *Dates* — try a ranked format list against the whole column with a ≥95% success threshold
  before accepting; DMY/MDY ambiguity resolved by scanning for any day > 12; fall back to
  asking the user rather than guessing.
- *Currency / locale* — extend `_parse_number` (already handles `1.234,56` and K/M/B) with
  per-column consistency voting: decide the decimal mark once for the column, not per cell.
- *Percent* — detect from `%` in values or header; store the number, record `unit`.
- *Structural noise* — blank rows; merged headers (empty header cells forward-filled);
  trailing totals (last row where an entity column is blank or "Total" and numerics equal
  the column sum within 0.5%); multi-sheet xlsx (profile every sheet, propose the largest
  rectangular table, let the user switch sheets).

**Confirmation UI** — new `frontend/src/components/clients/CSVMappingDialog.tsx`.
A table of *your column → our field*, each row showing the AI's confidence as
High / Medium / Low, plus an editable target dropdown. Rules:
- **Any mapping below 0.80 confidence starts unconfirmed and the Confirm button stays
  disabled until the user resolves it.** ("Never silently accept a low-confidence
  mapping.")
- `ambiguities[]` render as inline questions above the table.
- Live preview of the first 5 normalised rows, so the user sees `₹1.234,56 → 1234.56`
  before committing.

**Failure UX** — the parser must never emit a generic error. Three tiers:
1. File unreadable → format-specific message (existing behaviour, keep it).
2. Readable but no numeric columns → "We found 6 columns but none contained numbers we
   could read. Here's what we saw in each" + the profile table.
3. Readable, numerics found, mapping ambiguous → **open the manual mapping UI pre-filled**,
   never a dead end. A user who maps by hand still gets a report.

**Persistence** — `csv_mappings` table (migration SQL delivered in Phase 1, not run),
scoped `(user_id, client_id, name)`, storing the confirmed mapping plus a
`column_fingerprint` (sorted, normalised header hash). Next upload: fingerprint match →
one-click re-apply, no LLM call. This keeps the "next month is one click" promise and caps
OpenAI cost at roughly one call per new export format per client.

**The 5 existing templates become seeded rows in `csv_mappings`** with `is_system = true`,
not a parallel code path — as the Phase 1 prompt requires.

**Flow into the pipeline** — mapped output emits `source_id = "csv:<slug>"` into the
canonical envelope from Section B. Rendering needs **no new slide types**: the `csv_data`
slide (index 13) is already duplicated per source (`report_generator.py:1950–1975`), and
`generate_csv_comparison_chart` (`chart_generator.py:1145`) already renders
current-vs-previous bars.

**New capability worth calling out:** because mapped uploads can carry a date column, a CSV
source can populate a **time-series** chart for the first time — the current KPI-list format
cannot. That is a visible quality jump for LinkedIn / TikTok reporting.

**Raise these limits** (all currently too low for real exports): `MAX_METRICS` 20 → 200
mapped metrics (still 6 per slide), `MAX_FILE_SIZE` 1 MB → 10 MB, accepted extensions
`.csv` → `.csv` / `.tsv` / `.xlsx`.

**Harder than it looks:** date-format disambiguation across locales, and multi-sheet
workbooks where the "real" table is not the largest one. Both are handled by falling back
to the user rather than guessing.

---

### D-B — Fast ungated integrations

**Strategic value: medium (catch-up). Confidence: high. Estimate: 2 days for the credential
layer + ~0.75 day per source ≈ 6–7 days for all seven.** *Assumes D-0 has landed; without
it, roughly double.*

**Credential UX (build once).** Today `PLATFORMS[]`
(`frontend/.../integrations/page.tsx:33`) assumes every source is OAuth — each entry
requires an `oauthType`. Extend the entry with
`credentialType: 'oauth' | 'api_key' | 'key_pair'` and a `fields[]` descriptor served from
the adapter's `required_fields`, then render a generic modal (masked inputs,
paste-friendly, per-field help text and a deep link to where in *their* dashboard the key
lives). On submit: `POST /api/connections` → encrypt via existing `encryption.py` →
**immediately call `adapter.probe()`** and refuse to save a credential that doesn't
authenticate. Storage reuses `connections.access_token_encrypted` for single secrets; key
pairs go in a new `credentials_encrypted JSONB` column.

**Migration:** widen the `connections_platform_check` constraint (migration 009 pattern) to
allow the new `source_id` values.

| Source | Metrics contributed | Slides |
|---|---|---|
| Stripe | revenue, transactions, AOV, refunds, MRR, new vs returning customers, top products | New `ecommerce_overview` slide (index 19) |
| Shopify / WooCommerce | orders, revenue, AOV, conversion rate, top products | Same `ecommerce_overview` |
| Klaviyo / Mailchimp | sends, open rate, click rate, unsubscribes, revenue-per-recipient (Klaviyo) | New `email_overview` slide (index 20) |
| CallRail | total calls, first-time callers, answered rate, calls by source | Reuse `csv_data` slide (index 13) |
| Plausible / Matomo | visitors, pageviews, bounce rate, top sources, top pages | Reuse the **GA4 slides** — the metric vocabulary matches |

**Two new slide types (19, 20) appended after 18** — never inserted, so `SLIDE_INDEX` stays
stable. All six `.pptx` files need those two slides added; `backend/scripts/` already has
template-editing precedent (`audit_templates.py`, `fix_csv_slide_layout.py`).

Per source also: 2 chart functions, `_replace_charts` token entries, a `SLIDE_POOL`
predicate, `METRIC_REGISTRY` entries so Goals & Alerts covers the new metrics, an
`ai_narrative` section prompt, and plan gating.

**Stripe caveat worth stating:** revenue attribution is the differentiator here, but Stripe
knows revenue, not *which channel drove it*. Cross-source attribution (Meta spend → Stripe
revenue → blended ROAS) is a further feature, not a freebie. Recommend shipping the revenue
slide first and treating blended ROAS as a separate item.

**Recommended order** (highest value first, cheapest tie-break): Stripe → Klaviyo →
WooCommerce → Mailchimp → CallRail → Plausible/Matomo → Shopify last (pending F-3).

---

### D-C — Agency PPTX template upload

**Strategic value: highest. Confidence: LOW as specified. This section is the pushback.**

#### The problem with the spec as written

The prompt asks to "enumerate slide layouts and placeholders from an arbitrary uploaded
template" and "map our 19 slide types onto their arbitrary layouts."

`python-pptx` **can** do the enumeration — `prs.slide_layouts`, `layout.placeholders`,
`placeholder_format.type/idx` are all reliable API. That is not the blocker.

The blocker is that **our generator does not consume layouts or placeholders.** It:
- addresses slides by integer index into a fixed 19-slide deck (`SLIDE_INDEX`);
- substitutes `{{token}}` strings inside shapes we authored;
- positions charts at coordinates read from *our* placeholder text boxes;
- draws the cover from a per-theme table of absolute inch coordinates
  (`theme_layout.py:62`), because our cover has no placeholders at all.

An arbitrary agency deck has none of our tokens, no guaranteed slide count or order, and
unknown geometry. Building `SlideLayout.placeholders`-driven rendering means **replacing
the rendering engine** — every one of the ~19 chart placements, the KPI scorecard, the
sparkline embedding (`_embed_kpi_sparklines`, :426), the logo boxes, the cover module, and
the footer renumbering. Honest estimate for the general case: **3–4 weeks, with high risk of
visual regressions across all six existing templates.** I do not recommend it now.

Additional real-world hazards for the general case: SmartArt and charts stored as custom
XML that python-pptx exposes as opaque blobs; `.potx` files whose layouts are unused and
therefore unstyled; decks whose "design" lives in the slide master's background picture
rather than in the theme; layouts with duplicate placeholder `idx` values; and
16:9-vs-4:3 mismatches against our 13.33″ assumption.

#### Three scoped options

**Option C1 — "Brand transplant" (recommended MVP). ~3.5 days. High confidence.**
Agency uploads their deck. We **do not render into it.** We extract from it and re-skin our
own 19-slide template:
- `prs.slide_master.theme` → the 12 theme colours (`dk1/lt1/dk2/lt2/accent1..6`) and the
  major / minor font faces. Both are stable, well-specified OOXML that python-pptx reads
  reliably.
- Apply those colours as a new dynamic entry in `CHART_THEMES` (`chart_generator.py:58`) so
  **matplotlib charts match the deck** — this is the specific requirement in the Phase 3
  prompt, and it is fully achievable in this option.
- Apply the same palette + fonts to our template at render time, plus their logo.
- Preview against dummy data using the existing `demo_data.py`.

What the agency gets: reports in *their* colours and *their* typeface, charts included.
What they don't get: their exact slide layouts.

> **CORRECTED 2026-08-22 (Saurabh).** My original "roughly 70% of the perceived value"
> claim was wrong. GoReportPilot **already ships white-label** — agency logo, brand colour,
> custom footer, per-client logo. C1 adds font extraction, fuller theme-colour extraction,
> and chart colour matching: **polish on an existing feature, not a new one.** Competitors
> now give white-label away on every tier, so C1 is **parity work, not differentiation**.
>
> **C2 is the moat.** Build C1 because it is cheap and because theme extraction is a hard
> technical prerequisite for C2's chart theming — but do not treat C1 as a substitute for
> C2, and **do not lead marketing with C1**.

Zero risk to the existing six templates either way.

**Option C2 — "Certified template" (the real moat). ~4.5 days on top of C1. Medium-high
confidence.**
We publish a downloadable **starter template**: our 19 slides carrying our `{{token}}`
vocabulary, structurally minimal. The agency restyles it in PowerPoint — their fonts,
colours, backgrounds, logo, chrome — keeping the tokens and slide order. They upload it
back.

On upload we **validate hard and specifically**:
- exactly 19 slides in `SLIDE_INDEX` order (identified by token fingerprint, not position,
  so we can report *which* slide is misplaced);
- every required token present on its expected slide — the error names the missing token and
  the slide: *"Slide 8 (Meta Ads Overview) is missing `{{chart_spend}}` — the chart has
  nowhere to go. Re-add the placeholder text box."*;
- 13.33″ × 7.5″ slide size;
- every chart placeholder is a text box (not a picture or graphic frame).

This is the "constrained version" the prompt anticipates, and it is genuinely uncopiable —
it makes GoReportPilot render *their deck*, with no engine rewrite, because the agency
supplies the geometry by moving our tokens.

**Option C3 — arbitrary template, layout-mapped. 3–4 weeks. Low confidence. Not now.**

#### Recommendation

**Ship C1 first, then C2.** Together ~8 days, both fully reversible, neither touches the
existing six templates. Market both under one name ("Bring your own deck") — but the
marketing weight belongs on **C2**; C1 is the zero-effort on-ramp, not the story.

**Decided:** C1 ships this cycle. **C2 is deferred until agency feedback**, on the reasoning
that building C2, Stripe, and MCP together with zero customer signal risks three bets at
once. C2 remains the highest-value item on the deferred list and should be first out of the
gate in block two unless feedback says otherwise.

#### Cross-cutting requirements (apply to C1 and C2)

- **Fallback:** if a required layout/token is missing at *generation* time, fall back to
  `modern_clean` for that slide and attach a warning to the report record. Never fail the
  whole report. Under C2 this should be near-impossible because upload validation is
  strict — the fallback is the safety net for templates that pass validation and are later
  edited in storage.
- **Slide-pool preservation:** unchanged. Deletion still runs on indices, and under C2 the
  uploaded deck is index-compatible by construction. No blank slides, ever.
- **Plan gating:** Agency tier only. `plans.py` needs a new `features.custom_template: bool`
  — `false` on starter/pro, `true` on agency. Note this would be the first feature *not*
  included in the trial; that is a deliberate positioning choice worth confirming (F-5).
- **Adversarial upload safety** — this is user-supplied binary parsed server-side, so: hard
  20 MB cap before any parsing; verify the `PK\x03\x04` header and open as a zip with a
  **member-count cap (≤ 2000) and uncompressed-size cap (≤ 200 MB)** to stop zip bombs;
  reject any member path containing `..` or an absolute path (zip-slip); parse in a
  subprocess with a timeout so a malformed part cannot hang a worker; **strip all embedded
  media, OLE objects, and external relationships** before storing; never render
  agency-supplied XML into any HTML surface. Store in Supabase Storage under a **private**
  bucket keyed by `user_id`, not the public `logos` bucket.

---

### D-D — MCP server

**Strategic value: medium. Confidence: medium. Estimate: 5–7 days — not a Sonnet-scale task
as scoped. Recommend deferring past this cycle (see E).**

#### Verified spec position (2026-08-22)

The current MCP spec revision is **2026-07-28**. Authorization is *optional*, but for HTTP
transports the spec says implementations **SHOULD** conform, and conformance means: the MCP
server is an **OAuth 2.1 resource server**; it **MUST** implement **RFC 9728 Protected
Resource Metadata**; clients **MUST** send **RFC 8707 resource indicators**; PKCE
throughout; **Dynamic Client Registration is now deprecated** in favour of **OAuth Client ID
Metadata Documents**. Transport is **Streamable HTTP** (single endpoint, POST + optional SSE
upgrade) — SSE-only is legacy.

**The decisive constraint:** Anthropic's custom-connector UI takes OAuth client id/secret
(or CIMD/DCR); there is a standing issue that it offers **no way to set a bearer token or
custom header**. So the prompt's "API key per user" option produces a server that Cursor and
the Messages API can use but that **agencies cannot install from Claude.ai** — which is the
entire point of the feature.

#### Recommended design

- **Auth: OAuth 2.1.** Cheapest conformant path is to front Supabase Auth: implement
  `/.well-known/oauth-protected-resource` (RFC 9728) and
  `/.well-known/oauth-authorization-server` (RFC 8414) on the FastAPI app, an
  `/oauth/authorize` that delegates login to the existing Supabase session, and an
  `/oauth/token` issuing short-lived JWTs audience-bound to the MCP canonical URI. Support
  CIMD; keep DCR as a fallback for older clients. **Also** accept a static
  `Authorization: Bearer grp_sk_…` API key for Cursor/CLI users — the spec permits it and it
  costs little once OAuth exists. Do not build key-only.
- **Transport:** Streamable HTTP at `POST /mcp`, mounted on the existing FastAPI app
  (`main.py:158–179` pattern) so it inherits CORS, `slowapi` rate limiting, and deploys with
  the Railway container. No separate service.
- **Tools:**

  | Tool | Notes |
  |---|---|
  | `list_clients` | id, name, connected sources, last report date |
  | `get_client_connections` | health status per source |
  | `get_metrics` | `client_id`, `period_start/end`, optional `sources[]` → canonical envelope. **Highest-value tool** — lets Claude analyse without generating anything |
  | `compare_periods` | period-over-period deltas from `data_snapshots` |
  | `generate_report` | async; returns `report_id` immediately |
  | `get_report_status` | `queued / generating / ready / failed` |
  | `list_reports` / `get_report` | metadata + narrative sections |
  | `get_report_download_url` | signed URL, PPTX or PDF |
  | `create_share_link` | reuses `routers/shared.py` |
  | `list_goals` / `get_goal_status` | surfaces Goals & Alerts (Track E synergy) |

  Deliberately **excluded from v1:** delete, send-to-client, and billing tools. An agent
  emailing a client report is not a mistake we want to be able to make.
- **Plan enforcement:** every tool resolves `user_id` from the token and calls the same
  `middleware/plan_enforcement.py` helpers the REST API uses. `generate_report` counts
  against the same trial/report limits (`reports.py:277–288`). Reuse, do not fork.
- **Rate limiting:** `slowapi` on `/mcp`, tier-scaled, plus a per-user daily tool-call budget
  — agent loops burn calls far faster than humans.
- **Discovery / install:** a Connections-page card showing the server URL with a copy button
  and a two-line "add this in Claude → Settings → Connectors" walkthrough, plus a docs page.

#### Honest positioning

The competitive claim that "agencies can now self-serve much of what we sell" is true for
*querying*. Meta's own MCP (open beta since 2026-04-29, `mcp.facebook.com/ads`, 29 tools,
Business OAuth, **no App Review**) already lets an agency ask Claude about their ad
performance. What it cannot do is produce a branded, editable, client-ready deck. Our MCP
server's differentiated tool is therefore `generate_report`, not `get_metrics`. Positioned
that way, MCP is a distribution channel for the moat rather than a defence of the commodity
layer — which is also why it can wait one cycle.

---

### D-E — Goals & Alerts marketing surface

**Estimate: 0.5 day. Copy only. Verified built and working.**

`goals` table (migration 018), `routers/goals.py` (5 endpoints + metric catalog),
`services/goal_checker.py` with a 15-metric `METRIC_REGISTRY` (:40–61), status thresholds
(on_track ≥100%, at_risk ≥80%, missed below), idempotent alert dispatch via `alerts_sent`
keys, and per-client goal limits already in `plans.py` (`goal_limit`: starter 1, pro 3,
agency 999, trial 3).

Nothing to build. Landing / pricing / features copy only, in Phase 5.

---

## E. Recommended build order

Ranked by (strategic value × confidence) ÷ effort, gated items off the critical path.

| # | Item | Days | Value | Confidence | Gate |
|---|---|---|---|---|---|
| 0 | **D-0 adapter seam + collapse reports.py duplication** | 2 | Enabling | High | None |
| 1 | **Track A — universal CSV/XLSX** | 5–6 | Highest | High | None |
| 2 | **Track E — Goals & Alerts copy** | 0.5 | Medium | Certain | None |
| 3 | **Track C1 — brand transplant** | 3.5 | High | High | None |
| 4 | **Track B — Stripe, Klaviyo, WooCommerce** (credential layer + 3 sources) | 4 | Medium-high | High | None |
| 5 | **Track C2 — certified template** | 4.5 | Highest | Medium-high | None |
| 6 | **Track B cont. — Mailchimp, CallRail, Plausible/Matomo** | 2.5 | Medium | High | None |
| 7 | **Track D — MCP server** | 5–7 | Medium | Medium | None, but heavy |
| — | Track E full marketing surface (Phase 5) | 1 | High | Certain | Must follow shipping |
| — | YouTube Analytics | 1 build + 3–5 business days review | Medium | Medium | **F-1 decision** |
| — | Shopify | 2–5 | Medium | Medium | **F-3 decision** |
| — | Microsoft Ads, GBP | — | Low now | Low | Deferred |

**Total for items 0–7: ~28 working days.** The prompt's "~4 weeks" is achievable only if
Track C is scoped to C1+C2 and Track D slips — which is exactly the recommendation.

### Dependencies

- **A and B both depend on D-0.** Building either first means writing per-source boilerplate
  that D-0 then deletes.
- **C2 depends on C1** (theme extraction is reused for chart colours).
- **D depends on the canonical envelope from D-0** — `get_metrics` should return the
  canonical shape, not four inconsistent per-platform dicts.
- **Phase 5 copy depends on 1–7 actually shipping.** Do not write the copy first.

### Wasted-work warnings

1. **Any Track B integration written before D-0** duplicates ~180 lines that D-0 removes.
2. **Any Track A output written against the current `raw_data` shape** rather than the
   canonical envelope gets rewritten when D-0's schema lands. Land D-0's *schema* even if
   the full refactor is staged.
3. **Any C3-style layout-mapping work is wasted** unless the whole engine is rewritten. Do
   not start layout mapping "to see how far it gets."
4. **New slide types inserted anywhere below index 18** invalidate `SLIDE_INDEX` and force
   all six `.pptx` files to be rebuilt. Always append.

### If only two weeks were available

**Ship: D-0 (2) + Track A (6) + Track E copy (0.5) + Track C1 (3.5) = 12 days, 2 days buffer.**

**Cut: Track B, Track C2, Track D entirely.**

Reasoning: Track A is the answer to the integration-count question and needs no one's
permission. C1 is the cheapest credible version of the only genuinely uncopiable feature and
delivers the visible "it's our brand" moment. Track B is catch-up on a race the strategy
document itself says we cannot win — five more connectors do not change a competitive
position, and universal CSV covers those platforms anyway. Track D defends a layer
(querying) that Meta now gives away free; it can wait a cycle without losing ground.

---

## F. Risks and open questions — **DECIDED 2026-08-22**

| # | Decision |
|---|---|
| F-1 | **Resolved.** Google OAuth verification **was approved** (~10 days, April 2026); CLAUDE.md was stale and has been corrected. YouTube Analytics is unblocked but **deferred past this cycle**. Consent-screen edits are no longer free — see the warning added to CLAUDE.md. |
| F-2 | **Yes — build D-0 first.** The `regenerate_report` bug justifies it on its own; fix it inside D-0 and call it out in the commit. |
| F-3 | **Option (c) — skip Shopify.** Universal CSV covers Shopify exports. Revisit with option (b) if e-commerce demand appears. |
| F-4 | **Confirmed C1 + C2**, not the arbitrary-template general case — with the value correction recorded in D-C above. |
| F-5 | **Include `custom_template` in the trial**, Agency-only on paid tiers. Prospects must see the differentiator during evaluation. |
| F-6 | **Accepted** — 25 mappings/day per user, with a clear user-facing message. |
| F-7 | **Deferred with Track D.** No decision needed this cycle. |
| F-8 | Meta App Review resubmitted Aug 2026, awaiting; **not blocking**. **Do not re-base Meta on the AI-connector path** — Meta's MCP uses Business OAuth for users connecting their *own* accounts, which does not cover a SaaS serving users with no role on our app. App Review is still required. |

The original question text is retained below for context.

---

**F-1 — YouTube Analytics vs. the in-flight Google verification. ⚠️ Highest-stakes.**
Adding `yt-analytics.readonly` requires re-submitting for sensitive-scope review (3–5
business days typical). The real risk is not the timeline — it is that **CLAUDE.md records
our Google OAuth production verification as still pending**, and editing the consent screen
while a review is in flight can reset that review. That would delay *GA4, Google Ads, and
Search Console* — our three most important integrations — to add one minor source.
**Question: has Google verification been approved since April 2026?**
If yes → YouTube is a 1-day build plus a short review, worth doing.
If still pending → **do not touch the consent screen.** Deferred, no exceptions.

**F-2 — Is a 2-day refactor before feature work acceptable?** D-0 is the right engineering
call but produces no user-visible change. If the answer is no, I need to know now, because
Tracks A and B are designed on top of it.

**F-3 — Shopify approach.** Admin-created custom apps were discontinued in 2026. Options:
(a) instruct merchants through the Dev Dashboard and handle ~24h `client_credentials` token
refresh (moderate build, awkward onboarding); (b) build a proper public app with custom
distribution and full OAuth (cleaner UX, 3–5 days, no Shopify approval needed for unlisted
distribution); (c) skip Shopify for now — universal CSV covers Shopify's analytics export
perfectly well. **Recommendation: (c) now, (b) when e-commerce demand is proven.**

**F-4 — Track C scope.** Confirm C1+C2 instead of the arbitrary-template general case. If
the answer is "no, I want true arbitrary templates," that is a 3–4 week project that should
*replace*, not accompany, Tracks A/B/D this cycle.

**F-5 — Does `custom_template` belong outside the trial?** Every other feature is
trial-inclusive by design ("let them experience it", `plans.py` trial block). Gating our
strongest differentiator out of the trial means prospects never see it. **Recommendation:
include in trial, Agency-only on paid tiers.**

**F-6 — OpenAI cost per CSV mapping.** ~7–10k tokens per *new* format, cached by fingerprint
thereafter. Negligible at current volume, but 50 distinct files is 50 calls. Recommend a
per-user daily mapping cap (say 25) with a clear message.

**F-7 — Track D auth build.** Confirm we accept building a small OAuth 2.1 authorization
surface. An API-key-only MCP server is roughly 2 days but is not installable from Claude.ai
— I consider that not worth shipping.

**F-8 — Meta App Review status.** CLAUDE.md says review was in progress ~April 2026. Meta's
own MCP server now bypasses App Review entirely via Business OAuth. If our review is still
stalled, it is worth asking whether the Meta integration should be re-based on the
AI-connector path. Out of scope for this blueprint, but it materially affects the Meta story.

---

## G. Where the strategic context and the codebase disagree

**G-1 — "Make PPTX uncopiable (agency template upload is the killer feature)" — right
conclusion, wrong mechanism.** The strategy assumes template upload is a feature we can add.
Our renderer is index-and-token based, so the general case is an engine rewrite. The moat is
real and worth building; it must be built as C1+C2. **This is the single largest correction
in Phase 0.**

**G-2 — "Get to ~10 solid integrations and stop counting" — we are further from 10 than the
count suggests.** We have 4 native sources plus a KPI-list CSV importer. The strategic
context implies the marginal integration is cheap; in this codebase it costs ~180 lines of
duplicated orchestration plus edits in six other files plus rebuilding all six `.pptx`
templates. The number is reachable — after D-0.

**G-3 — "Solve the long tail with universal CSV" — fully supported, and cheaper than the
strategy assumes.** The multi-source CSV slide-duplication machinery already exists
(`_duplicate_slide` :1492, `_populate_csv_slide` :1518). Track A is a front-end to machinery
that is already load-bearing in production. This is the best value-per-day item in the
roadmap.

**G-4 — "Ship an MCP server before it becomes table stakes" — directionally right, but the
auth cost is understated and the urgency is overstated.** Meta's free MCP covers *querying*
Meta ads. Our differentiated MCP tool is `generate_report`. Since MCP distributes the moat
rather than being the moat, it should follow Tracks A and C rather than precede them.

**G-5 — "Reframe from time savings to client retention" — no codebase objection, and Goals
& Alerts is the proof point.** Anomaly detection with email alerts is literally the "clients
feel uninformed" fix. Recommend Phase 5 lead with Goals & Alerts as the retention mechanism
rather than listing it as a feature bullet.

**G-6 — One correction to the Phase 2 prompt:** it says "map metrics onto existing slide
types where possible; only add new slide types where the blueprint says they are needed."
Two new slide types (`ecommerce_overview`, `email_overview`) *are* needed, and adding them
means editing all six `.pptx` binaries. That is a real sub-task with no shortcut and should
be budgeted (~0.5 day) rather than discovered mid-phase.

**G-7 — A gap neither the strategy nor the prompts mention.** `regenerate_report`
(`reports.py:1401`) silently drops CSV sources and hardcodes `modern_clean` (:1747), so
regenerating an expired report **loses the client's chosen visual template and every CSV
source**. Report files are ephemeral on Railway (CLAUDE.md: "regenerate on 410"), so this
fires in normal use. It is a live production bug, it is fixed for free by D-0, and it is a
stronger argument for the refactor than anything in the roadmap.

---

*End of Phase 0. No production code was written. Awaiting decisions on F-1 through F-8
before Phase 1 begins.*
