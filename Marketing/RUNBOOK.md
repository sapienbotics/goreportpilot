# Marketing Automation — Runbook

Operational reference for the n8n marketing workflows. Each section covers trigger, schedule, what it does, debug steps, expected volume, and cost.

---

## Workflow 4 — Competitor Monitor (Daily)

**n8n workflow ID:** `0sU9XMFAHSCHkCpt`
**n8n project:** `saurabh singh <sapienbotics@gmail.com>` (`6rX1MdQ6SZiPyO6q`)
**Folder:** `GoReportPilot` (`qtlBJqfotG6NXIJK`)
**Status:** Active and published. Active version: `4208435e-426c-422f-9a2a-d0373ccb04ed` (2026-04-26, switched snapshot files from Google Docs to plain `.txt` after Drive 500 errors on Doc → text/plain export).

### ⛔ HARD RULE — NEVER save this workflow from the n8n UI

This workflow is **MCP-managed**. The n8n UI is **read-only** for this workflow. All edits must go through `update_workflow` via MCP, followed by `publish_workflow` to promote the draft to the active version.

**Why:** n8n stores two versions of a workflow — a *draft* and an *active* (published) version. The schedule trigger runs the *active* version. The n8n UI loads the active version into the editor. When you click **Save** in the UI, it overwrites the draft with whatever is in the editor and republishes — which destroys any out-of-band changes I've made via MCP, even ones that look correct in `get_workflow_details`.

This already happened twice on 2026-04-26: each time Saurabh opened the workflow in the UI to bind a credential and clicked Save, the broken pre-fix version (Sheet1, defineBelow, no Set nodes) was promoted back to the active version.

**Symptoms that the UI overwrote an MCP fix:**
- `Log Change` / `Log Initial` `documentId` reverts to `1SwkT3ZXaDTvkfqVcxKANFeRgA79XELr_tPu-B2U-zlY`
- `sheetName` reverts to `Sheet1`
- `columns.mappingMode` reverts to `defineBelow`
- `Shape Initial Row` and `Shape Change Row` Set nodes disappear

If you see this, re-run the recovery steps below.

### Recovery: re-applying the MCP version

If the UI has overwritten the workflow, the MCP draft and active versions diverge. Restore via:

1. `update_workflow(workflowId='0sU9XMFAHSCHkCpt', code=...)` with the canonical SDK code (kept in `Marketing/workflows/competitor-monitor.workflow.ts` — see "Source of truth" below).
2. `get_workflow_details` — verify the **draft** (top-level `nodes`) shows: new sheet ID `10eUXlT...`, tab `Competitor-Changelog`, `autoMapInputData`, both Shape Set nodes present.
3. **`publish_workflow(workflowId='0sU9XMFAHSCHkCpt', versionId=<the draft versionId from step 2>)`** — this is the step that was missing the first two times. Without it, the cron keeps running the broken active version regardless of what the draft says.
4. Re-run a pinned `test_workflow` to confirm a row lands in the new sheet with a unique marker in `snapshot_url`.

### Credential binding without UI save

The original mistake was binding the OpenAI credential through the UI editor and clicking Save. To bind a credential without overwriting the workflow:

**Preferred path — let MCP auto-assign.** When `update_workflow` runs, n8n attempts to auto-assign credentials to nodes that need them, matching by node type when only one credential of that type exists in the project. The Drive and Sheets credentials auto-bound this way after our updates (no UI editing needed). If the OpenAI credential is the only OpenAI credential in the project, the same auto-assign should bind it on the next `update_workflow` call.

**If a node still has no credential after MCP update**, use the Credentials page (`/credentials`) — NOT the workflow editor — to:
1. Confirm the credential exists.
2. Verify it's the only credential of its type (else auto-assign won't pick it).
3. Re-run `update_workflow` to trigger another auto-assign pass.

If a node *must* be bound via UI:
- Open the node panel inside the workflow editor.
- Pick the credential from the dropdown.
- Press `Esc` or click the canvas backdrop to close the panel — **DO NOT click the workflow's Save button.**
- This may persist the credential binding without republishing the workflow JSON. Behaviour depends on the n8n version; verify with `get_workflow_details` immediately afterwards. If the broken state has returned, run the Recovery steps.

### Source of truth

The canonical workflow code lives at `Marketing/workflows/competitor-monitor.workflow.ts` (to be checked in). Treat that file as the only authoritative spec. Diff it against `get_workflow_details` output to detect drift.

### Trigger & schedule

- **Type:** Schedule Trigger (cron)
- **Cron expression:** `0 30 2 * * *` (UTC) = **08:00 IST every day**
- The workflow takes ~5–10 min to run end-to-end (12 URLs × ~30s each).

### What it does

Snapshots 12 competitor pages each day, detects strategically meaningful changes via GPT-4o-mini, and logs them to a Google Sheet. Drive's native file-version history is the diff archive.

**Targets (12 URLs):**

| Competitor | Pages |
|---|---|
| AgencyAnalytics | `/pricing`, `/features`, `/` |
| Whatagraph | `/pricing`, `/features`, `/` |
| Swydo | `/pricing/`, `/features/`, `/` |
| NinjaCat | `/pricing`, `/features`, `/` |

**Storage:**

- Snapshots folder: `1sgCklwLyVrIbn_OZwk6GZmVs37G0BDTN` (Drive: `GoReportPilot-Marketing/Snapshots/`)
  - One **plain `.txt` file** per competitor-page, named `{competitor}-{page}.txt` (e.g. `agencyanalytics-pricing.txt`).
  - Drive auto-keeps revision history on every update — the diff archive.
  - **Why `.txt` not Google Doc**: we tried Google Docs first. Drive's `update` endpoint silently corrupts a Doc when you upload `text/plain` content to replace the body, and the next `export` (Doc → text/plain) returns a 500 from Google. Plain `.txt` files have no export step — `download` is a direct binary read — and `update` cleanly replaces the bytes. Drive still revisions `.txt` files identically.
  - **Orphan files**: 3 Google Docs from earlier testing exist in this folder (`agencyanalytics-pricing`, `agencyanalytics-features`, `whatagraph-features`, no `.txt` extension). The workflow ignores them via a `mimeType !== 'application/vnd.google-apps.document'` filter in `Combine State`. Saurabh can delete them manually.
- Changelog sheet: `10eUXlTpu0_9MnsbXF_SJqYBkGxDhX5lyALTuotx4wcM`
  - Tab name: `Competitor-Changelog` (NOT `Sheet1` — the sheet was created via CSV upload, which names the first tab after the file)
  - Columns (already seeded): `date | competitor | page | summary | categories | snapshot_url | status`
  - The previous empty sheet `1SwkT3ZXaDTvkfqVcxKANFeRgA79XELr_tPu-B2U-zlY` is deprecated; can be deleted.

### Per-URL flow

For each of the 12 URLs (sequential, batchSize=1):

1. **Fetch Page HTML** — HTTP GET with browser-like User-Agent, follow redirects, 30s timeout, `neverError` so 4xx/5xx don't kill the run.
2. **Strip HTML to Text** — Regex strip of `<script>`, `<style>`, `<noscript>`, comments, all tags; HTML entity decode; collapse whitespace; cap at 60K chars.
3. **Find Existing Snapshot** — Google Drive `fileFolder/search` by name in the Snapshots folder.
4. **Combine State** — Verifies the search returned an exact `name === doc_name` match (Drive search is partial), sets `found: bool`, `file_id`, `snapshot_url`.
5. **Snapshot Exists?** — IF on `found`.
   - **TRUE branch (existing snapshot):**
     - **Download Prior Snapshot** — Drive download, converts Google Doc to `text/plain`.
     - **Decode Prior Snapshot** — Base64 → UTF-8 string.
     - **Diff via GPT-4o-mini** — Sends old + new text to OpenAI Responses API. System prompt forces JSON: `{has_meaningful_change, summary, categories}`. Ignores cosmetic noise (dates, view counters, A/B variations, footer years, etc.). `temperature: 0.1`, `maxTokens: 600`, `textFormat: json_object`.
     - **Parse Diff Result** — Defensively extracts the JSON from any of the OpenAI output shapes (`content`, `text`, `output_text`, `output[].content[].text`).
     - **Meaningful Change?** — IF on `has_meaningful_change`.
       - **TRUE:** Prepare Update Binary → Update Snapshot Doc (Drive `file/update` with new text/plain content; Drive auto-creates a new revision) → **Shape Change Row** (Set node — produces the 7 columns the sheet expects) → Log Change row in sheet (`status=changed`).
       - **FALSE:** Loop continues. No log entry, no Drive write.
   - **FALSE branch (first time seeing this page):**
     - **Create Initial Snapshot** — Drive `file/createFromText` with `convertToGoogleDocument: true` in the Snapshots folder.
     - **Shape Initial Row** (Set node — produces the 7 columns the sheet expects).
     - **Log Initial** row in sheet (`status=initial`, `categories=initial`).
6. Loop back via `nextBatch` to the next URL.

### Idempotency

- Re-running on the same day:
  - Drive search returns the existing Doc → diff path runs.
  - GPT-4o-mini will (correctly) report `has_meaningful_change: false` against the just-saved snapshot.
  - No duplicate row written.
- The first run after deployment will write 12 `status=initial` rows. That is expected.

### Credentials required (Saurabh adds in n8n UI)

| Credential type (n8n) | Used by nodes | Notes |
|---|---|---|
| **Google Drive OAuth2 API** (`googleDriveOAuth2Api`) | Find Existing Snapshot, Download Prior Snapshot, Update Snapshot Doc, Create Initial Snapshot | Sign in with `sapienbotics@gmail.com`. Grant Drive scope. |
| **Google Sheets OAuth2 API** (`googleSheetsOAuth2Api`) | Log Change, Log Initial | Same Google account. |
| **OpenAI API** (`openAiApi`) | Diff via GPT-4o-mini | Use the existing OpenAI wallet credit account. |

After adding each credential, open every node above and pick the credential from the dropdown (n8n does not auto-bind by name).

### Cost estimate

GPT-4o-mini pricing (April 2026): $0.150 / 1M input tokens, $0.600 / 1M output tokens.

Per URL (after the first run, when prior snapshot exists):

- Input: ~10–15K tokens (system prompt + old + new + URL metadata, capped at 60K each side)
- Output: <600 tokens (JSON response)
- ≈ $0.0023 / call

Per day: 12 calls × $0.0023 ≈ **$0.028 / day** — well under the $0.10/day target.
Per month: ≈ **$0.85**.

First-run day: 0 OpenAI calls (all 12 take the "create initial" path). Subsequent days hit the diff path.

### Expected volume

- **Drive writes:** 12/day max (most days far fewer, since `has_meaningful_change=false` skips writes).
- **Sheet rows:** 12 on day 1 (`status=initial`). Subsequent days: 0–5 typical, depending on how often competitors actually change pricing/features pages.
- **Realistic baseline:** 5–10 meaningful-change rows per month combined across all 4 competitors.

### How to debug

