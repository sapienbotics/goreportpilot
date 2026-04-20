# Phase 3 v2 — Post-Deploy Concerns Analysis

**Status:** analysis only — NO code changes yet.
**Prepared:** 2026-04-20
**Scope:** 4 concerns surfaced after the v2 deploy (commit `430b726`).
Root-cause investigation against current code + original pre-strip
templates + on-disk thumbnails. Architectural decisions flagged for
your approval before any fix is coded.

---

## 0. Executive summary

| Concern | Verdict | Fix shape |
|---|---|---|
| **C1** — Headline/period alignment inconsistent | **Real bug.** `cover_customization.py` hardcodes `PP_ALIGN.CENTER` for headline + period; 5 of 6 original templates were LEFT-aligned. | Make alignment per-theme (from theme_layout) |
| **C2** — Subtitle as tagline, not period append | **UX reversal** of the v1 design decision. Needs architectural call. | Add `subtitle_box` slot per theme + dynamic period Y |
| **C3** — Gradient Modern thumbnail wrong | **Not a bug.** Thumbnail on disk is correct (3 gradient strips visible). Likely browser cache or user mis-testing. | Cache-bust query param in picker `<img>` |
| **C4** — "Prepared by" missing from preview + size concerns | **Real parity gap.** DesignTab preview never renders `agency_attribution`. Font sizing is designer-intent and subjective. | Add attribution overlay to preview; leave font sizing to your call |

**Three architectural decisions need your approval** before coding
(DA1 alignment inheritance, DA2 subtitle layout strategy, DA3
preview-element-completeness promise). Details in §4.

---

## 1. C1 — Headline/period alignment audit

### Evidence — measured from pre-strip templates

Query: for each theme, inspect `{{client_name}}` and `{{report_period}}`
paragraph alignment in the HEAD~2 commit (`68d155d`, pre-strip state).

| theme | client_name align | report_period align |
|---|---|---|
| modern_clean    | **default (left)** | **default (left)** |
| dark_executive  | **default (left)** | **default (left)** |
| colorful_agency | **default (left)** | **default (left)** |
| bold_geometric  | **default (left)** | **default (left)** |
| minimal_elegant | **CENTER** | **CENTER** |
| gradient_modern | **default (left)** | **default (left)** |

### Current code behaviour

`backend/services/cover_customization.py:296` (`_draw_headline`):
```python
align=PP_ALIGN.CENTER,
```

`backend/services/cover_customization.py:317` (`_draw_period_line`):
```python
align=PP_ALIGN.CENTER,
```

Hardcoded. No per-theme override.

### Root cause

In the v1 rewrite (`3cde04c`) I defaulted headline + period to
CENTER alignment under the (wrong) assumption that centered text
"looks clean on all templates". This overrode the designer intent
for 5 of 6 themes. Post-deploy screenshots show:

- Minimal Elegant (was center, still center) — consistent ✓
- Every other theme: forced center, looks unlike the original
  composition the template designer authored

Compounding factor: `_add_text_box` uses `MSO_ANCHOR.MIDDLE` for
headline (vertical-centre inside the box). Some template designers
expect top-anchor for headline boxes to set up vertical hierarchy.

### Fix shape

Two options. Both additive, no breaking changes.

**Option C1-A — Derive alignment from box aspect ratio (heuristic)**
If `box.w > box.x * 2` (box is clearly centred on slide), use CENTER.
Else LEFT. Works because templates with narrow left-offset boxes
(bold_geometric `client_name_box` at x=0.8, w=7.0) were designed for
left alignment.
- Pros: no schema change; self-adapting.
- Cons: opaque; "why is this one centered but that one isn't?".

