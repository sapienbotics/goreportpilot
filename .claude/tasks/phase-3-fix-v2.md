# Phase 3 Fix v2 — Cover Presets Shape-Dump Bugs

**Status:** ✅ Complete — awaiting user verification.
**Completed:** 2026-04-19
**Scope:** Five bugs surfaced by direct python-pptx shape inspection of a generated cover slide.

---

## 1. Bugs & root causes

### Bug 1 — Custom headline leaks into {{report_type}} slot
**Symptom:** Both Text 4 ({{client_name}}) and Text 6 ({{report_type}}) render "New Report".

**Root cause:** `_HEADLINE_PLACEHOLDERS = ("{{client_name}}", "{{report_type}}")`. My substitution loop replaced the headline token in any run containing *either* placeholder. The intent was defensive ("replace any title-like slot"), but it destroyed the report-type label.

**Fix:** Split the tuple into two purposes:
- `_HEADLINE_SUB_TOKENS = ("{{client_name}}",)` — narrow, substitution only
- `_HEADLINE_COLOR_TOKENS = ("{{client_name}}", "{{report_type}}")` — broad, colouring only

Now the report-type slot keeps its real label ("Monthly Report", "Performance Report", …) but still gets recoloured to match the preset palette.

### Bug 2 — Subtitle overwrites the reporting period
**Symptom:** Text 5 ({{report_period}}) rendered "Current FY" instead of "January 2026".

**Root cause:** `_SUBTITLE_PLACEHOLDERS = ("{{report_period}}", "{{report_date}}")`. Subtitle replaced the period slot, which is the most critical date information on the cover.

**Fix:** Narrow subtitle substitution to `{{report_date}}` ONLY:
- `_SUBTITLE_SUB_TOKENS = ("{{report_date}}",)`
- `_SUBTITLE_COLOR_TOKENS = ("{{report_period}}", "{{report_date}}", "{{agency_name}}", "{{agency_email}}")`

Now:
- The reporting period ("Jan 1 – Jan 31, 2026") ALWAYS shows on the cover.
- The report's generation date slot is what subtitle overrides when set.
- If the user doesn't set a subtitle, the generation date shows normally.
- Both slots still receive the subtitle colour from the preset.

