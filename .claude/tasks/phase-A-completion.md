# Phase A (Backend) — Design System Option F v1

**Status:** ✅ Complete — awaiting your verification. Stop point per instruction.
**Completed:** 2026-04-20
**Scope:** all backend work for the Design System unification (migration, theme layout, cover customisation module, thumbnails, generate/regenerate/scheduler wiring). Frontend is Phase B.

---

## 1. What was built

### Migration
- `supabase/migrations/017_design_system.sql`
  - Adds `clients.theme VARCHAR(30) DEFAULT 'modern_clean'` with CHECK in the 6 theme values
  - Backfills `theme` from legacy `cover_design_preset` (minimal→minimal_elegant, bold→bold_geometric, corporate→dark_executive, gradient→gradient_modern; default/hero/unknown → modern_clean)
  - Creates `idx_clients_theme`

### Backend services
| File | Change |
|---|---|
| `backend/services/theme_layout.py` | **NEW** — single source of truth for per-theme cover coordinates. Measured from all 6 `.pptx` templates via python-pptx. Includes `brand_tint_strategy` flag: `"header_band"` for 3 themes that have a recolour-safe band (modern_clean, dark_executive, gradient_modern); `"none"` for 3 themes with multi-shape decoration (colorful_agency, bold_geometric, minimal_elegant) |
| `backend/services/cover_customization.py` | **NEW** (~230 lines) — replaces the 485-line `cover_presets.py`. Does only 4 things: headline replace, subtitle append, header-band tint (if theme supports), accent bar (if theme supports). No strip, no reposition, no font boost, no hero. Text substitutions run on every preset. |
| `backend/services/cover_presets.py` | **DELETED** — superseded. |
| `backend/services/report_generator.py` | Updated `generate_pptx_report` to call `apply_cover_customization` instead of `apply_cover_preset`. Passes `theme` from `cover_customization` dict. Logo placement logic in `_embed_logos` unchanged (still works per Railway logs from Phase 3). |
| `backend/services/scheduler.py` | Dropped all `visual_template` logic from `_process_scheduled_report`. `_generate_report_internal` reads `client.theme` authoritatively. Legacy `scheduled_reports.visual_template` is logged (if set) and ignored. |

### Schemas
- `backend/models/schemas.py`
  - `ClientUpdate`: added `theme` field with validator for 6 allowed values. Deprecated fields (`cover_design_preset`, `cover_hero_image_url`) kept nullable for backward compat.
  - `ClientResponse`: added `theme`; same deprecation handling.
  - `CoverPreviewRequest`: rewritten to use `theme` + minimal overrides. Old `preset`, `hero_image_url`, `visual_template` fields removed.

### Routers
- `backend/routers/reports.py`
  - **Preview endpoint (`POST /preview-cover`)**: rewritten to use `theme` from request or client row. Calls `apply_cover_customization` (not `apply_cover_preset`). Logo + sample-value substitution unchanged.
  - **`_generate_report_internal`**: reads `client.theme` → uses as `visual_template`. Any caller-supplied `visual_template` that differs is logged and ignored (backward compat for in-flight callers).
  - **`regenerate_report`**: same pattern — `client.theme` drives both the template choice and the cover customisation.

### Assets
- `backend/static/cover_thumbnails/*.png` — 6 thumbnails generated via LibreOffice CLI:
  - modern_clean.png, dark_executive.png, colorful_agency.png, bold_geometric.png, minimal_elegant.png, gradient_modern.png
  - Sizes: 27–34 KB each
  - Served via existing `/static` mount

---

## 2. Files changed summary

| File | Kind | Notes |
|---|---|---|
| `supabase/migrations/017_design_system.sql` | NEW | Migration |
| `backend/services/theme_layout.py` | NEW | ~130 lines — coord/font/tint-strategy constants |
| `backend/services/cover_customization.py` | NEW | ~230 lines — replaces `cover_presets.py` |
| `backend/services/cover_presets.py` | DELETED | |
| `backend/services/scheduler.py` | MOD | Drop legacy visual_template plan-check + propagation |
| `backend/services/report_generator.py` | MOD | Call `apply_cover_customization` |
| `backend/routers/reports.py` | MOD | Preview endpoint + generate + regenerate use `theme` |
| `backend/models/schemas.py` | MOD | `theme` field on ClientUpdate / ClientResponse / CoverPreviewRequest |
| `backend/static/cover_thumbnails/*.png` | NEW (6 files) | Thumbnails for frontend preview layer |
| `.claude/tasks/phase-A-completion.md` | NEW | This doc |

---

## 3. Verification done in-session

- ✅ `ast.parse` clean on all 6 modified/new Python files
- ✅ `grep` confirms no stale `cover_presets` or `apply_cover_preset` references anywhere in backend
- ✅ Coordinates measured directly from each `.pptx` via python-pptx (not guessed)
- ✅ 6 thumbnails generated successfully (filesizes 27–34 KB, all under static dir)

---

## 4. Manual verification required

