# PHASE 1 & 2 — REFINED PLAN
**Review of the original Phase 1/2 feature plan against actual code and docs.**
Produced: April 19, 2026. No code written — planning document only.

---

## 0. HEADLINE REFINEMENTS

1. **Two referenced docs don't exist.** The original plan cites `docs/reportpilot-auth-integration-deepdive.md` and `docs/reportpilot-feature-design-blueprint.md`. Neither is in `docs/`, though backend code (`ai_narrative.py:3`, `connections.py:4`, `utils/data_parser.py:4`) references the blueprint. Either recover from backup or treat code + this plan as the spec.
2. **~60% of Feature 1.2 infrastructure already exists.** `connections` table already has `last_successful_pull`, `consecutive_failures`, `token_expires_at`, `status`. Do not create a new `connection_health` table — extend the existing columns + add a scheduled job.
3. **Feature 1.1 is *not* a narrative rewrite — it's a pre-processing + schema change.** `backend/services/ai_narrative.py` already has SCQA, bad-month detection, "explain WHY" rule, chart-insight headlines, and section-specific instructions. The real gap is **data preparation** (inject top movers) + **output schema** (reasoning references).
4. **Feature 1.3 has a data-availability risk** that the original plan understates. Need to verify `data_snapshots` is actually being populated per report, with retention. If each report overwrites or snapshots only the current period, multi-month trend detection is impossible without an ingestion-job change.
5. **Build order changes.** Recommend: 1.2 (connection health) → 2.2 (cover page) → 1.1 (narrative v2) → 2.3 (comments) → 2.1 (goals) → 1.3 (trends). Reasoning below.
6. **Scheduler reality check.** `services/scheduler.py` is a lightweight asyncio loop invoked from FastAPI lifespan, not full APScheduler. It polls hourly via `check_and_run_scheduled_reports`. New background jobs (health check, goal evaluation) must plug into the same pattern — don't assume APScheduler primitives exist.

---

## 1. CURRENT-STATE AUDIT (what already exists — so we extend, not rebuild)

| Area | What exists | Implication |
|---|---|---|
| **AI narrative prompt** | `ai_narrative.py:24-63` SYSTEM_PROMPT already mandates "explain WHY metrics changed", "never say 'traffic increased' — say 'sessions grew from X to Y (+Z%)'", SCQA structure, chart-insight one-liners ([ai_narrative.py](backend/services/ai_narrative.py)) | Feature 1.1's prompt rules are already in place. Real gap = giving AI the *data* to make causal claims (top movers). |
| **Bad-month detection** | `_detect_bad_month` at `ai_narrative.py:125` triggers a four-beat recovery prompt when any primary KPI drops >5% | Pattern to follow for trend detection in Feature 1.3 |
| **`connections` table schema** | Has `last_successful_pull`, `consecutive_failures`, `token_expires_at`, `status` ([001_initial_schema.sql:60-76](supabase/migrations/001_initial_schema.sql)) | Feature 1.2 adds a scheduled job + a `health_last_checked_at` column, nothing more |
| **Scheduler loop** | Hourly asyncio task calls `check_and_run_scheduled_reports` ([scheduler.py:17](backend/services/scheduler.py)). Uses `next_run_at` pattern. | Health checks and goal evaluations plug in as sibling async functions, not new infra |
| **Data snapshots** | `data_snapshots` table exists (migration 001:83); populated by `csv_upload.py:157` for CSV; needs verification for native pulls | **Must audit** before committing to Feature 1.3 |
| **Cover slide generation** | `report_generator.py` has placeholder-based cover with agency + client logo insertion (line 966-1081) | Feature 2.2 extends per-client overrides, reuses placeholder machinery |
| **Shared reports + views** | `shared_reports` and `report_views` tables exist, plus RLS ([008_shared_reports.sql](supabase/migrations/008_shared_reports.sql)) | Feature 2.3 adds a sibling `report_comments` table with the same RLS pattern |
| **Email service** | `email_service.send_report_email` + Resend integration already live | Health alerts, goal alerts, comment notifications all reuse this |
| **Scheduled reports** | Full CRUD + auto-send + plan enforcement ([scheduler.py:54-219](backend/services/scheduler.py)) | Pattern reusable for goal evaluation |

