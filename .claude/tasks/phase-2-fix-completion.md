# Phase 2 Bug Fixes — Duplicate Connections + Google `expiring_soon`

**Status:** ✅ Complete — awaiting user verification.
**Completed:** 2026-04-19
**Scope:** Two stacked bugs surfaced by real-world Search Console + GA4 reconnects.

---

## Bug A — Duplicate connections per (client, platform)

### Symptom
Dashboard health widget showed "Videogenie · Google Analytics" listed twice. Each OAuth reconnect was creating a new `connections` row instead of updating the existing one.

### Root cause
`create_connection()` deduped on `(client_id, platform, account_id)`. On a reconnect the user frequently re-picks a GA4 property — either because the picker re-renders all properties fresh or because the user deliberately chooses a different property. When the new `account_id` differed from the stored one (e.g. `properties/12345` vs `properties/67890`, or even trailing-whitespace differences), the dedup query returned no match → `INSERT` created a second row.

Compounding factor: the UX shows exactly one "integration per platform per client." Two rows then appeared as two widget cards with no way to tell them apart.

### Fix
**`backend/routers/connections.py` — dedup key simplified.** Now `(client_id, platform)` only. If the user picks a different property on reconnect, the single row's `account_id` is overwritten — which is semantically correct, since each client can only have one active OAuth-connected integration per platform at a time.

**Defensive runtime cleanup.** If the SELECT returns multiple rows (from pre-fix duplicates still sitting in the DB), we delete the extras and UPDATE the first. Belt-and-suspenders — should be a no-op after migration 015 runs, but guards the gap between deploy and migration.

**Migration 015 — history cleanup + DB safety net.**
`supabase/migrations/015_dedupe_connections.sql`:
1. `DELETE` duplicates, keeping the newest row per `(client_id, platform)` for non-CSV platforms. CSV uploads legitimately create multiple `csv_*` rows per client and are explicitly excluded via `WHERE platform NOT LIKE 'csv\_%' ESCAPE '\'`.
2. Adds a `PARTIAL UNIQUE INDEX idx_connections_unique_oauth_per_client ON (client_id, platform) WHERE platform NOT LIKE 'csv\_%'`. DB-level constraint that prevents any future code path from reintroducing duplicates.

---

## Bug B — Google platforms flip to `expiring_soon` right after reconnect

### Symptom
Immediately after a successful GA4 / Google Ads / Search Console reconnect, `health_status` became `'expiring_soon'` even though the user just completed a fresh OAuth flow.

### Root cause
`token_expires_at` stores the **access token**'s expiry. For Google OAuth, that's **1 hour**. My `_is_expiring_soon()` threshold was 7 days. Result: `now < expiry <= 7 days` was always `true` for any Google connection (1 hour is always ≤ 7 days), so every probe flagged every Google platform as `expiring_soon` regardless of whether the integration was actually at risk.

The stored 1-hour expiry was always going to expire within 7 days — that's a categorical property of Google access tokens, not a signal that the integration is in trouble. The real long-lived credential for Google is the `refresh_token`, which has no stored expiry (Google revokes it only on explicit user action).

For Meta, by contrast, `token_expires_at` stores the **long-lived 60-day access token** (Meta issues one after the short→long token swap). Warning 7 days before that expires IS useful — Meta tokens can't be auto-refreshed the way Google's can.

### Fix
**`backend/services/health_check.py` — platform-aware expiry check.** `_is_expiring_soon()` now takes `platform` as a parameter and returns `False` for anything that isn't `meta_ads`. Google platforms only transition between `healthy` ↔ `broken`, driven by whether the actual probe API call succeeds (which internally auto-refreshes the access token via `_get_valid_access_token`).

Meta's 7-day `expiring_soon` warning stays intact — that's the one platform where the user genuinely needs to act before expiry.

Updated the caller in `_probe_one_connection` to pass `platform` through.

---

## Files Changed

| File | Change |
|---|---|
| `backend/routers/connections.py` | Dedup now `(client_id, platform)`; defensive cleanup when multiple rows exist; rest of create_connection logic unchanged |
| `backend/services/health_check.py` | `_is_expiring_soon(platform, ...)` — returns `False` for non-Meta platforms; caller updated |
| `supabase/migrations/015_dedupe_connections.sql` | **NEW** — dedup cleanup + partial unique index |
| `.claude/tasks/phase-2-fix-completion.md` | **NEW** — this file |

---

## Verification Done In-Session

- ✅ Python `ast.parse` clean on both modified modules
- ✅ SQL manually reviewed for CSV exclusion + partial-index syntax

---

## Test Plan — Manual Verification Required