### Prerequisite
1. Run migration 017 in Supabase SQL Editor.
2. Deploy backend to Railway (or restart locally).
3. (For thumbnails) confirm `/static/cover_thumbnails/{theme}.png` resolves — should be served automatically since `static` is already mounted.

### Test 1 — Migration backfilled theme correctly
```sql
SELECT cover_design_preset, theme, COUNT(*)
FROM clients
GROUP BY cover_design_preset, theme
ORDER BY cover_design_preset, theme;
```
Expected: existing `minimal` preset → `minimal_elegant`, `bold` → `bold_geometric`, `corporate` → `dark_executive`, `gradient` → `gradient_modern`, `default`/`hero`/NULL → `modern_clean`.

### Test 2 — Preview endpoint returns a clean PPTX
For a client whose `theme` = `modern_clean`:
```
curl -X POST ... /api/reports/preview-cover \
  -d '{"client_id":"...","headline":"Q2 Review","subtitle":"Executive Brief","primary_color":"#DC2626","accent_color":"#F59E0B"}'
```
Open the returned PPTX. Cover should show:
- The `modern_clean` template layout intact (title where the template puts it)
- "Q2 Review" in place of the client name
- "April 2026 — Executive Brief" in place of just "April 2026"
- Red header band tint
- Thin amber accent bar at the bottom of the header
- Agency + client logos at their default placeholder positions (or user-selected positions if overridden)
- No broken shapes, no missing content

### Test 3 — Preview for a multi-shape theme (brand tint skipped)
For a client whose `theme` = `colorful_agency` or `bold_geometric`:
- Send same request with `primary_color` set
- Expected: cover has the user's headline/subtitle applied, logos placed, BUT the multi-coloured decoration is UNCHANGED (the theme's brand_tint_strategy is `"none"`)
- Backend log should show: `Cover: header band not found for theme colorful_agency; skipping tint` OR no tint log at all
- This is correct behaviour — those themes use designer-chosen palettes

### Test 4 — Full report generation uses theme
Generate a full report for a client with `theme = 'dark_executive'`:
- Expected: all 19 slides come from `dark_executive.pptx`
- Cover: dark navy with user customisations applied
- Content slides: template-native design (unchanged)
- Charts: palette matches the user's brand primary (if set) or the template's default

### Test 5 — Scheduler ignores legacy visual_template
For a scheduled report with the old `visual_template='bold_geometric'` in the DB but the client's current theme is `modern_clean`:
- When the schedule fires, `scheduler.py` logs the legacy value at debug level and proceeds using `client.theme`
- Generated report uses `modern_clean`

### Test 6 — Legacy API caller with `visual_template`
A report-generate request body that includes `visual_template` should be ignored with a warning log:
```
Ignoring legacy visual_template='bold_geometric' for client <id> — using theme='modern_clean'
```

### Test 7 — Thumbnails served
Browser: `GET /static/cover_thumbnails/modern_clean.png` returns the 27 KB PNG.

---

## 5. Known limitations (intentional, documented in design doc)

1. **Brand colour doesn't tint content slide chrome.** Slides 2-19 use the template's original palette. Charts pick up the brand colour. See DESIGN-SYSTEM-PLAN.md §5.
2. **3 themes have no brand-tint support.** `colorful_agency`, `bold_geometric`, `minimal_elegant` — multi-shape decoration would break under a single recolour. Frontend hint text in Phase B will make this clear.
3. **Hero image concept dropped.** Migration maps old `hero` preset → `modern_clean`. If users ask for hero back, ship as a dedicated `hero_photo.pptx` theme later.
4. **Template hard-coded labels kept.** "PERFORMANCE REPORT" + "Prepared by ..." still appear (Option A from design doc §11). Defer template polish to post-ship.
5. **PPTX preview not PNG preview.** Frontend preview in Phase B uses static thumbnails + CSS overlays. Pixel-exact match requires download.

---

## 6. What's ready for your review

1. **Run migration 017** (Supabase SQL Editor).
2. **Deploy backend** (Railway or local restart).
3. **Run Tests 1–7** from §4. Test 1 and Test 2 are the critical ones — they cover the migration backfill and the preview rendering for the happy-path theme.
4. **Inspect code** (if desired):
   - `backend/services/theme_layout.py` — coordinate spec
   - `backend/services/cover_customization.py` — replacement for cover_presets
   - `backend/routers/reports.py` — search for `client_theme = client.get("theme")` in `_generate_report_internal`, `regenerate_report`, and `preview_cover`

### STOP

Phase A complete. Awaiting your verification before Phase B (frontend rebuild).

When approved, Phase B will:
- Rebuild `ReportCustomizationTab.tsx` → `DesignTab.tsx` with theme picker + overlay preview
- Remove visual-template selector from `ReportsTab.tsx` and `SchedulesTab.tsx`
- Update `Client` type + `ClientUpdatePayload` + `CoverPreviewRequest` types to match new backend
- `npx tsc --noEmit` clean
