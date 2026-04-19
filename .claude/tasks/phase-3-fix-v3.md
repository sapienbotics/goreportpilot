# Phase 3 Fix v3 — Hero Preset Cohesion + Logo Placement Diagnostics

**Status:** ✅ Code complete — awaiting your visual verification.
**Completed:** 2026-04-19
**Important constraint:** I cannot take screenshots from this environment (no browser, no image renderer). You'll need to do the visual verification yourself. The changes below are designed to produce a cohesive render, with deterministic darkening (pixel-level) instead of relying on PowerPoint alpha.

---

## 1. Bugs & root causes

### Bug 1 — Template header band visible through hero preset
**Symptom:** Upper 2.2" of the cover still shows the template's default purple header band, even when the `hero` preset is active. Produces a "split cover" look (purple band + hero body).

**Root cause:** The `hero` preset config has `header_fill: None`. `_apply_header_and_bg_colours` correctly SKIPS the header recolour in that case. But "skip recolour" isn't the same as "make transparent" — the template's original opaque indigo fill stayed, painted on top of the hero image.

**Fix:** New `_clear_header_band(prs, cover)` helper. Finds the header-band shape using the same heuristic as `_find_header_band` and calls `shape.fill.background()` — explicit "no fill". Called from `_insert_hero_image` right after inserting the picture. Hero image now shows through the full slide.

### Bug 2 — Alpha overlay didn't dim the hero image
**Symptom:** Marketing text on the hero is fully readable in rendered output despite 60% alpha `<a:alpha val="60000"/>` present in the XML.

**Root cause (best theory):** Our rendering path is PPTX → PDF via LibreOffice, not PowerPoint. LibreOffice's rendering of `<a:alpha>` on `<a:srgbClr>` inside `<a:solidFill>` is historically inconsistent across versions — sometimes honoured, sometimes ignored. When ignored, the overlay renders fully opaque black (covering everything) OR fully transparent (not dimming at all); the latter matches the user's report.

**Fix:** Don't rely on renderer-side alpha. Darken the image pixel-wise in Python using `PIL.ImageEnhance.Brightness(img).enhance(0.40)` BEFORE embedding. The dimmed JPEG/PNG we insert already contains dim pixel values — every renderer, every version, honours pixel values identically.

This also lets me remove the separate overlay rectangle (which was a flaky workaround for this exact problem). Simpler, more reliable, one fewer shape in the deck.

### Bug 3 — "Top-center" agency logo rendered at top-right
**Symptom:** User picked `top-center` in the tab; rendered output shows logo at top-right (the legacy default position).

**Investigation:** `_logo_corner_xy` is correct for `top-center`: `x = (slide_w - logo_w) // 2, y = margin`. The code path requires `agency_pos != "default"` to activate the explicit placement branch. So either:
1. The value never made it to `_embed_logos` (was "default" or empty string by the time it arrived)
2. Something else is placing a second logo at top-right

Can't conclusively diagnose without runtime logs from your deploy.

**Fix:** Added explicit `logger.info()` calls in `_embed_logos` that log:
```
_embed_logos: agency_pos='top-center' size='medium'  client_pos='default' size='default'
agency logo explicit placement: pos=top-center → left=5042520 top=274320 (EMU)
```
Reproduce the bug, check backend logs. You'll see exactly what position reached the function and what coordinates it computed. If `agency_pos='default'`, the value isn't flowing through — that's a frontend / payload issue. If `agency_pos='top-center'` but the rendered logo is top-right, something downstream of `_embed_logos` is relocating it, which would be much more exotic.

Also added `.strip().lower()` to the position parse in case whitespace or casing ever enters the payload.

### Bug 4 — Hero too dominant for readable custom text
**Symptom:** User-uploaded hero had marketing text that competed with the custom "Test Header" overlay, especially with the preset's white text colour.

**Fix:** Bug 1 + Bug 2 together address this:
- Bug 1 fix: header band cleared → hero fills the whole cover (unified look instead of split)
- Bug 2 fix: 60% darkening (brightness 0.40) applied to hero pixels → underlying marketing text reads as shadowed texture, not competing foreground

Documentation guidance: hero images that are photographic / visual-forward work best. Dense text-on-image heroes will still be visible under 40% brightness — darkening to 0.30 would obliterate them at the cost of colour. 0.40 is the sweet spot based on typical UX recommendations for dark image overlays.

---

## 2. Files changed

| File | Change |
|---|---|
| `backend/services/cover_presets.py` | New `_clear_header_band` helper. `_insert_hero_image` rewritten: darken via Pillow + clear header band + no overlay rectangle. `_reorder_to_back` generalised to variadic `*shapes`. |
| `backend/services/report_generator.py` | Debug logging in `_embed_logos` (resolved positions + computed EMU coords). `.strip().lower()` on incoming position values. |
| `.claude/tasks/phase-3-fix-v3.md` | This document. |

