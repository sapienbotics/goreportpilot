# Phase B (Frontend) — Design System Option F v1

**Status:** ✅ Complete — awaiting your verification. Stop point per instruction.
**Completed:** 2026-04-20
**Scope:** all frontend work for the Design System unification. Backend Phase A was already verified and is live.

---

## 1. What was built

### New files

| File | Size | Purpose |
|---|---|---|
| `frontend/src/lib/theme-layout.ts` | ~170 lines | Single source of truth for theme layout coords — mirrors `backend/services/theme_layout.py`. Exports `THEME_IDS`, `THEME_LAYOUT`, `boxToPercentStyle`, `ThemeId` type. 6 themes with labels + taglines for the picker. |
| `frontend/src/components/clients/tabs/DesignTab.tsx` | ~470 lines | The unified Design tab. 4 sections + sticky overlay preview. Replaces `ReportCustomizationTab.tsx` (deleted). |
| `.claude/tasks/phase-B-completion.md` | This file | |

### Modified files

| File | Change |
|---|---|
| `frontend/src/types/index.ts` | `Client` interface: added `theme` (typed as new `Theme` enum), kept deprecated `cover_design_preset` / `cover_hero_image_url` nullable for backward compat. `CoverPreset` type removed. `Theme` type exported. |
| `frontend/src/lib/api.ts` | `ClientUpdatePayload.theme` added; `cover_design_preset` / `cover_hero_image_url` removed. `previewCover()` payload type: `theme` added, `preset` / `hero_image_url` / `visual_template` removed. `ReportGeneratePayload.visual_template` marked `@deprecated` (still optional for backward compat). |
| `frontend/src/app/dashboard/clients/[clientId]/page.tsx` | Import `DesignTab` (was `ReportCustomizationTab`). Tab id `'customization'` → `'design'`, label "Report customisation" → "Design". Deleted `visualTemplate` state + setter + usages. `handleGenerate` no longer sends `visual_template`. |
| `frontend/src/components/clients/tabs/ReportsTab.tsx` | Removed `VisualValue` type + `visualTemplate` + `setVisualTemplate` props. Removed the entire "Visual Style" button grid. Kept `Lock` icon (still used for trial/expired badges). |
| `frontend/src/components/clients/tabs/SchedulesTab.tsx` | Removed `VISUAL_TEMPLATE_OPTIONS` constant. Removed the "Visual style" select block. Removed `Lock` icon import + `usePlanFeatures` call (both orphaned after the block removal). |

### Deleted
- `frontend/src/components/clients/tabs/ReportCustomizationTab.tsx`

---

## 2. DesignTab — the 4 sections

### A. Theme picker
- 3×2 grid of 6 cards, each showing:
  - Real template thumbnail served from `/static/cover_thumbnails/{theme}.png` (Phase A ships these)
  - Theme label ("Modern Clean", "Dark Executive", etc.)
  - 1-line tagline
- Selected card has indigo ring + border
- Caption: *"The theme governs the whole deck — cover and all content slides share a design language."*

### B. Brand colours
- Two `ColorField` controls: Primary + Accent
- Each is a `<input type="color">` + hex text input side by side, with validation
- Primary's placeholder shows the agency default (fetched from `/api/settings/profile`)
- Hint text (with info icon): *"Brand colour applies to the cover header … and chart palette. Slide backgrounds and decorative elements follow the chosen theme."* — dynamically reflects whether the selected theme supports band tinting

