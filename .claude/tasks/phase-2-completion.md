# Phase 2 — Connection Health Monitor

**Status:** ✅ Complete — awaiting user verification.
**Completed:** 2026-04-19
**Scope:** Periodic health probing for every OAuth connection, idempotent alert emails, pre-generation gating, dashboard widget.

---

## 1. What Was Built

### Migration
- `supabase/migrations/013_connection_health.sql` (additive, `IF NOT EXISTS`, idempotent). Adds to `connections`:
  - `last_health_check_at TIMESTAMPTZ`
  - `health_status VARCHAR(20) DEFAULT 'healthy'` with CHECK (`healthy|warning|broken|expiring_soon`)
  - `alerts_sent JSONB DEFAULT '{}'::jsonb` — tracks idempotency per alert type
  - Index `idx_connections_health_status`
  - Back-fills existing rows with `'healthy'`
- **Note:** `last_error_message` column was already in migration 001 — not re-added.

### Backend services
| File | Change | What it does |
|---|---|---|
| `backend/services/health_check.py` | **NEW** (~400 lines) | Core health-probe engine |
| `backend/services/scheduler.py` | +36 lines | `check_and_run_health_checks()` with 6h cadence |
| `backend/services/snapshot_saver.py` | +15 lines | Post-save hook calls `check_suspicious_zero_data()` |
| `backend/main.py` | +6 lines | Main scheduler loop now calls health checks each tick |
| `backend/routers/reports.py` | +51 lines | Pre-generation gate in both generate + regenerate |
| `backend/routers/dashboard.py` | +104 lines | New `GET /api/dashboard/connection-health` endpoint |

### Frontend
| File | Change |
|---|---|
| `frontend/src/components/dashboard/connection-health-widget.tsx` | **NEW** — full widget |
| `frontend/src/app/dashboard/page.tsx` | Replaced inline Connection Health card with widget; pruned orphaned imports |
| `frontend/src/app/dashboard/integrations/page.tsx` | Widget added at top |

---

## 2. How It Works

### Probe cadence
- `main.py` scheduler loop runs every **15 minutes**.
- Each tick calls `check_and_run_scheduled_reports()` and then `check_and_run_health_checks()`.
- `check_and_run_health_checks()` uses a module-level `_last_health_check_ts` timer and short-circuits unless **6 hours** have passed. First boot after deploy → immediate sweep.

### Per-platform probes
Each is the cheapest meaningful auth check for that platform:
| Platform | Probe |
|---|---|
| GA4 | GET `analyticsadmin.googleapis.com/v1beta/{property}` (token refresh via `_get_valid_access_token`) |
| Meta Ads | GET `graph.facebook.com/v21.0/me?fields=id` |
| Google Ads | `customer_service.list_accessible_customers()` (wrapped in `asyncio.to_thread`) |
| Search Console | GET `webmasters/v3/sites` |

### Batching
- 50 connections per batch (`BATCH_SIZE`)
- 30-second sleep between batches (`BATCH_JITTER_SECONDS`)
- 15s per-probe HTTP timeout

### Health-status transitions
```
probe OK + expires > 7d   → health_status = 'healthy'
probe OK + expires ≤ 7d   → health_status = 'expiring_soon'
probe fails                → health_status = 'broken'
```
(`'warning'` is set out-of-band by the zero-data detector.)

### Idempotent alert emails
`alerts_sent jsonb` tracks per-alert ISO timestamps. Logic:
- **Broken:** fires once on transition (`old != 'broken' && new == 'broken'`). Clears when status leaves broken.
- **Expiring:** fires once while `health_status == 'expiring_soon'` and the key isn't already present. Clears when status leaves expiring_soon (so reconnection re-arms for the next cycle).
- **Zero-data:** fires once per zero-data streak. Clears when a non-zero pull arrives.

All three emails use a single `_send_alert_email()` builder with a minimal branded HTML template. Recipient = `profiles.agency_email || profiles.email`.

### Suspicious zero-data detection
Called from `snapshot_saver.save_snapshot()` after every successful upsert:
- Current pull zero + last 2 snapshots non-zero → `health_status = 'warning'` + fire alert once
- Current pull non-zero → clear `alerts_sent.zero_data`, downgrade status from warning → healthy

Primary metric per platform:
- GA4 → `summary.sessions`
- Meta/Google Ads/Search Console → `summary.impressions`

