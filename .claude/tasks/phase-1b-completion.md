# Phase 1b — Path A: Wire Google Ads + Search Console Data Pulls

**Status:** ✅ Complete — awaiting user verification.
**Completed:** 2026-04-19
**Scope:** Remediate the dead-code finding from Phase 1 audit §3 — wire `pull_google_ads_data` and `pull_search_console_data` into both `_generate_report_internal` and `regenerate_report`, with matching snapshot hooks.

---

## 1. What Was Built

### Wiring (4 new pull orchestrations)

| File | Function | Platform | Structure |
|---|---|---|---|
| `routers/reports.py` | `_generate_report_internal` | `google_ads` | Query connection → pull (sync via `asyncio.to_thread`) → save snapshot |
| `routers/reports.py` | `_generate_report_internal` | `search_console` | Query connection → pull (async) → save snapshot |
| `routers/reports.py` | `regenerate_report` | `google_ads` | Same pattern |
| `routers/reports.py` | `regenerate_report` | `search_console` | Same pattern |

### Snapshot-hook count per platform × function (expected: 8)

Verified via grep:
```
242  platform="ga4",                  # _generate_report_internal
289  platform="meta_ads",             # _generate_report_internal
347  platform="google_ads",           # _generate_report_internal   (NEW)
402  platform="search_console",       # _generate_report_internal   (NEW)
1296 platform="ga4",                  # regenerate_report
1337 platform="meta_ads",             # regenerate_report
1390 platform="google_ads",           # regenerate_report           (NEW)
1442 platform="search_console",       # regenerate_report           (NEW)
```

### `raw_data` assembly now includes the new keys

```python
if google_ads_data is not None:
    raw_data["google_ads"] = google_ads_data
if search_console_data is not None:
    raw_data["search_console"] = search_console_data
```

### `has_data` check extended

```python
has_data = (
    ga4_data is not None
    or meta_data is not None
    or google_ads_data is not None
    or search_console_data is not None
    or bool(csv_sources)   # generate only; regenerate omits this
)
```

---

## 2. Downstream Pipeline Verification

**Every downstream consumer was already prepared** — Phase 1b only fixes the data-starvation bug.

| Consumer | Coverage already in place | Evidence |
|---|---|---|
| `services/ai_narrative.py` | Conditional section injection on `data["google_ads"]["summary"]` and `data["search_console"]["summary"]`; section instructions defined; user prompt includes Google Ads + SC metrics | Lines 172-173, 242-246, 318-319, 348-356 |
| `services/chart_generator.py` | Charts for Google Ads + Search Console (daily lines, campaign/query bars) | Lines 1222, 1234, 1273-1274 |
| `services/report_generator.py` | PPTX placeholders `{{google_ads_narrative}}` and `{{seo_narrative}}`, slide indexing for `google_ads_overview` | Lines 1542-1543, 1591 |
| `services/demo_data.py` | Mock Google Ads + SC dicts — already produces same shape as real pull | Lines 226, 266 |

**Net effect:** The first time a user with Google Ads and/or Search Console connections generates a report after this deploys, those platforms' data will flow all the way through to:
- AI narrative (new `google_ads_performance` + `seo_performance` sections)
- PPTX slides (Google Ads Overview + SEO Overview slides)
- `data_snapshots` (new rows per platform per period)

---

## 3. Design Notes

### Synchronous pull wrapping (`pull_google_ads_data` is sync)
The google-ads client library is synchronous. Wrapped with `asyncio.to_thread()` so it doesn't block the event loop during data fetching:
```python
gads_result = await asyncio.to_thread(
    pull_google_ads_data,
    access_token_encrypted=...,
    ...
)
```
`asyncio` is already imported at the top of `reports.py`.

### Empty-dict normalisation
Both new pull services return `{}` on failure (not an exception). The wrapper normalises empty dict to `None` so the existing `if data is not None:` guard pattern works uniformly:
```python
google_ads_data = gads_result if gads_result else None
```

### Token expiry handling
Parsed from the connection's `token_expires_at` (ISO string) into a unix timestamp for each pull. Mirrors the GA4 pattern exactly. For Google Ads, the docstring notes the token is refreshed internally by the google-ads client regardless — we pass it for interface consistency, and for future use by a connection-health probe.

### Snapshot-save placement
Snapshot calls stay **outside** the pull try/except, guarded by `if data is not None` — identical pattern to Phase 1. Guarantees a snapshot-save failure never nulls successfully-pulled data.

### Column names chosen
- `"google_ads"` and `"search_console"` match the `platform` CHECK constraint in migration 001:63.
- `account_id` semantics: for Google Ads it's the numeric customer ID; for Search Console it's the verified site URL or `sc-domain:` identifier. Both flow through unchanged from the OAuth callback.

---

## 4. Files Changed

| File | Change | Lines |
|---|---|---|
| `backend/routers/reports.py` | Wired Google Ads + Search Console pulls into both generate and regenerate flows; updated `raw_data` assembly + `has_data` check in both | +236 |
| `.claude/tasks/phase-1b-completion.md` | **NEW** — this file | — |
| `.claude/tasks/phase-roadmap.md` | Phase 1b tracked as complete | ~15 updated |

**No migrations. No env changes. No frontend changes. No new files in `backend/`** — everything reuses existing services + the Phase 1 snapshot saver.

---

