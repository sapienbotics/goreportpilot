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
**Status:** ✅ complete — awaiting user verification

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

## Phase 2 — Connection Health Monitor (3 days)
**Status:** ⏭ not yet started

**Tasks outline:**
- Migration `013_connection_health.sql` (adds `last_health_check_at`, `health_status`, index)
- New `services/health_check.py` with `check_all_connections_health()`
- Per-platform cheap probes (GA4 properties.list, Meta me?fields=id, etc.)
- Batch + jitter (50 at a time, 30s sleeps)
- "Suspicious zero data" detection
- Plug into `scheduler.py` at 6h cadence via modulo on hourly tick
- Pre-generation gate in `_generate_report_internal` + `regenerate_report` (HTTP 422 on broken)
- Three email templates (broken, expiring, suspicious-zero) via `translations.py`
- Endpoint `GET /api/dashboard/connection-health`
- Frontend `ConnectionHealthWidget.tsx`

---

## Phase 3 — Custom Cover Page Editor (2 days)
**Status:** ⏭ not yet started

**Tasks outline:**
- Migration `014_cover_customization.sql` (adds `cover_design_preset`, `cover_headline`, `cover_subtitle`, `cover_hero_image_url` to clients)
- 5 cover-slide variants in `backend/templates/cover_variants/` (minimal, bold, corporate, hero, gradient)
- In-place shape modification in `report_generator.py` slide[0]
- Hero image upload via existing Supabase Storage `logos` bucket → `cover_heroes/` subfolder, 2MB cap
- `POST /api/reports/preview-cover` → 1280×720 PNG
- Frontend: new "Cover Page" tab in client settings, preset selector, live preview

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