**Chosen option (matches user's recommended option c):** subtitle replaces the soft date slot only; period is never touched.

### Bug 3 — Hero overlay too transparent
**Symptom:** Rectangle 12 (the overlay) doesn't dim the hero image — marketing text underneath is clearly readable.

**Root cause:** `_set_shape_fill_alpha(overlay, 40)` = 40% opacity black + 60% image pass-through. Too light.

**Fix:** `_set_shape_fill_alpha(overlay, 60)` — 60% opacity black + 40% image. Image still reads as texture but foreground text dominates.

### Bug 4 — Client logo in "footer-center" lands at y ≈ 5.2"
**Symptom:** User picked `footer-center`; logo sat at y=5.20" (mid-slide visually), not at y≈6.7" as expected.

**Root cause:** NOT a positioning bug. `_logo_corner_xy` correctly returns `(slide_center_x, slide_h - logo_h - margin)`, which for a 2" tall logo on a 7.5" slide gives y=5.20". The logo's BOTTOM edge is correctly at ~7.2" (i.e., "at the footer"). The problem is the logo is just too tall — a "medium" client logo defaults to 2" tall, so its top edge sits at 5.20".

**Fix:** New helper `_clamp_logo_for_position(position, max_w, max_h, kind)` clamps logo height when the position is footer/bottom:
- Agency footer: max 2.5" × 0.6"
- Client footer: max 3.0" × 0.8"

Called from `_embed_logos` after `_logo_max_box` and before `_fit_image_to_box`. With the clamp applied, a footer-center client logo now fits in a 0.8" tall box, and its top edge lands at ~6.4"–6.7" depending on aspect ratio. Visually "at the footer" as expected.

Non-footer positions are unchanged.

### Bug 5 — Accent bar invisible
**Symptom:** Rectangle 13 rendered at 0.06" tall — about 4 pixels at standard zoom.

**Root cause:** `bar_h = Emu(54_000)` ≈ 0.059". Too thin to register as a design element.

**Fix:** `bar_h = Inches(0.10)` = 0.10" ≈ 6–10 pixels. Visible but not obtrusive.

---

## 2. Execution-order change

Earlier code ran `_substitute_cover_text` BEFORE `_recolour_cover_text`. That silently defeated recolouring because by the time recolour scanned runs for placeholder tokens, they had already been substituted with custom text and didn't match the token filters.

New order inside `apply_cover_preset`:
```
1. _apply_header_and_bg_colours   (shape-fill only; ignores text)
2. _insert_hero_image             (adds pic + 60% overlay; z-order at back)
3. _recolour_cover_text           (runs contain tokens → colour persists)
4. _substitute_cover_text         (tokens → custom text; colour already applied)
5. _draw_accent_bar               (adds thin accent stripe)
```

With this order, recolour sees intact `{{client_name}}` / `{{report_type}}` / etc. tokens, applies preset colours, and the substitution pass then swaps the tokens for the custom values while preserving the runs' colour.

---

## 3. Files changed

| File | Change |
|---|---|
| `backend/services/cover_presets.py` | Split tokens into `_HEADLINE_SUB_TOKENS` / `_HEADLINE_COLOR_TOKENS` / `_SUBTITLE_SUB_TOKENS` / `_SUBTITLE_COLOR_TOKENS`. Reordered `apply_cover_preset` (recolour before substitute). Overlay alpha 40→60. Accent bar height 0.06→0.10. |
| `backend/services/report_generator.py` | New `_clamp_logo_for_position` helper. Called in both branches of `_embed_logos`. |
| `.claude/tasks/phase-3-fix-v2.md` | This file. |

Python `ast.parse` clean. No frontend changes; types and API payloads unchanged.

---

## 4. Verification steps

Run migration 016 (if not already applied). Restart backend. Then:

### Test 1 — Dump slide1 shapes after a full generate
For a client with preset=`hero`, headline=`TEST HEAD`, subtitle=`TEST SUB`:
```bash
unzip -p report.pptx ppt/slides/slide1.xml > slide1.xml
```
Open `slide1.xml` and find every `<a:t>` text node on the cover. Expect:
- Exactly ONE `<a:t>TEST HEAD</a:t>` — in the client_name text frame.
- ONE `<a:t>TEST SUB</a:t>` — in the report_date text frame.
- `<a:t>Monthly Report</a:t>` (or whatever the report_type resolves to) — NOT replaced.
- `<a:t>April 2026</a:t>` (or whatever the period resolves to) — NOT replaced.

### Test 2 — Hero image dimming
Generate with `hero` preset + any hero image. Open the PPTX. Expect:
- Hero picture at z-index 0 (back of spTree).
- Overlay rectangle immediately above, size 13.33 × 7.5".
- Overlay visibly darkens the image — marketing text / faces / logos on the hero should read as shadowed silhouettes, not clear details.

Inspect the overlay's XML:
```xml
<a:solidFill>
  <a:srgbClr val="000000">
    <a:alpha val="60000"/>
  </a:srgbClr>
</a:solidFill>
```
`val="60000"` = 60% opacity (was 40000 = 40%).

### Test 3 — Footer-center logo lands in the footer
Set client logo position = `footer-center`, size = `medium`. Generate a report. Inspect slide1 XML:
```xml
<p:pic>  <!-- client logo -->
  <p:nvPicPr><p:cNvPr id="..." name="Picture 15"/></p:nvPicPr>
  <p:spPr>
    <a:xfrm>
      <a:off x="5120000" y="6100000"/>   <!-- y should be ≈6.1"–6.8" -->
      <a:ext cx="1800000" cy="700000"/>  <!-- height ≤ 0.8" -->
    </a:xfrm>
```
Expect `y` between ~6.1" and ~6.7" (roughly slide_h=7.5" − logo_h − 0.3" margin). Height capped at 0.8" regardless of "medium" / "large" selection.

### Test 4 — Accent bar visible
Set accent color = `#F59E0B`. Generate. Open the PPTX. The accent bar should be a clearly visible horizontal stripe about 0.10" tall, at the bottom of the header band.
```xml
<a:ext cx="12192000" cy="91440"/>   <!-- cy=91440 EMU = 0.10" -->
```

### Test 5 — No regressions across 30 combinations
Cycle 5 presets × 6 visual templates. For each:
- No duplicate title text
- Report type label still shows ("Monthly Report" etc.)
- Reporting period date range still shows
- Shape count stays at template baseline (+2 for hero: pic + overlay; +1 for non-hero with accent: just accent bar)

---

## 5. Known limitations

1. **Subtitle only overrides generation date, not period.** If a template's cover doesn't include `{{report_date}}`, the custom subtitle has no visible effect. All six shipped templates include it. If a future template drops `{{report_date}}`, add it back or change `_SUBTITLE_SUB_TOKENS`.
2. **Footer logo clamping is silent.** If a user explicitly picks a "large" logo AND places it in the footer, the size will be silently reduced to fit the footer band. The alternative — letting a 3" tall logo spill halfway up the slide — was judged worse UX. Document in the tab if user confusion arises.
3. **Alpha XML patch uses lxml.etree directly.** Any python-pptx update that reorganizes `FillFormat._xPr` would need a corresponding update to `_set_shape_fill_alpha`. Covered by visual inspection, not an automated test.

---

## 6. Commit-ready

All changes:
- `backend/services/cover_presets.py` — token group split, order change, alpha 60, accent bar 0.10"
- `backend/services/report_generator.py` — `_clamp_logo_for_position` helper
- `.claude/tasks/phase-3-fix-v2.md`

No migration changes. No frontend changes. Python `ast.parse` clean.

## STOP

Awaiting your verification against the 5-test plan above.