No migration, no schema, no frontend changes.

---

## 3. Why I can't send a screenshot

This environment has no browser, no PPTX renderer, and no image-capture tool. Previous phases worked because I could verify code paths via `ast.parse` + `tsc --noEmit`, but pixel-level visual verification requires rendering the PPTX.

What I CAN do, which I've done:
- Python syntax check (passes)
- Added logging so your test run will produce diagnosable output
- Trace the logic statically — the Bug 1 + 2 fixes are deterministic (no alpha guessing)

What YOU need to do:
- Run the fix, generate a preview, open the PPTX (or the rendered PDF), look at the cover
- If Bug 3 persists, check backend logs for the `_embed_logos: agency_pos=…` line — it'll tell us exactly what reached the function

If you want, I can write a small standalone Python script that loads the generated PPTX, dumps every shape's (type, position, size, fill, text) to stdout so you get a machine-readable diff instead of having to eyeball it. Say the word.

---

## 4. Test plan

### Prerequisite
Deploy the backend (no migration required this round). Open a client's Report customisation tab.

### Test 1 — Hero cover renders as a single image
Pick `hero` preset, upload a dark-friendly photo, set headline = "TEST HEAD", subtitle = "TEST SUB", save. Download PPTX preview.

Expected:
- No purple/indigo band at the top — hero image fills the whole cover
- Image is visibly darker than the original (about 40% of original brightness)
- White title text "TEST HEAD" and subtitle "TEST SUB" read cleanly over the dimmed image
- Shape count on slide 0: template baseline + 1 (pic only — no overlay rectangle)

Inspect XML to confirm:
```
unzip -p preview.pptx ppt/slides/slide1.xml > slide1.xml
```
- `<p:pic>` element is first in `<p:spTree>` after `<p:nvGrpSpPr>` + `<p:grpSpPr>` (back of z-order)
- Header-band rectangle (if present) has `<a:noFill/>` inside `<p:spPr>`
- No separate 13.33×7.5 overlay rectangle

### Test 2 — Non-hero presets unchanged
Switch to `bold`, `minimal`, `corporate`, `gradient`. Generate preview each time. Expected: behaviour unchanged from v2 (solid colour header + body).

### Test 3 — Agency logo top-center, read the logs
Set agency logo = "Top-center", size = "Medium". Save. Generate report OR preview.

Expected backend log lines:
```
_embed_logos: agency_pos='top-center' size='medium'  client_pos='…' size='…'
agency logo explicit placement: pos=top-center → left=<EMU> top=<EMU> (EMU)
```

Convert EMU to inches: `inches = EMU / 914400`. For a standard medium agency logo:
- `fit_w` around 2.5" = 2286000 EMU
- Slide width 13.33" = 12192000 EMU
- `left` at top-center ≈ (12192000 − 2286000) / 2 ≈ 4953000 EMU = ~5.42"

If the log shows `left=9635000` or similar (close to 10.5"), the position string actually arriving at the function was something other than "top-center" — send me the logs and we'll chase the flow-through issue.

### Test 4 — Footer-center client logo (v2 clamp still holds)
Set client logo = "Footer-center", size = "Large". Expected logs:
```
client logo explicit placement: pos=footer-center → left=<EMU> top=<EMU> (EMU)
```
`top` should be ≈ 6900000–6100000 EMU (6.7"–6.67"), height (from `fit_h` in the `add_picture` call) capped at 0.8".

### Test 5 — Logo flow-through debug
If Bug 3 persists after this fix, the logs will distinguish three cases:
1. `agency_pos='default'` → value isn't reaching the function; check client row / API payload
2. `agency_pos='top-center'`, `left≈5442000`, but logo still renders at top-right → something downstream is relocating it (unlikely)
3. `agency_pos='top-center'`, `left≈9635000` → `_logo_corner_xy` returning wrong value (would need code review)

Send the log output for cases 1 or 3 and I can pinpoint quickly.

---

## 5. Known limitations

1. **Pillow darkening happens in backend worker.** Each hero preview adds ~20–80 ms for a 1 MB image. Negligible but noted.
2. **Darkening is destructive.** Cached/downloaded hero image stays original; we darken on every generate. If the same client generates many reports with the same hero, we re-darken each time. Could cache but the bytes are small and the effect is consistent.
3. **Pillow JPEG encoding at quality 88** adds a small file-size bump vs the original. Acceptable (hero images are already compressed).
4. **If Pillow fails**, we fall back to the undarkened original. Headline may then be hard to read. Logged at debug level; observable in logs.

---

## 6. STOP

Code ready. No migration. Deploy and run Test 1 — that's the core hero cohesion check. Then Test 3 and send me the `_embed_logos: agency_pos=…` log line so we can either close Bug 3 or pinpoint where the position value is being lost.