**Option C1-B — Explicit per-theme alignment ⭐ RECOMMENDED**
Add a `client_name_align` + `report_period_align` field (or nest
alignment inside the font spec) to `theme_layout`. Mirror in the TS
copy. `_draw_headline` / `_draw_period_line` read it.
- Pros: explicit; matches designer intent exactly; extensible (if
  some theme later wants right-alignment for an accent, it's one line).
- Cons: schema adds a field per box; maintain discipline on parity.

**Recommendation: Option C1-B.** The `agency_attribution` field we
added in v2 already has an `align` key ("left" | "center" | "right")
with a working resolver (`_resolve_alignment`). Same pattern
generalised to headline + period is cheap and symmetrical.

---

## 2. C2 — Subtitle as tagline (UX reversal of v1 ADR)

### Current behaviour (shipped v1 + v2)

`cover_customization.py:99-103`:
```python
period_line = period_label if not subtitle else f"{period_label} — {subtitle}"
```

Rendered as a single line at `report_period_box`:
```
April 2026 — Executive Brief
```

### Desired behaviour (user request)

Three stacked lines on cover:
```
Test Header              ← headline (unchanged position + style)
Test Sub                 ← subtitle (NEW — tagline position, below headline)
April 2026               ← period only (subtitle removed from append)
```

Subtitle acts as a tagline — visually tied to headline, not to period.

### Why this breaks v1 ADR

Phase B (commit `54ff14d`) explicitly chose the append-to-period
approach because:
1. No vertical space between headline and period in the template
   coords (gap is 0.10–0.20" in 5 of 6 themes).
2. Subtitle is an "extra optional line" — appending to period reused
   an already-visible text run.

User's request reverses both: subtitle is PRIMARY-TIER (tagline under
headline), not a period suffix.

### Vertical space audit

Gap between headline bottom and period top per theme:

| theme | headline ends | period starts | gap |
|---|---|---|---|
| modern_clean    | 4.20 | 4.35 | 0.15 |
| dark_executive  | 4.00 | 4.15 | 0.15 |
| colorful_agency | 3.40 | 3.60 | 0.20 |
| bold_geometric  | 3.80 | 3.90 | 0.10 |
| minimal_elegant | 3.80 | 4.30 | 0.50 |
| gradient_modern | 4.60 | 4.70 | 0.10 |

5 of 6 themes: 0.10–0.20". Insufficient for a legible subtitle
(needs ~0.35" for 11pt text + padding).

### Architectural options

**Option C2-A — Squeeze into existing gap (reject)**
Use 6-10pt font in the 0.10–0.20" gap.
- Con: illegible; loses tagline hierarchy.

**Option C2-B — Dynamic period Y with new `subtitle_box` slot ⭐ RECOMMENDED**
- Add `subtitle_box` per theme. Coords occupy the ORIGINAL period slot
  (subtitle.y = original period.y, h = 0.35).
- When subtitle is set:
  - Draw subtitle at `subtitle_box` coords
  - Draw period at `subtitle.y + subtitle.h + gap` (e.g., modern_clean
    period shifts 4.35 → 4.80)
- When subtitle is unset:
  - Period stays at its original Y (4.35) — no gap, matches current render
  - `_draw_subtitle` is a no-op

Pros:
- Best-of-both: clean layout with subtitle, unchanged layout without
- Designer-intent preserved when subtitle absent
- Only period.y changes dynamically (single line of logic in
  `_draw_period_line`)

Cons:
- Period.y becomes dynamic (minor complexity)
- Re-measurement needed per theme: does `subtitle.y + subtitle.h +
  gap + period.h` still fit within the slide? All 6 fit comfortably
  (max bottom edge lands at 5.30" on 7.50" slide).

**Option C2-C — Static 3-row composition (shrink headline)**
Always reserve space for subtitle. Shrink `client_name_box.h` from
1.5"→1.0"; add `subtitle_box` in vacated space; period unchanged.
- Pros: deterministic coords.
- Cons: headline truncates for long client names (esp. serif themes);
  awkward empty row when subtitle unset.

**Option C2-D — Subtitle below period (reuse stripped report_type slot)**
Subtitle occupies where `{{report_type}}` used to be (immediately
below period).
```
Headline
April 2026
Test Sub     ← subtitle here
```
- Con: doesn't match user's stated "subtitle directly below headline
  as a tagline" request.

**Recommendation: Option C2-B (dynamic period Y).** Minimal code
change, matches user intent exactly, graceful no-subtitle fallback.

### Preview side

`DesignTab.tsx` currently has a `periodStyle` overlay that concatenates
period + " — " + subtitle via `buildPeriodLine()`. For C2-B:

- Add a new `subtitleStyle` overlay (own CSS absolute position)
- `periodStyle` overlay: reverts to period only
- Dynamic top-offset: when subtitle is set, period overlay's top
  shifts down by `subtitle.h + gap` (as percent of slide height)

Parity with backend: identical subtitle_box coords from theme_layout.ts
mirror (which means adding `subtitle_box` field to TS too).

---

## 3. C3 — Gradient Modern thumbnail

### Ground truth

Current state of `backend/static/cover_thumbnails/gradient_modern.png`:

- **git status:** clean (matches `HEAD`)
- **git hash-object:** `915410999cb52283bf9eac490088f89e612e882d`
- **Visual inspection:** 3 gradient strips (orange + crimson + purple)
  across the top 35%, "PERFORMANCE REPORT" label in white on the
  orange left strip, 3 footer strips at the bottom — i.e. CORRECT

`backend/templates/pptx/gradient_modern.pptx` cover:
```
Cover shape count: 7
  [0] Shape 0    (0.00,0.00,13.30x2.60)   top gradient base
  [1] Shape 1    (3.99,0.00, 9.31x2.60)   second gradient overlay
  [2] Shape 2    (8.64,0.00, 4.66x2.60)   third gradient overlay
  [3] Text 3     (0.80,0.60, 6.00x0.40)  "PERFORMANCE REPORT"
  [4] Shape 10   (0.00,7.42, 5.32x0.08)   footer strip 1
  [5] Shape 11   (5.32,7.42, 4.66x0.08)   footer strip 2
  [6] Shape 12   (9.97,7.42, 3.33x0.08)   footer strip 3
```

All 7 expected decorative shapes intact.

### Why user saw "indigo panel with thin divider"

Two likely causes:

1. **Browser thumbnail cache (most probable).** The thumbnail URL is
   `${API_URL}/static/cover_thumbnails/${theme}.png` with no
   cache-bust. If the user's browser cached the v0 (pre-strip) version
   of gradient_modern — which WAS essentially "header band + body" at
   that time because the gradient was poorly rendered pre-fix — it
   continues serving that from the browser disk cache.
2. **User mis-identifying the theme.** "Indigo panel with thin divider"
   visually describes `modern_clean` (solid band + footer divider),
   not `gradient_modern`. Possible they were testing modern_clean and
   reported it against the wrong theme name.

Neither is a codebase bug. Both are reproducible to confirm.

### Fix shape

**Option C3-A — Cache-bust query param ⭐ RECOMMENDED**
Append `?v=<build-hash>` or `?v=<thumbnail-mtime>` to the thumbnail
`<img src>` URL in `DesignTab.tsx`. Browser re-fetches whenever the
hash changes.
- Pros: trivial 1-line change, permanent fix
- Cons: invalidates CDN cache on every deploy

**Option C3-B — Force-refresh once**
Ask the user to hard-refresh (Ctrl+Shift+R) their browser. Confirms
whether C3 was cache vs. genuine.
- Pros: zero code change if it resolves
- Cons: reactive, doesn't prevent recurrence

**Recommendation: Option C3-A** (and do C3-B first to confirm diagnosis).
Cache-busting is near-free and prevents the class of bug.

---

## 4. C4 — "Prepared by" missing from preview + font size concerns

### 4a. Preview parity gap — confirmed

`grep "agency_attribution" frontend/src/components/clients/tabs/DesignTab.tsx`
→ **zero matches**.

The field exists in `frontend/src/lib/theme-layout.ts` (added in v2
commit `430b726`) but `DesignTab.tsx` never reads it and never
renders the "Prepared by …" text in the preview overlay.

Result: preview doesn't match PPTX render — the PPTX carries a
"Prepared by …" text line the preview hides.

### 4b. Font size concern

User observation: "Font size may be too small (looks ~10-11pt, could
be 12-14pt)".

Current values in `theme_layout.py`:

| theme | attribution size_pt |
|---|---|
| modern_clean    | 11 |
| dark_executive  | 11 |
| colorful_agency | 11 |
| bold_geometric  | 11 |
| minimal_elegant |  9 |
| gradient_modern | 11 |

Measured directly from pre-strip template runs. 9-11pt is
"subdued cover metadata" scale — designer intent was that the
attribution NOT compete with the headline (40-44pt) or period (14-16pt).

Bumping to 12-14pt would:
- Make attribution more visible (user's ask)
- Create competition with period_font (14pt) — attribution would read
  as primary rather than tertiary
- Diverge from designer intent

This is a **subjective call**, not a bug.

### 4c. "PERFORMANCE REPORT" size

Static chrome text, hardcoded in each template master's text run.
Size is designer's choice (typically ~14pt uppercase tracking-wide).

Per D-E Option E-3 (approved earlier): "accept template designer
intent, no changes". We shouldn't resize it. If the user now wants
to revisit D-E, that's a scope change — flagged but not proposed here.

### 4d. Alignment claim ("both elements left-aligned at x=0.80")

Correct per designer intent. Original template paragraphs for
`PERFORMANCE REPORT` and `Prepared by …` were left-aligned on 5 of 6
themes (minimal_elegant is centred, matches theme_layout
`agency_attribution.align = "center"`). No mismatch.

### Fix shape

**Option C4-A — Add attribution overlay to DesignTab preview ⭐ RECOMMENDED**
Parallel to the existing `nameStyle` / `periodStyle` overlays, add
`attributionStyle` computed from `layout.agency_attribution`. Renders
"Prepared by {agencyName}" at the theme's attribution coords + font.
- Pros: closes preview-vs-PPTX parity gap; no backend change
- Cons: requires fetching agency name (already fetched by Design tab
  via `settingsApi.getProfile` — just need to surface it)

**Option C4-B — Bump attribution font size to 12-14pt**
Modify `theme_layout.py` font specs.
- Pros: more visible
- Cons: breaks designer hierarchy; may clash with period (14pt); needs
  your explicit call per §0 "subjective call"

**Option C4-C — Leave attribution font as-is**
Respect designer intent. Document that 9-11pt is deliberate.
- Pros: no change
- Cons: user may find it too small

**Recommendation:**
- **Always apply C4-A** (preview parity — strictly fixes the gap).
- **C4-B vs C4-C** is your call (DA3 below).

---

## 5. Architectural decisions required

Three decisions. Each has trade-offs. Pick one option per decision.

### DA1 — Alignment inheritance strategy (C1)

- **A-1:** Per-theme `client_name_align` + `report_period_align`
  fields in `theme_layout`, explicit left/center/right. Mirror
  agency_attribution.align pattern. ⭐
- **A-2:** Heuristic: derive from box geometry (wide-centred box →
  center; narrow left-offset box → left).
- **A-3:** Always LEFT (override my v1 CENTER-everywhere hardcode)
  — matches 5/6 themes by default; minimal_elegant still gets
  CENTER via an explicit override.

### DA2 — Subtitle layout strategy (C2)

- **B-1:** Add `subtitle_box` per theme; period Y becomes dynamic
  (subtitle absent → period at original y; subtitle present →
  period shifts down by subtitle.h + gap). ⭐
- **B-2:** Static 3-row composition — shrink headline.h to reserve
  permanent subtitle space. Subtitle-absent state shows an empty row.
- **B-3:** Keep current append-to-period behaviour (reject user's
  request; explain trade-offs).

### DA3 — Attribution font + preview render (C4)

- **C-1:** Preview renders attribution AND keep current 9-11pt
  font sizes (designer intent). ⭐
- **C-2:** Preview renders attribution AND bump to 12-14pt (user
  ask).
- **C-3:** Skip preview render; leave font as-is. (Keeps the parity
  gap — not recommended.)

---

## 6. Proposed fix sequencing

Assuming recommended options (A-1, B-1, C-1):

### Phase X-fix (one consolidated pass)

1. **C1 alignment** (low risk, isolated):
   - Add `client_name_align` + `report_period_align` to
     `theme_layout.py` (Python) + `theme-layout.ts` (TS mirror).
     Measure from pre-strip templates: modern_clean/dark_executive/
     colorful_agency/bold_geometric/gradient_modern = "left",
     minimal_elegant = "center".
   - Update `_draw_headline` + `_draw_period_line` to read the field
     via `_resolve_alignment` (existing helper).
   - Update DesignTab preview `nameStyle` / `periodStyle` to apply
     corresponding CSS `textAlign` + `justifyContent`.

2. **C2 subtitle slot** (medium risk — reverses v1 ADR):
   - Add `subtitle_box` + `subtitle_font` to `theme_layout.py` + TS
     mirror. Coords: subtitle.y = original_period.y, h=0.35, same x+w
     as period. Font: mid-tier sizing (e.g., 16pt vs period's 14pt).
   - New `_draw_subtitle` in `cover_customization.py`.
   - `_draw_period_line` signature gains `shift_y: float` — receives
     computed shift when subtitle is set.
   - `apply_cover_customization` drops the " — subtitle" append and
     calls `_draw_subtitle` + shifted `_draw_period_line`.
   - DesignTab preview: add `subtitleStyle` overlay, `periodStyle`
     drops subtitle text, period top-offset dynamic.

3. **C3 thumbnail cache-bust** (trivial):
   - In DesignTab.tsx, append `?v=${Date.now() or build hash}` to
     the `<img src>` in the theme picker AND the preview base image.
   - Verify via hard-refresh that gradient_modern displays correctly.

4. **C4 attribution preview** (low risk):
   - Add `attributionStyle` + `agencyName` to DesignTab overlay.
   - Render "Prepared by {agencyName}" at `layout.agency_attribution`
     coords with theme font specs.
   - No backend change.

5. **Verification**:
   - Regenerate end-to-end smoke test asserting: all 6 themes stack
     3 text lines (headline / subtitle / period) when subtitle set;
     2 lines when not; all at theme-specific alignments.
   - Colour-parity test still passes (no regression).
   - `tsc` + `lint` clean.

**Estimated effort:** ~1.5 days of code changes + verification.
Single commit or split per concern — happy to go either way.

### Dependency graph

```
C1 alignment  ──┐
                ├── C4 attribution (preview parity — reads alignment)
C3 cache-bust ──┤
                └── C2 subtitle (independent of others)
```

C2 is standalone. C1 precedes C4 (attribution preview reuses the
alignment resolver). C3 is trivial and can land first as a quick win.

---

## 7. What's NOT in scope for this round

- **Revisiting D-E** (template chrome colour protection / "PERFORMANCE
  REPORT" size/colour). User already approved E-3 = accept designer
  intent. Flagged as an explicit scope boundary.
- **Logo default-size calibration** — already adjusted in v2 (D-B
  Option B-1, client medium → 2.5×1.5).
- **Per-theme preview proportional accuracy** — CRIT-6 was skipped
  (perceptual, coord math verified).

---

## STOP

Awaiting your decision on **DA1, DA2, DA3**. Once approved:
1. I'll sequence per §6.
2. Single commit (or split per concern — your call).
3. STOP after coding for your verification pass.

If you want different options (e.g. DA2 B-3 to keep the v1 append
behaviour, or DA3 C-2 to bump attribution font), state which and I'll
adjust the implementation plan.
