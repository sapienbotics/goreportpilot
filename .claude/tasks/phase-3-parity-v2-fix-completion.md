# Phase 3 — Design System Parity v2 Fix (PHASE-FIX v2) — Completion

**Status:** complete — awaiting your verification.
**Date:** 2026-04-20
**Decisions applied:** D-A Option A-1, D-B Option B-1, D-C Option C-1,
D-D Option D-1, D-E Option E-3, CRIT-6 skipped (per your approval).

---

## 0. Executive summary

Three sub-phases implemented in one consolidated pass.

| Sub-phase | Deliverable | Status |
|---|---|---|
| **A-fix2** | Accent bar repositioned to body-side of band boundary + client logo `medium` shrunk to 2.5"×1.5" | ✅ |
| **B-fix2** | `agency_attribution` field added to theme_layout (Python + TS mirror); `apply_cover_customization` draws "Prepared by <agency_name>" at each theme's original attribution coords | ✅ |
| **C-fix2** | `minimal_elegant.pptx` master enhanced with two subtle editorial horizontal rules; thumbnail regenerated | ✅ |

**Verification:**
- `npx tsc --noEmit` ✅ clean
- `npx next lint` ✅ clean (2 files)
- `verify_cover_color_parity.py` ✅ 12/12 assertions still pass (regression-safe)
- End-to-end render across 6 themes ✅ all shapes + coords correct:
  - Modern Clean accent bar at y=2.20 (below band, on white body — high contrast)
  - Dark Executive accent bar at y=2.04 (on dark navy body — high contrast)
  - Gradient Modern accent bar at y=2.60 (on body — high contrast)
  - All 6 themes now carry "Prepared by SapienBotics" at their native attribution positions

---

## 1. Phase A-fix2 — quick wins

### 1a. Accent bar repositioning (D-A Option A-1)

**Root cause:** the original `_draw_accent_bar` positioned the bar at
`band.y + band.h - 0.10`, placing it **inside** thick bands (modern_clean
2.2", gradient_modern 2.6"). With user-picked similar-hue brand + accent
colours, the bar visually merged with the band. Dark Executive
appeared to "work" only because its 0.04" band is thinner than the
0.10" bar, so 60% of the bar spilled onto the dark body with high
contrast — coincidence, not design.

**Fix:** one-line change in `cover_customization.py:_draw_accent_bar`:

```python
# Before
bar_top_emu = int((band_spec["y"] + band_spec["h"]) * EMU) - bar_h_emu

# After
bar_top_emu = int((band_spec["y"] + band_spec["h"]) * EMU)
```

**Result (verified in end-to-end smoke):**

| theme | band y-range | new accent bar y-range | context |
|---|---|---|---|
| modern_clean    | [0.00, 2.20] | [2.20, 2.30] | on white body — visible |
| dark_executive  | [2.00, 2.04] | [2.04, 2.14] | on dark navy body — visible |
| gradient_modern | [0.00, 2.60] | [2.60, 2.70] | on body — visible |

Consistent "band/body boundary marker" semantic across all three
brand-tinted themes. No longer camouflaged.

### 1b. Client logo `medium` shrunk (D-B Option B-1)

**Root cause:** `_logo_max_box("medium", kind="client")` returned
(3.0", 2.0") — 20-27% larger than every theme's `client_logo_placeholder`
box (average 2.5"×1.57"). Cover was dominated by the logo.

**Fix:** one-constant change in `report_generator.py:_logo_max_box`:

```python
# Before
"medium":  (Inches(3.0), Inches(2.0)),

# After
"medium":  (Inches(2.5), Inches(1.5)),
```

