# GoReportPilot — Design System Plan (Option F, v1)

**Status:** design proposal — no code written yet.
**Prepared:** 2026-04-20
**Scope:** replace the current scattered cover-customisation system with a unified, template-first "Design" surface. v1 explicitly excludes the hero-image preset — it returns later as a dedicated template if demand exists.

This document is the design contract. Once approved, implementation follows from here and does not need further architectural decisions.

---

## 1. Core principle

**The template owns the design. Code owns only minimal overrides.**

Each of the 6 existing visual templates is treated as a complete, designer-authored artefact — cover + 18 content slides, cohesive by construction. The product exposes 6 **themes**, one per template. Users pick one theme per client and get a professionally-designed deck. Customisation is additive and minimal so design coherence cannot be broken by user action.

---

## 2. The 6 themes (1:1 with existing templates)

| Theme ID | Template file | Style |
|---|---|---|
| `modern_clean` | `modern_clean.pptx` | Light, minimalist; indigo accent |
| `dark_executive` | `dark_executive.pptx` | Dark navy, corporate, serif headings |
| `colorful_agency` | `colorful_agency.pptx` | Bold, multi-colour, agency-forward |
| `bold_geometric` | `bold_geometric.pptx` | High-contrast, geometric, modern |
| `minimal_elegant` | `minimal_elegant.pptx` | Off-white, serif, editorial |
| `gradient_modern` | `gradient_modern.pptx` | Gradient accents, dark body |

No hero theme in v1. The existing `hero` preset value is migrated to `modern_clean` (see §6 migration). A dedicated "Hero Image" theme may ship in a future release as its own `hero_photo.pptx` template.

---

## 3. Schema (single source of truth)

### 3.1 `clients` table — new and changed columns

| Column | Type | Default | Notes |
|---|---|---|---|
| `theme` | `VARCHAR(30)` CHECK in the 6 values above | `'modern_clean'` | NEW. Replaces `cover_design_preset`. Per-client design choice. |
| `cover_headline` | TEXT | NULL | EXISTS. Override for `{{client_name}}`. |
| `cover_subtitle` | TEXT | NULL | EXISTS. Appended to `{{report_period}}`. |
| `cover_brand_primary_color` | VARCHAR(7) | NULL | EXISTS. Per-client override of agency brand. |
| `cover_brand_accent_color` | VARCHAR(7) | NULL | EXISTS. Used for cover accent bar + chart secondary. |
| `cover_agency_logo_position` | VARCHAR(20) | `'default'` | EXISTS. 8 values. |
| `cover_agency_logo_size` | VARCHAR(20) | `'default'` | EXISTS. `default|small|medium|large`. |
| `cover_client_logo_position` | VARCHAR(20) | `'default'` | EXISTS. |
| `cover_client_logo_size` | VARCHAR(20) | `'default'` | EXISTS. |
| `cover_design_preset` | — | — | **DEPRECATED.** Keep column for one release. UI stops writing. Reads return NULL. Drop in migration 018. |
| `cover_hero_image_url` | — | — | **DEPRECATED.** Drop in migration 018. v1 doesn't use hero. |

### 3.2 `reports` / `scheduled_reports` tables

| Column | Change |
|---|---|
| `visual_template` | DEPRECATED for new writes. UI stops showing template selector. On generation, the client's `theme` wins. Column stays for historical reads. |

### 3.3 `ClientUpdate` / `ClientResponse` Pydantic schemas

- Add: `theme: str | None` with validator against the 6 enum values.
- Keep: all `cover_*` fields from Phase 3 (except deprecated ones above).
- Remove from client-facing responses: `cover_hero_image_url`, `cover_design_preset` (nullable but not exposed in UI).

---

## 4. Customisation fields (the total knob set)

### 4.1 Per-client (in the Design tab)

| Field | Type | Description | Scope of effect |
|---|---|---|---|
| `theme` | enum | Which template to use for the whole deck | All 19 slides + charts |
| `cover_brand_primary_color` | hex, optional | Overrides the theme's default brand color | Cover header tint + chart primary |
| `cover_brand_accent_color` | hex, optional | Secondary accent | Cover accent bar (optional) + chart secondary |
| `cover_headline` | text, optional | Replaces `{{client_name}}` on cover | Cover slide only |
| `cover_subtitle` | text, optional | Appended to `{{report_period}}` as `"April 2026 — <subtitle>"` | Cover slide only |
| `cover_agency_logo_position` | enum (8 positions + default) | Where agency logo sits on cover | Cover only |
| `cover_agency_logo_size` | enum (4) | How large | Cover only |
| `cover_client_logo_position` | enum (8) | Where client logo sits | Cover only |
| `cover_client_logo_size` | enum (4) | How large | Cover only |