### C. Cover text
- Headline input (max 80 chars, placeholder shows client's real name)
- Subtitle input (max 120 chars)
- Live preview of the period line below the subtitle field: *"April 2026 — Executive Brief"*

### D. Logo placement
- Two `LogoRow`s: Agency + Client
- Each shows logo thumbnail + position dropdown + size dropdown
- If no agency logo set on profile → hint to upload in Settings
- Client logo has an inline upload button (reuses existing `uploadClientLogo`)
- Position: 8 options (default / top-left / top-right / top-center / footer-left / footer-right / footer-center / centre)
- Size: 4 options (default / small / medium / large)

### Live preview (right column, sticky)
- Base layer: the selected theme's thumbnail PNG at slide aspect ratio (13.333:7.5)
- Band tint overlay: positioned over the theme's `header_band` coordinates, filled with primary colour, `mixBlendMode: multiply` + 85% opacity. Skipped for themes with `brand_tint_strategy: 'none'`.
- Accent bar: thin strip at the bottom of the band, accent colour
- Headline text: absolutely-positioned at `theme.client_name_box` coords, using the theme's font name/size/colour from `theme-layout.ts`
- Subtitle text: same, at `theme.report_period_box`
- Agency logo: `<img>` at user-selected position (or placeholder default)
- Client logo: same

### Save / Download
- Top-right of the card: **Download PPTX preview** (calls `previewCover` with current form state) + **Save** (disabled until changes)
- Saving PATCHes `/api/clients/{id}` with the full field set → toast + client update

---

## 3. What disappeared from other tabs

### Reports tab
- "Visual Style" section with 6 template buttons
- `visualTemplate` / `setVisualTemplate` props
- Template included in generate-report payload

### Schedules tab
- "Visual style" select
- `visual_template` field surfaced in the form (kept in the payload default at client-page level for backward compat with the legacy DB column)

### Client detail page
- `visualTemplate` state + setter + passthrough props
- `visual_template` in `handleGenerate` payload

---

## 4. Verification done in-session

- ✅ `npx tsc --noEmit` — clean (no errors)
- ✅ `npx next lint --file <each changed file>` — clean
- ✅ No grep hits for stale `ReportCustomizationTab` or `CoverPreset` type references
- ✅ `VisualValue` type from ReportsTab is removed; replaced references audit clean
- ✅ Orphaned imports (`Lock` in SchedulesTab, `usePlanFeatures` in SchedulesTab) pruned

---

## 5. End-to-end test plan

### Prerequisite
Deploy frontend (Vercel or local `npm run dev`). Backend Phase A already running with migration 017 applied.

### Test 1 — Design tab renders the 6 themes
1. Open a client → click **Design** tab.
2. Expected: 6 theme cards with real cover thumbnails (served from backend `/static/cover_thumbnails/`).
3. Click different themes. Card ring updates. Preview image swaps.

### Test 2 — Live preview reflects form state
1. Pick `bold_geometric`.
2. Type headline "Q2 Review" and subtitle "Executive Brief".
3. Preview shows:
   - bold_geometric thumbnail
   - "Q2 Review" overlaid at the template's client_name position
   - "April 2026 — Executive Brief" below
4. Set primary to `#DC2626`. Header-band area shows a faint red tint (blend mode multiply) — this theme has `brand_tint_strategy: 'none'` so tint is skipped. Hint text updates to reflect that.
5. Set primary on `modern_clean` preset: tint IS visible on the header band.
6. Set accent to `#F59E0B` on `modern_clean`: thin amber bar at the band bottom.

### Test 3 — Logo placement preview
1. Set agency logo to "Top-center / medium" → preview logo moves to top centre.
2. Set client logo to "Footer-center / small" → preview logo moves to bottom centre.
3. Preview logos' sizes change as expected per size setting.

### Test 4 — Save persists + Download PPTX preview
1. Make changes, click **Save**.
2. Toast: *"Design saved."* Save button disables.
3. Click **Download PPTX preview** → downloads `{client}_cover_preview.pptx`.
4. Open the file — cover should show the exact customisations applied (real rendering, not CSS approximation).

### Test 5 — Reports tab no longer has visual style selector
1. Go to Reports tab.
2. Expected: no "Visual Style" section. Detail level + Date range + CSV upload only.
3. Generate a report. It uses the client's current theme (from Design tab).

### Test 6 — Schedules tab no longer has visual style selector
1. Go to Schedules tab.
2. Expected: no "Visual style" dropdown. Frequency + Timezone + Detail level + Attachment format + Auto-send remain.

### Test 7 — Backward compat
1. Create a client before Phase A migration would have had `cover_design_preset='bold'`.
2. After migration 017, their `theme` should be `'bold_geometric'`.
3. Open Design tab for that client — `bold_geometric` is selected by default.

### Test 8 — No broken URL bookmarks
1. Old URL `/dashboard/clients/{id}?tab=customization` — no longer matches; falls through to Overview. Acceptable.
2. New URL `/dashboard/clients/{id}?tab=design` — opens the Design tab.

---

## 6. Known limitations (documented in DESIGN-SYSTEM-PLAN.md)

1. **Preview is not pixel-exact** with the downloaded PPTX. Font rendering between Chrome and PowerPoint/WPS/Google Slides differs. Preview is designer-quality and meaningfully representative; for byte-accurate verification, use **Download PPTX preview**.
2. **3 themes don't support brand tint** on cover (colorful_agency, bold_geometric, minimal_elegant). Brand colour still flows to charts. Hint text in the Design tab makes this clear.
3. **Hero image dropped** in v1. Old `cover_hero_image_url` kept as nullable deprecated field in types for backward compat; UI doesn't expose it. Will be revisited later as a dedicated theme.
4. **Preview for agency logo** uses the `/api/settings/profile` fetch. If the profile doesn't have an agency logo uploaded, that slot in the preview shows nothing (with a hint in the controls).
5. **Scheduled reports with stale `visual_template`** in the DB: backend scheduler ignores the field (Phase A work). Frontend sends a default value when creating new schedules to avoid NULL issues on the legacy column.

---

## 7. Files changed — final tally

| File | Status | Lines |
|---|---|---|
| `frontend/src/lib/theme-layout.ts` | NEW | ~170 |
| `frontend/src/components/clients/tabs/DesignTab.tsx` | NEW | ~470 |
| `frontend/src/components/clients/tabs/ReportCustomizationTab.tsx` | DELETED | — |
| `frontend/src/types/index.ts` | MOD | +4 / −3 |
| `frontend/src/lib/api.ts` | MOD | +4 / −7 |
| `frontend/src/app/dashboard/clients/[clientId]/page.tsx` | MOD | +5 / −8 |
| `frontend/src/components/clients/tabs/ReportsTab.tsx` | MOD | +4 / −47 |
| `frontend/src/components/clients/tabs/SchedulesTab.tsx` | MOD | +4 / −26 |
| `.claude/tasks/phase-B-completion.md` | NEW | This file |

Net reduction in frontend complexity: ~500 lines of per-report template-picker UI deleted; ~640 new lines added (the DesignTab is richer than what it replaces — adds live preview overlays, 8-position logo placement, etc.).

---

## STOP

Phase B complete. Deploy the frontend and run the 8-test plan in §5.

When verified, we can commit+push. Let me know if you want the commit composed now or after your verification.