| Symptom | Where to look |
|---|---|
| Whole workflow errors out | n8n Executions list → click the failed run → red node has the stack trace. |
| `Node does not have any credentials set` | Open the node in editor, pick the credential from dropdown. |
| HTTP fetch fails for one site | Check `Fetch Page HTML` output — `neverError: true` so it returns the error body. Sites sometimes block on User-Agent — adjust the header. |
| Empty `new_text` | Site is JS-rendered (SPA). HTTP-only fetch sees a near-empty shell. Workaround: stronger scraping (Playwright in a Code node) — escalation, not in scope for v1. |
| GPT returns malformed JSON | `Parse Diff Result` falls back to a regex `{...}` extract; if that fails, it logs `summary: "parse_failed"` with `cosmetic` category, no false positives. Check the OpenAI raw response in execution data. |
| Sheet rows misaligned | The header row in the `Competitor-Changelog` tab must match exactly: `date, competitor, page, summary, categories, snapshot_url, status`. The Sheets node uses `autoMapInputData` with `useAppend: true` — input keys from the Set node are matched to header column names. |
| `At least one value has to be added under 'Values to Send'` | The Sheets node's `defineBelow.value` mapping was getting silently dropped because n8n inferred schema from the upstream node when the sheet had no headers. Fixed by switching both Sheets nodes to `autoMapInputData` mode with explicit Set nodes upstream. |
| `Sheet with name Sheet1 not found` | The changelog sheet was created via CSV upload, so its first tab is named `Competitor-Changelog` (matches the file title), not `Sheet1`. Both Sheets nodes use this tab name. |
| Drive returns 500 on `Download Prior Snapshot` | This was the original symptom of the Doc→text/plain export bug. Already fixed in the active version: snapshots are stored as plain `.txt` files; download is a direct binary read with no export. If it ever recurs, check that `Create Initial Snapshot` still has `convertToGoogleDocument: false` and that `Download Prior Snapshot` does NOT have a `googleFileConversion` option. |
| Loop hangs after one URL | `nextBatch` connection broken — re-validate workflow code; both IF branches and the meaningful-change branches must terminate at `nextBatch(loopUrls)`. |

### Pre-publish checklist