---

## 2. FEATURE 1.1 — Diagnostic AI Narrative v2 (REFINED)

### What the original plan got right
- Inject top movers (campaigns, segments, sources) pre-prompt.
- Add reasoning transparency (`reasoning_data` per section).
- "Show reasoning" UI toggle.

### What it missed / needs adjustment

**Scope reduction — the prompt itself barely needs changes.** The system prompt at `ai_narrative.py:24-63` already says: *"Explain WHY metrics changed (connect cause to effect where possible)"*, *"Be specific with numbers"*, *"Reference specific campaigns by name"* (for data_heavy tone). Rewriting it is not the work.

**The actual work is three things:**
1. **Data pre-processing module** — new `_compute_top_movers()` helper that, given the `data` dict, returns: top-3 best/worst campaigns by spend-delta and conversion-delta; top-3 traffic sources by session-change; top-3 landing pages by engagement-delta. Inject into the `user_prompt` as a dedicated "TOP MOVERS" block.
2. **Output schema change** — update the `response_format` schema (currently loose JSON). Introduce `{"text": "...", "evidence": [{"metric": "...", "value": "...", "delta_pct": ..., "source": "ga4.campaign.brand-awareness"}]}` per section. This is a breaking change for narrative consumers — `report_generator.py` and the frontend preview both render `narrative.executive_summary` as a string today. Needs dual-format support for at least one release.
3. **Confidence indicators are risky.** "High confidence — 3 data points support this" invites the AI to fabricate its own confidence. A safer pattern: *derive* confidence mechanically from row count in `evidence` array (3+ = high, 1-2 = medium, 0 = suppress the claim). Don't let the model self-assess.

### Success criteria — tighten
- Original: "every AI claim references a specific campaign/segment/source by name." → **Too strong.** Some sections (executive_summary) reasonably generalize. Restate: *"every data-bearing claim in `key_wins`, `concerns`, `next_steps` must have at least one `evidence[]` row with a source path."*
- Add: *"No narrative section includes numbers that don't appear in the underlying data dict."* (guards against hallucination — enforceable via post-generation validation, not just prompt discipline.)

### Risks
- **Token cost.** Adding a TOP MOVERS block + requiring evidence arrays per section will push token usage up ~30-50%. Need to verify GPT-4.1 pricing fits the $19 Starter margin at Starter's report volume (20/month) before ship.
- **JSON schema strictness.** `response_format={"type": "json_object"}` is loose. Consider moving to a strict JSON schema (OpenAI Structured Outputs) to guarantee evidence arrays exist.
- **Chart insights already exist** — don't duplicate. The `chart_insights` object at `ai_narrative.py:285-299` is already the "diagnostic one-liner per chart" artifact. New work should *enrich* it with evidence, not replace it.

### Effort revised: **3 days**, not 2.
Day 1: `_compute_top_movers()` + prompt plumbing. Day 2: evidence schema + dual-format output + post-generation validation. Day 3: "Show reasoning" UI + token-cost measurement.

---

## 3. FEATURE 1.2 — Connection Health Monitor (REFINED)

### What's already in place — don't rebuild
- `connections.consecutive_failures` (counter exists)
- `connections.last_successful_pull` (timestamp exists)
- `connections.token_expires_at` (timestamp exists)
- `connections.status` ('active' and presumably others)
- Hourly scheduler loop ([scheduler.py:17](backend/services/scheduler.py))