`default` also updated to match `medium` (they're aliases).
`small` unchanged (1.5"×1.0"). `large` unchanged (4.5"×3.0"; users
who explicitly want oversized still get it). Agency max-box unchanged
(was never flagged).

**Verified table:**
```
agency  medium  : (2.50", 0.80")   ← unchanged
client  medium  : (2.50", 1.50")   ← new
client  default : (2.50", 1.50")   ← new
```

---

## 2. Phase B-fix2 — agency attribution restored (composition fix)

### 2a. theme_layout schema extension

Added `agency_attribution` field to every theme in
`backend/services/theme_layout.py` + TypeScript mirror in
`frontend/src/lib/theme-layout.ts`. Each theme carries:

```python
"agency_attribution": {
    "box":   {"x": …, "y": …, "w": …, "h": …},    # inches
    "font":  {"name": …, "size_pt": …, "color_hex": …, "bold": …},
    "align": "left" | "center" | "right",
}
```

Coordinates + fonts **measured directly from the pre-strip template
masters** (via `git show 68d155d:backend/templates/pptx/{theme}.pptx`)
so the restored text sits exactly where the template designer
originally placed it. Measured specs:

| theme | box | font | size | colour | align |
|---|---|---|---|---|---|
| modern_clean    | (0.8, 1.15, 6.0×0.35) | Calibri Light | 11 | #C7D2FE | left |
| dark_executive  | (0.8, 6.70, 8.0×0.35) | Calibri | 11 | #475569 | left |
| colorful_agency | (0.8, 6.80, 8.0×0.35) | Calibri | 11 | #94A3B8 | left |
| bold_geometric  | (0.8, 6.80, 8.0×0.35) | Calibri | 11 | #A5B4FC | left |
| minimal_elegant | (1.5, 6.90, 10.3×0.30) | Calibri | 9 | #94A3B8 | center |
| gradient_modern | (0.8, 1.20, 6.0×0.35) | Calibri | 11 | #FECDD3 | left |

**Modern Clean** and **Gradient Modern** put attribution inside the
tinted band (where colour C7D2FE / FECDD3 reads as "light text on
brand fill"). The other four use footer placement. All six slots
were configured; none are `None`.

### 2b. apply_cover_customization signature

New optional parameter `agency_name`:

```python
def apply_cover_customization(
    prs,
    *,
    theme: str,
    headline: str,
    period_label: str,
    subtitle: Optional[str] = None,
    brand_primary_color: Optional[str] = None,
    accent_color: Optional[str] = None,
    agency_name: Optional[str] = None,   # ← new, v2 fix
) -> None:
```

Step 5 added after period line:

```python
clean_agency = (agency_name or "").strip()
if clean_agency:
    _draw_agency_attribution(cover, theme, clean_agency)
```

Skipped when `agency_name` is empty — no "Prepared by" pretend text
if the agency hasn't been configured yet.

### 2c. _draw_agency_attribution + _resolve_alignment

New helpers in `cover_customization.py`:

- `_draw_agency_attribution(cover, theme, agency_name)` reads the
  theme's `agency_attribution` spec, formats `f"Prepared by {agency_name}"`,
  and calls `_add_text_box` with the spec's box + font + alignment.
- `_resolve_alignment(key)` translates the `"left"/"center"/"right"`
  string to the `PP_ALIGN` enum value.

### 2d. Call sites wired

Both call sites now pass `agency_name`:

- `backend/services/report_generator.py:generate_pptx_report` —
  pulls from `replacements["{{agency_name}}"]` (already resolved via
  `_build_replacements`: profile → client → "Your Agency" fallback).
- `backend/routers/reports.py:preview_cover` — passes
  `branding["agency_name"]`.

---

## 3. Phase C-fix2 — minimal_elegant decorative chrome

### 3a. Why it was needed

Per v2 analysis §CRIT-4: after PHASE-FIX strip, `minimal_elegant` had
only **one** shape left on its cover (a 0.01" horizontal divider at
y=4.00). In the picker thumbnail the theme was indistinguishable
from a broken/empty card — users couldn't pick what they couldn't see.

### 3b. New script + template enhancement

New script: `backend/scripts/enhance_minimal_elegant_chrome.py`.
Idempotent (detects existing rules by coordinates and skips duplicate
adds). Modifications:

1. **Top rule added:** 2.0"×0.04" rectangle at (5.65, 0.55), filled
   slate-800 (#1E293B). Sits above where the agency logo renders,
   acting as a classic editorial "header mark".
2. **Existing divider thickened:** 0.01"→0.04" height at y=4.00, same
   slate-800 colour. Survives thumbnail rasterisation now.

Net effect: the picker thumbnail shows **two thin dark horizontal
rules** bracketing the whitespace — instantly recognisable as
editorial / serif-era typography, while preserving the theme's
minimalist identity (still 90% whitespace).

### 3c. Thumbnail regenerated

`regenerate_cover_thumbnails.py` re-run. `minimal_elegant.png` now
6.4 KB (was 6.3 KB — rules add minimal filesize).

---

## 4. Files changed

### New

| File | Purpose |
|---|---|
| `backend/scripts/enhance_minimal_elegant_chrome.py` | One-shot + idempotent template enhancement for minimal_elegant |
| `.claude/tasks/phase-3-parity-v2-analysis.md` | Root-cause analysis (written earlier, already committed) |
| `.claude/tasks/phase-3-parity-v2-fix-completion.md` | This file |

### Modified — backend

| File | Change |
|---|---|
| `backend/services/cover_customization.py` | Accent bar reposition. `agency_name` parameter added. New `_draw_agency_attribution` + `_resolve_alignment` helpers. Docstring updated. |
| `backend/services/theme_layout.py` | `agency_attribution` field added to all 6 themes. Docstring updated. |
| `backend/services/report_generator.py` | `_logo_max_box("medium"/"default", kind="client")` → (2.5", 1.5"). `apply_cover_customization` call site passes `agency_name` from replacements dict. |
| `backend/routers/reports.py` | `preview_cover` passes `agency_name=branding["agency_name"]`. |

### Modified — frontend

| File | Change |
|---|---|
| `frontend/src/lib/theme-layout.ts` | `AgencyAttribution` interface + `agency_attribution` field on `ThemeLayout`. All 6 theme specs extended with mirror coords. |

### Modified — assets

| Path | Change |
|---|---|
| `backend/templates/pptx/minimal_elegant.pptx` | Two decorative slate-800 rules added (top at 5.65/0.55, middle at 5.65/4.00 thickened). |
| `backend/static/cover_thumbnails/minimal_elegant.png` | Regenerated from enhanced master — now shows the two editorial rules. |

---

## 5. Verification done in-session

```
$ python backend/scripts/enhance_minimal_elegant_chrome.py
  thickened existing divider at y=4.0 to height 0.04"
  added top rule at (5.65, 0.55, 2.0×0.04)
  Cover shape count: 1 → 2 ✓

$ python backend/scripts/regenerate_cover_thumbnails.py
  6 thumbnails regenerated (no placeholder re-strip needed — templates already clean)
  minimal_elegant.png: 6.4 KB ✓

$ python backend/scripts/verify_cover_color_parity.py
  All colour-parity assertions passed. (12/12) ✓

$ python <end-to-end smoke>
  6 themes × accent bar position: all at band.y + band.h (body side) ✓
  6 themes × agency attribution: all drawn at original coords ✓
  client medium: (2.50", 1.50") verified ✓

$ cd frontend && npx tsc --noEmit    ✓ clean
$ cd frontend && npx next lint        ✓ clean (2 files)
```

End-to-end cover composition for modern_clean with test inputs
(headline="Acme Corp", subtitle="Executive Brief",
primary="#3AB2CB", accent="#3ACBC1", agency="SapienBotics"):

```
7 shapes on cover:
  [0] Shape 0         (0.00, 0.00, 13.30×2.20)  band (tinted teal)
  [1] Text 1          (0.80, 0.55,  6.00×0.40)  "PERFORMANCE REPORT"
  [2] Shape 8         (0.80, 7.00, 11.70×0.01)  footer divider
  [3] Rectangle 10    (0.00, 2.20, 13.30×0.10)  accent bar ← v2 fix
  [4] TextBox 11      (0.80, 2.70, 11.70×1.50)  "Acme Corp"
  [5] TextBox 12      (0.80, 4.35, 11.70×0.50)  "April 2026 — Executive Brief"
  [6] TextBox 13      (0.80, 1.15,  6.00×0.35)  "Prepared by SapienBotics" ← v2 fix
```

The band is now populated (TextBox 13 restores "Prepared by …" at
designer-intended position), the accent bar sits at the band/body
boundary (Rectangle 10 at y=2.20), and the composition matches the
template designer's original layout intent.

---

## 6. Verification plan (your turn)

1. **Accent bar visible across all brand-tinted themes** — open Design
   tab, set primary + accent on modern_clean → Download PPTX preview
   → accent bar visible as a thin teal strip just below the header
   band on white body. Repeat for dark_executive (on dark navy) and
   gradient_modern (on light body below gradient).
2. **Client logo reasonably sized** — default-size logo should occupy
   ~20% of slide height (was ~27%). No longer "dominates" the cover.
   Users who want larger can still pick "Large".
3. **"Prepared by <agency>" appears on cover** — generate any report;
   cover carries the attribution text at the theme's native position:
   - modern_clean / gradient_modern: inside the tinted band
   - dark_executive / colorful_agency / bold_geometric: footer-left
   - minimal_elegant: center footer
4. **minimal_elegant picker-recognisable** — Design tab theme picker;
   minimal_elegant card now shows two thin dark horizontal rules
   (editorial mark). Clearly distinguishable from other themes.
5. **Existing functionality regression-free** —
   - Colour parity still exact (`verify_cover_color_parity.py` passes
     12/12).
   - Headline + period/subtitle text still at correct coords.
   - Logo placement dropdowns still reflect immediately in preview.
   - Generate full report from a client → cover matches preview
     within font-rendering tolerance.

---

## 7. Decisions not implemented

Per your message, two items were explicitly skipped:

- **D-E (template chrome colour protection)** — Option E-3 accepted:
  template-designer colour intent kept (dark_executive's teal
  "PERFORMANCE REPORT" stays teal). If user's brand is also teal,
  visual affinity is by chance, not bug.
- **CRIT-6 (preview proportional drift)** — perceptual only, no code
  change required. Preview coord math provably correct
  (boxToPercentStyle outputs 29.33% band height for modern_clean,
  matching the PPTX's 2.2/7.5 ratio exactly).

---

## STOP

PHASE-FIX v2 complete. Deploy backend (Railway) + frontend (Vercel)
and walk through the 5-point verification plan in §6. If all passes,
commit stands. If any issue surfaces, ping me with the specific
theme + symptom and I'll diagnose.