### 4.2 Explicitly NOT customisable in v1

- Font family (stays theme-locked)
- Font sizes (stays theme-locked)
- Cover text positions (bound to template's coordinates)
- Content slide (2-19) colours, layouts, or chrome
- Hero image (deferred)
- Per-report overrides (Reports tab has no design controls)

This minimal knob set is **deliberate**. Less surface area = less bug surface + more design coherence.

---

## 5. Colour flow — honest about what tints where

A per-client `brand_primary_color` override affects:

| Surface | Effect |
|---|---|
| Cover header band | ✅ Recoloured by code at generation time (single shape, well-defined) |
| Cover accent bar | ✅ Drawn in accent colour if set (code-controlled) |
| Chart palette primary | ✅ Existing behaviour — `branding['brand_color']` flows to `chart_generator` |
| Content slide chrome | ❌ Stays the template's design |

**Why the deliberate omission on content slides:** each template has 30-80+ shapes across slides 2-19 with template-specific palettes and accents. Generic recolouring would break designs. v1 accepts the trade-off: charts pick up the brand colour; content slide chrome stays true to the template.

If the user's brand colour *significantly* differs from the template's palette, they should pick a theme whose palette aligns. Theme thumbnails make this obvious at selection time.

**Messaging to user:** the Design tab shows a subtle hint next to the colour pickers:
> *Brand colour applies to the cover header and chart palette. Slide backgrounds and decorative elements follow the chosen theme.*

---

## 6. Migration from current state

### 6.1 Data migration (migration 017)

```sql
-- 017_design_system.sql

-- Add theme column with safe default.
ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS theme VARCHAR(30) DEFAULT 'modern_clean';

-- Optional CHECK on allowed values.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'clients_theme_check') THEN
    ALTER TABLE clients ADD CONSTRAINT clients_theme_check
      CHECK (theme IN (
        'modern_clean','dark_executive','colorful_agency',
        'bold_geometric','minimal_elegant','gradient_modern'
      ));
  END IF;
END $$;

-- Best-effort backfill from the old cover_design_preset values.
UPDATE clients SET theme = CASE
    WHEN cover_design_preset = 'minimal'   THEN 'minimal_elegant'
    WHEN cover_design_preset = 'bold'      THEN 'bold_geometric'
    WHEN cover_design_preset = 'corporate' THEN 'dark_executive'
    WHEN cover_design_preset = 'gradient'  THEN 'gradient_modern'
    WHEN cover_design_preset = 'hero'      THEN 'modern_clean'  -- hero dropped
    ELSE 'modern_clean'
  END
WHERE theme IS NULL OR theme = 'modern_clean';
```

Clients with a working preset before migration end up on the theme that best matches their old intent. New clients get `modern_clean` by default.

### 6.2 Later cleanup (migration 018, post-stabilisation)

- Drop `cover_design_preset` column.
- Drop `cover_hero_image_url` column.
- Leave `visual_template` on `reports` + `scheduled_reports` for historical reads. Future migration may drop those too.

### 6.3 Frontend

- `ReportCustomizationTab.tsx` → renamed `DesignTab.tsx`, rebuilt per §7.
- `ReportsTab.tsx` → remove visual-template selector. Period + report-length-preset (full/summary/brief) + CSV upload remain.
- `SchedulesTab.tsx` → remove visual-template selector. Frequency + time + attachment type remain.
- Client-detail tabs list → rename `customization` → `design`. Icon unchanged.

### 6.4 Backend

- `reports.py` `_generate_report_internal` and `regenerate_report`: read `client.theme`, use as `visual_template`. If request payload specifies `visual_template`, log-warn and ignore (backwards compat for any in-flight callers).
- `scheduler.py`: read `client.theme`, ignore `scheduled_reports.visual_template` on new runs.
- `cover_presets.py` → renamed `cover_customization.py`. Rewritten per §8.

---

## 7. The Design tab — UX specification

Single vertically-stacked tab. Four sections:

### 7.1 Section A — Theme

6 cards in a 3×2 grid. Each card:
- Pre-rendered cover thumbnail at ~240×135 px (actual cover of that template)
- Theme name
- One-line description
- Selected card has a 2px indigo ring

Clicking a card sets `theme` locally. Live preview (§7.5) updates.

### 7.2 Section B — Brand colours

- **Primary colour**: colour swatch + hex input + Clear button. Placeholder shows the theme's default brand colour so user sees what they're overriding.
- **Accent colour**: same pattern.
- Small italic note: *"Brand colour applies to the cover header and chart palette. Slide backgrounds follow the chosen theme."*

### 7.3 Section C — Cover text

- **Headline** input (max 80 chars). Placeholder: *"Leave blank to use the client name"*.
- **Subtitle** input (max 120 chars). Placeholder: *"Leave blank to show just the report period"*.
- Below subtitle field, preview the resulting period line: `"{period} — {subtitle}"` or just `{period}` if blank.

### 7.4 Section D — Logo placement

Two rows, one for agency logo and one for client logo. Each row has:
- Position dropdown (8 options: `default`, `top-left`, `top-right`, `top-center`, `footer-left`, `footer-right`, `footer-center`, `center`).
- Size dropdown (`default`, `small`, `medium`, `large`).

If the profile/client doesn't have a logo uploaded, greyed out with a link to upload.

### 7.5 Live preview (always visible, right side or below on narrow)

**The preview is the template's actual cover thumbnail with CSS overlays for user-customisable elements.**

Composition (bottom to top):
1. **Base layer** (`<img src="/static/cover_thumbnails/{theme}.png">`) — shows the theme's designer-rendered cover at ~960×540 px.
2. **Brand-colour tint layer** (if primary set): a `<div>` absolutely positioned over the template's header-band region (coordinates from §9 per-theme) filled with the user's primary colour. Blend mode `multiply` to preserve decorative detail where present.
3. **Accent-bar layer** (if accent set): thin `<div>` at the header-band bottom edge, user's accent colour.
4. **Headline overlay**: `<div>` at the template's `{{client_name}}` position, rendered in the template's font family + point size + computed colour, showing either the user's headline or the client name placeholder.
5. **Subtitle overlay**: similar to headline, at `{{report_period}}` position, showing `"April 2026 — {subtitle}"` or just the period.
6. **Agency logo overlay**: `<img>` at the position + size the user selected. If default, at the template's original placeholder position.
7. **Client logo overlay**: same.

The preview scales to the container via a CSS transform `scale(...)` so it looks right at any width.

Below the preview, a button: **Download PPTX preview** — fetches the real single-slide PPTX for byte-accurate confirmation.

### 7.6 Save / Cancel

- Changes are local until **Save**. Save POSTs a single `PATCH /api/clients/{id}` with all changed fields.
- Toast on success. Preview re-renders from new props.

---

## 8. Backend rendering — what actually happens on generate

### 8.1 On `POST /api/reports/generate`

```
1. Load client row → get theme + all cover_* overrides.
2. Load the theme's .pptx template file (slides 1-19 designer-authored).
3. Build `branding` dict (agency name, logo, brand_color with client override).
4. Build `cover_customization` dict with user's cover_* fields.
5. Call generate_pptx_report(theme, branding, cover_customization, ...).
6. Inside generate_pptx_report:
     a. apply_cover_customization runs BEFORE text substitution:
          - If headline set → replace {{client_name}} in cover text runs.
          - If subtitle set → append " — {subtitle}" after {{report_period}}
            (token stays, real period substitutes later).
          - If brand_primary_color set → recolour the header band shape
            (single shape identified by heuristic — topmost full-width
            non-text non-picture shape in top third).
          - If accent_color set → draw accent bar (thin rectangle).
     b. Generator's normal text-substitution pass runs (no change).
     c. _embed_logos runs with user-selected position + size overrides
        (existing Phase 3 logic, already working per logs).
     d. Content slides 2-19 render from the template unchanged.
     e. Charts use branding['brand_color'] + accent_color.
7. Return bytes.
```

**Critical constraint:** `apply_cover_customization` does NOT strip shapes, does NOT reposition, does NOT delete placeholders, does NOT apply preset-specific layouts. It only performs 4 surgical operations: headline replace, subtitle append, header-band tint, accent-bar draw. Logos are handled by the existing `_embed_logos` path.

### 8.2 On `POST /api/reports/preview-cover`

Takes ad-hoc overrides from the request body (for live editing) or reads from the client row. Calls the same `apply_cover_customization` logic inside a 1-slide presentation. Returns PPTX bytes.

### 8.3 `cover_customization.py` (rewritten `cover_presets.py`)

| Section | Lines (approx) |
|---|---|
| Doc string + imports | 20 |
| `apply_cover_customization(prs, ...)` — orchestrator | 40 |
| `_recolor_header_band(prs, cover, hex)` — single shape fill change | 25 |
| `_draw_accent_bar(prs, cover, hex)` — existing, kept | 20 |
| `_substitute_cover_text(cover, headline, subtitle)` — existing, kept | 25 |
| Helpers (`_normalise_hex`, `_hex_to_rgb`, `_find_header_band`) | 30 |
| **Total** | **~160 lines** |

Shrinks from the current 485-line file. No strip, no reposition, no font boost, no hero image logic.

### 8.4 Removed from `cover_customization.py`

Compared to current `cover_presets.py`:
- `_strip_cover_for_preset` / `_strip_cover_for_hero`
- `_reposition_cover_text_for_preset`
- `_ensure_hero_headline_size`
- `_log_cover_shapes`
- `_insert_hero_image` / `_reorder_to_back` / `_delete_header_band` / `_clear_header_band`
- `_recolour_cover_text` (preset palette recolouring — handled by template + text substitution keeps template colours)
- `PRESETS` dict (no preset concept anymore)

### 8.5 `_embed_logos` (in `report_generator.py`)

Kept as-is. v4 logo placement logic works correctly per Railway logs. No changes needed for v1.

---

## 9. Per-theme coordinate constants (single source of truth)

Shared between frontend preview overlays and backend cover code. Stored as a JSON file shipped with the frontend and parsed by the backend, OR duplicated as literal constants in both codebases with a comment noting they must stay in sync.

### 9.1 Structure

```json
{
  "modern_clean": {
    "slide_inches":    { "width": 13.33, "height": 7.50 },
    "header_band":     { "x": 0.0, "y": 0.0, "w": 13.33, "h": 2.20 },
    "accent_bar":      { "x": 0.0, "y": 2.16, "w": 13.33, "h": 0.10 },
    "client_name_box": { "x": 0.5, "y": 5.00, "w": 12.3, "h": 1.20,
                         "font": "Inter", "size_pt": 44, "color_hex": "FFFFFF",
                         "align": "left" },
    "report_period_box": { "x": 0.5, "y": 6.30, "w": 12.3, "h": 0.50,
                           "font": "Inter", "size_pt": 18, "color_hex": "CBD5E1",
                           "align": "left" },
    "header_default_fill": "4338CA",
    "agency_label_default": "{{agency_name}}",
    "default_logo_placements": {
      "agency": { "x": 10.5, "y": 0.4, "w": 2.5, "h": 0.8 },
      "client": { "x": 5.0,  "y": 5.5, "w": 3.0, "h": 2.0 }
    }
  },
  "dark_executive": { ...same shape, different coordinates... },
  "colorful_agency": { ... },
  "bold_geometric": { ... },
  "minimal_elegant": { ... },
  "gradient_modern": { ... }
}
```

### 9.2 How coordinates are obtained

During implementation:
1. Open each `.pptx` in PowerPoint (or python-pptx).
2. Note each relevant shape's `(left, top, width, height)` in EMU, convert to inches by `/914400`.
3. Record the template's default font, size, and colour for the `{{client_name}}` and `{{report_period}}` text runs.
4. Populate the JSON.

This is a one-time measurement task (~30 minutes for all 6 themes).

### 9.3 How coordinates are used

**Frontend** (preview overlays): `left = x/13.33 * container_width_px`, `top = y/7.5 * container_height_px`. Overlays absolutely positioned on top of the template thumbnail.

**Backend** (`apply_cover_customization`): 
- Header-band recolour: `_find_header_band` heuristic (current logic) — these coordinates are a fallback if heuristic fails.
- Accent bar: coordinates directly from the JSON.
- Logos: `_logo_corner_xy` already uses slide_w / slide_h; no per-theme values needed (positions are corner-based, not theme-based).

Text positions (`{{client_name}}`, `{{report_period}}`) are NOT used by the backend because text substitution happens on EXISTING template runs. The coordinates are needed only for frontend overlays.

---

## 10. Thumbnails

### 10.1 Generation

**v1 approach**: manual one-time export.
1. Run a small script using LibreOffice CLI:
   ```bash
   soffice --headless --convert-to png \
     --outdir backend/static/cover_thumbnails \
     backend/templates/pptx/modern_clean.pptx
   ```
   This produces a PNG of slide 1. Rename to `modern_clean.png`.
2. Repeat for the 5 others.
3. Commit the 6 PNGs to the repo (`backend/static/cover_thumbnails/*.png`).

**Ship with placeholder text** for `{{client_name}}` etc. Thumbnails are decorative reference — user sees them for theme picking, not as an editor preview. The DETAILED preview in the Design tab overlays user customisations on top.

### 10.2 Served where

- Backend: `/static/cover_thumbnails/{theme}.png` via existing static mount.
- Or ship directly with the frontend under `/public/cover_thumbnails/`. Simpler for CDN + cache.

Decide at implementation time. Both work.

### 10.3 Future

If templates change, re-run the export script. Document in `CLAUDE.md` as a dev workflow.

---

## 11. Template hygiene (optional one-time task)

The existing templates have hard-coded text like `PERFORMANCE REPORT`, `Prepared by {{agency_name}}` on their covers. Two stances:

### Option A — leave as-is
- These are part of the template's design. They show in the downloaded PPTX.
- Preview thumbnail shows them too (honest representation).
- Zero work.

### Option B — remove them
- Open each `.pptx` in PowerPoint. Delete the `PERFORMANCE REPORT` label and the `Prepared by {{agency_name}}` text from slide 1.
- Save. Regenerate thumbnails.
- Effort: ~30 min × 6 templates = 3 hours.
- Risk: may alter the template's visual balance in ways the original designer didn't intend.

**Recommendation: Option A for v1.** Defer to a dedicated template-polish pass post-ship if feedback warrants. Users who find the labels problematic will flag it explicitly; otherwise it's risk without signal.

---

## 12. Acceptance criteria

Per theme, the following must hold before ship:

1. **Theme selection persists.** Pick each theme; regenerate a report; verify the correct template is used.
2. **Headline override substitutes correctly.** With headline set, `{{client_name}}` is replaced on cover. Client name still appears on other slides where `{{client_name}}` token exists.
3. **Subtitle appends correctly.** With subtitle set, cover shows `"{period} — {subtitle}"`. Without subtitle, period renders alone.
4. **Brand colour tints cover header.** Verify via XML inspection: the header band shape's fill is the user's hex.
5. **Brand colour flows to charts.** Chart primary colour matches client's brand.
6. **Accent colour draws a bar.** With accent set, a thin horizontal rectangle appears at the header-band bottom.
7. **Logos honour position + size.** Agency logo at "top-center, medium" renders at the correct (x, y) with sensible dimensions. Client logo at "footer-center, small" similarly.
8. **Content slides unchanged.** Slides 2-19 render identical to how the template file draws them. No unintended regressions.
9. **Preview matches PPTX reasonably.** Preview is not pixel-perfect (font rendering differs between Chrome and PowerPoint) but meaningfully represents what the user will download. Headlines, colours, logo positions visually correspond.
10. **Backward compat.** Existing clients' reports continue to generate without errors. `visual_template` in request body is ignored with a warning log.

### Smoke test (end-to-end)

1. Pick theme `bold_geometric`.
2. Set brand primary `#DC2626`, accent `#F59E0B`.
3. Set headline `"Q2 Performance Review"`, subtitle `"Executive Brief"`.
4. Agency logo top-center / medium, client logo footer-center / small.
5. Save.
6. Preview updates to show all overrides.
7. Download PPTX preview. Confirm cover matches preview within reasonable fidelity.
8. Generate full report. Cover matches. Content slides 2-19 render per `bold_geometric` design. Charts use `#DC2626` as primary.

Repeat for all 6 themes.

---

## 13. Effort breakdown

| Phase | Work | Days |
|---|---|---|
| 1 | Migration 017 + `theme` field on schemas + backward-compat reads | 0.5 |
| 2 | Measure + JSON-encode per-theme coordinates (§9) | 0.5 |
| 3 | Generate 6 thumbnail PNGs via LibreOffice | 0.25 |
| 4 | Rewrite `cover_customization.py` (minimal 160 lines) | 1.0 |
| 5 | Frontend: rebuild `DesignTab.tsx` with 4 sections + overlay preview | 1.5 |
| 6 | Remove visual-template selector from Reports + Schedules tabs | 0.5 |
| 7 | Wire `client.theme` into generate + regenerate paths | 0.25 |
| 8 | Testing: 6 themes × 10 acceptance criteria | 1.0 |
| 9 | Documentation: update `CLAUDE.md`, write `phase-4-completion.md` | 0.25 |
| **Total** | | **~5.75 days** |

---

## 14. Explicitly out of scope for v1

- **Hero image theme.** Deferred. If added later, ships as `hero_photo.pptx` — its own 19-slide template with hero-optimised content slides, not a pseudo-preset on top of other templates.
- **Font family override.** Users can't change typography. Theme decides.
- **Per-slide customisation.** Content slides (2-19) are template-native.
- **Custom report_type / agency footer.** Continue using existing generator logic.
- **Multi-language cover typography.** v1 uses the template's native font; long non-Latin headlines may overflow. Acceptable for v1 — flag if users report.
- **CSV cover overrides.** Existing CSV upload flow untouched.
- **Per-report design overrides.** Design is per-client. Every report for a client uses the client's design.

---

## 15. Risks + mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `_find_header_band` heuristic fails for a specific theme | Medium | Per-theme coordinate JSON includes `header_band` as fallback. Apply by coordinates if heuristic returns None. |
| Long custom headlines overflow the template's `{{client_name}}` box | Medium | Document behaviour. Template's auto-shrink (if enabled) handles most cases. If overflow is common, add a word-wrap post-process. |
| Preview thumbnail is rendered at LibreOffice-different fidelity than WPS / PowerPoint / Google Slides | Low | Ship a "Download PPTX preview" button so user can verify in their actual renderer. Preview doesn't promise pixel match. |
| Backfill migration maps `cover_design_preset='hero'` to `modern_clean` which isn't what user intended | Low | Hero was rarely used per logs. Users who notice can pick a different theme. |
| Existing scheduled reports with `visual_template` set expect that template | Low | Scheduler now reads `client.theme`, ignores `scheduled_reports.visual_template`. Document in migration notes. Users reviewing their schedules see the theme name in the Schedules tab (read-only badge showing current theme). |
| Font rendering differs between Chrome (preview) and WPS/PowerPoint (PPTX) | Medium | Ship "Download PPTX preview" button for byte-accurate verification. Choose common web-safe fonts (Inter / Arial fallback) in both surfaces. |

---

## 16. What a good v1 delivery looks like

**User flow (agency owner POV):**
1. Opens a client.
2. Clicks **Design** tab.
3. Sees 6 theme cards with real thumbnails. Picks `dark_executive`.
4. Types `"Q2 Performance Review"` as headline. Preview updates instantly.
5. Drops in brand colour `#0F766E`. Preview header tints teal. Charts in downloaded report will use teal.
6. Sets agency logo to "top-center / medium". Preview shows logo move.
7. Clicks Save. Done.
8. Generates report. PPTX cover shows the teal dark-executive layout with "Q2 Performance Review" in the title position, agency logo top-center, period as "April 2026 — Executive Brief" if subtitle was set. Slides 2-19 are dark-executive template chrome unchanged. Charts are teal-palette.

No surprises. Design is coherent. Preview matched. One tab, done.

---

## STOP

This document is the contract. Once you approve:

1. Implementation proceeds phase-by-phase per §13.
2. Each phase's commit message cites the relevant §.
3. Any change to scope → edit this doc first, commit the diff, then code.

If there's anything you want changed — a theme rename, a field to add/remove, a different migration stance, Option A vs B in §11, acceptance criteria tweaks — flag it now and I'll revise the doc before code.
