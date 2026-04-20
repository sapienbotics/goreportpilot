# Phase 3 — Design System Parity Fix (PHASE-FIX) — Completion

**Status:** complete — awaiting your verification.
**Date:** 2026-04-20
**Decisions applied:** D1-B, D2-B, D3-B, D4-A (per `phase-3-parity-analysis.md` §4).

---

## 0. Executive summary

All four sub-phases (A-fix, B-fix, C-fix, D-fix) implemented. The
biggest architectural change is that the cover slide is now
**chrome-only in every template** — placeholder text and logo shapes
were stripped from the 6 master PPTX files. `cover_customization.py`
is the sole writer of cover text + colour + logo-placement-fallback
at generate time, drawing on `theme_layout` coordinates.

**Verification signals:**

| Check | Result |
|---|---|
| 6 template masters → placeholders removed from cover | ✅ (0 placeholder shapes remain on cover slides) |
| Content slides 2-19 → placeholders preserved | ✅ (85-86 placeholder-bearing shapes per deck) |
| 6 thumbnails regenerated → chrome-only | ✅ (6.3–12.8 KB each, no `{{tokens}}` visible) |
| End-to-end render on modern_clean | ✅ (6 shapes: 3 chrome + accent bar + headline + period line) |
| Brand hex `#3AB2CB` round-trip | ✅ (exact `val="3AB2CB"` in slide1.xml, zero modifier children) |
| Accent hex `#3ACBC1` round-trip | ✅ (exact, zero modifiers) |
| `verify_cover_color_parity.py` across 3 brand-tinted themes | ✅ 12/12 assertions pass |
| `npx tsc --noEmit` | ✅ clean |
| `npx next lint` (DesignTab, theme-layout, types) | ✅ clean |

---

## 1. A-fix — chrome-only templates + thumbnails + cover_customization rewrite

### 1a. Strip + regenerate script

`backend/scripts/regenerate_cover_thumbnails.py` (new, ~210 lines).
Single script does both jobs:

1. Loads every `backend/templates/pptx/{theme}.pptx`.
2. Walks the cover slide (`slides[0]`) and deletes every text shape
   whose text contains a `{{placeholder}}` token.
   - Removes 6-7 shapes per template: `{{client_name}}`, `{{report_period}}`,
     `{{report_type}}`, `{{agency_name}}` (top + footer variants),
     `{{agency_logo}}`, `{{client_logo}}`.
   - Keeps decorative chrome (header bands, gradient strips,
     geometric blocks, divider lines) and the static "PERFORMANCE
     REPORT" label.
3. Saves the stripped template back in place.
4. Builds a one-slide copy of the stripped template and converts it
   to PNG via LibreOffice CLI (`soffice --convert-to png`).
5. Writes the PNG to `backend/static/cover_thumbnails/{theme}.png`.

Idempotent: re-runs safely. Reads `SOFFICE_PATH` from env; Windows default
is `C:/Program Files/LibreOffice/program/soffice.com`.

### 1b. Templates — state after strip

```
modern_clean:    10 cover shapes → 3 (Shape 0 band, "PERFORMANCE REPORT", Shape 8 divider)
dark_executive:  9 cover shapes  → 3
colorful_agency: 12 cover shapes → 6 (3 color strips + sidebar + label + footer strip)
bold_geometric:  9 cover shapes  → 3 (right block + label + thin line)
minimal_elegant: 7 cover shapes  → 1 (thin divider only — the whitespace IS the design)
gradient_modern: 13 cover shapes → 7 (3 top gradient strips + label + 3 footer strips)
```

Content slides 2-19 untouched: 85-86 placeholder-bearing shapes per deck.

### 1c. Thumbnails — chrome-only

All 6 PNGs regenerated from the stripped masters. No `{{tokens}}`, no
placeholder logos visible. Sizes 6.3–12.8 KB (smaller than before
because less content).

### 1d. `cover_customization.py` — complete rewrite

Was (v3): finds placeholder text shapes and substitutes `{{client_name}}`
→ headline, `{{report_period}}` → period_label, etc.

Now (v4, post-strip): is the SOLE writer of cover text + colours.