## 5. Test Plan — Manual Verification Required

I cannot run end-to-end tests against live platform APIs from this environment (no credentials). Saurabh must run these:

### Prerequisite
A client with **all four** connections active: GA4 + Meta Ads + Google Ads + Search Console. If such a client doesn't exist, create one in staging or use an existing full-stack client.

### Test 1 — Generate a fresh report (all 4 platforms)
1. `POST /api/reports/generate` for the client.
2. **Check backend logs** — expect four "Using real <platform> data for client X" lines:
   ```
   Using real GA4 data for client <id>
   Using real Meta Ads data for client <id>
   Using real Google Ads data for client <id>
   Using real Search Console data for client <id>
   ```
3. **Check backend logs** — expect four "data_snapshots inserted" lines (one per platform).
4. **Check DB:**
   ```sql
   SELECT platform, period_start, period_end, pulled_at
   FROM data_snapshots
   WHERE client_id = '<test-client-id>'
   ORDER BY pulled_at DESC
   LIMIT 10;
   ```
   Expected: 4 rows, one per platform, all with today's `pulled_at`.
5. **Open the generated PPTX:**
   - Google Ads Overview slide now has content (was blank before Phase 1b).
   - SEO Overview slide now has content.
   - AI narrative preview contains `google_ads_performance` and `seo_performance` sections.

### Test 2 — Regenerate the same report (idempotency + regenerate path)
1. `POST /api/reports/{report_id}/regenerate` for the same report.
2. **Check backend logs** — expect four "data_snapshots updated" lines (not inserted).
3. **Check DB** — row count for that client should not increase. `pulled_at` should advance on all four rows.

### Test 3 — Partial connections (graceful degradation)
1. For a client with only GA4 + Google Ads (no Meta, no SC), generate a report.
2. Expected: two snapshot rows, two "Using real X data" logs, no errors, no "Using real Meta Ads" or "Using real Search Console" logs.
3. PPTX should omit the sections for absent platforms (existing behaviour — not Phase 1b code).

### Test 4 — Pull failure handling
1. Temporarily invalidate a Google Ads refresh token (e.g. revoke access at Google's account level).
2. Generate a report.
3. Expected: log contains `Real Google Ads pull failed for client <id>` (or the service's own error log). Report still generates successfully with data from remaining connected platforms. **No snapshot row** for Google Ads in this period (because the pull returned `{}`).

### Test 5 — Connection exists but pull service returns empty
1. For a new Google Ads account with zero historical data, generate a report.
2. Expected: `pull_google_ads_data` returns `{}` → `google_ads_data = None` → no snapshot row, no narrative section. No errors.

---

## 6. Known Limitations

1. **I cannot verify PPTX rendering for Google Ads + SC slides without running the generator** — the slide templates and chart code exist (confirmed via grep), but visual correctness of the new rendered slides needs Saurabh's eyeball check on Test 1.
2. **`data_summary` (DB-stored summary JSON)** still extracts only GA4 + Meta fields ([reports.py:399-417](backend/routers/reports.py)). Extending it would require corresponding frontend changes. Left for a future UX-only pass; does not affect snapshot saving or PPTX output.
3. **Connection ownership** is not re-checked on the new `google_ads` + `search_console` connection queries. Consistent with the existing GA4 + Meta pattern (ownership is verified once at the top of each function via the `clients` table). Acceptable but worth noting for security review.
4. **No health-probe integration** — Phase 2 will add pre-generation gating. Today, broken Google Ads / SC connections simply log exceptions and skip the platform, same as GA4/Meta today.
5. **CSV snapshot still uses plain INSERT** ([csv_upload.py:157](backend/routers/csv_upload.py)). Not Phase 1b scope; noted in Phase 1 audit §5.

---

## 7. Acceptance Criteria Check

Per your Path A instructions:

| Criterion | Status |
|---|---|
| 1. Wire `pull_google_ads_data()` into both `_generate_report_internal` and `regenerate_report` | ✅ Done — matches GA4/Meta pattern |
| 2. Wire `pull_search_console_data()` same way | ✅ Done |
| 3. Add snapshot_saver hooks for both new platforms | ✅ Done — 4 new hooks, same outside-try-except pattern as Phase 1 |
| 4. Verify ai_narrative.py already handles google_ads + search_console sections | ✅ Verified — see §2 |
| 5. Test end-to-end with a client that has all 4 connections | ⏳ Manual — test plan in §5; requires Saurabh to run |
| 6. Produce `.claude/tasks/phase-1b-completion.md` with test results | ✅ Done — test plan here; results pending manual run |
| 7. Update `phase-roadmap.md` | ✅ Done |
| 8. STOP for your review before Phase 2 | ✅ Stopping now |

---

## 8. What's Ready for Your Review

1. **Run the 5 tests in §5.** Test 1 is the critical one — confirms all 4 platforms flow through end-to-end.
2. **Inspect diff:** [backend/routers/reports.py](backend/routers/reports.py) — search for `platform="google_ads"` and `platform="search_console"` to land at the new blocks.
3. **Commit decision:** if tests pass, ready to commit. Suggested message:
   ```
   feat: wire Google Ads + Search Console data pulls (Phase 1b / Path A)
   ```

---

## STOP

Phase 1b is complete. Awaiting your verification of the test plan before starting Phase 2 (Connection Health Monitor).