### Minimal net-new work
1. **Schema additions** — add `last_health_check_at TIMESTAMPTZ`, `health_status VARCHAR(20)` (`'healthy' | 'warning' | 'broken' | 'expiring_soon'`), `last_error_message TEXT` to `connections`. Write as migration `013_connection_health.sql`.
2. **Health-check job** — new `services/health_check.py` with `check_all_connections_health()`. Plug into the existing scheduler loop ([scheduler.py:17](backend/services/scheduler.py)) alongside `check_and_run_scheduled_reports`. Runs every 6 hours via a mod check on the hourly tick.
3. **Per-platform health probes** — one cheap API call per platform (GA4: `properties.list`; Meta: `me?fields=id`; Google Ads: `customers:listAccessibleCustomers`; Search Console: `sites.list`). All live on existing service modules — extend, don't duplicate.
4. **Pre-generation gate** — in `routers/reports.py`'s `_generate_report_internal`, before calling any data-pull service, read `health_status` for all connections on the client. If any is `broken` or `expiring_soon` AND was due to be pulled, **fail fast with 422** and email the owner instead of silently producing an empty report. Scheduled reports must use the same gate (currently silent per the empty-report competitor pain we identified).
5. **Dashboard widget** — `frontend/src/components/dashboard/ConnectionHealthWidget.tsx` consuming a new `GET /api/dashboard/connection-health` endpoint. Show count of healthy / warning / broken + top-3 broken clients with reconnect CTA.
6. **Emails** — three templates: (a) connection broken (send immediately on transition to broken), (b) token expiring in 7 days (send once, idempotent), (c) suspicious-zero-data after successful pull returns 0 sessions (flag as potential disconnect even if API returns 200).

### Edge cases the original plan missed
- **"Suspicious zero data."** A successful 200 response with zero sessions/impressions isn't technically a failure, but is the exact pattern that produces "empty scheduled report sent to client" — our marketing hook. Implementation: if current-period pull returns 0 for a connection that had non-zero in the last 2 pulls, flag `health_status = 'warning'` and include in pre-generation gate.
- **Token-refresh race.** `encryption.py` handles token decrypt; health probe must be able to trigger a refresh. If refresh itself fails, that's when we transition to `broken`. Needs coordination with `auth.py` refresh flow.
- **Rate limits.** Probing every connection every 6 hours at scale (imagine 500 users × 4 platforms = 2000 probes) can hit API quotas. Add jitter; probe connections in batches of 50 with 30s sleeps.
- **Probe cost vs. accuracy.** A `me?fields=id` call tells you the token is valid, not that data for *this client's account* is accessible. If an account loses access (agency pulled off ad account), probe won't catch it. Deeper probe = more cost. Ship shallow probe first; upgrade if needed.

### Success criteria — add measurable one
Original: "zero empty reports sent." → **Can't measure that directly.** Replace with: *"100% of scheduled reports with broken/expiring connections are blocked pre-generation; owner is notified within the probe interval (max 6 hours after break)."*

### Effort revised: **3 days** (unchanged).

---

## 4. FEATURE 1.3 — MoM + YoY Pattern Detection (MOVE TO PHASE 2)

### Why this should move out of Phase 1
- **Data-availability risk.** Need to verify `data_snapshots` is actually populated per pull for native platforms (GA4, Meta, Google Ads, SC). Grep shows only `csv_upload.py:157` explicitly inserting snapshots. **If native data pulls aren't snapshotting, multi-period trend detection requires an ingestion change first** — adding weeks to the estimate.
- **No user-voice evidence in USER-RESEARCH-APRIL-2026.md.** Pain #1 (empty reports), #3 (ugly covers), #4 (shallow AI) are heavily cited. Long-term trend detection is a Claude-proposed feature, not a user-asked one. Shipping it before validating demand is premature.
- **3-month lookback means 3-month wait for new clients** — limited value in the first quarter after any signup.

### Recommendation
Move to Phase 2 (or Phase 3). Before building, run a one-day audit:
1. Query `data_snapshots` in production — how many rows per client, what periods?
2. If empty/sparse, estimate ingestion-change scope.
3. If populated, proceed with scoped version: YoY only (simpler, no seasonality logic), gated behind `data_snapshots` count ≥ 12.

### If it does ship, scope tightening
- Drop "seasonality detection" — requires multi-year data most clients don't have.
- Drop "inflection point in Week 2" — requires week-level data we may not retain.
- Keep only: *consecutive-period trend detection* (3 months sessions direction) and *YoY comparison when data allows*.

---

