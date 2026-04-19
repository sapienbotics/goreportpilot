# Phase 1 — Native Data Pull Audit

**Produced:** 2026-04-19
**Scope:** Every native-platform data pull path relevant to snapshot persistence.
**Goal:** Document where pulls happen so snapshot-save hooks land in the right places — and flag anything that isn't actually running.

---

## 1. Table of Service Modules

| Service module | Main function | Async? | Takes `supabase`? | Takes `connection_id`? | Called from |
|---|---|---|---|---|---|
| `services/google_analytics.py` | `pull_ga4_data()` | ✅ async | ✅ yes | ✅ yes | `routers/reports.py` (2 call sites) |
| `services/meta_ads.py` | `pull_meta_ads_data()` | ✅ async | ❌ no | ✅ yes (optional) | `routers/reports.py` (2 call sites) |
| `services/google_ads.py` | `pull_google_ads_data()` | ❌ sync | ❌ no | ❌ no | **NEVER CALLED** (dead code) |
| `services/search_console.py` | `pull_search_console_data()` | ✅ async | ❌ no | ❌ no | **NEVER CALLED** (dead code) |
| `routers/csv_upload.py` | CSV upload flow | ✅ async | (uses admin client) | creates its own connection | already saves to `data_snapshots` (see §5) |

---

## 2. Call-Site Inventory (Where Pulls Actually Execute)

Only two routers invoke data pulls, both in `backend/routers/reports.py`:

### 2a. `_generate_report_internal` (line 100) — primary generation pipeline
- **GA4 pull** at [reports.py:217](backend/routers/reports.py). Guarded by `if ga4_conn_result.data:`. Inside a try/except that nulls `ga4_data` on failure.
- **Meta Ads pull** at [reports.py:253](backend/routers/reports.py). Same guard pattern.

### 2b. `regenerate_report` (line 1037) — `POST /api/reports/{id}/regenerate`
- **GA4 pull** at [reports.py:1127](backend/routers/reports.py). Duplicated orchestration (same token-parsing + error-handling logic as 2a).
- **Meta Ads pull** at [reports.py:1157](backend/routers/reports.py). Same.

**4 hook points total.** Both functions use locally-scoped `supabase` (param or `get_supabase_admin()`); the saver can call it directly without plumbing changes.

---

## 3. Critical Audit Finding — Google Ads & Search Console Are Dead Code

**Problem:** `pull_google_ads_data()` and `pull_search_console_data()` are fully implemented and exported, but **never invoked anywhere in the codebase**:

```
$ grep -rn "pull_google_ads_data\|pull_search_console_data" backend/ --include="*.py" \
    | grep -v "def pull_\|logger.error"
(no matches outside definitions + error-log format strings)
```

**Supporting evidence:**
- `services/ai_narrative.py:242-246` reads `data.get("google_ads", {}).get("summary")` and `data.get("search_console", {}).get("summary")` — the AI narrative is *prepared* to emit sections for these platforms.
- `services/demo_data.py:226,266` contains `"google_ads"` and `"search_console"` mock dicts — demo mode renders these sections correctly.
- `routers/admin_analytics.py:287,288` counts connections by platform, including `google_ads` and `search_console` — these connections CAN be created in production.
- `routers/auth.py:374,401,459,486` — OAuth flows for Google Ads and Search Console exist and work (connection rows do get written).

**Net effect:** A user can connect Google Ads + Search Console to a client through the UI. The OAuth succeeds, the connection row saves. **But when they generate a report, neither platform's data is pulled** — `raw_data` only contains `ga4` and `meta_ads` keys. The AI narrative omits the SEO / Google Ads sections (because their `summary` key is absent). Users who paid for these integrations are getting reports that silently ignore them.

**Remediation — not Phase 1 work, flagged for Saurabh's decision:**

There are two reasonable paths forward. Recommend path A:

**Path A (recommended):** Wire Google Ads and Search Console into both `_generate_report_internal` and `regenerate_report`. Add snapshot-save hooks at the same time. Estimated effort: half a day including testing.

**Path B:** Explicitly delete the unused pull services and OAuth flows until the integration is wired end-to-end. Reduces surface area but throws away work.

Either way, the current state is a bug — connections accepted but not used. Recommend Path A is scheduled either as a tail task on Phase 1 (with your approval) or as its own mini-phase before Phase 2.

---

## 4. What Was Hooked in Phase 1

All four currently-live native-pull call sites now invoke `save_snapshot()`:

| File | Function | Platform | Line hooked after |
|---|---|---|---|
| `routers/reports.py` | `_generate_report_internal` | `ga4` | after GA4 try/except |
| `routers/reports.py` | `_generate_report_internal` | `meta_ads` | after Meta try/except |
| `routers/reports.py` | `regenerate_report` | `ga4` | after GA4 try/except |
| `routers/reports.py` | `regenerate_report` | `meta_ads` | after Meta try/except |

**Design choice:** The save call is placed **outside** the pull's try/except, guarded by `if ga4_data is not None` / `if meta_data is not None`. This ensures a snapshot-save failure can never null the successfully-pulled data. Combined with the helper's own internal try/except, this is belt-and-suspenders — the report flow is insulated from any snapshot failure mode.

Google Ads / Search Console are **not** hooked because there is nothing to hook — they don't run. When Path A ships, the same hook pattern applies.

---

## 5. CSV Uploads — Already Save, but Not Idempotent

`routers/csv_upload.py:157` already inserts to `data_snapshots`. However:

1. It uses a **plain INSERT**, not an upsert. Re-uploading the same day creates a duplicate row.
2. Its `period_start` and `period_end` are both set to today's date — CSV is treated as a point-in-time import, not a date-range snapshot.

Out of Phase 1 scope but worth a 15-minute cleanup pass later — swap the plain insert for a call to the new `save_snapshot()` helper so CSV uploads also benefit from idempotency.

---

## 6. Schema Compatibility

`data_snapshots` schema ([001_initial_schema.sql:83](supabase/migrations/001_initial_schema.sql)) matches the saver's payload 1:1 — no migration required for Phase 1.

| Column | Saver writes | Notes |
|---|---|---|
| `connection_id` | ✅ | from call site |
| `client_id` | ✅ | from call site |
| `platform` | ✅ | `"ga4"` or `"meta_ads"` |
| `period_start` / `period_end` | ✅ | ISO date strings |
| `metrics` | ✅ | full parsed dict from pull service |
| `raw_response` | optional | empty dict for now; reserved for future |
| `pulled_at` | ✅ | UTC ISO timestamp |
| `is_valid` | ✅ | true (Phase 2 health-check will flag invalid later) |

**Indexes already in place** ([001_initial_schema.sql:198-200](supabase/migrations/001_initial_schema.sql)):
- `idx_data_snapshots_client_id` on `client_id`
- `idx_data_snapshots_connection_id` on `connection_id`
- `idx_data_snapshots_period` on `(client_id, period_start, period_end)`

The saver's SELECT uses `connection_id + period_start + period_end`. The existing index covers it sufficiently; no new index needed.

---

## 7. Logical Upsert Key

There is **no DB unique constraint** on `(connection_id, period_start, period_end)` today. The saver implements upsert via explicit SELECT → UPDATE/INSERT instead of `ON CONFLICT`. Trade-offs:

- ✅ Works without a schema migration.
- ✅ Can ship Phase 1 immediately.
- ⚠ Tiny race window: two concurrent saves for the same tuple could both see "no existing row" and both INSERT. Extremely low probability in practice (same report regeneration happens in a single process).
- 📝 Future improvement (optional): add `UNIQUE (connection_id, period_start, period_end)` to `data_snapshots` in a later migration, then switch the saver to `upsert()`. Not required for Phase 1's acceptance criteria.

---

## 8. Test Plan for User Verification

1. Ensure a client has at least one active GA4 or Meta Ads connection.
2. Generate one report (`POST /api/reports/generate`).
3. In Supabase SQL Editor:
   ```sql
   SELECT id, platform, period_start, period_end, pulled_at
   FROM data_snapshots
   WHERE client_id = '<the-test-client-id>'
   ORDER BY pulled_at DESC
   LIMIT 10;
   ```
   Expected: 1 row per connected platform (1 if only GA4, 1 if only Meta, 2 if both).
4. Regenerate the same report (`POST /api/reports/{id}/regenerate`).
5. Repeat the SELECT. Expected: **same row count** (no new inserts). `pulled_at` should advance on the updated rows.
6. Inspect backend logs for `data_snapshots inserted` (first run) and `data_snapshots updated` (second run) log lines.

A negative test is also worth running:
7. Force a snapshot failure (e.g. temporarily revoke `service_role` permissions on `data_snapshots`). Regenerate a report. Expected: report still generates successfully; backend log contains `save_snapshot failed (non-fatal)` but no user-visible error.
