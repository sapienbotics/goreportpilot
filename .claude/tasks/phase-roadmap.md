# GoReportPilot Phase 1 & 2 Build — Roadmap

**Model:** Opus 4.7, xhigh effort.
**Started:** 2026-04-19
**Mode:** Sequential — one phase at a time, stop for user review after each.

---

## Phase Status Legend
- ⏳ in progress
- ✅ completed (awaiting user verification)
- 🟢 verified by user
- ⏸ blocked / waiting for user decision
- ⏭ not yet started
- 🐛 known issue

---

## Phase 1 — Snapshot-Saving Infrastructure (1 day)
**Status:** 🟢 verified by user 2026-04-19

**Purpose:** Start accumulating historical data so future MoM/YoY trend detection (deferred Phase 7) has data to work with in 3 months.

**Tasks:**
- ✅ Audit all four native-pull service modules + orchestration sites
- ✅ Identify hook points (2 call sites in `_generate_report_internal`, 2 in `regenerate_report`)
- ✅ Build idempotent `save_snapshot()` helper in new `backend/services/snapshot_saver.py`
- ✅ Wire save call into all 4 hook points (reports.py)
- ✅ Write `phase-1-snapshot-audit.md`
- ✅ Write `phase-1-completion.md`

**Key audit finding (requires user decision):** `pull_google_ads_data` and `pull_search_console_data` are DEFINED but NEVER CALLED. Only GA4 and Meta Ads data pulls run in production. See audit §3 for remediation paths (A/B/C).

**Acceptance criteria:**
- ✅ Code implements: idempotent save on successful GA4 + Meta pulls (both generate and regenerate flows)
- ⏳ User must verify: generate report → `data_snapshots` rows appear; regenerate → no duplicates
- ✅ Audit doc written

**Files changed:**
- NEW: `backend/services/snapshot_saver.py` (87 lines)
- MODIFIED: `backend/routers/reports.py` (+48 lines, 4 hook blocks)
- NEW: `.claude/tasks/phase-1-snapshot-audit.md`
- NEW: `.claude/tasks/phase-1-completion.md`

---

## Phase 1b — Path A: Wire Google Ads + Search Console (remediation)
**Status:** ✅ complete — awaiting user verification

**Purpose:** Remediate the dead-code finding from Phase 1 audit §3 — `pull_google_ads_data` and `pull_search_console_data` were defined but never invoked anywhere. Both now wired into production pull orchestration with matching snapshot hooks.

**Tasks:**
- ✅ Verify downstream pipeline (ai_narrative, chart_generator, report_generator, demo_data) already handles both platforms
- ✅ Wire Google Ads pull into `_generate_report_internal` (sync via `asyncio.to_thread`)
- ✅ Wire Search Console pull into `_generate_report_internal`
- ✅ Mirror both into `regenerate_report`
- ✅ Update `raw_data` assembly + `has_data` check (both functions)
- ✅ Add 4 new snapshot hooks (total 8 across both platforms × both functions)
- ✅ Syntax-verified via `ast.parse`
- ⏳ End-to-end test with all-4-connections client — awaits user run (5-test plan in phase-1b-completion.md §5)

**Files changed:**
- MODIFIED: `backend/routers/reports.py` (+236 lines)
- NEW: `.claude/tasks/phase-1b-completion.md`

---

## Phase 1b — Path A: Wire Google Ads + Search Console (remediation)
**Status:** 🟢 verified by user 2026-04-19

---

## Phase 2 — Connection Health Monitor (3 days)
**Status:** ✅ complete — awaiting user verification

**Tasks:**
- ✅ Migration `013_connection_health.sql` — adds `last_health_check_at`, `health_status`, `alerts_sent`, CHECK constraint, index
- ✅ New `services/health_check.py` (~418 lines) — 4 platform probes + batching + status transitions + alert emails
- ✅ 6h cadence via `_last_health_check_ts` timer in `scheduler.py` (NOT modulo on hourly — main loop is 15 min)
- ✅ "Suspicious zero data" detection in `snapshot_saver` post-save hook
- ✅ Pre-generation gate in `_generate_report_internal` + `regenerate_report` (HTTP 422 on broken/expiring_soon)
- ✅ Three alert emails via inline HTML builder + Resend (English-only; i18n is a documented follow-up)
- ✅ `GET /api/dashboard/connection-health` endpoint
- ✅ `connection-health-widget.tsx` (Phase 2 frontend) + dropped into dashboard home + integrations page
- ✅ Pruned orphaned imports in dashboard/page.tsx
- ✅ TypeScript + Python syntax clean
- ⏳ User must verify: run migration 013, then run 8-test plan in `phase-2-completion.md` §5

**Files changed:**
- NEW: `supabase/migrations/013_connection_health.sql`
- NEW: `backend/services/health_check.py`
- NEW: `frontend/src/components/dashboard/connection-health-widget.tsx`
- NEW: `.claude/tasks/phase-2-completion.md`
- MODIFIED: `backend/services/scheduler.py`, `backend/services/snapshot_saver.py`, `backend/main.py`, `backend/routers/reports.py`, `backend/routers/dashboard.py`, `frontend/src/app/dashboard/page.tsx`, `frontend/src/app/dashboard/integrations/page.tsx`