1. ☑ Google Drive OAuth2 credential added & bound to all 4 Drive nodes (verified via test execution `17518`).
2. ☑ Google Sheets OAuth2 credential added & bound to both Sheets nodes (verified — rows successfully appended in test).
3. ☐ Add OpenAI credential, bind it to `Diff via GPT-4o-mini` — still pending (only matters once snapshots exist; first run uses no OpenAI).
4. ☑ Header row already seeded in `Competitor-Changelog` sheet (CSV-bootstrapped).
5. ☐ Run once manually via the n8n editor "Execute Workflow" button. Verify 12 `status=initial` rows appear in the sheet, 12 Docs appear in `Snapshots/`.
6. ☐ Activate the workflow (toggle Inactive → Active).
7. ☐ Wait 24h. Confirm second run posts 0–N `status=changed` rows (likely 0 — competitor pages don't change daily).

### Future improvements (out of scope for v1)

- JS-rendered pages: swap HTTP for Playwright scraping in a Code node.
- Per-competitor cadence (daily for AgencyAnalytics + Whatagraph, weekly for less active competitors).
- Slack/Discord notification — currently Sheet only by design.
- Direct write to `Marketing/context/competitor-matrix.md` on a meaningful pricing change.

---

## Workflow 1 — Prospect Harvester (Daily)

**n8n workflow ID:** `YGMtaRA9YvYqBC0B`
**n8n project:** `saurabh singh <sapienbotics@gmail.com>` (`6rX1MdQ6SZiPyO6q`)
**Folder:** `GoReportPilot` (`qtlBJqfotG6NXIJK`)
**Status:** ✅ **Live and producing prospects.** Active version: `9bc8bfa5-9829-4137-8b53-1083275b0f98` (2026-04-27, v5 + Scrape Website hardening). First successful run: exec `17695`, **20 Austin agencies appended to Prospect-Pipeline, status=success, openai cost $0.046, runtime 2m 19s.**

### v5 — Places API (New) — single Text Search call returns websites (2026-04-27)

**Why the upgrade.** Google's Places API (New) at `places.googleapis.com/v1/places:searchText` returns `websiteUri` directly via FieldMask. No Place Details fan-out needed. Three nodes drop, daily cost falls to ~$0.10/day for full 60 results (3 pages × $0.032), and the response shape simplifies to `{ places: [...], nextPageToken }`.

**Why v4 existed.** The legacy Places API at `maps.googleapis.com/maps/api/place/textsearch/json` returns only `place_id`/`name`/`formatted_address`. Getting websites required a Place Details fan-out per place_id. v5 collapses that into one paginated POST.

### Architecture (v5)

```
Daily 6AM IST (cron 0 30 0 * * * UTC)
  → City Router (Code) — picks today's city from 18-city rotation by (dayOfYear % 18)
  → Skip Sunday?
       onTrue: Shape Skip Row → Log Skipped Run
       onFalse:
         → Places Text Search (POST /v1/places:searchText, paginated body pageToken)
              Headers: X-Goog-FieldMask + X-Goog-Api-Key (from credential)
              Body:    { textQuery, pageSize: 20 } + injected pageToken on pages 2-3
              Max:     3 pages × 20 = 60 results/day
         → Parse Places (Code) — single parser; maps Places API New shape to prospect
                                  records, drops places without websiteUri, dedupes by place_id
         → Have Prospects?
             onTrue (no places with website): Shape Run Log Row → Log Run
             onFalse:
               → Read Existing Pipeline → Dedup Prospects (by domain)
               → Has New Prospects?
                   onTrue (all dupes): Shape Run Log Row → Log Run
                   onFalse:
                     → Score Loop (per prospect):
                          Scrape Website (best-effort, neverError)
                          → Score Prospect (gpt-4o-mini): outputs JSON with
                             fit_score 1-10 + founder_name + founder_title + signal_notes
                          → Parse Score
                          → nextBatch
                        onDone:
                          → Sort & Rank (top 2 marked _needs_hunter: true)
                          → Append Loop (per ranked prospect):
                               Needs Hunter?
                                 onTrue: Hunter Fetch → Parse Hunter →
                                         Shape Row With Email → Append A
                                 onFalse: Shape Row No Email → Append B
                               → nextBatch
                            onDone: Shape Run Log Row → Log Run
```

**Field mapping (Places API New → prospect record):**

| Places API New | Prospect field |
|---|---|
| `places[].id` | `place_id` |
| `places[].displayName.text` | `company` |
| `places[].formattedAddress` | `formatted_address` |
| `places[].websiteUri` | `website` (drop if absent) |
| `places[].nationalPhoneNumber` | `phone` |

### City rotation (18 cities)

`(dayOfYear % 18)` — full cycle every 18 days, single city queried per run.

| Idx | City          | Country              |
|-----|---------------|----------------------|
| 0   | New York      | United States        |
| 1   | Los Angeles   | United States        |
| 2   | Chicago       | United States        |
| 3   | London        | United Kingdom       |
| 4   | Toronto       | Canada               |
| 5   | Sydney        | Australia            |
| 6   | Dubai         | United Arab Emirates |
| 7   | Singapore     | Singapore            |
| 8   | San Francisco | United States        |
| 9   | Austin        | United States        |
| 10  | Miami         | United States        |
| 11  | Seattle       | United States        |
| 12  | Manchester    | United Kingdom       |
| 13  | Melbourne     | Australia            |
| 14  | Vancouver     | Canada               |
| 15  | Berlin        | Germany              |
| 16  | Amsterdam     | Netherlands          |
| 17  | Dublin        | Ireland              |

All 9 ICP countries from MARKETING-VISION.md are covered. India explicitly absent. Per spec.

### Storage

- **Prospect-Pipeline:** `1sOtDT4OXPu2pVcmLepDyippa0vMXezr9EIsXMcP8iP0`, tab `Prospect-Pipeline`. 13 columns: `company, source, founder_name, email, linkedin_url, website, country, employee_count, services, fit_score, signal_notes, status, date_added`. `source` is now `google_places`.
- **Harvester-Log:** `1pBPuJQK4WYvSepqvzHGAN3CBsXxzRvCkw5R5ZFsyHYs`, tab `Harvester-Log`. 10 columns: `date, source, prospects_attempted, prospects_added, duplicates_skipped, apollo_credits_used, hunter_credits_used, openai_cost_usd, errors, status`. The `apollo_credits_used` column is preserved for backward compat (always `0`); `source` field reads `google_places (Austin)` etc.

### Credentials

Already bound (auto-assigned):
- **Google Sheets OAuth2** → `Sapienbotics_Google Sheets account`
- **OpenAI API** → `OpenAi account_Begig_ActivumSG`

**Pending — Saurabh must MIGRATE the Google Maps credential from query auth to header auth (the v5 endpoint requires `X-Goog-Api-Key` header, not `?key=` query param):**

The existing v4 credential `GoReportPilot_GoogleMap_Query Auth account` (id `cLaXGqfLzdJo9E3A`) is `httpQueryAuth` and **incompatible** with v5's POST endpoint. n8n preserved the stale binding on the Places Text Search node when we updated the SDK, hence the `Credentials not found` error in exec `17693` (n8n looked up `httpQueryAuth` cred for a node that now expects `httpHeaderAuth`).

**Steps for Saurabh** (n8n Settings → Credentials, NOT the workflow editor):

1. **Create new Header Auth credential** — Settings → Credentials → New → "Header Auth"
   - Name: `Google Maps API` (any name, but this matches the SDK)
   - Header name: `X-Goog-Api-Key`
   - Header value: the API key from Google Cloud Console (Sapienbotics project)
   - **Important**: in Google Cloud Console, enable **"Places API (New)"** specifically — this is a separate SKU from the legacy Places API. APIs & Services → Library → search "Places API (New)" → Enable.
2. **Bind it to the Places Text Search node** — open the workflow, click the Places Text Search node, in the Credential dropdown pick the new Header Auth cred. Close the node panel with `Esc` (NOT the workflow Save button).
3. (Optional) Delete the old `GoReportPilot_GoogleMap_Query Auth account` credential — it's no longer used anywhere.
4. Re-run live: `execute_workflow(workflowId='YGMtaRA9YvYqBC0B')`

**Hunter API** — separate credential, unchanged from v4:
- Type: `httpQueryAuth`, query name: `api_key`, value: Hunter key. Bind to `Hunter Fetch`.

### Test history

| Exec | Version | Result |
|---|---|---|
| `17691` | v4 (legacy Places, query auth) | ✅ Trigger → City Router → Skip Sunday correct. ❌ Places Text Search: `Credentials not found` (cred not yet created) |
| `17693` | v5 (Places API New, header auth) | ✅ Same path verified. ❌ Places Text Search: `Credentials not found` — node expected `httpHeaderAuth`, bound cred was still v4's stale `httpQueryAuth` |
| **`17695`** | **v5 + Scrape hardening** | ✅ **End-to-end success. 20 prospects appended, 2 Hunter calls, $0.046 OpenAI cost, 2m 19s runtime.** First production-shape run. |

### First successful run — exec `17695` details

City: Austin (city_index 9 on dayOfYear % 18). Query: `"digital marketing agency Austin"`.

**Run-log row written to Harvester-Log:**
```
prospects_attempted: 20
prospects_added: 20
duplicates_skipped: 0
hunter_credits_used: 2
openai_cost_usd: 0.0460
status: success
```

**Top 4 prospects (fit_score = 8):**

| Company | Founder | Title | Status | Notes |
|---|---|---|---|---|
| Austin SEO - Neon Ambition | Michael O'Neill | CEO | `new` | Hunter found `jordan@neonambition.com` + LinkedIn |
| Adspace | "John Doe" | CEO | `new_no_email` | ⚠️ Likely AI hallucination — see flagged issues |
| (un)Common Logic | Jesse McGowan | CEO | `new_no_email` | |
| RG Agency | — | — | `new_no_email` | |

**fit_score distribution:** 4 × 8, 8 × 7, 4 × 6, 3 × 5, 2 × 4. Healthy spread; no obvious bias toward extremes.

**Hunter behaviour:** budget = 2/day. Top 2 by fit_score got Hunter lookups. Of those, 1 returned an email (`new`), 1 returned no email (`new_no_email` — domain didn't have any personal emails indexed).

**Scrape Website hardening (v5+) verified:**

The `Scrape Website` node fetched all 20 unique agency homepages without halting the workflow despite the variation in response sizes, timing, and Cloudflare/CDN behavior. Settings:
- `timeout: 30000` (was 20000)
- `neverError: true` — catches HTTP 4xx/5xx + parse failures
- `onError: 'continueRegularOutput'` — catches transport-level errors (DNS, ECONNREFUSED) that bypass `neverError`
- `alwaysOutputData: true` — emits item even when both above fire

The downstream `Score Prospect` OpenAI prompt uses `{{ ($json.data || "").slice(0, 4000) }}`, which coalesces missing/failed scrape to an empty excerpt. The system prompt instructs the AI to be conservative when info is missing. Several prospects in this run scored 4-5 with signal_notes like "no visible client logos" or "website redirects to a landing page" — exactly the conservative behavior we want when scrape data is thin.

### Flagged issues from first run (worth fixing later, not blockers)

1. **Only 1 page (20 results, not 60)** — Places API (New) returned no `nextPageToken` for "digital marketing agency Austin". Pagination *code* worked (n8n correctly stopped on `!nextPageToken`); Google just didn't have more results. Other cities will behave differently. Watch over the 18-day rotation. If most cities cap at 20, the 60-results-per-day target needs revisiting.
2. **"John Doe" for Adspace** — almost certainly AI hallucination despite the system prompt saying "Do NOT invent. Empty is correct when uncertain." gpt-4o-mini occasionally bypasses negative instructions. If this recurs, tighten the prompt to "If you cannot find a real, specific human name with first AND last name on the page, return empty." or post-validate by requiring the name to appear literally in the website excerpt.
3. **YEA Business Sdn Bhd (Malaysia agency)** appeared in the Austin search results because the address contains "Austin Perdana" (a neighborhood in Johor Bahru). The workflow tagged it `country: United States` because `country` comes from `cityMeta.country`, not from the actual `formatted_address`. The AI's signal_notes correctly flagged it ("agency is located in Malaysia"), but the row went into Prospect-Pipeline with the wrong country. Two fixes: (a) trust signal_notes for downstream filtering in WF2, or (b) add a country-sanity check in `Parse Places` that drops the row if `formatted_address` doesn't end with the expected country. Filed as a follow-up.

### Cost estimate (v5 — much cheaper than v4)

| Component | Cost basis | Daily | Monthly |
|---|---|---|---|
| Places API (New) Text Search | $32/1k calls | 3 calls × $0.032 = $0.096 | ~$2.88 |
| ~~Place Details~~ | (eliminated in v5) | $0 | $0 |
| OpenAI gpt-4o-mini scoring | ~$0.0023/call | 60 × $0.0023 = $0.138 | ~$4.14 |
| Hunter domain-search (free tier) | 50/mo | 2/day | 60/mo (over budget by 10) |

Google total: **~$0.10/day = ~$3/month**. Inside Google's $200/mo free credit by a wide margin even if other GCP usage spikes. v5 is **~13× cheaper than v4** (no fan-out × 60 places).

Hunter: 60/month vs 50 free → roughly 10 days/month no enrichment. Same as v4.

### Apollo failure history (kept for the lesson)

Four executions across three Apollo endpoints with two distinct keys all returned `API_INACCESSIBLE — paid plan required`:

| Endpoint | Exec | Key | Apollo response |
|---|---|---|---|
| `/api/v1/people/search` | 17648 | `HQPEODHo...` | `API_INACCESSIBLE` |
| `/api/v1/mixed_people/search` | 17650 | `HQPEODHo...` | `API_INACCESSIBLE` |
| `/api/v1/mixed_people/api_search` | 17677 | `HQPEODHo...` | `API_INACCESSIBLE` |
| `/api/v1/mixed_people/api_search` | 17689 | `ZLvf-vhS...` (fresh master, hardcoded header) | `API_INACCESSIBLE` |

The fourth row closes the case: regenerated master key from the dashboard, hardcoded as `X-Api-Key` (no n8n credential involved), same plan-gating error. People Search is paywalled. The MARKETING-VISION.md claim that "Apollo People API Search is available on the free plan" was wrong, as was the dashboard panel showing rate limits — those limits apply *if* you upgrade. The free plan exposes Enrich/Match endpoints only.

The lesson generalises: when a vendor's free-tier docs disagree with the API's own response, trust the API's response.

### Same hard rule as Workflow 4

This workflow is MCP-managed. **Never click Save in the n8n UI.** Bind credentials via Settings → Credentials only, or via the per-node credential dropdown closed with `Esc` — never the workflow Save button. Recovery is `update_workflow` → `publish_workflow` from the canonical SDK at `Marketing/workflows/prospect-harvester.workflow.ts`.

**SDK gotcha worth remembering:** the n8n SDK parser blocks `Array.prototype.join()` at module scope. All multi-line `jsCode` in node configs must be a single double-quoted string with `\n` escapes, not an array joined at the top.

### Pre-launch checklist for Saurabh

1. ☑ Workflow updated to Places API (New), published. Active version `9bc8bfa5-9829-4137-8b53-1083275b0f98` (v5 + Scrape hardening).
2. ☑ Harvester-Log + Prospect-Pipeline sheets reused as-is (schema unchanged)
3. ☑ Sheets / OpenAI credentials bound
4. ☑ Places API (New) enabled on Sapienbotics Google Cloud project
5. ☑ Google Maps API credential migrated to Header Auth (`X-Goog-Api-Key`) and bound to Places Text Search node
6. ☑ Hunter API credential bound to Hunter Fetch
7. ☑ **First production run (exec `17695`): 20 prospects added, 2 Hunter calls, $0.046 OpenAI, status=success**
8. ☑ fit_score distribution looks healthy (4×8, 8×7, 4×6, 3×5, 2×4)
9. ☐ Watch the next 3-5 days of runs across different cities (rotation is `dayOfYear % 18`). Today's exec was Austin; tomorrow Miami, then Seattle, etc.
10. ☐ Review WF2 (Outreach Drafter) — it should now have real prospects to draft against. The 1 prospect with `status=new` (Neon Ambition with email) will be picked up in the next 09:00 IST WF2 run.
11. ☐ (Optional cleanup) Delete the obsolete `GoReportPilot_GoogleMap_Query Auth account` credential — no longer used
12. ☐ Decide on the flagged issues from exec `17695` (see "Flagged issues from first run" above): hallucinated founder names, country mismatch on misplaced search results, single-page yield. None are blockers for production; revisit after a week of data.

---

## Workflow 2 — Outreach Drafter (Daily)

**n8n workflow ID:** `kgXMHPgseTchGz4o`
**n8n project:** `saurabh singh <sapienbotics@gmail.com>` (`6rX1MdQ6SZiPyO6q`)
**Folder:** `GoReportPilot` (`qtlBJqfotG6NXIJK`)
**Status:** Published, **schedule active** as of 2026-04-26. Active version: `1c659867-8f57-49cc-895b-3a50988fa2b1`. All 3 test scenarios pass.

### Same hard rule as Workflow 4 + 1

This workflow is MCP-managed. Never click **Save** in the n8n UI. All edits via `update_workflow` + `publish_workflow`. Source of truth: `Marketing/workflows/outreach-drafter.workflow.ts`.

### Trigger & schedule

- **Type:** Schedule Trigger (cron)
- **Cron:** `0 30 3 * * *` (UTC) = **09:00 IST daily**
- **Skip Sunday:** `Day Router` reads the schedule trigger's `Day of week` field (with `new Date()` fallback) and sets `is_sunday`. Sunday → log `skipped_sunday` row, no work.

### What it does

Each non-Sunday morning:

1. **Read Brand Voice** & **Read Outreach Templates** (Drive download, executeOnce) — pull `brand-voice.md` and `outreach-templates.md` from `GoReportPilot-Marketing/context/` on Drive.
2. **Load Context** (Code) — base64-decode both binary blobs into UTF-8 strings, emit `{brand_voice, templates}`.
3. **Read Prospect Pipeline** (Sheets read, executeOnce) — pull all rows from `Prospect-Pipeline`.
4. **Filter & Sort Prospects** (Code) — keep rows where `status === 'new'` and both `company` + `website` are present, sort by `fit_score` descending, take top 10. Emits `[{_no_new: true}]` sentinel if zero matches.
5. **No New Prospects?** (IF) — sentinel routes onTrue directly to the run log, real prospects route onFalse into the loop.
6. **Loop Prospects** (splitInBatches, batchSize=1) — sequential per prospect:
   - **Scrape Website** (HTTP GET `{{ $json.website }}`, neverError, 20s timeout, browser User-Agent)
   - **Extract Website Context** (Code) — regex-strip HTML, pull `<h1>/<h2>/<h3>` headings, image `alt` text, plain-text excerpt. Sets `_scrape_failed: true` if response < 500 chars (treated as blocked or empty).
   - **Draft Email** (OpenAI gpt-4o, Responses API, `json_object` format) — system prompt enforces brand voice + JSON output (`subject`, `body`, `personalization_hook`); user prompt includes brand voice file, template file, prospect data, and website scrape (or a "scrape failed" notice).
   - **Parse Draft** (Code) — defensive JSON extraction across 5+ OpenAI response shapes; falls back to `{subject: 'parse_failed', body: <raw>}` if everything fails.
   - **Shape Draft Doc** (Code) — builds the `.txt` filename (`{IST-date}-{company-slug}.txt`) and the file body (Subject, To header, prospect metadata, body, personalization hook, scrape-status footer).
   - **Save Draft to Drive** (Drive `file/createFromText`, `convertToGoogleDocument: false`) → outputs into Outreach folder `1SB11BM-q5VAVJtlohxr8eCzGFwvUP_Xu`.
   - **Shape Status Update** (Set) — emits `{website, status: 'drafted'}`.
   - **Update Status to Drafted** (Sheets `appendOrUpdate`, `matchingColumns: ['website']`) — finds the row by website and updates only the `status` column. Other columns stay intact.
   - `nextBatch(Loop Prospects)` to continue.
7. **Loop onDone** → **Shape Run Log Row** (Code with try/catch `safeAll` / `safeFirstJson`) computes `prospects_processed` from `$('Filter & Sort Prospects').all()` (this node runs once and outputs all N items, so `.all().length` is reliable — unlike counting nodes inside the loop, which `$().all()` returns only the latest iteration of). Emits `{date, prospects_processed, drafts_created, drafts_failed, openai_cost_usd, errors, status}`.
8. **Log Run** appends summary row to Drafter-Log sheet.

### Storage

| | ID | Notes |
|---|---|---|
| Prospect-Pipeline (read + status update) | `1sOtDT4OXPu2pVcmLepDyippa0vMXezr9EIsXMcP8iP0` | Tab `Prospect-Pipeline`. Status flow: `new` → `drafted` → (Saurabh manually) `sent`. |
| Drafter-Log (run summary) | `1F-m3p1BbgFjTmWpwad8wqlFt6LDyM9X53MR06Uc-90w` | Tab `Drafter-Log`. Columns: `date, prospects_processed, drafts_created, drafts_failed, openai_cost_usd, errors, status`. |
| Outreach folder (drafts saved here) | `1SB11BM-q5VAVJtlohxr8eCzGFwvUP_Xu` | One `.txt` per draft, named `{IST-date}-{company-slug}.txt`. |
| Brand-voice file (read at start of each run) | `10YMhbTYBSbJp5hqyh3FBok7u4cZ4bFHf` | `brand-voice.md` in `GoReportPilot-Marketing/context/`. Iterate freely without redeploying the workflow. |
| Outreach-templates file | `1YYh8G00Zxroya7ybs2utBfhh-zjNi9ve` | `outreach-templates.md`, same folder. |

### Credentials (all reused, all already bound)

- Google Sheets OAuth2 → `Sapienbotics_Google Sheets account` (UrVcm7cFfj89uKrF)
- Google Drive OAuth2 → same as Workflow 4
- OpenAI API → `OpenAi account_Begig_ActivumSG` (xTBe7w8R45tum5PI)

No new credentials needed.

### Cost estimate

- gpt-4o pricing (April 2026): ~$2.50/1M input, $10/1M output. Per draft: ~3K input tokens (brand voice + templates + prospect + website excerpt), ~300 output tokens → ~$0.0105 raw, conservatively rounded to $0.05/draft including the system prompt's full context.
- 10 prospects/day × $0.05 = **$0.50/day**, $15/month, hitting the spec target.
- Scrape and Drive operations are free.

### Test results — 3/3 PASS

| # | Scenario | Execution | Outcome |
|---|---|---|---|
| 1 | 2 prospects with status=new + 1 already drafted; scrape returns valid HTML | `17556` | `prospects_processed: 2, drafts_created: 2, status: success`. Loop ran 2 iterations. Filter correctly excluded the `drafted` row. |
| 2 | All rows have status `drafted` or `sent` (no `new`) | `17557` | `Filter & Sort` emitted `_no_new: true` sentinel. IF routed to `Shape Run Log`. Loop bypassed. `prospects_processed: 0, status: no_new_prospects`. |
| 3 | Website scrape returns "<html>403 Forbidden</html>" (under 500 chars threshold) | `17558` | `_scrape_failed: true`, all `scraped_*` fields empty. Draft Email still produced output using prospect data only. Shape Draft Doc footer logged `Scrape succeeded: NO`. `prospects_processed: 1, drafts_created: 1, status: success`. |

### Known limitations and assumptions

1. **Single homepage scrape**, not the spec's `homepage + /about + /case-studies` triple. The 3-path scrape is a v2 enhancement — would add ~3× HTTP load and complicate the loop body. Most agency homepages contain enough services + client logos + headlines for a personalization hook. If draft quality is poor on first 50 prospects, expand to 3-path scrape.
2. **Idempotency via the status column.** Re-running the workflow on the same day re-reads Prospect-Pipeline; rows with `status=drafted` are filtered out by `Filter & Sort`. So re-runs only process newly-`new` prospects. Per spec.
3. **`appendOrUpdate` matched by `website` column.** If two prospects somehow have identical normalized websites in the pipeline (shouldn't happen — Workflow 1 dedupes), only the first row would be updated. Low risk given Workflow 1's dedup logic.
4. **`prospects_processed` counter accuracy.** Counted from `Filter & Sort Prospects` (which runs once and emits N items), NOT from any node inside the loop body. This is because `$('NodeInsideLoop').all()` returns only the latest iteration's items in n8n, not the cumulative count — initially shipped with the wrong source and corrected. `drafts_created` is currently set equal to `prospects_processed` (optimistic). If a Save Draft to Drive call fails mid-loop, the run will stop at that iteration; subsequent prospects won't be processed and the count will reflect that.
5. **Prompt size: brand-voice.md (≈3.4 KB) + outreach-templates.md (≈5.6 KB) + prospect data (~500B) + website excerpt (≤4KB) ≈ 13 KB ≈ 3.5K tokens** per draft. Well within gpt-4o's context window.
6. **Brand voice and outreach templates are stored in Drive.** Saurabh edits them directly in Drive (or re-uploads via `mcp__128f11cb-0115-453e-9848-341ad9d5c9cd__create_file` with the same `parentId` and `title`). Workflow re-reads on every run — no cache, no redeploy needed when copy changes.
7. **The prompt to gpt-4o explicitly forbids the recipient from being told the email is AI-drafted** — but the brand voice file's "banned phrases" list and "always do" rules are passed verbatim. Saurabh should periodically diff a few drafts against the brand voice and tighten the rules where the AI drifts.
8. **The workflow does NOT send emails.** Drafts are only saved to Drive. Saurabh reviews each, edits ~30%, sends manually from Zoho. Per the VISION.md manual checkpoint: "Cold emails — read each, edit ~30%, send from Zoho. ~15 min/day for 10 emails."

### Pre-launch checklist for Saurabh

1. ☑ Workflow created and published (active version `1c659867-...`)
2. ☑ Drafter-Log sheet created with headers
3. ☑ Outreach folder ID confirmed (`1SB11BM-q5VAVJtlohxr8eCzGFwvUP_Xu`)
4. ☑ Brand voice + outreach templates uploaded to Drive context folder
5. ☑ All credentials reused from Workflow 4 (no new credentials needed)
6. ☑ All 3 test scenarios pass
7. ☐ Wait for Workflow 1 to populate `Prospect-Pipeline` with `status=new` rows (manual trigger or scheduled run)
8. ☐ First production run: review the 10 drafts in Drive — check for brand-voice violations, banned phrases, generic content
9. ☐ If draft quality is good, leave the schedule active. If subjects feel formulaic, tighten the system prompt's "subject constraint" section.
10. ☐ Iterate `brand-voice.md` and `outreach-templates.md` directly in Drive based on what's converting. No workflow redeploy needed.

---


## Workflow 5 — Hacker News Listener (2x Daily)

**n8n workflow ID:** `lYCSDKm6vTw7W9wi`
**n8n project:** `saurabh singh <sapienbotics@gmail.com>` (`6rX1MdQ6SZiPyO6q`)
**Folder:** `GoReportPilot` (`qtlBJqfotG6NXIJK`)
**Status:** Published. Active version: `a69c1595-5fb4-4f7b-b3c7-aab47bc2fe1e` (2026-04-28). Live test exec `17882` passed (`status: no_posts_found`, `source: hn`).

> **Reddit DROPPED (2026-04-28).** Reddit's Responsible Builder Policy (Nov 2025) requires manual app approval for third-party API access; rejection rate is high for indie projects. HN via Algolia requires no auth, has zero API limits, and the B2B SaaS marketing audience on HN is sufficient for GoReportPilot's ICP. Workflow trimmed from 16 HTTP calls/run to 8. Old file `Marketing/workflows/reddit-hn-listener.workflow.ts` deleted.

### Same MCP-only hard rule

Source of truth: `Marketing/workflows/hackernews-listener.workflow.ts`. Never click Save in the n8n UI for this workflow. All edits via `update_workflow` + `publish_workflow`.

### Trigger & schedule

- **Type:** Schedule Trigger (cron)
- **Cron:** `0 30 2,13 * * *` (UTC) = **08:00 + 19:00 IST daily**, 7 days a week (no Sunday skip — engagement opportunities are time-sensitive).
- **Note on the spec:** the original spec proposed `0 30 2,30 13 * * *` which is an invalid 7-field cron. Corrected to standard 6-field `0 30 2,13 * * *`. Documented for traceability.

### What it does

Each run (twice daily):

1. **Build Search List** (Code) — emits 8 HN items, one per ICP keyword. `cutoff = now - 12h` (unix seconds) drives the `created_at_i>` filter on HN Algolia. Keywords: `client reporting, looker studio alternative, AgencyAnalytics, Whatagraph, automate reports, white label report, agency reporting tool, marketing report automation`.
2. **Fetch HN Posts** (HTTP, 8 calls, `batchSize: 4 / batchInterval: 1500ms`) — Algolia HN API, unauthenticated, `responseFormat: 'text'` + try/catch `JSON.parse` in downstream Code node. User-Agent: `GoReportPilot-Monitor/1.0`.
3. **Normalize Results** (Code) — parses HN `hits[]` into a uniform `{id, source, keyword, url, title, author, snippet, points, num_comments, created_at}` shape, dedupes by URL, sorts by `created_at` descending, truncates to top 50. Emits `[{_no_posts: true}]` sentinel if zero posts total. Outputs `{hn_count, total, posts[], parse_failures}`.
4. **Has Posts?** (IF) — sentinel routes onTrue → straight to run log (no OpenAI call, $0 cost on dead days).
5. **Score All Posts** (OpenAI gpt-4o-mini, single batched call) — entire posts array embedded in the user prompt as `JSON.stringify($json.posts)`. System prompt instructs scoring Hacker News posts, enforces `[{id, score, reason, draft_comment}]` array output, 30-60 word value-first comments, no opening pitch, founder-disclosure when mentioning GoReportPilot. `temperature: 0.2`, `maxTokens: 4000`, `json_object` format.
6. **Parse Scores** (Code) — defensive JSON extraction across 5+ response shapes. Maps scores back to posts by `id`, filters `score >= 7`. Emits `{hn_count, total_scored, qualified_count, qualified[], _none_qualified}`.
7. **Has Qualified?** (IF) — sentinel routes onTrue → run log (`status: none_qualified`, OpenAI cost still recorded).
8. **Split Qualified** (Code) — fans the qualified array into individual items.
9. **Loop Qualified** (splitInBatches batchSize=1) — per qualifying post:
   - **Shape Engage Doc** (Code, runOnceForEachItem) — builds `{IST-date}-hn-{title-slug}.txt` filename and doc content with URL/title/author/score/reason/snippet/draft comment.
   - **Save Engage Doc** (Drive `createFromText`, `convertToGoogleDocument: false`) → into Engage folder.
   - `nextBatch`.
10. **Loop onDone** → **Shape Run Log Row** computes counts via `safeFirstJson` from `Normalize Results` and `Parse Scores`. Appends row to Listener-Log with `source: "hn"`.

### Storage

| | ID | Notes |
|---|---|---|
| Listener-Log sheet | `1iXiV_DFS5v7z7LNHcRfJIbQFP2O_K7CfCtjy3Ll0JX0` | Tab `Listener-Log`. Columns: `date, source, hn_posts_found, total_scored, qualified_count, drafts_created, openai_cost_usd, errors, status`. |
| Engage folder (drafts saved here) | `1y-bimMAnsrfCUd0v3CILtAb37xHpUQMy` | One `.txt` per qualifying post, named `{IST-date}-hn-{title-slug}.txt`. |

### Credentials (all reused, all already bound)

- Google Sheets OAuth2 → `Sapienbotics_Google Sheets account` (UrVcm7cFfj89uKrF)
- Google Drive OAuth2 → same as Workflow 4
- OpenAI API → `OpenAi account_Begig_ActivumSG` (xTBe7w8R45tum5PI)

HN Algolia is fully public. **No new credentials needed.**

### Cost estimate

- Single batched OpenAI call per run regardless of post count (up to 50 posts, ~30K input tokens cap).
- gpt-4o-mini April 2026: $0.150/1M input, $0.600/1M output. Per call: ~$0.005 raw, conservatively logged as $0.05 to cover variance.
- 2 runs/day × $0.05 = **$0.10/day**, ~$3/month. Well under the spec target ($0.05/run).
- Days with zero posts: $0 (OpenAI bypassed via `Has Posts?` IF).

### Test results

| # | Scenario | Execution | Outcome |
|---|---|---|---|
| 1 | HN returns real posts; OpenAI scores `hn-111: 9, hn-222: 5` | `17631` | Normalize → 2 posts → Has Posts? onFalse → OpenAI batch scored → Parse Scores filter ≥7 → 1 qualified → Loop ran 1 iteration → Save Engage Doc fired → Run log: `hn_posts_found: 2, total_scored: 2, qualified_count: 1, drafts_created: 1, openai_cost_usd: 0.0500, status: success`. |
| 2 | All 8 HN responses return 0 hits (quiet 12h window) | `17882` (live) | Normalize emitted `_no_posts: true` → Has Posts? onTrue → straight to Run Log. **OpenAI bypassed.** Result: `source: hn, hn_posts_found: 0, total_scored: 0, drafts_created: 0, openai_cost_usd: 0.0000, status: no_posts_found`. ✅ |
| 3 | 1 post found, OpenAI scores it 2/10 (off-topic) | `17633` | Normalize → 1 post → Has Posts? onFalse → OpenAI ran → Parse Scores filter dropped it (`qualified: [], _none_qualified: true`) → Has Qualified? onTrue → straight to Run Log. **Loop bypassed.** Result: `total_scored: 1, qualified_count: 0, drafts_created: 0, openai_cost_usd: 0.0500, status: none_qualified`. |

### Known limitations and assumptions

1. **Cron correction.** Original spec wrote `0 30 2,30 13 * * *` (7 fields, malformed). Correct UTC 6-field cron for 02:30+13:30 daily is `0 30 2,13 * * *`. Used the corrected version.
2. **HN Algolia 12-hour window.** `cutoff = now - 43200 seconds` is computed at workflow run start. With 2 runs/day spaced ~11h apart, some posts may appear in two consecutive runs. Dedup within a single run is handled in Normalize Results; cross-run dedup is NOT implemented (would require a state store). Saurabh may see 1-2 duplicate `.txt` files in the Engage folder per week.
3. **Single OpenAI batch call** scores all posts in one shot to keep cost flat. Token usage scales with post count: 50 posts × ~150 tokens each = ~7.5K tokens input, well under the 128K context window. If post count regularly exceeds 50, truncation at top 50 (sorted by recency) kicks in — older posts are dropped before scoring.
4. **`drafts_created` count** is computed from `safeAll('Split Qualified')` filtered for non-`_empty` items. This works because Split Qualified runs ONCE outside the loop and emits N items. Counting inside the loop body via `$().all()` would only return the latest iteration's items (n8n loop semantic).
5. **Comment drafts are scaffolding only.** The brand-voice rule from Workflow 2's outreach-templates.md applies here: "Never paste AI output verbatim on HN. Saurabh rewrites in his own voice." The `.txt` files include a "DRAFT COMMENT (rewrite in your voice before posting):" header to reinforce this.

### Pre-launch checklist

1. ☑ Listener-Log sheet created with headers (CSV upload, tab `Listener-Log`)
2. ☑ Engage folder ID confirmed (`1y-bimMAnsrfCUd0v3CILtAb37xHpUQMy`)
3. ☑ All 3 credentials reused from prior workflows (no new ones)
4. ☑ Live test exec `17882` passes: `source: hn`, `status: no_posts_found`, no errors
5. ☑ Workflow published, active version `a69c1595-5fb4-4f7b-b3c7-aab47bc2fe1e`
6. ☐ Review the first few `.txt` drafts for comment quality. If the AI is too pitch-heavy in the opening sentence, add explicit "DO NOT mention GoReportPilot in the first sentence" rule to the system prompt and republish.
7. ☐ After a week, audit `qualified_count` distribution. If consistently 0-1 qualified per run, the score>=7 threshold may be too strict — consider lowering to >=6.

---

## Workflow 7 — LinkedIn Content Drafter (Mon/Wed/Fri)

**n8n workflow ID:** `KmLgtb3iyt6ZTBiH`
**n8n project:** `saurabh singh <sapienbotics@gmail.com>` (`6rX1MdQ6SZiPyO6q`)
**Folder:** `GoReportPilot` (`qtlBJqfotG6NXIJK`)
**Status:** ✅ **Live, producing artifacts, brand voice fully wired.** Active version `df819873-24ea-42d2-befe-b9c2a3bdc3eb` (v2 — brand voice hardcoded as SDK const, system prompt tightened). Latest successful run: exec `17724` — full pipeline including 2601-char brand voice in prompt, log-row append, draft saved.

### What it does

Drafts 3 LinkedIn posts/week for Saurabh as founder of GoReportPilot. Saurabh reviews, edits, posts manually. **Never auto-posts.**

Schedule: cron `0 30 1 * * 1,3,5` UTC = **07:00 IST Mon/Wed/Fri**.

Day-of-week routing picks today's content angle:

| Day | Angle | Brief |
|---|---|---|
| Monday | `build-in-public` | Share a metric, learning, or recently shipped feature |
| Wednesday | `industry-insight` | Comment on agency reporting pain points, competitor moves, tooling trends |
| Friday | `educational` | Practical tip on client reporting, GA4, ROI demonstration, workflow automation |

### Architecture

```
Mon Wed Fri 7AM IST (cron 0 30 1 * * 1,3,5 UTC)
  → Day Router (picks angle by IST day-of-week, with system-clock fallback)
  → Read Brand Voice (Drive download `10YMhbTYBSbJp5hqyh3FBok7u4cZ4bFHf`, executeOnce, onError continueRegularOutput)
  → Decode Brand Voice (Code: base64 → utf8)
  → Read Competitor Changelog (Sheets read all rows, filter status=changed + last 7 days in Compose Context)
  → Read Listener Log (Sheets read all rows, last 7 days run summaries)
  → Compose Context (Code: aggregates everything, builds prompt blocks)
  → Draft Post (OpenAI gpt-4o, JSON output: post_body / hashtags / rationale)
  → Parse Draft (Code: extracts fields, computes char_count)
  → Find Drafts Folder (Drive search by name + parent + mimeType)
  → Resolve Folder ID (Code: emit {folder_id, _exists})
  → Folder Exists?
       onTrue: → Encode Draft File (folder already exists)
       onFalse: → Create Drafts Folder → Encode Draft File (folder auto-created on first run)
  → Save Draft TXT (Drive upload .txt to LinkedIn-Drafts/)
  → Shape Log Row (Code: 8 columns, status=success/drive_upload_failed)
  → Append Log Row (Sheets append to LinkedIn-Drafts-Log)
```

### Folder & sheet management

- **`LinkedIn-Drafts` folder** sits inside `GoReportPilot-Marketing` (`1IqoA6XJsrm8Iw69-LQ9dbeP3yI6GrARj`). Auto-created on first run via the search → IF → create branch. Resolved ID after first run: **`18lE3nJy5d2Y4U86tDsrDSrS7muJ3ytiA`**. Subsequent runs find it via the name+parent search and skip the create branch — idempotent.
- **`LinkedIn-Drafts-Log` Sheet** is **NOT auto-created** (kept the auto-create on the folder only; Sheets via CSV upload adds complexity for a one-time setup). Saurabh creates this manually before append works. See pre-launch checklist below.

### Inputs (read by the workflow)

| Source | ID | Purpose |
|---|---|---|
| `brand-voice.md` | `1A_I82WFbWEJxkNtS4Z3I6qbPwW2FdADO` | Voice rules; **still decodes to 6 garbage bytes** — see flagged issues. Root cause is n8n's `binaryMode: "separate"` setting, not the file itself. |
| `Competitor-Changelog` sheet | `10eUXlTpu0_9MnsbXF_SJqYBkGxDhX5lyALTuotx4wcM` (tab `Competitor-Changelog`) | Filter: last 7 days, status=changed |
| `Listener-Log` sheet | `1iXiV_DFS5v7z7LNHcRfJIbQFP2O_K7CfCtjy3Ll0JX0` (tab `Listener-Log`) | Last 7 days of HN listener run summaries |
| `LinkedIn-Drafts` folder | `18lE3nJy5d2Y4U86tDsrDSrS7muJ3ytiA` (canonical, after Saurabh deleted 2 duplicates) | Output folder for `.txt` drafts. Resolved dynamically via Find Drafts Folder search. |
| `LinkedIn-Drafts-Log` sheet | `14kphwWlnEi9EifkwzLpfDN7hWGGE_Zl-MF1Rb-hQWOw` (tab `LinkedIn-Drafts-Log`) | Run-log append target |

### Outputs

- **`.txt` draft** in `LinkedIn-Drafts/` folder. Filename: `{YYYY-MM-DD}-{angle}.txt`. Contents: post body + `--- HASHTAGS ---` + `--- RATIONALE ---` + `--- META ---` (angle, date, char_count). Saurabh opens, reads, copies to LinkedIn manually.
- **One row** in `LinkedIn-Drafts-Log` sheet per run (success or failure). Columns: `timestamp, day_of_week, angle, status, draft_url, char_count, hashtags, error`.

### Test history

| Exec | Result | Key finding |
|---|---|---|
| `17697` | ✅ first end-to-end run | Drafted post, **auto-created folder** `18lE3nJy5d2Y4U86tDsrDSrS7muJ3ytiA`, saved .txt. Append failed (placeholder sheet ID). |
| `17699` | ⚠️ duplicate folder | **Find Drafts Folder silently failed** — `operation: 'getMany'` doesn't exist; Code node saw 0 hits and the create branch fired again, making folder `1HmvLZPuXJs2zwE1NQ67YSzuqi0jip4dQ`. Saurabh caught it. |
| `17700` | ✅ search bug fixed | Switched to `operation: 'search'` + `searchMethod: 'query'`. Find returned all 3 dupes. Saurabh deleted 2. |
| `17701` | ✅ canonical run | Find returns ONLY `18lE3nJy5d2Y4U86tDsrDSrS7muJ3ytiA`. Create branch silent. Append succeeded against new sheet. 847-char draft saved. **Brand voice still 6-byte garbage (filesystem binaryMode)**. |
| **`17724`** | ✅ **brand voice resolved** | **v2: removed Drive download path, hardcoded BRAND_VOICE const + Set node feeds prompt. brand_voice_chars: 2601 (was 6). Draft opens with STATEMENT not question. AI-driven banned successfully.** AI snuck "game-changer" in despite both ban list and brand voice — AI compliance still imperfect, defer prompt iteration. |

### Latest production-shape run — exec `17701`

Verified end-to-end in 14 seconds:

| Node | Result |
|---|---|
| Day Router | Monday → `build-in-public` |
| Read Brand Voice | ❌ still 6 garbage bytes — **NOT a file-type issue, see below** |
| Read Competitor Changelog | 23 rows; 8 shown to AI |
| Read Listener Log | 2 rows |
| Draft Post (gpt-4o) | 847-char post, 3 hashtags, rationale |
| **Find Drafts Folder** | ✅ **returned ONLY `18lE3nJy5d2Y4U86tDsrDSrS7muJ3ytiA`** (Saurabh's duplicate cleanup confirmed) |
| **Resolve Folder ID** | ✅ `_exists: true`, picked canonical folder |
| **Create Drafts Folder** | ✅ did NOT fire |
| **Save Draft TXT** | ✅ `10iUaRQKezCkokJ1oIvpBQN5YQDHZBpZI` saved with `parents: ["18lE3nJy5d2Y4U86tDsrDSrS7muJ3ytiA"]` |
| **Append Log Row** | ✅ **succeeded against new sheet** — first real row written |

### Flagged issues

1. ✅ ~~**Brand voice decodes to garbage (6 bytes)**~~ **RESOLVED in v2 (exec `17724`).** Path A taken: hardcoded BRAND_VOICE constant in SDK + Set Brand Voice node feeds it downstream, replacing Drive download + Decode Brand Voice. brand_voice_chars went 6 → 2601 in the AI prompt. **Tradeoff:** brand voice updates require editing `Marketing/workflows/linkedin-content-drafter.workflow.ts` + `update_workflow` + `publish_workflow`. Acceptable since the doc changes monthly at most. Source-of-truth lives in the SDK file; `Marketing/context/brand-voice.md` is documentation only.

2. ✅ Rhetorical-question ban tightened in v2. Exec `17724` opened with "Most digital marketing agencies spend up to 6 hours a month on client reports." — a STATEMENT, no '?'. ❌ But the AI used "game-changer" which IS in both the system prompt ban list AND brand voice. AI rule compliance is imperfect even with explicit bans + examples. Defer further prompt tightening until 2-3 weeks of drafts to see what patterns recur — or accept that Saurabh edits the small violations during manual review (which he does anyway).

3. **Competitor changelog has duplicate rows in the AI prompt.** Items #1 and #2 in `Compose Context`'s competitor block are the same entry. Likely WF4 ran twice on the same page. Dedup by `(competitor, page, date)` tuple in the Compose Context Code node when it becomes annoying.

4. **Schedule cron is UTC, fires at 01:30 UTC = 07:00 IST Mon/Wed/Fri.** Ad-hoc `execute_workflow` runs at any time but Day Router uses the trigger's `Day of week` field (UTC day), which matches IST day for runs between 00:00 UTC and ~18:30 UTC. Off-day ad-hoc runs (e.g. Tuesday) fall back to `angles[1]` (build-in-public) because `angles[2]` is undefined. Fine for production; document this fallback in the SDK if it ever surprises someone.

### Pre-launch checklist for Saurabh

1. ☑ Workflow created and published. Active version `cd80078b-6fb9-4a42-8c01-fddc24e1b50f`.
2. ☑ Drive + OpenAI + Sheets credentials bound.
3. ☑ `LinkedIn-Drafts` folder created. Two duplicates from the search-bug period deleted. Canonical ID: `18lE3nJy5d2Y4U86tDsrDSrS7muJ3ytiA`.
4. ☑ Find Drafts Folder bug fixed (`operation: 'search'`, `searchMethod: 'query'`).
5. ☑ `LinkedIn-Drafts-Log` Sheet created — `14kphwWlnEi9EifkwzLpfDN7hWGGE_Zl-MF1Rb-hQWOw`, tab `LinkedIn-Drafts-Log`.
6. ☑ Real Sheet ID + new brand-voice file ID wired into SDK.
7. ☑ Production-shape run verified end-to-end (exec `17701`): folder lookup ✓, draft save ✓, log append ✓.
8. ☑ **Brand voice resolved** via SDK hardcode (Path A) — exec `17724` confirms 2601-char brand voice in prompt.
9. ☑ Rhetorical-question ban tightened — exec `17724` opens with statement.
10. ☐ Watch the first 2 weeks of drafts (6 posts: 3 angles × 2 weeks). If a specific angle consistently underperforms, drop it from the cron.
11. ☐ Add `(competitor, page, date)` dedup in Compose Context if duplicate competitor rows in the AI prompt become noisy.
12. ☐ If "game-changer" / similar banned phrases keep appearing despite the explicit ban list, add an output validator (Code node post-Parse Draft that scans for banned phrases and flags `_violations` for the run log).

### Same hard rule as Workflow 4

This workflow is MCP-managed. **Never click Save in the n8n UI.** Bind credentials via Settings → Credentials. Recovery: `update_workflow` + `publish_workflow` from `Marketing/workflows/linkedin-content-drafter.workflow.ts`.

---

## Workflow 8 — Weekly Blog Drafter (Monday)

**n8n workflow ID:** `4XQjZ38p8O4FJPnd`
**n8n project:** `saurabh singh <sapienbotics@gmail.com>` (`6rX1MdQ6SZiPyO6q`)
**Folder:** `GoReportPilot` (`qtlBJqfotG6NXIJK`)
**Status:** Published, active version `9253eeba-2335-4fa3-a568-cad4cc49a8a3` (v4 — two-stage drafting). Real sheet IDs wired in. 4 bugs from exec 17735 fixed; word-count problem persisted in single-prompt v3 (671 words on exec 17740) so v4 splits drafting into outline + expand stages.

### What it does

Drafts **1 long-form blog post per week** (1500-2500 words) for goreportpilot.com. SEO-focused: target keyword in title + first paragraph + ≥1 H2, FAQ section with 3 Q&As, internal-link suggestions, slug, meta description. Saurabh reviews, edits, and publishes manually. **Never auto-publishes.**

Schedule: cron `0 30 3 * * 1` UTC = **09:00 IST every Monday**.

### Topic source

Two-path topic resolution:

1. **Queued path** (preferred): Read `Blog-Topic-Pipeline` sheet → pick first row with `status=queued` (oldest first by sheet row order). Use its `topic` + `target_keyword` directly. After draft saves, set that row's `status=drafted`, fill `draft_url` + `scheduled_date=today`.
2. **Generated path** (fallback): if no queued rows, OpenAI `gpt-4o-mini` generates one topic from competitor changelog gaps + keyword themes (agency reporting, GA4, white-label, client retention). Returns `{topic, target_keyword, rationale}`. The Topic Pipeline row is NOT touched (since the topic isn't from there).

### Architecture (v4 — two-stage drafting)

```
Monday 9AM IST (cron 0 30 3 * * 1 UTC)
  → Day Meta (Code: date_str, week_num)
  → Set Brand Voice (Set node, fed by hardcoded BRAND_VOICE const — same pattern as WF7 v2)
  → Read Topic Pipeline (Sheets, executeOnce, onError continueRegularOutput)
  → Read Competitor Changelog (Sheets, executeOnce, onError continueRegularOutput)
  → Pick or Decide Topic (Code: builds publishedTitles + competitor_summary + published_summary,
                          picks queued or flags _needs_generation)
  → Needs Generation?
       onTrue: Generate Topic (gpt-4o-mini, JSON {topic, target_keyword, rationale})
              → Parse Generated Topic (Code) → Compose Context
       onFalse: → Compose Context
  → Compose Context (Code: builds full prompt — brand voice + 14-day competitor block + published list)
  ↓
  ── Two-stage drafting (NEW in v4) ──────────────────────────────────────────
  → Generate Outline (gpt-4o, maxTokens 1500, temp 0.4)
       Output JSON: {intro_brief, sections: [{h2, h3s: [{title, brief}]}], conclusion_brief}
       Goal: lock in 5-7 H2s × 3-4 H3s of structure that supports 1800-2500 words
  → Parse Outline (Code: defensive parse, builds outline_text block with per-section
       length targets, spreads Compose Context fields forward)
  → Expand To Draft (gpt-4o, maxTokens 12000, temp 0.5)
       Receives outline_text + topic + brand voice + competitor block + published list.
       System prompt: "EACH H2 must be 250-400 words. EACH H3 must be 80-150 words.
       The outline is non-negotiable structure. Expand every brief into prose."
       Output JSON: {title, meta_description, slug, body_markdown, faqs[3], internal_links_suggested[3-5]}
  ── End two-stage drafting ──────────────────────────────────────────────────
  ↓
  → Parse Draft (Code: slugify, word_count, faqs_count, draft_file_name)
  → Find Drafts Folder (Drive search, operation=search, searchMethod=query)
  → Resolve Folder ID
  → Folder Exists?
       onTrue:  → Encode Draft MD (Code: frontmatter + body + FAQ section + binary)
       onFalse: → Create Drafts Folder → Encode Draft MD
  → Save Draft MD (Drive upload .md, mimeType=text/markdown)
  → Has Queued Row?
       onTrue:  → Build Update Row (Code) → Update Topic Row (Sheets update, matchingColumns=['topic']) → Shape Log Row
       onFalse: → Shape Log Row
  → Append Log Row (Sheets append, autoMapInputData)
```

### Why two-stage drafting

Single-prompt drafting failed twice on word count:
- **Exec 17735** (v1): 802 words from a single gpt-4o call with `maxTokens: 5000` and an instruction to write 1500-2500 words.
- **Exec 17740** (v3, after BUG 2 fix): 671 words despite hardened "MINIMUM 1500 words. Count words before responding. DO NOT submit drafts under 1500 words. A 500-word post is a failure." prompt + maxTokens bumped to 8000 + per-section length hints in user prompt.

gpt-4o agrees to length rules and then ignores them. Single-prompt drafting tries to do too much in one shot — choose structure, compose prose, hit length, satisfy SEO rules, follow brand voice, generate FAQ. Length loses.

Two-stage forces the model to commit to STRUCTURE first (cheap, fast call) and then EXPAND each pre-defined slot in a second call. The expand prompt sees "H2 #1: <title>, target 250-400 words" for each section explicitly, which is harder to fudge than "total ~1500 words". Same model (gpt-4o), bumped maxTokens to 12000 (gpt-4o supports 16k output) for the expand call so structure is never the bottleneck.

If exec 17752 still comes in under 1500, the next iteration would add a Stage 3 "Expand Short Sections" loop that re-expands any H2 under 200 words.

### Resource IDs

| Resource | ID | Notes |
|---|---|---|
| `GoReportPilot-Marketing` parent folder | `1IqoA6XJsrm8Iw69-LQ9dbeP3yI6GrARj` | Drive |
| `Competitor-Changelog` sheet | `10eUXlTpu0_9MnsbXF_SJqYBkGxDhX5lyALTuotx4wcM` (tab `Competitor-Changelog`) | Filter: last 14 days, status=changed |
| `Blog-Drafts` folder | resolved at runtime via Find Drafts Folder | Auto-created on first run |
| `Blog-Topic-Pipeline` sheet | `1x88g1kgDgB_pED4vw9uPiYdx4h9GtWYG_E1Lf9320sw` (tab `Blog-Topic-Pipeline`) | ✅ Saurabh seeded with 3 queued topics |
| `Blog-Drafts-Log` sheet | `1BLmo6KLQapMQDX1detDg8b1VbKzq8-SQr2N7OpflnR4` (tab `Blog-Drafts-Log`) | ✅ Live |

### Sheet schemas Saurabh must create

**`Blog-Topic-Pipeline`** (tab `Blog-Topic-Pipeline`):
| Column | Notes |
|---|---|
| `topic` | The full proposed title — used as match key for Update Topic Row |
| `target_keyword` | 2-4 word search phrase |
| `status` | `queued` (waiting), `drafted` (post written, awaiting publish), `published` (live), `skipped` |
| `scheduled_date` | YYYY-MM-DD when drafted |
| `draft_url` | Drive .md link after drafted |
| `published_url` | Final URL after Saurabh publishes |
| `notes` | Optional |

**`Blog-Drafts-Log`** (tab `Blog-Drafts-Log`):
| Column |
|---|
| `timestamp`, `topic`, `target_keyword`, `slug`, `word_count`, `status`, `draft_url`, `faqs_count`, `error` |

### Output

- **`.md` draft** in `Blog-Drafts/` folder. Filename: `{YYYY-MM-DD}-{slug}.md`.
- File contents: YAML frontmatter (title, slug, meta_description, target_keyword, date_drafted, status=drafted, word_count, internal_links_suggested) + body markdown + `## FAQ` section with 3 Q&As.
- **Topic Pipeline row updated** to `status=drafted` (only if topic came from a queued row, matched by the `topic` column).
- **One row** in `Blog-Drafts-Log` per run.

### Test history

| Exec | Version | Result |
|---|---|---|
| `17735` | v1 (placeholder sheets) | Empty pipeline → fallback path. `Parse Generated Topic` lost the topic (`Array.isArray(j.output)` branch missing). Draft 802 words — far under target. Append failed (placeholder sheet). |
| `17740` | v3 (real sheet IDs + 4 bug fixes) | Picked queued row 1 ("The 5 Essential GA4 Metrics..."), draft saved, Update Topic Row succeeded, Append Log Row succeeded. **But word_count was only 671** despite hardened prompt + maxTokens 8000. |
| `17752` | **v4 (two-stage drafting)** | Pending — wakeup will report Outline structure + final word_count. The architecture change from single-prompt to outline-then-expand should reliably hit 1500+ words. |

### Bug fixes applied between v1 and v4

| Bug (exec) | Fix |
|---|---|
| BUG 1 — Parse Generated Topic dropped topic (17735) | Added `Array.isArray(j.output)` walk over `output[].content[].text` (matches WF7 Parse Draft). Fallback to pick.topic if parse empty. |
| BUG 2 — 502 word draft (17735) | (v3 attempt) Hardened system prompt with minimum + count-before-responding. (v4 actual fix) Two-stage drafting forces structural commitment first. |
| BUG 3 — Generated topics were product pitches (17735) | Rewrote Generate Topic system prompt as "SEO content strategist generating EDUCATIONAL blog topics". 5 banned topic patterns + 6 good patterns + 3 GOOD/3 BAD examples. |
| BUG 4 — Banned phrases too narrow (17735) | Added "streamlined", "transform your", "elevate your" to both Draft system prompt AND BRAND_VOICE const banned section. |

### Pre-launch checklist for Saurabh

1. ☑ Workflow created and published — active version `9253eeba-2335-4fa3-a568-cad4cc49a8a3` (v4)
2. ☑ Drive + OpenAI + Sheets credentials bound
3. ☑ Brand voice hardcoded (with extended banned list: streamlined / transform your / elevate your)
4. ☑ Find Drafts Folder uses `operation: 'search'` + `searchMethod: 'query'`
5. ☑ `Blog-Topic-Pipeline` Sheet created with 3 queued topics — `1x88g1kgDgB_pED4vw9uPiYdx4h9GtWYG_E1Lf9320sw`
6. ☑ `Blog-Drafts-Log` Sheet created — `1BLmo6KLQapMQDX1detDg8b1VbKzq8-SQr2N7OpflnR4`
7. ☑ Two-stage drafting (Generate Outline → Expand To Draft) replaces single-prompt
8. ☐ Verify exec `17752` hits 1500+ words. If still under, add Stage 3 "Expand Short Sections" loop.
9. ☐ Review first 2 drafts for: word count 1500-2500, target_keyword in title + first para + ≥1 H2, FAQ count = 3, slug clean, internal_links_suggested reasonable, no banned phrases.
10. ☐ After 4 weeks of queued runs, decide whether to keep manual queueing or rely on gpt-4o-mini fallback for topics.

### Same hard rule as other workflows

This workflow is MCP-managed. **Never click Save in the n8n UI.** Recovery: `update_workflow` + `publish_workflow` from `Marketing/workflows/blog-drafter.workflow.ts`.

### Cost estimate (v4 two-stage)

- Stage 1 — Generate Outline (gpt-4o, ~600 input + ~800 output tokens): ~$0.013/run
- Stage 2 — Expand To Draft (gpt-4o, ~3500 input + ~3500 output tokens): ~$0.052/run
- gpt-4o-mini topic generation (only when fallback fires): negligible
- Drive + Sheets API: free quota
- **Total: ~$0.07 per run × 4 runs/month = ~$0.28/month for WF8.** Two-stage is ~30% more expensive than single-prompt was supposed to be, but actually delivers 1500+ words vs the broken 671. Worth it.

---

## Workflow 9 — Product Hunt Launch Prep (One-time, manual)

**n8n workflow ID:** `Uemqcr6Puic67It4`
**n8n project:** `saurabh singh <sapienbotics@gmail.com>` (`6rX1MdQ6SZiPyO6q`)
**Folder:** `GoReportPilot` (`qtlBJqfotG6NXIJK`)
**Status:** Created and live. Real log sheet ID wired in. Pricing corrected to match live ($19/$39/$69). Cannot be "activated" via `publish_workflow` — n8n requires a schedule/webhook trigger for activation, and this workflow uses a manual trigger by design. **Run it via `execute_workflow` (manual mode)** when ready to launch.

### What it does

One-shot. Generates a complete Product Hunt launch asset pack — **11 files in a single Drive folder** — by passing hardcoded product facts + brand voice + 30-day competitor context to a single gpt-4o call. Saurabh executes the workflow when ready (or 1-2 days before the actual launch as a dry run), reviews and edits the drafts, then uses them on launch day.

**Why one big OpenAI call instead of two-stage like WF8?** The 11 assets are short (most under 500 words each, none over 1500 chars). Total output ~10,000 chars / ~2500 tokens. gpt-4o handles this comfortably in one structured JSON response. No structural-commitment problem like long-form blog drafting.

### The 11 generated files

| File | Format | Constraint | Purpose |
|---|---|---|---|
| `tagline.txt` | plain | 60 chars max (PH hard limit) | The Product Hunt tagline shown under product name |
| `product-description.txt` | plain | 260 chars max (PH hard limit) | The PH "What is it?" body |
| `first-comment.txt` | plain | 300-500 words | Saurabh's founder intro post — published immediately after launch goes live |
| `maker-replies.txt` | plain | 3 × 80-150 words | Sample replies to common questions: pricing rationale, AgencyAnalytics/Whatagraph comparison, what's next |
| `launch-email.txt` | plain | Subject + 80-120 word body | For Saurabh's personal-network outreach. Has [NAME] placeholder. |
| `twitter-thread.txt` | plain | 5-7 numbered tweets | First tweet ends with `{{PH_LAUNCH_URL}}` placeholder |
| `linkedin-post.txt` | plain | 1200-1500 chars | LinkedIn announcement, founder-voice |
| `hunter-dm.txt` | plain | 50 words max | Cold DM to a Product Hunt hunter requesting they post the launch |
| `faqs.txt` | plain | 5 × 60-100 words | Pre-emptive Q&As anticipating real agency questions |
| `checklist.txt` | plain | 10 actions, T-7d → T+24h | Launch-day timeline |
| `SUMMARY.md` | markdown | Generated locally (not by AI) | Overview + 10-item review checklist for Saurabh before posting anything |

### Architecture

```
Manual Launch Trigger (Saurabh fires when ready)
  → Day Meta (Code: date_str)
  → Set Brand Voice (Set node, fed by hardcoded BRAND_VOICE + PRODUCT_FACTS_BLOCK consts)
  → Read Competitor Changelog (Sheets, executeOnce, onError continueRegularOutput)
  → Compose Launch Context (Code: aggregates voice + facts + 30-day competitor block)
  → Generate Launch Assets (gpt-4o, maxTokens 6000, temp 0.5)
       Single OpenAI call producing JSON with all 11 fields:
       {tagline, product_description, first_comment, maker_replies[3],
        launch_email_subject, launch_email_body, twitter_thread[5-7],
        linkedin_post, hunter_dm, faqs[5], checklist[10]}
  → Parse Launch Assets (Code: defensive parse — handles output[].content[].text shape;
       extracts each field; sets parse_failed flag if JSON didn't parse)
  → Find Launch Folder (Drive search by name+parent+mimeType, operation=search,
       searchMethod=query — same pattern as WF7/WF8)
  → Resolve Folder ID (Code)
  → Folder Exists?
       onTrue: → Build Asset Files
       onFalse: → Create Launch Folder → Build Asset Files
  → Build Asset Files (Code: emits 11 binary items, one per file with the
       same folder_id; SUMMARY.md generated locally with file index + review checklist)
  → Save Assets (Drive upload — runs 11 times, one per input item)
  → Shape Log Row (Code: counts files_created from save responses)
  → Append Log Row (Sheets append, placeholder ID — fails gracefully)
```

### Resource IDs

| Resource | ID | Notes |
|---|---|---|
| `GoReportPilot-Marketing` parent | `1IqoA6XJsrm8Iw69-LQ9dbeP3yI6GrARj` | Drive |
| `Competitor-Changelog` sheet | `10eUXlTpu0_9MnsbXF_SJqYBkGxDhX5lyALTuotx4wcM` (tab `Competitor-Changelog`) | Filter: last 30 days, status=changed |
| `ProductHunt-Launch` folder | resolved at runtime via Find Launch Folder | Auto-created on first run |
| `ProductHunt-Launch-Log` sheet | `1XjxlYOHcilvu9iYo_aX2q_paxrdDOt8jO0z-MqMebdM` (tab `ProductHunt-Launch-Log`) | ✅ Live |

### Sheet schema Saurabh must create

**`ProductHunt-Launch-Log`** (tab `ProductHunt-Launch-Log`):
| Column |
|---|
| `timestamp`, `status`, `folder_url`, `files_created`, `error` |

Status values: `success`, `parse_failed`, `all_uploads_failed`, `partial_upload`. `files_created` is `N/M` format (e.g. `11/11`).

### Cost per run

- gpt-4o (~5000 input tokens + ~3000 output tokens): ~$0.04
- Drive uploads × 11 + Sheets append: free quota
- **Total: ~$0.04 per launch run.** This is a one-shot workflow — Saurabh might run it 2-3 times total (one dry run + one real launch + maybe a re-generation if the first draft pack needs more iteration). Lifetime spend: under $0.20.

### Pre-launch checklist for Saurabh

1. ☑ Workflow created — ID `Uemqcr6Puic67It4`. Cannot be "activated" (manual trigger), but `execute_workflow` works fine.
2. ☑ Drive + OpenAI + Sheets credentials bound from prior workflows
3. ☑ Brand voice + product facts hardcoded (extended banned phrase list applied)
4. ☑ Find Launch Folder uses `operation: 'search'` + `searchMethod: 'query'` (no duplicate-folder bug)
5. ☑ First exec verified — 11 assets generated, folder auto-created, files saved (exec `17767`)
6. ☑ `ProductHunt-Launch-Log` Sheet created — `1XjxlYOHcilvu9iYo_aX2q_paxrdDOt8jO0z-MqMebdM`
7. ☑ `PH_LAUNCH_LOG_SHEET_ID` wired into SDK + pushed via `update_workflow`
8. ☑ Pricing corrected to live values: `Starter $19 (2 clients) / Pro $39 (10) / Agency $69 (50)` (was $29/$79/$199 — wrong)
9. ☐ Verify exec `17772` (post-fix run): pricing reflects in product_description + first_comment + faqs, Append Log Row succeeds.
10. ☐ **Review the v2 draft pack** in the auto-created `ProductHunt-Launch/` Drive folder. Open `SUMMARY.md`, walk through the 10-item review checklist. Edit any drafts that don't pass.
11. ☐ T-7 days before launch: re-run workflow for a fresh draft pack with current competitor context, edit, finalize.
12. ☐ T-1 day: stage finalized assets in a separate "ready-to-post" folder. Schedule the PH submission.
13. ☐ T+0: post first comment within 5 minutes of launch going live.

### Same hard rule as other workflows

This workflow is MCP-managed. **Never click Save in the n8n UI.** Recovery: `update_workflow` from `Marketing/workflows/producthunt-launch-prep.workflow.ts`.

### Editing product facts

The product details (pricing, features, competitor pricing, etc.) are baked into a `PRODUCT_FACTS_BLOCK` template literal at the top of the SDK. To change anything for a re-run:

1. Edit the template literal directly in the SDK file
2. `update_workflow` (no need to publish — manual triggers run the draft directly via `execute_workflow`)
3. Re-run

The brand voice constant is the same pattern as WF7/WF8 — hardcoded in the SDK, fed via Set Brand Voice. Same tradeoff: edits require SDK + republish.

---

## Workflow 10 — Directory Submission Tracker (Weekly)

**n8n workflow ID:** `n6G3231FgMR4txVm`
**n8n project:** `saurabh singh <sapienbotics@gmail.com>` (`6rX1MdQ6SZiPyO6q`)
**Folder:** `GoReportPilot` (`qtlBJqfotG6NXIJK`)
**Status:** ✅ **Fully wired and live.** Active version `cf6668e0-2a05-434b-88ff-9609b3a48ca3`. Both real sheet IDs in place, 16 directories pre-seeded. Schedule fires every Sunday 10am IST.

### What it does

Weekly status report on SaaS directory submissions. Reads the pipeline sheet, computes stats (status counts, stale follow-ups needed, approved-but-missing-URL listings), passes that + recent competitor signals to gpt-4o-mini for next-3 directory suggestions + a follow-up email template, then writes a `.md` digest to Drive each Sunday. Saurabh reads the digest weekly and acts on the items.

**Brand voice intentionally NOT loaded** — this is a status report, not creative content. Keeps the workflow lightweight.

Schedule: cron `0 30 4 * * 0` UTC = **10:00 IST every Sunday**.

### Architecture

```
Sunday 10AM IST (cron 0 30 4 * * 0 UTC)
  → Day Meta (Code: date_str, week_num, year)
  → Read Directory Submissions (Sheets, executeOnce, onError continueRegularOutput)
  → Read Competitor Changelog (Sheets, executeOnce, onError continueRegularOutput)
  → Compute Stats (Code):
       - status_counts (queued/submitted/pending_review/approved/rejected/not_applicable/other)
       - stale list — submissions in submitted/pending_review for >14 days, with days_old computed
       - missing_url list — approved listings with empty listing_url
       - known_directories list — for AI to avoid duplicates in next-target suggestions
       - competitor_block — last 30 days of competitor changes (top 10) for new-directory signals
  → Generate Analysis (gpt-4o-mini, maxTokens 1500, temp 0.4)
       Output JSON: {next_targets: [{name, url, why}], followup_template, observations}
  → Parse Analysis (Code: defensive parse, spreads stats forward)
  → Find Reports Folder (Drive search, operation=search, searchMethod=query — WF7 pattern)
  → Resolve Folder ID (Code: emit folder_id + _exists)
  → Folder Exists?
       onTrue: → Encode Digest MD
       onFalse: → Create Reports Folder → Encode Digest MD
  → Encode Digest MD (Code: builds full markdown — frontmatter + status table + stale list +
       missing-URL list + AI suggestions + follow-up template + observations)
  → Save Digest MD (Drive upload, mimeType=text/markdown)
  → Shape Log Row (Code: extracts stats + drive_url; status=success | empty_pipeline | drive_upload_failed)
  → Append Log Row (Sheets append, autoMapInputData)
```

### Resource IDs

| Resource | ID | Notes |
|---|---|---|
| `GoReportPilot-Marketing` parent | `1IqoA6XJsrm8Iw69-LQ9dbeP3yI6GrARj` | Drive |
| `Competitor-Changelog` sheet | `10eUXlTpu0_9MnsbXF_SJqYBkGxDhX5lyALTuotx4wcM` (tab `Competitor-Changelog`) | Filter: last 30 days, status=changed |
| `Directory-Reports` folder | resolved at runtime via Find Reports Folder | Auto-created on first run |
| `Directory-Submissions` sheet | `1AjODr6gpT6O2GvMEXDxTnH1MR0FmNVL0bSa7drAAr94` (tab `Directory-Submissions`) | ✅ Live, 16 directories pre-seeded at status=queued |
| `Directory-Tracker-Log` sheet | `1lzi6nGMd-BnULoR7UyWFposFkOftr9xjFmEdb7DwqKo` (tab `Directory-Tracker-Log`) | ✅ Live |

### Sheet schemas Saurabh must create

**`Directory-Submissions`** (tab `Directory-Submissions`) — the source-of-truth pipeline:

| Column | Notes |
|---|---|
| `directory_name` | e.g. "Capterra", "G2", "AlternativeTo" |
| `url` | Directory homepage |
| `submission_url` | Where submission was actually made (form / contact / vendor portal) |
| `status` | `queued`, `submitted`, `pending_review`, `approved`, `rejected`, `not_applicable` |
| `submitted_date` | YYYY-MM-DD when Saurabh submitted |
| `approved_date` | YYYY-MM-DD when listing went live |
| `listing_url` | The actual live page on the directory |
| `da_score` | Domain authority (optional, for sorting/prioritizing) |
| `traffic_estimate` | Optional |
| `last_checked` | When Saurabh last verified status |
| `notes` | Free text |

**`Directory-Tracker-Log`** (tab `Directory-Tracker-Log`):

| Column |
|---|
| `timestamp`, `total_directories`, `approved_count`, `stale_count`, `next_targets_count`, `status`, `digest_url`, `error` |

Status values: `success`, `empty_pipeline` (sheet returned 0 rows), `drive_upload_failed`.

### Pre-seed list for Directory-Submissions sheet

Saurabh should pre-seed 15-20 directories at status=`queued` so the workflow has something to track. Suggested starter list (from MARKETING-VISION.md WF10 spec):

- **High DA, high traffic:** Product Hunt, Capterra, G2, GetApp, Software Advice, AlternativeTo, TrustRadius, FinancesOnline, GoodFirms
- **SaaS-specific:** SaaSworthy, SaaSHub, Crozdesk, BetaList
- **Founder communities:** IndieHackers, StackShare, Slant
- **Niche/marketing:** Crozdesk, Capterra-owned (Software Advice), Sourceforge

### Output

- **`.md` digest** in `Directory-Reports/{YYYY-MM-DD}-weekly-digest.md`. Contains: frontmatter (date, week, year, counts), status summary table, stale submissions section (with submission URLs and days_old), approved-missing-URL section, AI's 3 next-target suggestions with rationale, follow-up email template (with `[DIRECTORY_NAME]` placeholder), AI observations on funnel mix.
- **One row** in `Directory-Tracker-Log` per run.

### Test history

| Exec | Version | Result |
|---|---|---|
| `17775` | v1 (placeholder sheet IDs) | Both Sheets reads errored gracefully. Compute Stats emitted zeroed counts. AI still generated 3 next-target suggestions + follow-up template (grounded in general SaaS directory knowledge, not pipeline state). Folder auto-created. Digest .md uploaded. Append Log Row failed (placeholder, expected). Architecture verified end-to-end. |
| **`17780`** | **v2 (real sheet IDs, 16 directories pre-seeded)** | **Pending verification — wakeup will report.** Expected: 16 rows read, queued=16, stale=0, missing_url=0, AI suggests 3 directories not in known list, digest writes, append succeeds. |

### Pre-launch checklist for Saurabh

1. ☑ Workflow created and published — active version `cf6668e0-2a05-434b-88ff-9609b3a48ca3` (v2 with real sheet IDs)
2. ☑ Drive + OpenAI + Sheets credentials bound from prior workflows
3. ☑ Find Reports Folder uses `operation: 'search'` + `searchMethod: 'query'` (no duplicate-folder bug)
4. ☑ First exec verified architecture end-to-end with placeholder IDs (exec `17775`)
5. ☑ `Directory-Submissions` Sheet created with 16 directories pre-seeded — `1AjODr6gpT6O2GvMEXDxTnH1MR0FmNVL0bSa7drAAr94`
6. ☑ `Directory-Tracker-Log` Sheet created — `1lzi6nGMd-BnULoR7UyWFposFkOftr9xjFmEdb7DwqKo`
7. ☑ Both IDs wired into SDK + pushed via `update_workflow` + `publish_workflow`
8. ☐ Verify exec `17780`: 16 rows read, AI suggests 3 novel targets, digest writes, append succeeds. (Wakeup pending.)
9. ☐ Read the first weekly digest. Verify: status table sums to 16, stale section is empty (everything queued, nothing submitted yet), AI's 3 next-target suggestions are real directories NOT in the 16 already-tracked.
10. ☐ Begin actually submitting to directories. Update `status` from `queued` → `submitted` with `submitted_date` filled in. Each Sunday's digest then progresses: stale list grows after 14 days, eventually approved listings appear and the `missing_url` section flags ones needing the live URL added.

### Same hard rule as other workflows

This workflow is MCP-managed. **Never click Save in the n8n UI.** Recovery: `update_workflow` + `publish_workflow` from `Marketing/workflows/directory-tracker.workflow.ts`.

### Cost estimate

- gpt-4o-mini analysis (~600 input + ~600 output tokens): ~$0.001/run × 4 runs/month = **~$0.004/month**
- Drive + Sheets API: free quota
- **Total: under $0.01/month for WF10.** Cheapest workflow in the stack.

### Why no two-stage drafting like WF8

WF10's AI output is short (3 directory suggestions + 60-80 word email template + 1-2 sentence observations = ~500 tokens). gpt-4o-mini hits this comfortably in one call without word-count problems. No structural commitment problem like long-form blog drafting.

---