### Pre-generation gate
In both `_generate_report_internal` and `regenerate_report`, after client-ownership check:
```python
unhealthy = (supabase.table("connections")
    .select("id,platform,health_status")
    .eq("client_id", client_id)
    .in_("health_status", ["broken", "expiring_soon"])
    .execute())
if unhealthy.data and not csv_sources:
    raise HTTPException(422, detail=...)
```
- Returns HTTP 422 with a human-readable list like: *"meta_ads (broken), google_ads (expiring_soon). Open the Integrations page and reconnect."*
- Bypass when `csv_sources` are supplied to the primary generate (CSV-only reports don't need OAuth health).
- `warning` does NOT block — it's informational.

### Dashboard endpoint
`GET /api/dashboard/connection-health` returns:
```json
{
  "summary":     {"total": 8, "healthy": 5, "warning": 1, "broken": 1, "expiring_soon": 1},
  "by_platform": {"ga4": {"connected": 3, "healthy": 3, ...}, ...},
  "issues":      [ top-3 by severity with client_name, platform, error ... ]
}
```

### Widget
- 4 count tiles (Healthy / Expiring / Warning / Broken) with colour-coded icons
- Top-3 problem connections with status badges + `Reconnect` CTA linking to `/dashboard/integrations`
- Refresh button (calls the endpoint again)
- Empty state (no connections yet) + all-healthy state
- Reusable via `title` prop — dashboard uses default "Connection Health"; integrations page uses "Connection health (all clients)"

---

## 3. Files Changed

| File | Lines |
|---|---|
| `supabase/migrations/013_connection_health.sql` | +45 (new) |
| `backend/services/health_check.py` | +418 (new) |
| `backend/services/scheduler.py` | +36 |
| `backend/services/snapshot_saver.py` | +15 |
| `backend/main.py` | +6 / -2 |
| `backend/routers/reports.py` | +51 |
| `backend/routers/dashboard.py` | +104 |
| `frontend/src/components/dashboard/connection-health-widget.tsx` | +248 (new) |
| `frontend/src/app/dashboard/page.tsx` | +2 / -52 (widget replaces inline card) |
| `frontend/src/app/dashboard/integrations/page.tsx` | +5 |
| `.claude/tasks/phase-2-completion.md` | (this file) |
| `.claude/tasks/phase-roadmap.md` | updated |

---

## 4. Verification Done In-Session

- ✅ Python syntax: `ast.parse` on all 6 modified/new modules
- ✅ TypeScript: `npx tsc --noEmit` clean (no errors)
- ✅ Grep: all snapshot hooks intact from Phase 1 (8 total still present)
- ✅ No circular imports (health_check imports google_analytics helpers; both are leaf modules relative to supabase_client)

---

## 5. Test Plan — Manual Verification Required

### Prerequisite
Run migration 013 in Supabase SQL Editor:
```sql
-- Paste contents of supabase/migrations/013_connection_health.sql
```
Then restart the backend so the scheduler loop picks up the new cadence.

### Test 1 — Boot-time sweep populates health_status
1. After deploy + migration, wait up to 15 minutes for the first scheduler tick.
2. In Supabase SQL Editor:
   ```sql
   SELECT platform, health_status, last_health_check_at, last_error_message
   FROM connections
   WHERE platform NOT LIKE 'csv_%'
   ORDER BY last_health_check_at DESC NULLS LAST;
   ```
3. Expected: every row has `last_health_check_at` within the last ~6 hours, `health_status` set (mostly `healthy`).
4. Backend logs contain: `Health check: probing N connection(s)` and `Health check complete in X.Xs`.

### Test 2 — Broken-connection gate
1. Pick a client. In Supabase:
   ```sql
   UPDATE connections SET health_status = 'broken'
   WHERE client_id = '<client_id>' AND platform = 'ga4';
   ```
2. Try to generate a report via the UI (or POST `/api/reports/generate`).
3. Expected: HTTP 422 with message: *"One or more platform connections need attention… ga4 (broken)… Open the Integrations page…"*
4. Same test for `expiring_soon` → same 422 response.
5. Reset the value back to `'healthy'` after testing.

### Test 3 — Dashboard widget renders
1. Log into the dashboard.
2. Expected: widget shows 4 count tiles + top-3 issues list (if any issues). If all healthy, shows ✓ All connections healthy.
3. Click a Reconnect link → routes to `/dashboard/integrations`.
4. Refresh button spins, re-fetches.

### Test 4 — Integrations page widget renders
1. Navigate to `/dashboard/integrations`.
2. Expected: widget appears at top, titled "Connection health (all clients)".

### Test 5 — Broken-alert email fires once
1. In Supabase, clear any alerts_sent entries on a test connection:
   ```sql
   UPDATE connections SET alerts_sent = '{}' WHERE id = '<connection_id>';
   ```
2. Revoke the OAuth token externally (e.g. remove GoReportPilot at `https://myaccount.google.com/permissions`) so the probe fails.
3. Wait for the next 6-hour health sweep (or force by restarting backend — cadence counter resets on process restart).
4. Expected:
   - `connections.health_status = 'broken'`
   - `alerts_sent = {"broken": "<iso timestamp>"}`
   - Alert email arrives at the agency owner's address
5. Run a 2nd sweep (wait another 6 hours or restart). Still broken → **no second email** (idempotent).
6. Reconnect via the UI. Next sweep → status = healthy, `alerts_sent.broken` cleared.

### Test 6 — Expiring-soon alert
1. Set `token_expires_at` to ~3 days out:
   ```sql
   UPDATE connections
   SET token_expires_at = NOW() + INTERVAL '3 days',
       alerts_sent = '{}',
       health_status = 'healthy'
   WHERE id = '<connection_id>';
   ```
2. Trigger a sweep. Expected: status = `expiring_soon`, alert email sent, `alerts_sent.expiring` set.
3. Second sweep while still expiring → no duplicate email.

### Test 7 — Suspicious zero-data warning
1. Generate 2 real reports for the same client/platform in different periods to build non-zero snapshot history.
2. Simulate a zero-data pull — either disconnect the tracking tag temporarily, or create a fresh test client with a valid connection but an empty property for the current period.
3. Generate a 3rd report.
4. Expected:
   - New `data_snapshots` row written with zero metrics
   - `connections.health_status = 'warning'`
   - `alerts_sent.zero_data` populated
   - Warning email arrives
5. Restore real data and generate again → warning clears, `health_status` back to `'healthy'`.

### Test 8 — Probe failure doesn't break the sweep
1. Introduce a known bad token for one connection (e.g. set `access_token_encrypted` to garbage).
2. Trigger a sweep.
3. Expected: that connection becomes `broken`, other connections probe normally. Backend log has `Health probe failed for connection <id>` but the sweep completes.

---

## 6. Known Limitations & Follow-ups

1. **Alert emails are English-only.** Infrastructure is in place (`_build_alert_html` + per-line format strings) but the copy is hard-coded English. Translating to the 13 supported languages is a follow-up — the agency owner's profile doesn't currently expose a preferred language.
2. **Cadence resets on process restart.** `_last_health_check_ts` lives in memory. A deploy during the 6-hour window triggers an immediate sweep after boot. Acceptable; documented.
3. **Zero-data alert fires asynchronously from a sync context.** `_mark_warning_and_alert` schedules the async send via `asyncio.ensure_future` when an event loop is running, or `asyncio.run` otherwise. Under Railway's gunicorn+uvicorn worker model this should work, but edge cases around worker recycling could drop an alert. Accept for now; robustify in a later pass if needed.
4. **"Warning" status does NOT block generation.** Spec says block `broken` and `expiring_soon` only. Warning is informational. Documented.
5. **Ownership check on the gate query.** The gate queries `connections` by `client_id` only. Client ownership is already verified immediately above (`clients.user_id = auth.uid()`). Consistent with the existing pattern throughout `reports.py`.
6. **CSV-only regenerate path.** `regenerate_report` doesn't accept `csv_sources`, so its gate always runs. That's correct — you can't regenerate a CSV-only report without new CSVs, and there's no CSV to check against.
7. **No observability on alert delivery.** Email send success is logged (`Alert <key> sent to <addr>`) but not persisted per-connection. If you later want a "last alert delivered at" audit trail, extend `alerts_sent` to include delivery receipts.

---

## 7. Acceptance Criteria Check

Per the master build prompt:

| Criterion | Status |
|---|---|
| Migration 013 adds `last_health_check_at`, `health_status`, index | ✅ + `alerts_sent`; `last_error_message` already existed |
| `services/health_check.py` with per-platform probes | ✅ GA4 / Meta / Google Ads / Search Console |
| Batch 50 + 30s jitter | ✅ `BATCH_SIZE=50`, `BATCH_JITTER_SECONDS=30` |
| Suspicious-zero detection | ✅ Post-save hook in snapshot_saver |
| Plug into scheduler at 6h cadence | ✅ Via `_last_health_check_ts` timer |
| Pre-generation gate (422 on broken/expiring) | ✅ Both `_generate_report_internal` + `regenerate_report` |
| 3 email templates, idempotent | ✅ Broken / Expiring / Zero-data |
| i18n via `translations.py` | ⚠ English only — documented as follow-up (agency profile has no language field today) |
| `GET /api/dashboard/connection-health` | ✅ |
| `ConnectionHealthWidget.tsx` | ✅ + drop-ins to dashboard home + integrations page |
| Reconnect flow unchanged | ✅ No auth.py / connections.py changes — widget links to existing `/dashboard/integrations` |
| STOP for review | ✅ Stopping now |

---

## 8. What's Ready for Your Review

1. **Run migration 013** in Supabase SQL Editor.
2. **Deploy** to Railway (or restart local backend) so the scheduler loop picks up `check_and_run_health_checks`.
3. **Run the 8 tests in §5.** Test 1 is the gate — confirm `last_health_check_at` populates within 15 min.
4. **Inspect diffs** if you want code-level review:
   - Core: `backend/services/health_check.py`
   - Gate: `backend/routers/reports.py` (search "1c — Connection health pre-generation gate")
   - Widget: `frontend/src/components/dashboard/connection-health-widget.tsx`
5. **Commit decision** — when you're ready, suggested message:
   ```
   feat: phase 2 connection health monitor
   ```

---

## STOP

Phase 2 is complete. Awaiting your verification before Phase 3 (Custom Cover Page Editor).