Signature change:
```python
apply_cover_customization(
    prs,
    *,
    theme: str,
    headline: str,             # now required — caller resolves user override vs client.name
    period_label: str,         # now required — caller computes from report period
    subtitle: Optional[str] = None,
    brand_primary_color: Optional[str] = None,
    accent_color: Optional[str] = None,
) -> None
```

Function does:

1. **Recolour header band** — find the band shape via heuristic +
   coord fallback; set `fill.fore_color.rgb = <user_hex>`. **C-fix:**
   scrub `<a:lumMod>` / `<a:lumOff>` / `<a:tint>` / `<a:shade>` child
   elements from the resulting `<a:srgbClr>` so the rendered colour
   matches the hex byte-for-byte. Skipped for themes whose
   `brand_tint_strategy == 'none'`.

2. **Draw accent bar** — 0.10" strip at the bottom of the band. Same
   colour scrub applied. Skipped for non-band themes.

3. **Draw headline text box** — `add_textbox` at
   `theme_layout.client_name_box` coordinates with
   `theme_layout.client_name_font` specs. Center-aligned, middle-anchored,
   zero-margin to honour the spec coords exactly.

4. **Draw period + subtitle text box** — same, at
   `report_period_box` with `report_period_font`. Text is
   `period_label` or `f"{period_label} — {subtitle}"`.

Logos are NOT drawn here — `_embed_logos` still handles them after
this function runs.

### 1e. `_embed_logos` — theme-layout fallback

When the "default" logo position is picked AND no placeholder shape
exists on the cover (which is the new norm after strip), the logo is
placed using `theme_layout.{agency,client}_logo_placeholder` coords.

Order of preference (agency + client identical):

1. If a placeholder shape with the old `{{agency_logo}}` text still
   exists → use its box (legacy templates, backward-compat).
2. Else if `branding['_cover_theme']` is set → use
   `theme_layout[theme].{agency,client}_logo_placeholder`.
3. Else → hardcoded top-right / footer-center corner (final
   safety net).

Helpers `_theme_agency_logo_box` and `_theme_client_logo_box` added
in `report_generator.py`. Both routers (`preview_cover`, `generate_report`,
regenerate flow) set `branding["_cover_theme"] = client_theme` so the
fallback kicks in.

### 1f. Call-site updates

- `routers/reports.py:_render_preview` (preview endpoint) now
  computes effective headline (user override OR `client.name`) and
  passes `period_label=today.strftime("%B %Y")` to the customization
  call.
- `routers/reports.py:generate_report` — adds `branding["_cover_theme"]`.
- `routers/reports.py:regenerate_report` — same.
- `services/report_generator.py:generate_pptx_report` — reads
  `report_period_label` from the `replacements` dict (already computed
  by `_build_replacements`) and passes it through.

---

## 2. B-fix — DesignTab preview polish

`frontend/src/components/clients/tabs/DesignTab.tsx`.

### 2a. Solid tint (was blend mode)

```ts
// Before (v1)
bandStyle = { background: primary, mixBlendMode: 'multiply', opacity: 0.85 }

// After (v2)
bandStyle = { background: primary, zIndex: 1 }
```

Rationale: the chrome-only thumbnails leave the band region clean,
so blend-mode compositing is no longer useful — a solid overlay at
opacity 1.0 renders the user's exact hex with no muddy colour
interaction. Matches the PPTX's exact-colour behaviour.

### 2b. Accent bar — visibility

- Height bumped from `0.08"` to `0.10"` (now matches backend).
- Explicit `zIndex: 2` so it sits above the band overlay.
- Positioned at `band.y + band.h - 0.10` so it hugs the band bottom.

### 2c. Text overlays — z-index ordering