### Prerequisite
Run migration 015 in Supabase SQL Editor:
```sql
-- Paste contents of supabase/migrations/015_dedupe_connections.sql
```
You should see a confirmation of deleted rows (however many duplicates existed) + the partial unique index created.

### Test 1 — Cleanup worked, no duplicates remain
```sql
SELECT client_id, platform, COUNT(*) AS n
FROM connections
WHERE platform NOT LIKE 'csv\_%' ESCAPE '\'
GROUP BY client_id, platform
HAVING COUNT(*) > 1;
```
**Expected:** 0 rows.

### Test 2 — Widget now shows each connection once
Load the dashboard. Expand the connection health widget. For the Videogenie client, GA4 should appear exactly once.

### Test 3 — Reconnect updates, does not duplicate
1. For an already-connected client, click Reconnect in the widget or integrations card.
2. Complete the OAuth flow.
3. In Supabase:
   ```sql
   SELECT id, platform, account_id, status, health_status, created_at, updated_at
   FROM connections
   WHERE client_id='5dfa44ea-b73b-4e15-b21f-139eebd7164f'
   ORDER BY updated_at DESC;
   ```
**Expected:** Same number of rows as before the reconnect (no new row inserted). The row's `updated_at` advanced, `status='active'`, `health_status='healthy'`.

### Test 4 — Google platform stays `healthy` after reconnect
Right after a GA4 / Google Ads / Search Console reconnect:
```sql
SELECT platform, health_status, token_expires_at, last_health_check_at
FROM connections
WHERE client_id='<client_id>'
  AND platform IN ('ga4','google_ads','search_console');
```
**Expected:** `health_status='healthy'` (NOT `'expiring_soon'`), `last_health_check_at` within the last 10 seconds (inline post-reconnect probe). `token_expires_at` will be ~1 hour out — that's normal for Google and no longer triggers `'expiring_soon'`.

### Test 5 — Google platform stays `healthy` across multiple sweeps
Wait 2 hours. The stored access token is now expired (1-hour lifetime). At the next 6-hour sweep tick:
- `_probe_search_console` / `_probe_ga4` call `_get_valid_access_token` → detect expiry → refresh via Google's OAuth endpoint → write refreshed token back to DB → probe the API → success
- `health_status` stays `'healthy'`

Verify by watching backend logs — after a probe sweep, you should see `GA4 access token expired for connection ... — refreshing` messages, NOT `SC auth rejected (401)` or similar.

### Test 6 — Meta's expiring_soon warning still works
If you have a Meta Ads connection with `token_expires_at` under 7 days out, the next sweep should flag it `expiring_soon`. Force this in SQL:
```sql
UPDATE connections
SET token_expires_at = NOW() + INTERVAL '3 days'
WHERE platform = 'meta_ads' AND client_id = '<client_id>';
```
Trigger an immediate probe via `POST /api/connections/{id}/probe` or wait for the next sweep. Expected: `health_status='expiring_soon'`, expiring alert email fires (once).

### Test 7 — Partial unique index blocks manual duplicate insertion
Try to insert a duplicate manually in SQL:
```sql
INSERT INTO connections (client_id, platform, account_id, access_token_encrypted)
VALUES ('<existing_client_id>', 'ga4', 'bogus', 'bogus');
```
**Expected:** `ERROR: duplicate key value violates unique constraint "idx_connections_unique_oauth_per_client"`. The DB safety net is working.

### Test 8 — CSV uploads still allow multiple rows per client
CSVs are excluded from the unique index — they legitimately create multiple `csv_<slug>` rows per client. Upload two different CSVs for the same client via the existing flow; both should succeed.

---

## Root Cause Quick-Reference

| Bug | Why it happened |
|---|---|
| A — Duplicate connection rows | `create_connection` deduped on `(client_id, platform, account_id)`; reconnects with different property pick inserted a 2nd row |
| B — Google `expiring_soon` immediately | `_is_expiring_soon` treated 1-hour access-token expiry the same as Meta's 60-day long-lived token; Google tokens auto-refresh so expiry is meaningless there |

---

## Known Follow-ups (Not This Fix)

1. **Frontend "Check now" button.** `POST /api/connections/{id}/probe` exists from the earlier fix. UI-side wire-up is not in this commit — user can add a button on the integrations page card if wanted.
2. **History audit of pre-fix duplicates.** Migration 015 keeps the **newest** row per (client_id, platform). If an older row had better `health_status` or `alerts_sent` state worth preserving, that's lost. Acceptable — the newest row carries the freshest tokens.
3. **Google token revocation detection.** If a user revokes GoReportPilot's access externally (at Google My Account), the refresh token stops working. The next probe's `_get_valid_access_token` will fail → probe returns broken → alert fires. Already handled by existing probe error paths.

---

## STOP

Phase 2 bug fixes complete. Awaiting your verification.