---

## Phase 3 — Custom Cover Page Editor (2 days)
**Status:** ✅ complete — awaiting user verification

**Tasks:**
- ✅ Migration `014_cover_customization.sql` — adds 4 cover_* columns + CHECK on preset
- ✅ `services/cover_presets.py` (~330 lines) — 5 preset style configs + `apply_cover_preset()` in-place modifier (NOT 5 PPTX files — deviation documented)
- ✅ Hook in `report_generator.py` after `_embed_logos`
- ✅ Hero image upload at `POST /{client_id}/cover-hero` → Supabase `logos` bucket `cover_heroes/` subfolder, 2MB
- ✅ `POST /api/reports/preview-cover` — returns PPTX bytes (PNG conversion deferred as documented follow-up)
- ✅ `CoverPageTab.tsx` — preset selector, headline/subtitle, hero uploader, CSS live mockup, PPTX download
- ✅ Client detail page: new 'cover' tab with ImageIcon
- ✅ Python `ast.parse` + `npx tsc --noEmit` both clean
- ⏳ User must verify: run migration 014, run 10-test plan in `phase-3-completion.md` §5

**Deviations from master prompt (documented in completion doc §6):**
1. No 5 PPTX variant files — Python style configs instead (refined plan §6 recommendation)
2. Preview endpoint returns PPTX, not 1280×720 PNG — CSS live mockup in tab covers instant preview; PPTX for pixel-perfect

**Files changed:**
- NEW: `supabase/migrations/014_cover_customization.sql`
- NEW: `backend/services/cover_presets.py`
- NEW: `frontend/src/components/clients/tabs/CoverPageTab.tsx`
- NEW: `.claude/tasks/phase-3-completion.md`
- MODIFIED: `backend/services/report_generator.py`, `backend/routers/clients.py`, `backend/routers/reports.py`, `backend/models/schemas.py`, `backend/main.py`, `frontend/src/app/dashboard/clients/[clientId]/page.tsx`, `frontend/src/types/index.ts`, `frontend/src/lib/api.ts`

---

## Phase 4 — Diagnostic AI Narrative v2 (3 days)
**Status:** ⏭ not yet started

**Tasks outline:**
- Pre-processing: `_compute_top_movers(data)` in `ai_narrative.py` (top 3 best/worst campaigns, traffic sources, landing pages)
- Inject TOP MOVERS block into user prompt
- Change output schema: every section returns `{text, evidence[]}`
- Dual-format support (wrap legacy string outputs)
- Mechanical confidence from `len(evidence)`: 3+ = high, 1-2 = medium, 0 = suppress
- Post-generation validation: no numbers allowed that aren't in source data
- Strict validation on `key_wins`, `concerns`, `next_steps` only
- Frontend: "Show reasoning" toggle per narrative section

---

## Phase 5 — Client Comments on Shared Reports (3 days)
**Status:** ⏭ not yet started

**Tasks outline:**
- Migration `015_report_comments.sql` (new `report_comments` table + `enable_comments` on `shared_reports`)
- Endpoints: POST/GET `/api/shared/{hash}/comments`, DELETE `/api/reports/comments/{id}`, POST reply
- Anti-spam: `slowapi` 5/hr/IP, honeypot, length guard
- Debounced 15-min digest email to agency owner
- Dashboard view: all comments filterable by client
- Frontend: comment thread on `shared/[hash]/page.tsx`, inline agency replies
- i18n (13 languages)

---

## Phase 6 — Goals & Alerts (4 days)
**Status:** ⏭ not yet started

**Tasks outline:**
- Migration `016_client_goals.sql` (new `client_goals` table + RLS)
- New `services/goal_evaluator.py`
- Plug into `scheduler.py` — daily default
- Skip eval if client's relevant connection is broken/warning (Phase 2 integration)
- Idempotent breach email (once per breach-streak), resolution email when back
- AI "why it breached" explanation (reuses Phase 4 narrative)
- Report integration: new "Goals Progress" slide before Next Steps
- Plan gating: Starter 1/client, Pro 3/client, Agency unlimited
- Frontend: "Goals" tab in client settings, dashboard widget

---

## Phase 7 — DEFERRED (MoM/YoY Trends)
**Status:** ⏸ blocked — waiting for `data_snapshots` to accumulate ≥3 months of history (projected June-July 2026)

No work now. Phase 1 starts the data accumulation.

---

## Cross-Cutting (applies to every phase)
- Structured logs with correlation IDs
- i18n via `services/translations.py` (13 languages)
- Never modify .env files
- Never auto-run migrations (user runs manually in Supabase)
- Never start dev servers
- `cd frontend && npx tsc --noEmit` after every frontend change
- Git commit after each change set with descriptive message (waits for user approval)
- Create `phase-N-completion.md` after each phase
- STOP for user review between phases