- Headline overlay now has `zIndex: 3` + `justifyContent: 'center'` +
  `textAlign: 'center'` (matches backend's `PP_ALIGN.CENTER`).
- Period line `zIndex: 3` + top-aligned within its box.
- Logo overlays `zIndex: 4` so they stay on top of everything.

### 2d. Panel width

Right column: `480px` → `560px`. Preview now ~60px wider on desktop,
improving readability of the font-clamped overlay text.

### 2e. Dead code removal

- Unused `effectiveBrand` prop + the invisible `<span data-effective-brand>`
  debug span removed.
- The `OverlayPreview` props interface tightened (no more `effectiveBrand`
  field).

---

## 3. C-fix — colour scrub + logo size labels

### 3a. XML colour scrub (D4 Option A)

Added `_scrub_color_modifiers_on_shape(shape)` in `cover_customization.py`.
Called after every `fill.fore_color.rgb = …` assignment (band + accent bar).

Removes these child elements from every `<a:srgbClr>` under `<a:solidFill>`:

```
lumMod, lumOff, tint, shade, alpha, gamma, invGamma,
satMod, satOff, hueMod, hueOff,
comp, inv, gray, red, redMod, redOff, green, greenMod, greenOff,
blue, blueMod, blueOff
```

**Verification:** `backend/scripts/verify_cover_color_parity.py` (new)
runs `apply_cover_customization` on every brand-tinted theme with
`#3AB2CB` + `#3ACBC1`, saves the PPTX, unzips it, parses `slide1.xml`,
and asserts both:

- The target hex appears as a `<a:srgbClr val="..."/>` attribute.
- No luminance-modifier children remain on that element.

All 12 assertions pass (3 themes × 4 checks each).

### 3b. Logo size labels

`DesignTab.tsx`:

```ts
// Before
LOGO_SIZES = [
  { id: 'default', label: 'Default' },  // ← actually medium size
  { id: 'small', ... },
  { id: 'medium', label: 'Medium' },
  { id: 'large', label: 'Large' },
]

// After
LOGO_SIZES = [
  { id: 'small',  label: 'Small' },
  { id: 'medium', label: 'Medium (default)' },
  { id: 'large',  label: 'Large' },
]
```

The `'default'` option was removed from the visible picker; it was
identical to `'medium'` on the backend (`_logo_max_box`) and caused
confusion. Existing clients whose stored value is `'default'` are
normalised to `'medium'` on load via `normaliseLogoSize()` so the
dropdown shows the truth.

Backend still accepts `'default'` for backward compat — `LogoSize`
type retains `'default'` as a valid value for legacy API payloads.

---

## 4. D-fix — logo placement parity

**Verified already correct.** Reading `DesignTab.tsx`:

- `agencyPos` / `clientPos` are React state owned by `DesignTab`.
- Dropdowns' `onChange` fire `setAgencyPos` / `setClientPos`.
- State updates re-render `OverlayPreview`, which passes `agencyPos`
  down to `PreviewLogo`, which calls `positionToXY(agencyPos, ...)`.
- No save-round-trip required — the preview reflects the form state
  immediately.

No code change needed. The earlier concern C6 that "dropdowns don't
affect preview" was a downstream effect of C1 (thumbnail had baked-in
placeholder logos that masked the overlay's movement). With chrome-only
thumbnails (A-fix), the overlay logos are the only logos and the
dropdown effects are visible immediately.

---

## 5. Files changed

### New

| File | Purpose |
|---|---|
| `backend/scripts/regenerate_cover_thumbnails.py` | Strip cover placeholders + regenerate chrome-only PNGs |
| `backend/scripts/verify_cover_color_parity.py` | XML round-trip test for brand + accent hex (12 assertions) |
| `.claude/tasks/phase-3-parity-fix-completion.md` | This file |

### Modified — backend

| File | Change |
|---|---|
| `backend/services/cover_customization.py` | Complete rewrite. Now adds text boxes (was: substituted into placeholders). Adds XML scrub for luminance modifiers after colour set. |
| `backend/services/report_generator.py` | Added `_theme_agency_logo_box` / `_theme_client_logo_box` helpers. `_embed_logos` now falls back to theme_layout coords when no placeholder shape + position is default. `apply_cover_customization` call site updated for new signature (passes `headline`, `period_label`). |
| `backend/routers/reports.py` | `preview_cover`: passes effective headline + period_label, drops stale sample `{{client_name}}` / `{{report_period}}` substitutions (now no-op). `generate_report` + `regenerate_report`: add `branding["_cover_theme"]`. |

### Modified — frontend

| File | Change |
|---|---|
| `frontend/src/components/clients/tabs/DesignTab.tsx` | Solid overlay (no blend mode). Accent bar z-index + 0.10" height. Text overlays center-aligned. Panel 480→560px. `LOGO_SIZES` dropdown — `'default'` removed from picker, legacy value normalised to `'medium'` on load. Dead `effectiveBrand` prop removed. |

### Modified — assets (binary)

| Path | Change |
|---|---|
| `backend/templates/pptx/*.pptx` (6 files) | Cover slide stripped of placeholder text shapes + logo-placeholder shapes. Content slides untouched. |
| `backend/static/cover_thumbnails/*.png` (6 files) | Regenerated from stripped masters. Chrome-only. |

---

## 6. Verification done in-session

### Backend

```
$ python backend/scripts/regenerate_cover_thumbnails.py
▸ modern_clean       stripped 7 shapes → 9.6 KB PNG
▸ dark_executive     stripped 6 shapes → 9.3 KB PNG
▸ colorful_agency    stripped 6 shapes → 9.5 KB PNG
▸ bold_geometric     stripped 6 shapes → 12.8 KB PNG
▸ minimal_elegant    stripped 6 shapes → 6.3 KB PNG
▸ gradient_modern    stripped 6 shapes → 9.4 KB PNG

$ python backend/scripts/verify_cover_color_parity.py
All colour-parity assertions passed. (12/12)
```

End-to-end shape dump for `modern_clean` after full pipeline:
```
6 shapes:
  Shape 0        (band)       0.00,0.00 13.30×2.20
  Text 1         PERFORMANCE REPORT  0.80,0.55 6.00×0.40
  Shape 8        (divider)    0.80,7.00 11.70×0.01
  Rectangle 10   (accent bar) 0.00,2.10 13.30×0.10
  TextBox 11     Test Client  0.80,2.70 11.70×1.50
  TextBox 12     April 2026 — Executive Brief  0.80,4.35 11.70×0.50
```

Text box coords match `theme_layout.py` to the EMU.

### Frontend

```
$ npx tsc --noEmit        ✓ clean
$ npx next lint           ✓ clean (DesignTab, theme-layout, types)
```

---

## 7. Verification plan (your turn)

Each item maps back to one of the verification criteria you stated:

1. **Thumbnails show clean chrome** — open Design tab, confirm no
   `{{tokens}}` or native logos visible on any of the 6 theme cards.
2. **Preview overlay — no duplication** — type "Q2 Review" as headline
   on `modern_clean`. Preview shows ONLY "Q2 Review" in the correct
   position (not both the overlay and a thumbnail-baked `{{client_name}}`).
3. **Brand hex parity in XML** — already verified by
   `verify_cover_color_parity.py`: `#3AB2CB` → `val="3AB2CB"` in slide1.xml,
   zero modifier children.
4. **Accent hex parity** — same script: `#3ACBC1` → `val="3ACBC1"`,
   zero modifiers.
5. **Logo position live preview** — change agency dropdown from
   "Default" to "Top-center" → preview logo moves immediately. Save →
   Download PPTX preview → cover in PPTX matches preview position.
6. **Full-report cover matches preview** — generate a real report
   (Reports tab → Generate). Open cover in PowerPoint/WPS. It renders
   the same theme chrome, same headline, same period line (within
   font-rendering tolerance). Brand + accent hex render byte-accurate.

---

## 8. Known residual items (documented for the plan's §6 scope line)

- **Font rendering parity (C19)**: Chrome vs PowerPoint font metrics
  still differ slightly. Preview uses Inter/Georgia at clamped px
  sizes; PPTX uses Calibri/Calibri Light/Georgia at exact pt. Intent
  (D3 Option B) is "meaningful representation, not pixel-exact" —
  already documented in Design tab helper copy.
- **Hero image theme**: still dropped for v1.
- **Content slides (2-19) retain original template styling** —
  unchanged, matches Option F v1 §11 Option A.

---

## STOP

PHASE-FIX complete. Deploy backend (Railway) + frontend (Vercel) and
run through the 6-step verification plan in §7. If everything passes,
commit + push.

If any of the 6 verifications fail, let me know which one and I'll
investigate — but colour parity is already proven via the XML
assertions, and the template strip is reversible (git-tracked).