## 5. FEATURE 2.1 — Goals & Alerts (MINOR REFINEMENTS)

### Scope additions
- **Goal types beyond thresholds.** Original lists CAC ≤ X, ROAS ≥ X, spend ≤ X. Also needed: *percent-change goals* ("grow sessions 20% MoM"). Cheap addition at schema level (`operator` accepts `pct_change_gte` etc.).
- **Evaluation frequency.** Original says "hourly/daily." Hourly is overkill for most metrics and wastes API quota. Default to **daily** evaluation; expose `evaluation_frequency` for power users. Meta/GA4 APIs have daily granularity anyway.
- **Notification fatigue.** If CAC has breached for 14 days, we don't email daily. Idempotency: emit breach email once per goal per breach-streak; resolve email when back in bounds.

### Build-order dependency
- Goals & Alerts uses the same "schedule + evaluate + email" pattern as Feature 1.2 (health monitor). **Build 1.2 first**; it proves out the scheduler-extension pattern and email-alert plumbing. 2.1 then reuses 80% of that infrastructure.

### Missing edge case
- **Goal definition vs. data reality.** User sets "CAC ≤ ₹500" but their Meta connection is broken. Do we emit breach alerts against stale data? No — **goal evaluation must skip clients whose relevant connection is `broken` or `warning`**. Another reason to ship 1.2 first.

### Effort revised: **4 days** (was 3-4). Adds idempotency + connection-health integration.

---

## 6. FEATURE 2.2 — Custom Cover Page Editor (MINOR REFINEMENTS)

### What's already in place
- Cover slide is slide index 0, with placeholder-based logo insertion for agency + client logos ([report_generator.py:966-1081](backend/services/report_generator.py)).
- 6 visual templates all have a cover slide (`modern_clean`, `dark_executive`, etc.).

### Refinements
1. **Preset library ≠ new templates.** The original plan lists "5 preset cover designs (hero image, minimal, bold, corporate, gradient)." These should be **cover-slide variants within the existing 6 visual templates**, not 6 × 5 = 30 new PPTX files. Implementation: a separate `cover_variants/*.pptx` library with 5 cover-only slides, swapped into slide[0] at generation time based on `clients.cover_design_preset`.
2. **Hero image storage.** `logos` bucket in Supabase Storage already exists (`010_storage_logos_bucket.sql`). Either extend that bucket or create `cover_heroes`. Storage limit implications: a hero image is ~500KB-2MB vs. a logo at ~50KB. Consider Supabase Storage quota per plan.
3. **Live preview.** "Preview updates live as user edits" is a frontend-heavy lift. Cheapest path: render a **static PNG preview** of just the cover slide via a new `POST /api/reports/preview-cover` endpoint that returns a 1280×720 PNG. Do not try to render the full PPTX for preview.
4. **Schema additions to `clients`**: `cover_design_preset VARCHAR(50)`, `cover_headline TEXT`, `cover_subtitle TEXT`, `cover_hero_image_url TEXT`. Migration `014_cover_customization.sql`.

### Risks
- **PPTX slide-swap complexity.** Replacing slide[0] in a python-pptx document with a slide from a different deck is non-trivial (relationships, media refs, layout). Prototype a swap script before committing; alternate path is **in-place modification** of the existing cover slide's shapes (headline textbox, subtitle textbox, hero image picture box). In-place mod is simpler but limits design variance.
- **Per-preset color coherence.** If the agency picks "Bold" preset (red) but their brand color is green, the cover will fight the rest of the deck. Either force preset to honor brand color, or provide preset × brand-color matrix (expensive).

### Effort revised: **2 days** (was 1-2). Add a prototyping day for the PPTX variant strategy.

---

## 7. FEATURE 2.3 — Client Comments on Shared Reports (MINOR REFINEMENTS)

### What's already in place
- `shared_reports` table + RLS + hash-based auth ([008_shared_reports.sql](supabase/migrations/008_shared_reports.sql)).
- `report_views` tracks anonymous views with device_type + user_agent.
- Public insert policy already set on `report_views` — pattern reusable for comments.

