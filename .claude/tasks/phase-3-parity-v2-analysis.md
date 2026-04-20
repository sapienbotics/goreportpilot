# Phase 3 — Design System Parity v2 Analysis

**Status:** analysis only — no code changes yet.
**Prepared:** 2026-04-20
**Scope:** 6 critical issues raised after the PHASE-FIX deploy verification
(10 screenshots: 6 Design-tab previews + 4 generated-PPTX covers, themes
tested: modern_clean, dark_executive, colorful_agency, bold_geometric,
minimal_elegant). Ground-truth investigation by reading current code +
inspecting the 6 stripped templates + reproducing renders locally.

---

## 0. Executive summary

Six concerns, four root causes. Good news first: **the PHASE-FIX
colour scrub, placeholder strip, and logo placement are working as
designed** — the evidence below confirms each. The failures are in
three areas the v1 analysis didn't reach:

1. **Accent-bar positioning semantic is wrong** — the bar was spec'd
   "at the bottom of the band" which puts it *inside* thick bands,
   making it invisible against similar-hue tints. Visible on
   dark_executive only by accident (thin 0.04" band).
2. **Logo-size defaults are oversized for cover context** — "medium"
   at 3.0"×2.0" dominates covers. Per-theme placeholder boxes average
   ~2.5"×1.5". The `_logo_max_box("medium")` constants are legacy
   from when logos sat in a larger body area, not the cover.
3. **minimal_elegant template's design IS its typography** — stripping
   placeholder text shapes leaves almost nothing. The thumbnail
   becomes un-recognisable in the picker. Every other theme has
   non-text chrome (bands, gradient strips, geometric blocks) and
   survives the strip.
4. **Template designer put decorative label colours that clash with user brand** —
   dark_executive's "PERFORMANCE REPORT" is hardcoded teal `#06B6D4`
   in the template master. Coincidentally close to the user's tested
   `#3ACBC1` accent so it reads as "colour bleed", but it's actually
   the template's own choice. Not our code.

Two observations don't need code changes:
- **CRIT-6 (proportional drift)** appears to be perceptual, not a
  math bug. Preview band height is computed exactly (2.2/7.5 = 29.33%)
  and reflects the template's actual band extent. Likely "looks smaller"
  because a 560-px-wide preview scales small elements down to where
  eye weight differs from a full-screen PPTX.
- **CRIT-2 (Modern Clean composition disconnect)** is a design-intent
  conversation, not a defect. It's a direct consequence of the D2-B
  decision (strip all placeholder text including "Prepared by").
  Recovery requires either adding meaningful chrome back or
  re-positioning the headline higher.

**Five architectural decisions need your approval before coding**
(§4). Details per concern in §1.

---

## 1. Per-concern ground-truth + recommended fix

### CRIT-1 — Accent bar missing in Modern Clean PPTX

**Claim:** User sees the teal header band but NO visible accent bar
under it. dark_executive does show a visible accent bar.

**Investigation result:** the accent bar IS being drawn — I reproduced
the render and inspected the resulting PPTX:

```
modern_clean cover after apply_cover_customization:
  [0] 'Shape 0'       box=(0.00, 0.00, 13.30×2.20) fill=#3AB2CB  ← band
  [3] 'Rectangle 10'  box=(0.00, 2.10, 13.30×0.10) fill=#3ACBC1  ← accent bar
```

The bar is present in the XML (`<a:srgbClr val="3ACBC1"/>`), at the
correct fill. **The problem is its position.**

Looking at `_draw_accent_bar` in `cover_customization.py:189-217`:

```python
bar_top_emu = int((band_spec["y"] + band_spec["h"]) * EMU) - bar_h_emu
```

The bar is placed at `band.y + band.h - 0.10`, i.e. the *bottom 0.10"
of the band*, **inside the band itself**.

Effective positions per theme:

| theme | band y-range | bar y-range | bar lives |
|---|---|---|---|
| modern_clean    | [0.00, 2.20] | [2.10, 2.20] | **INSIDE** band (thick band eats it) |
| dark_executive  | [2.00, 2.04] | [1.94, 2.04] | straddles — 0.06" of bar is ABOVE the band in dark body |
| gradient_modern | [0.00, 2.60] | [2.50, 2.60] | **INSIDE** band |

In `dark_executive` the "band" is a 0.04"-tall accent line. A 0.10"
bar can't fit inside, so 60% of its height sits in the dark-navy body
area with high contrast — visible. That's coincidental, not design.

For `modern_clean` and `gradient_modern`, the bar sits entirely inside
a filled teal band. With user brand `#3AB2CB` and accent `#3ACBC1`
(both cyan-teal), the bar blends into the band — invisible.

**Code:** `backend/services/cover_customization.py:196-208`.

**Recommended fix:** position the bar *at the body side of the band
boundary* — `bar_top = band.y + band.h`, so it sits just below the
band on the body. Effect per theme:

| theme | new bar y-range | contrast context |
|---|---|---|
| modern_clean    | [2.20, 2.30] | on white body — high contrast ✓ |
| dark_executive  | [2.04, 2.14] | on dark-navy body — high contrast ✓ |
| gradient_modern | [2.60, 2.70] | on body — high contrast ✓ |

The bar becomes a true "band/body boundary marker" with consistent
visibility across all themes.

**Trade-offs:** the bar now intrudes into the body text area. For
modern_clean the headline box starts at y=2.70, leaving [2.30, 2.70]
= 0.40" of gap. Acceptable. For dark_executive the headline is at
y=2.50, giving [2.14, 2.50] = 0.36" of gap. Still fine. No collision.

---

### CRIT-2 — Modern Clean composition disconnect

**Claim:** "Preview shows tinted band on top 33%, then sudden white
body with black headline floating in middle. Band + body look like
two separate unrelated elements. No visual bridge."

**Investigation result:** this is a **consequence of D2-B (strip all
placeholder text)**, not a bug.

The original `modern_clean` cover had three text elements in the
band:

```
  [1] 'Text 1'  "PERFORMANCE REPORT"           0.80, 0.55
  [2] 'Text 2'  "Prepared by {{agency_name}}"  0.80, 1.15
  [3] 'Text 3'  "{{agency_logo}}"              10.5, 0.40
```

The band was visually *loaded* with left-column info (report type +
agency attribution) and right-column logo. After strip, only
"PERFORMANCE REPORT" at y=0.55 remains. The band's bottom half
(1.00–2.20) is now empty teal. Body area below is white with the
headline floating at y=2.70.

**Code / asset:** `backend/templates/pptx/modern_clean.pptx` cover
slide (7 shapes stripped, 3 decorative shapes kept). No code bug.

**Recommended fix (design-level, user choice):** four options.

**Option F-A — bring back "Prepared by {agency_name}" inside the band**,
written by `cover_customization.py` (not a placeholder). Preserves
chrome-only invariant (we never re-introduce `{{...}}` tokens) while
restoring the band's information density.
- Pro: restores the template's intended balance.
- Con: requires extending `theme_layout` with an optional
  `agency_attribution_box` per theme, and wiring agency_name through
  `apply_cover_customization`.

**Option F-B — move the headline into the band.** Adjust
`client_name_box` coords to sit at y=1.00 (inside the band, below
"PERFORMANCE REPORT" label). Requires re-measuring per theme and
flipping headline colour to white (since it's now on coloured fill).
- Pro: eliminates the band/body disconnect entirely.
- Con: breaks the "large body headline" convention users expect.
  Changes per-theme layouts significantly.

**Option F-C — add a visual bridge element.** One of:
- A thin vertical accent rule in the left margin spanning band +
  headline area.
- A subtle background gradient from band-colour to white over y=2.0–3.0.
- A decorative mark (monogram, dot row) at y=2.30.
- Pro: purely additive, preserves existing layouts.
- Con: one more design surface to maintain per theme.

**Option F-D — accept the composition.** Document that tinted-band
themes have an open body area by design. If the user dislikes the
gap, they should pick a theme whose design-language doesn't depend
on filled bands (bold_geometric, colorful_agency).
- Pro: zero code churn.
- Con: leaves the "disconnect" perception intact.

**My recommendation: F-A.** It's the highest-leverage fix — restores
composition balance for modern_clean, dark_executive, gradient_modern,
and colorful_agency (all of which had "Prepared by" in their
original design) with one code change and a theme_layout schema
extension. minimal_elegant and bold_geometric were designed without
that slot so they'd be no-ops for the new field.

---

### CRIT-3 — "PERFORMANCE REPORT" label color bleeding in Dark Executive

**Claim:** The label renders in teal (matching user's accent), but
it's a static template chrome element that should retain its own
colour.

**Investigation result:** the label's colour is `#06B6D4` — **hardcoded
in the template master's text run XML**, not a bleed from our code.
Direct inspection of `dark_executive.pptx` cover slide1.xml:

```xml
<a:r>
  <a:rPr lang="en-US" sz="1200" b="1" spc="600" ...>
    <a:solidFill>
      <a:srgbClr val="06B6D4"/>           ← hardcoded by template designer
    </a:solidFill>
    <a:latin typeface="Calibri" .../>
  </a:rPr>
  <a:t>PERFORMANCE REPORT</a:t>
</a:r>
```

`python-pptx` shows `run.font.color.rgb = 06B6D4` for the same shape.

The colour scrub in `cover_customization.py` operates exclusively on
`<p:spPr>/<a:solidFill>/<a:srgbClr>` (shape *fill* colour) on shapes
we touch (header band, accent bar). It **never** touches text-run
colours or unrelated shapes. Verified: `_scrub_color_modifiers_on_shape`
is called only from `_recolor_header_band` and `_draw_accent_bar`,
and each passes a specific single shape reference.

**Why it looks like "bleed":** the user tested with `#3ACBC1` (accent,
cyan-green) which is perceptually close to the template's hardcoded
`#06B6D4` (cyan). Both read as "teal" so the user assumed our code
re-coloured the label.

**Code:** nothing wrong in our code. Template chrome is by-design.

**Recommended fix:** one architectural choice.

**Option P-A — accept and document.** The template designer picked
teal for the label; the user happened to pick a teal brand colour.
If they pick a non-teal brand, the label still reads teal — intended
by designer. Ship as-is.

**Option P-B — edit the template masters to neutralise chrome colour.**
Change each template's `PERFORMANCE REPORT` label to a neutral hue
(white on dark themes, slate on light themes) so it never visually
conflicts with a user's brand/accent. One-time manual PowerPoint edit
per template (same workflow as the D2-B strip).

**Option P-C — recolour the label at generate-time to contrast
with user's brand/accent.** Compute contrast ratio and flip between
light-on-dark and dark-on-light. More complex; possible overreach
(we'd be overriding the template designer's colour intent).

**My recommendation: P-B** if we want a clean relationship between
user brand colours and template chrome. Ship P-A for now if template
editing is too disruptive.

---

### CRIT-4 — Thumbnails over-stripped for minimal_elegant

**Claim:** Minimal Elegant preview is "ALMOST EMPTY white panel with
just tiny logo + small text. User can't identify the theme."

**Investigation result:** the strip left minimal_elegant with **one
single decorative shape** (a 0.01"-tall divider at y=4.00). Compare:

| theme | shapes before strip | shapes after strip | chrome preserved |
|---|---|---|---|
| modern_clean    | 10 | 3 (band, label, divider) |
| dark_executive  | 9  | 3 (thin accent line, label, footer line) |
| colorful_agency | 12 | 6 (3 colour strips, sidebar, label, footer strip) |
| bold_geometric  | 9  | 3 (right block, label, thin line) |
| gradient_modern | 13 | 7 (3 gradient strips, label, 3 footer strips) |
| **minimal_elegant** | **7** | **1 (thin divider only)** |

The strip script treated all themes uniformly — delete any text shape
with a `{{placeholder}}` token. For every other theme, non-text
decorative chrome survived. **minimal_elegant's design language was
the typography itself.** Remove the text placeholders and there's
nothing left — not a bug in the script, but the consequence of
treating typography-driven design the same as decoration-driven design.

**Code / asset:** `backend/scripts/regenerate_cover_thumbnails.py`
was theme-agnostic. The single remaining shape is from the original
template (`Shape 2` at 5.65, 4.00, 2.00×0.01).

**Recommended fix:** three options.

**Option T-A — re-author minimal_elegant's template with subtle chrome.**
Add non-text decorative elements: a thin top rule, a monogram dot,
a serif-friendly horizontal flourish. Preserves the theme's minimalist
identity but makes it recognisable in the picker.
- Pro: keeps the chrome-only cover invariant.
- Con: manual template editing + design work.

**Option T-B — generate minimal_elegant's thumbnail *with sample text*.**
Only for the thumbnail asset (not the rendered PPTX): substitute
`{{client_name}}` → "Client Name", `{{report_period}}` → "April 2026"
before exporting the PNG. The generated PPTX still goes through
chrome-only cover_customization (templates still stripped). Hybrid:
thumbnail lies a little, but becomes recognisable.
- Pro: zero template changes; users see the theme's type character.
- Con: thumbnail shows content that won't be there for a client
  named something else. Minor fidelity break.

**Option T-C — apply Option T-B to ALL themes.** Backs out of
"chrome-only thumbnails" entirely and goes with "sample-substituted
thumbnails" (v1 Option A that we rejected). Thumbnails show realistic
sample content; overlays draw actual user content on top.
- Pro: consistent visual story for picker UX.
- Con: re-introduces the overlay-stacks-on-thumbnail-text problem
  (v1's C1/C2/C3 root cause). We already paid to fix this.

**My recommendation: T-A.** Minimal design work (one template, add
a single decorative element) preserves the v1 architectural decision
and gives minimal_elegant a picker-recognisable identity. T-B is a
cheaper alternative if template editing is too much friction.

---

### CRIT-5 — Client logo too large in cover

**Claim:** Ring logo takes ~20% of slide height. User set "default"
which was mapped to "medium" (3"×2") per PHASE-FIX. Too prominent.

**Investigation result:** confirmed. `_logo_max_box` in
`report_generator.py:969-988`:

```python
else:  # kind == "client"
    box = {
        "small":   (Inches(1.5), Inches(1.0)),
        "medium":  (Inches(3.0), Inches(2.0)),   # default
        "large":   (Inches(4.5), Inches(3.0)),
        "default": (Inches(3.0), Inches(2.0)),
    }
```

- `medium` client = 3.0" × 2.0" = **26.7% of slide height**
- Per-theme `client_logo_placeholder` boxes are all smaller:

| theme | placeholder w × h |
|---|---|
| modern_clean    | 2.5" × 1.5" |
| dark_executive  | 2.5" × 1.8" |
| colorful_agency | 2.5" × 1.8" |
| bold_geometric  | 2.5" × 1.8" |
| minimal_elegant | 2.5" × 1.0" |
| gradient_modern | 2.5" × 1.5" |

Average: ~2.5" × 1.57". The "medium" max-box is 20% wider and ~27%
taller than what the templates were designed for.

**Code:** `backend/services/report_generator.py:969-988` —
`_logo_max_box`. The 3×2 constant predates the theme_layout architecture.

**Recommended fix:** three options (non-exclusive — can combine).

**Option L-A — shrink the client "medium" box** to (2.0", 1.2") or
(2.5", 1.5"). Aligns with template-designer intent. Users who want
larger can pick "large" (still 4.5"×3.0").
- Pro: fixes the perceived-oversize problem in one constant change.
- Con: existing clients with "medium" saved get a visually smaller
  logo on their next regeneration. Acceptable given the current size
  is unanimously "too big".

**Option L-B — make the "default" size *not* equal to "medium".**
Separate `default` mapping to (2.0", 1.2"). Keep "medium" at 3×2 for
users who explicitly picked Medium.
- Pro: backwards-compat for users who picked Medium deliberately.
- Con: reintroduces the "what does default mean" label confusion
  PHASE-FIX just solved. Medium in the UI still shows 3×2, and
  default-on-backend is smaller.

**Option L-C — use the theme's `client_logo_placeholder` box as the
actual default ceiling.** For "default" / "medium", cap at
`theme_layout.client_logo_placeholder.w × .h`. Logos stay within the
designer's intent per theme.
- Pro: each theme gets the size its designer sized for.
- Con: small size differences between themes may confuse users who
  expect a consistent feel.

**My recommendation: L-A + partial L-C.** Reduce `client.medium` to
(2.5", 1.5") — matches the average template intent — and clamp
"default" to the current theme's placeholder box as an upper bound.
Keeps users' Medium intent honoured while respecting per-theme design.

Same audit should apply to the agency logo path, though agency was
never flagged: agency `medium` is (2.5", 0.8") which is already at
the low end; no change needed.

---

### CRIT-6 — Preview proportions drift from PPTX

**Claim:** "Preview band appears smaller proportionally than PPTX band
(2.2" = 29% of 7.5" slide, but preview looks like ~22%)."

**Investigation result:** the math is correct.

Frontend `boxToPercentStyle` in `theme-layout.ts:144-150`:
```ts
left:   `${(box.x / slideW) * 100}%`
top:    `${(box.y / slideH) * 100}%`
width:  `${(box.w / slideW) * 100}%`
height: `${(box.h / slideH) * 100}%`
```

For `modern_clean` band (x=0, y=0, w=13.3, h=2.2) with slide
(13.333 × 7.5): left=0%, top=0%, **width=99.75%**, **height=29.33%**.

Template actual band dimensions from python-pptx:
```
Shape 0: (0.000, 0.000, 13.300 × 2.200)
```

So the preview's 29.33% height correctly reflects the actual band
height. **No coordinate drift.**

**Three possible contributors to the perception:**

1. **Container border + rounded corners.** The preview container uses
   `border border-slate-200 rounded-lg overflow-hidden`. At 560px
   container width × ~315px height (16:9), the 1px border consumes
   ~0.3% visually on each side. Rounded corners (0.5rem = 8px) can
   clip the top edge of the band by a pixel or two, making it look
   slightly shorter.

2. **Scale-induced Gestalt perception.** A band that fills 29% of a
   315-px-tall preview is ~92px. A band that fills 29% of a 600-px-tall
   PPTX slide viewer is ~174px. Same proportion, different weight.
   Users commonly perceive elements in smaller views as "thinner".

3. **The 0.25% narrower-than-slide band** (13.3" vs 13.333" slide)
   shows as 99.75% width — a 0.033" unfilled strip on the right. At
   560px that's ~1.4px. Negligible but combined with the border can
   visually "shrink" the band.

**Code:** `frontend/src/lib/theme-layout.ts:144-150` (boxToPercentStyle)
and `DesignTab.tsx:482` (preview container).

**Recommended fix:** none required, but two low-risk polish items
if we want to close the concern:

**Option V-A — remove the container border.** Keeps the `rounded-lg`
and `shadow-sm` for cadre, but drops the visual frame that steals a
pixel from each edge.
- Pro: slight visual clarity improvement.
- Con: may look floaty against the white page background.

**Option V-B — update `theme_layout.modern_clean.header_band.w`
from 13.3 → 13.333.** Matches slide width exactly; preview band
spans the full 100%. Also update the PPTX so the band shape in the
template is extended to slide width. Minor template edit.
- Pro: exact-width band removes the 0.25% gap.
- Con: very small visual impact. Not worth the template edit unless
  combined with CRIT-4 template work.

**My recommendation: neither — document as perceptual.** The coord
math is provably correct. If you want to eliminate the perceptual
concern, Option V-A is the lightest touch.

---

## 2. Cross-cutting observations (your OBS-* list verified)

| OBS | Verified | Notes |
|---|---|---|
| OBS-1: Brand colour byte-accuracy | ✅ | `verify_cover_color_parity.py` passes 12/12 |
| OBS-2: No `{{placeholder}}` tokens visible | ✅ | Cover chrome-only across all 6 themes |
| OBS-3: Period + subtitle append works | ✅ | Confirmed in end-to-end render |
| OBS-4: Logo positioning respects template | ✅ | theme_layout fallback kicks in correctly |
| OBS-5: Honest hint for brand_tint_strategy='none' | ✅ | Preview shows it |
| OBS-6: Dark Executive looks best — accent bar visible there | Diagnosed in CRIT-1 (coincidental — thin band pushed bar into body area) |

---

## 3. Root-cause clusters

| Cluster | Concerns affected | Fix unlocks |
|---|---|---|
| Accent bar position semantic | CRIT-1 | 1 |
| Template chrome colour authored by designer | CRIT-3 | 1 (if acted on) |
| minimal_elegant design = typography | CRIT-4 | 1 |
| Logo sizing calibrated for body, not cover | CRIT-5 | 1 |
| Composition gap from placeholder strip | CRIT-2 | 1 (and arguably improves CRIT-1 too, since a denser band makes the accent bar less lonely) |
| Perceptual (no defect) | CRIT-6 | 0 |

**Highest-leverage fix: CRIT-2 Option F-A.** Restores composition
balance and gives the accent bar meaningful proximity to surrounding
content. Unblocks both CRIT-1 symptoms and CRIT-2.

---

## 4. Architectural decisions required

### D-A. Accent bar visibility strategy

**Context:** current impl puts the bar *inside* the bottom of the
band. For thick bands this camouflages it against similar-colour
tints.

- **Option A-1 — Reposition to band/body boundary (on body side).**
  `bar_top = band.y + band.h`. Consistent visibility across all
  brand-tinted themes. Single-line code change. **Recommended.**
- **Option A-2 — Keep current position but widen contrast
  requirement.** Require user's accent to differ from brand by a
  minimum contrast ratio; fall back to a derived high-contrast accent
  (e.g., complementary hue) if they pick too-similar colours. More
  complex; probably annoying to users who want harmony palettes.
- **Option A-3 — Drop the accent bar concept for thick-band themes**
  (modern_clean, gradient_modern). Only render it where the band is
  thin (dark_executive). Inconsistent feature set; bad UX.

### D-B. Default logo size

**Context:** client "medium" at 3"×2" dominates covers. Template
placeholder avg = 2.5"×1.5".

- **Option B-1 — Shrink client "medium" to 2.5"×1.5".** Matches
  template intent. Users who want bigger pick "large". **Recommended.**
- **Option B-2 — Shrink client "default" to 2.0"×1.2"**, leave
  "medium" at 3×2. Re-separates default from medium (reverses
  PHASE-FIX label clean-up).
- **Option B-3 — Per-theme logo sizing (theme_layout carries the
  size)**. Each theme declares its ideal cover-logo box. Different
  themes get slightly different "medium" sizes. More code, but
  highest fidelity to designer intent.

### D-C. minimal_elegant thumbnail recovery

**Context:** stripped template has only a 0.01" divider left.
Unrecognisable in picker.

- **Option C-1 — Add subtle non-text chrome to minimal_elegant master.**
  A thin top rule, a monogram dot, a horizontal flourish. One-time
  manual template edit. **Recommended.**
- **Option C-2 — Sample-substituted thumbnail for minimal_elegant only.**
  Generate its PNG with fake text baked in; keep the PPTX chrome-only.
  Hybrid; thumbnail lies a little.
- **Option C-3 — Sample-substituted thumbnails for ALL themes.**
  Backs out of chrome-only for thumbnails entirely; reintroduces the
  overlay-stacking problem PHASE-FIX solved.

### D-D. Modern Clean (and other tint-band themes) composition

**Context:** band is now empty except for "PERFORMANCE REPORT".
Body starts stark white with headline floating. Gap feels disconnected.

- **Option D-1 — Restore "Prepared by {agency_name}" in the band,
  written by `cover_customization.py` (no placeholder).** Extend
  `theme_layout` with optional `agency_attribution_box` per theme.
  Four themes had this slot originally; re-enabling closes the gap
  for those four and no-ops for the other two. **Recommended.**
- **Option D-2 — Move headline into the band.** Re-measure coords,
  flip colour per theme. Large theme_layout churn.
- **Option D-3 — Add a visual bridge element** (accent rule, gradient,
  monogram). Additive but one more surface to maintain.
- **Option D-4 — Accept and document.** Zero code churn.

### D-E. Template chrome colour protection (static labels)

**Context:** template designer hardcoded `PERFORMANCE REPORT` in
teal on dark_executive. Reads as "colour bleed" when user's brand is
also teal.

- **Option E-1 — Edit template masters** to neutralise chrome label
  colour per theme (white on dark, slate on light). Same workflow as
  D2-B strip. Once-off work.
- **Option E-2 — Recolour chrome labels at generate-time based on
  contrast with user's brand.** Code override of designer colour.
  Adds complexity; arguably overreaches.
- **Option E-3 — Accept as template-authored intent.** Document and
  move on. **Recommended if template editing is too much churn.**

---

## 5. Proposed fix sequencing

Ordered by dependency, risk, and leverage:

### Phase A-fix2 — Fast wins (0.5 day)
1. **D-A Option A-1** — reposition accent bar to `band.y + band.h`.
   Single-line code change in `_draw_accent_bar`. Immediately
   resolves CRIT-1 across all 3 brand-tinted themes. No template edits.
2. **D-B Option B-1** — shrink client `medium` max-box to (2.5", 1.5").
   Single-constant change in `_logo_max_box`. Resolves CRIT-5.

### Phase B-fix2 — Architecture extension (1 day)
3. **D-D Option D-1** — add `agency_attribution_box` per theme to
   `theme_layout.py` (+ TS mirror). Wire agency_name into
   `apply_cover_customization`. Add a 4th textbox draw step after
   headline/period. Resolves CRIT-2; improves visual density for the
   4 themes that had "Prepared by" slots originally.

### Phase C-fix2 — Design asset work (0.5–1 day, optional)
4. **D-C Option C-1** — add subtle decorative chrome to
   `minimal_elegant.pptx`. One-time template edit.
5. **D-E Option E-1** — neutralise PERFORMANCE REPORT colour in
   each template where the designer picked a brand-colour-adjacent
   hue (dark_executive's `#06B6D4`; others TBD after audit). One-time
   template edits.
6. Re-run `regenerate_cover_thumbnails.py` to pick up new chrome.

### Phase D-fix2 — CRIT-6 polish (0.25 day, optional)
7. **V-A** — remove the preview container border to eliminate
   pixel-level clipping. Only if the user still reports the
   proportion perception after Phase A-fix2 + B-fix2 are deployed.

**Independent:** CRIT-1 (Phase A), CRIT-5 (Phase A), CRIT-6 (Phase D)
can each ship alone. CRIT-2 (Phase B) is independent but benefits
from CRIT-1 shipping first (so accent bar is visible by the time the
composition is re-densified). CRIT-3 and CRIT-4 (Phase C) are asset
work — can be done in either order or skipped entirely.

**Total effort: 1.5–2.5 days** depending on which optional items
land.

---

## 6. What this analysis does NOT propose

- **Content-slide design changes.** The cover is the only surface
  touched by Option F v1 + PHASE-FIX. Slides 2-19 retain the
  template designer's original styling per the §11 Option A agreement.
- **Per-slide colour customisation** beyond the cover band + accent.
- **Hero image theme** — still dropped per DESIGN-SYSTEM-PLAN.md.
- **Pixel-exact preview-to-PPTX render matching.** Font metrics
  differ; D3 Option B ("meaningful representation") stands.
- **Revisiting the chrome-only strip strategy.** D2-B is correct;
  the per-theme compensation is where the work goes.

---

## STOP

Awaiting your decisions on D-A through D-E. Once approved:
1. I'll sequence Phase A-fix2 / B-fix2 / C-fix2 / D-fix2 per §5.
2. Each phase lands as a discrete reviewable commit.
3. No speculative code changes — only what's in the approved plan.

If you'd prefer a subset (e.g., only D-A and D-B for a quick fix,
deferring D-C/D/E), say which and I'll adjust.
