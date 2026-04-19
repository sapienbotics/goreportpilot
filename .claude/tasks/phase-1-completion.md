# Phase 1 — Completion Summary

**Status:** ✅ Complete — awaiting user verification.
**Completed:** 2026-04-19
**Elapsed:** ~1 day estimated in plan.

---

## What Was Built

A non-intrusive snapshot-saving layer that persists every successful native-platform data pull (GA4, Meta Ads) into `data_snapshots` with idempotent upsert semantics. The table already existed in migration 001 but was empty for native pulls — Phase 1 fixes that so future trend-detection features (Phase 7) have data to work with in 3 months.

---

## Files Changed

| File | Change | Lines |
|---|---|---|
| `backend/services/snapshot_saver.py` | **NEW** — `save_snapshot()` helper with idempotent SELECT→UPDATE/INSERT logic, bulletproof non-fatal error handling | 87 |
| `backend/routers/reports.py` | Added 4 save-snapshot hook calls (2 in `_generate_report_internal`, 2 in `regenerate_report`) | +48 |
| `.claude/tasks/phase-roadmap.md` | **NEW** — tracks all 6 phases | 108 |
| `.claude/tasks/phase-1-snapshot-audit.md` | **NEW** — audit findings, includes critical Google Ads / Search Console dead-code finding | 138 |
| `.claude/tasks/phase-1-completion.md` | **NEW** — this file | — |

**No migrations.** `data_snapshots` schema from migration 001 already matches. No env vars. No frontend changes.

---

## Design Decisions

1. **Placement outside pull try/except.** The save call is placed after each try/except block, guarded by `if data is not None`. This guarantees a snapshot-save failure can never null out successfully-pulled real data. The saver also wraps its own body in try/except so nothing propagates upward either way.

2. **Explicit SELECT → UPDATE/INSERT** instead of `ON CONFLICT`. The DB has no unique constraint on `(connection_id, period_start, period_end)` today — implementing upsert this way avoids a migration in Phase 1. Trade-off documented in audit §7; tiny race window acceptable for current scale.

3. **Inline imports.** Matches the existing pattern in `reports.py` (`from services.x import y  # noqa: PLC0415` inside functions) rather than introducing top-of-file imports.

4. **CSV already saves, not touched.** `csv_upload.py:157` already writes to `data_snapshots` (with plain INSERT, no idempotency). Out of Phase 1 scope; noted for future cleanup in audit §5.

---

## How to Test (user verification steps)

Full step-by-step plan is in [phase-1-snapshot-audit.md §8](.claude/tasks/phase-1-snapshot-audit.md). Summary:

1. **Positive path — single pull:** Generate a report for a client with an active GA4 or Meta Ads connection. Verify `data_snapshots` has 1 new row per connected platform.
2. **Positive path — idempotent:** Regenerate the same report. Row count should not increase; `pulled_at` advances on the existing row.
3. **Logs:** Backend should log `data_snapshots inserted` on first run, `data_snapshots updated` on subsequent runs.
4. **Negative path — non-fatal:** Revoke write permission on `data_snapshots` (temporarily), regenerate a report. Report should complete successfully; backend log contains `save_snapshot failed (non-fatal)`.

Quick SQL:
```sql
SELECT platform, period_start, period_end, pulled_at
FROM data_snapshots
WHERE client_id = '<test-client-id>'
ORDER BY pulled_at DESC;
```

---

## Known Limitations

1. **Google Ads and Search Console are dead code** — defined but never invoked. Audit §3 documents this. Requires your decision before Phase 2:
   - **Path A (recommended):** Wire them up + add snapshot hooks (~half day).
   - **Path B:** Delete unused pull services + OAuth flows.
   - **Path C:** Defer and proceed to Phase 2 as planned.
2. **`raw_response` field always `{}`.** Phase 1 stores only the parsed `metrics` dict. The raw API response isn't exposed cleanly by the pull services without a refactor. Acceptable — the parsed dict is rich enough for later trend analysis.
3. **No unique constraint** on `(connection_id, period_start, period_end)`. Theoretical race window on concurrent regenerations. Low-priority schema cleanup noted in audit §7.
4. **CSV path still uses plain INSERT.** Out of Phase 1 scope (not a "native" data pull). Fifteen-minute fix when time allows — swap the insert for a call to `save_snapshot()`.

---

## Acceptance Criteria Check

From the master build prompt:

| Criterion | Status |
|---|---|
| Generate 1 test report → 2-4 rows appear in `data_snapshots` (one per connected platform) | ✅ Implemented — user must verify with their real connections |
| Regenerate same report → no duplicate rows (update only) | ✅ Implemented — idempotent via SELECT→UPDATE/INSERT |
| Document the audit findings in `.claude/tasks/phase-1-snapshot-audit.md` | ✅ Done — includes dead-code finding for Google Ads / SC |

---

## What's Ready for Your Review

1. **Read:** [phase-1-snapshot-audit.md](.claude/tasks/phase-1-snapshot-audit.md) — pay special attention to §3 (Google Ads / Search Console dead-code finding).
2. **Read:** [phase-roadmap.md](.claude/tasks/phase-roadmap.md) — confirms all 6 phases are tracked.
3. **Inspect:** [backend/services/snapshot_saver.py](backend/services/snapshot_saver.py) — the new helper (87 lines).
4. **Inspect diff:** [backend/routers/reports.py](backend/routers/reports.py) — 4 new hook blocks, each ~13 lines. No changes to existing orchestration logic.
5. **Run:** the test plan in audit §8.
6. **Decide:** Path A / B / C for the Google Ads + Search Console finding before Phase 2 kicks off.

---

## STOP

Phase 1 is complete. Awaiting your verification + decision on the Google Ads / Search Console finding before starting Phase 2.