### Refinements
1. **Anti-spam.** Public-insert on comments + no auth = spam target. Add: rate limit (`slowapi` already in stack per CLAUDE.md) of 5 comments/hour/IP; optional reCAPTCHA on share pages that enable comments; honeypot field; server-side validation of reasonable comment length (3-5000 chars).
2. **Moderation.** Agency owner needs ability to **delete** any comment on their shared reports. Hide-by-default on first post until owner approves? Too friction-heavy for MVP. Ship: all comments visible, owner can delete, future pass adds moderation queue.
3. **Email digest vs. instant.** "Email notification within 5 minutes" per the original success criteria — but if a client reads the report and leaves 10 comments in a session, that's 10 emails. Better: debounced digest — 15 minutes of silence triggers the email with all comments in the window.
4. **Threading / replies.** Original says "reply capability" in agency dashboard. Replies can either appear inline on the shared page (client sees agency response) or be private to the dashboard (ops notes only). **Pick one for MVP.** Recommend: inline replies on shared page to lean into the two-way-conversation positioning — but add an internal-only `is_internal_note` flag for ops comments.
5. **Comment-disable toggle.** Not every shared report wants comments on. Add `enable_comments BOOLEAN DEFAULT true` to `shared_reports`. Toggleable at share-link creation.

### Schema
```
report_comments (
  id UUID PK,
  shared_report_id UUID → shared_reports,
  parent_comment_id UUID NULL → report_comments (threading),
  commenter_name VARCHAR,
  commenter_email VARCHAR,
  comment_text TEXT,
  is_internal_note BOOLEAN DEFAULT false,
  is_resolved BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ
)
```
Migration `015_report_comments.sql`.

### Effort revised: **3 days** (was 2). Adds anti-spam + debounced digest.

---

## 8. DEPENDENCIES & REVISED BUILD ORDER

```
┌─ 1.2 Connection Health ───────┐
│   • establishes scheduler     │
│     extension pattern         │
│   • establishes email-alert   │
│     templates                 │
│   • REQUIRED by 2.1 Goals     │
└────────────┬──────────────────┘
             │
             ▼
┌─ 2.2 Cover Page Editor ───────┐   (independent, quick win)
└───────────────────────────────┘
             │
             ▼
┌─ 1.1 Narrative v2 ────────────┐   (prompt + schema, no infra deps)
└───────────────────────────────┘
             │
             ▼
┌─ 2.3 Client Comments ─────────┐   (extends shared_reports)
└───────────────────────────────┘
             │
             ▼
┌─ 2.1 Goals & Alerts ──────────┐   (depends on 1.2's scheduler pattern)
└───────────────────────────────┘
             │
             ▼
┌─ 1.3 MoM/YoY ─────────────────┐   (audit data_snapshots first)
└───────────────────────────────┘
```

**Rationale:**
- **1.2 first** — biggest user pain (empty reports), establishes reusable infra for 2.1.
- **2.2 second** — fastest visual win, builds screenshot/demo momentum, zero infra risk.
- **1.1 third** — independent of infra; shipping earlier makes reports visibly better for marketing.
- **2.3 fourth** — extends proven shared-reports pattern.
- **2.1 fifth** — maximum reuse of 1.2's scheduler + email plumbing + health gating.
- **1.3 last** — requires snapshot-retention audit; lowest user-validation signal.

Total realistic effort: **17–19 days** (vs. original's implied ~12–15).

---

## 9. CROSS-CUTTING CONCERNS

### Monitoring & telemetry
None of the features proposed include observability. Before shipping any, add:
- Structured logs with correlation IDs for: narrative generation, health probes, goal evaluations, comment inserts.
- A minimal metrics sink — at least `INFO` logs with consistent shape so Railway log search works.
- Rate-limit counters visible in logs (not silent throttling).

### Plan enforcement
- Goals & Alerts: how many goals per client per plan? Unlimited on Agency, 3/client on Pro, 1/client on Starter? Decide at build time; add to `plans.py`.
- Custom covers: hero image upload on Pro/Agency only? Starter gets presets? Decide.
- Client comments: available on all plans? It's a lock-in feature — keep broadly available.

### Migration sequencing
Proposed new migrations:
- `013_connection_health.sql` — adds `last_health_check_at`, `health_status`, `last_error_message`
- `014_cover_customization.sql` — adds `cover_*` columns to `clients`
- `015_report_comments.sql` — new table + RLS
- `016_client_goals.sql` — new table + RLS

Run in order. Per CLAUDE.md rule #4 — all run manually in Supabase SQL Editor.

### Language / i18n
GoReportPilot supports 13 languages for narrative. Don't forget:
- Email alert templates (health, goals, comments) need translation strings. Reuse `services/translations.py` infra.
- Goal-breach narrative fragment (the "why it breached" AI explanation in 2.1) needs to respect client.language.
- Client comment notifications — send in agency owner's language (from profile), not client's.

### CLAUDE.md contradictions to resolve
- CLAUDE.md line 19: *"Project root: `F:\Sapienbotics\ClaudeCode\reportpilot\`"* — actual path is `...\GoReportPilot\`. Minor but should fix.
- CLAUDE.md says APScheduler; real scheduler is a lightweight asyncio lifespan loop. Update when other docs are touched.

---

## 10. SUCCESS CRITERIA — CONSOLIDATED & MEASURABLE

| Feature | Pre-ship measurable | Post-ship signal |
|---|---|---|
| 1.2 Health Monitor | All 4 platforms have a working probe; pre-generation gate blocks report when any required connection is `broken` | "Empty report incidents" = 0 in logs over 30 days |
| 2.2 Cover Editor | 5 presets render correctly across all 6 visual templates; hero image upload works with 2MB limit | % of clients with custom cover set > 40% within 30 days of ship |
| 1.1 Narrative v2 | Every `key_wins` / `concerns` / `next_steps` bullet has ≥1 evidence row; no numbers appear that aren't in source data | Reduction in manual narrative edits per report by users |
| 2.3 Comments | Anti-spam holds (no more than 5 comments/IP/hour); digest email fires within 15 min of last comment | Comments-per-shared-report average > 0.5 within 60 days |
| 2.1 Goals | Breach email emitted exactly once per breach-streak; skipped for clients with broken connections | % of paid users with ≥1 goal set > 30% |
| 1.3 Trends | (If built) Reports for clients with ≥12 snapshots include YoY block | Anecdotal — agency feedback on "wow" factor |

---

## 11. OPEN QUESTIONS FOR SAURABH

1. Are `data_snapshots` actually being populated per report for native platforms (GA4, Meta, Google Ads, SC), or only for CSV? **Need to check in Supabase before committing to Feature 1.3.**
2. Where are the referenced docs `reportpilot-auth-integration-deepdive.md` and `reportpilot-feature-design-blueprint.md`? Code imports still reference them.
3. Do we want **inline client replies on shared pages** for comments, or agency-only ops notes? Big UX decision for 2.3.
4. GPT-4.1 token cost tolerance for Feature 1.1 — if narrative cost doubles from $0.03 → $0.06 per report, is that acceptable at Starter ($19, 20 reports/month = $1.20 AI cost → still 94% margin)? Decide before coding.
5. Plan tier gating for each feature — need explicit decisions before enforcement middleware updates.

---

## 12. NOT IN SCOPE — REAFFIRMED

The original plan's exclusions are correct and validated by USER-RESEARCH-APRIL-2026.md:
- ❌ Integration count expansion (chase-the-competitor trap)
- ❌ Live dashboards (61.7% of agencies send static, not live)
- ❌ Drag-and-drop builder (weeks of work, maintenance burden)
- ❌ Mobile native app (cooling category, no competitor shipped one)
- ❌ AI Chat UI (can't out-ship incumbents; diagnostic narrative delivers same value)
- ❌ Benchmark data (fabrication risk)
- ❌ Forecasting (vendor-push, not user-pull)
- ❌ Proposals module (scope creep outside reporting)
- ❌ SQL/BI blending (dilutes simplicity wedge)

---

*End of refined plan. No code changes. Ready for Saurabh's review & prioritization.*
