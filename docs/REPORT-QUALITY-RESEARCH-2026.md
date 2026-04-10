# Report Quality Research — April 2026

**Scope:** What makes a marketing-agency client report look like a $500/month tool. Visual quality, layout, typography, chart design, content structure — not features.

**Method:** Four parallel research phases plus a gap analysis against GoReportPilot's current PPTX/chart output.

**Thesis:** A premium-quality report is not about more features. It's about a handful of non-negotiable conventions the $20/month tools all skip — action-titled charts, direct-labeled plots with muted gridlines, KPI cards pairing color with glyphs and a neutral band, Okabe-Ito or Slate-only palettes with WCAG-AA contrast, Inter/Arial typography with disciplined hierarchy, and SCQA-structured narrative. Every one of them is implementable in python-pptx in a week.

---

## 1. Competitor Report Visual Analysis

*Evidence limit: most competitor template galleries render preview images client-side, so pixel-precise hex codes and font sizes could not be extracted from public pages. Claims below come from documented customization surfaces, reviewer language, or official design-philosophy statements. Where evidence was thin, it's flagged.*

**AgencyAnalytics** — corporate-minimal. Deliberately neutral canvas so the agency's brand can take over. Users configure 4 color slots via picker or hex ([Customize dashboard colors](https://help.agencyanalytics.com/en/articles/1915534-customize-dashboard-colors)). Widgets are conservative: "basic scorecards, charts, and tables" with no advanced visualizations ([Whatagraph critique](https://whatagraph.com/blog/articles/agencyanalytics-dashboard)). Cover is the "first handshake with the reader" ([Custom logo](https://agencyanalytics.com/feature/custom-logo)). Structure: cover → executive summary → KPI scorecards → channel deep-dive ([SEO report guide](https://agencyanalytics.com/blog/how-to-make-an-seo-report-for-clients)).

**DashThis** — modern-approachable. Only competitor whose marketing-chrome hex codes were extractable: background `#e6eeef`, text `#2c3f49`, CTA `#ea474b` ([DashThis examples](https://dashthis.com/dashboard-examples/)). Ships 12 preset themes; custom hex on 10+ dashboard plan. Dashboard-first (single-scroll, not slide-first). Marketing fonts `f37light`/`f37bold` with Tahoma fallback, 11px–150px range. Reviewers describe 12 presets as "somewhat restrictive" ([review](https://whatagraph.com/reviews/dashthis)).

**Whatagraph** — modern-visual. Positions itself on design. AI brandbook extraction: upload a brandbook or client-site screenshot, Whatagraph auto-extracts fonts and colors ([white label](https://whatagraph.com/white-label)). Richer widget library than AgencyAnalytics — "trend charts, KPI comparison tables, line graphs, bar charts" plus infographic elements ([templates](https://whatagraph.com/templates/white-label-marketing-report-template)).

**Swydo** — workmanlike, least differentiated. No documented default palette. Resizable widget grid ([crafting reports](https://help.swydo.com/en/articles/10037886-crafting-your-reports)). Low-confidence section.

**NinjaCat** — most slide-deck-native competitor, and the most directly relevant reference. Shinobi template editor is "page-layout style similar to PowerPoint" ([Shinobi editor](https://support.ninjacat.io/hc/en-us/articles/115009839887-How-to-use-the-Shinobi-BETA-template-editor)). Widget library explicit: "tables, scorecards, bar graphs, line/spline, area, pie" ([data widget](https://support.ninjacat.io/hc/en-us/articles/115009837607-Constructing-a-Data-Widget-How-to-add-data-to-your-Shinobi-template)). Marketing site loads Lato, Open Sans, Montserrat, Inter. **Documented scorecard norm: four KPIs per slide** ("budget spent, total leads, cost per lead, conversion rate") ([client reporting examples](https://www.ninjacat.io/blog/client-reporting-examples)).

**TapClicks** — enterprise-maximalist. Only competitor explicitly marketing "pixel-perfect, completely editable" PowerPoint export ([Report Studio](https://www.tapclicks.com/tapclicks-report-studio)). Agencies upload their own templates; TapClicks populates them. No distinctive "TapClicks look" — it's a skinning engine. Confirms that BYO-template is enterprise table-stakes, not a visual differentiator.

**Databox** — colorful-analytics (the outlier). Ships 18 pre-defined background colors with curated chart themes per background ([Designer](https://help.databox.com/overview-designer)). Dark theme toggle ([dark theme](https://help.databox.com/how-to-enable-the-dark-theme-in-databox)). Dashboard-native with modular datablock grid. Scorecard + sparkline is the canonical datablock pattern ([datablock editor](https://help.databox.com/overview-datablock-editor)).

**Rollstack** — no visual style of its own. Data-pipe into BYO PowerPoint/Slides. $750+/mo. Proves enterprise will pay for automation-only when they already have a design system.

**Category-wide patterns:**
- Neutral-light canvas (white/slate-50) dominant; Databox is the outlier.
- Executive-summary-first structure is universal.
- KPI scorecard: **4 cards per row** (NinjaCat-documented norm), metric + big value + MoM delta + color-coded trend.
- Chart vocabulary is deliberately conservative: line, bar, pie, scorecard, table. No treemaps, sankeys, waterfalls anywhere.
- White-label is table stakes — everyone ships per-client logo + color overrides.
- Typography universally sans-serif: Lato / Open Sans / Montserrat / Inter / system sans. Two-level hierarchy.
- Slide count clusters 8–12. **GoReportPilot's 8-slide default is squarely in category norms.**
- Aesthetic buckets: corporate-minimal (AgencyAnalytics, NinjaCat, Swydo), modern-approachable (DashThis, Whatagraph), colorful-analytics (Databox). **Modern-approachable is the most defensible position for a new entrant** — only DashThis and Whatagraph occupy it, neither a design leader.

---

## 2. Professional Design Standards

**Typography.** Consulting firms standardize on neutral sans-serifs — McKinsey uses Arial + Georgia; BCG/Bain use Helvetica or Calibri. "Helvetica is the gold standard — it does not distract from content" ([Slidor](https://www.slidor.agency/blog/best-fonts-powerpoint-presentations-designers-guide)). **Inter** is the modern equivalent, "designed for digital, tall x-height, clear on monitors" ([UX Heart](https://uxheart.com/why-i-love-using-the-inter-font/)). Max 2 families per deck; no italics for emphasis.

**Recommended sizing for on-screen / PDF reading (16:9 deck):**

| Element | Size | Weight |
|---|---|---|
| Slide titles (action titles) | **24–28pt** | Bold |
| Section headers | 16–18pt | Medium |
| Body text | 12–14pt | Regular |
| KPI big numbers | **32–48pt** | Bold |
| KPI labels | 10–12pt | Regular |
| Chart axis labels | 9–10pt | Regular |
| Chart data labels | 9–11pt | Regular |
| Footer | 8–10pt | Regular |
| **Absolute minimum** | **9pt** | — |

Sources: [BrightCarbon font size](https://www.brightcarbon.com/blog/presentation-font-size/); [AIPPT typography](https://learn.aippt.com/best-practices-for-powerpoint-typography-and-text-readability/); [Slidor minimum](https://www.slidor.agency/blog/quelle-taille-de-police-minimum-pour-powerpoint).

**Line spacing:** 1.35 titles, 1.45 body, 1.2 KPI values. WCAG AAA requires ≥1.5 within paragraphs ([W3C WAI](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)). Paragraph space-after: 6–8pt.

**Color — max 4–6 per slide.** McKinsey decks use "black, white, and one accent color, typically blue" ([SlideModel](https://slidemodel.com/mckinsey-presentation-structure/); [Slideworks](https://slideworks.io/resources/how-mckinsey-consultants-make-presentations)). Knaflic: "use color sparingly and with purpose" ([Storytelling with Data](https://medium.com/analytics-vidhya/key-points-from-the-book-storytelling-with-data-by-cole-nussbaumer-knaflic-8c0a7b08960)).

**Color-blind-safe categorical palette: Okabe-Ito** — "gold standard, recommended by Nature Methods" ([Conceptviz](https://conceptviz.app/blog/okabe-ito-palette-hex-codes-complete-reference); [easystats](https://easystats.github.io/see/reference/okabeito_colors.html)):

| Color | Hex |
|---|---|
| Blue | `#0072B2` |
| Vermillion | `#D55E00` |
| Bluish Green | `#009E73` |
| Reddish Purple | `#CC79A7` |
| Orange | `#E69F00` |
| Sky Blue | `#56B4E9` |

**WCAG 2.1 AA contrast** ([W3C](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html); [WebAIM](https://webaim.org/articles/contrast/)): 4.5:1 normal text (<18pt), 3:1 large text, 7:1 AAA normal.

| Color on white | Ratio | Grade |
|---|---|---|
| Slate-900 `#0F172A` | 17:1 | AAA |
| Slate-500 `#64748B` | 4.6:1 | AA |
| Indigo-700 `#4338CA` | 8.6:1 | AAA |
| **Emerald `#059669`** | **3.8:1** | **FAILS AA** |
| Emerald-700 `#047857` | 5.1:1 | AA |
| Rose `#E11D48` | 4.8:1 | AA |
| Amber `#D97706` | 3.1:1 | Large only |

**Critical finding:** our current emerald fails AA for small trend labels — use `#047857` for body sizes, or always pair with a glyph.

**Pair color with shape cues.** ~8% of men have red/green color blindness. Never rely on color alone — "pair color with a secondary cue like arrow symbols ensures the signal survives" ([phData](https://www.phdata.io/blog/adding-up-and-down-arrows-in-power-bi/)).

**Charts — type selection:**

| Use | Chart |
|---|---|
| Ranking, magnitude, category comparison | **Horizontal bar** (the default workhorse; bars "lie at the top of visual perception" per [Knaflic](https://medium.com/analytics-vidhya/key-points-from-the-book-storytelling-with-data-by-cole-nussbaumer-knaflic-8c0a7b08960)) |
| Time series ≥5 points | Line |
| 2-point period comparison | Slopegraph (Tufte) |
| Part-to-whole, 2–4 categories | Donut (hole shows total) |
| Part-to-whole across categories | Stacked bar, ≤5 segments |
| **Avoid** | Area, 3D, radar, pies >4 slices, bubble |

**Chart titles MUST be action-titled.** "Sessions grew 23% after the Sept launch" not "Sessions over time." This is the McKinsey action-title principle — if the reader looked only at chart titles, the story would hold together ([SlideModel](https://slidemodel.com/mckinsey-presentation-structure/)). Top, left-aligned, 14–16pt bold.

**Legend placement:** prefer **direct labeling** for ≤4 series ([Data Europa](https://data.europa.eu/apps/data-visualisation-guide/axes-grids-and-legends)). When unavoidable, place top (below title) or right of plot — never bottom-center.

**Gridlines:** horizontal only, Slate-200 `#E2E8F0`, 0.5pt, alpha 0.5. Tufte: "maximize data-ink ratio; erase non-data-ink" ([Infovis Wiki](https://infovis-wiki.net/wiki/Data-Ink_Ratio)).

**Highlight strategy:** gray out non-focus bars in Slate-300; paint the winner in brand color.

**Layout.** 16:9 = **13.333" × 7.5"**. **0.5" perimeter margin.** Zone structure:

| Zone | y range | Height |
|---|---|---|
| Title | 0.4" → 1.1" | 0.7" |
| Subtitle (optional) | 1.1" → 1.4" | 0.3" |
| Body | 1.4" → 6.9" | 5.5" |
| Footer | 6.9" → 7.4" | 0.5" |

Implicit 12-column grid. 4 KPI cards at ~3" each, or 3 cards at ~4". Left-align everything; center only for title slides and KPI big numbers within their card. Snap coordinates to 0.1" increments.

**Spacing.** Between unrelated elements ≥0.25" (18pt); between related ones 0.08–0.12". Inter-paragraph 6–8pt after. Minimum gap between distinct elements 0.2". KPI card padding 0.2" all sides; 0.25" gap between cards.

**Animations.** **None.** McKinsey: "Refrain from fancy graphics and animations" ([SlideModel](https://slidemodel.com/mckinsey-presentation-structure/)). GoReportPilot outputs are async (PDF, email) — animations add zero value and signal amateurism.

**Number formatting:**

| Type | Format |
|---|---|
| Large integers | 0 decimals: `1,234,567` |
| Currency ≥$100 | 0 decimals: `$12,345` |
| Currency <$100 | 2 decimals: `$47.25` |
| Percentages | **1 decimal**: `23.4%` |
| Rates (CTR, CPC) | 2 decimals: `2.34%`, `$1.47` |
| Ratios (ROAS) | 1 decimal with ×: `3.2×` |
| Deltas | Signed + arrow: `↑ +23.4%` |

**K/M/B abbreviation for KPI card big numbers only** (not tables): `12.4K`, `2.3M`, `1.2B`. Sources: [Tableau](https://help.tableau.com/current/pro/desktop/en-us/formatting_specific_numbers.htm); [Microsoft globalization](https://learn.microsoft.com/en-us/globalization/locale/number-formatting).

**Trend indicators.** Direction = color + glyph. Filled triangles render reliably in Inter/Arial at 10pt:

| Direction | Glyph | Color |
|---|---|---|
| Up (good) | `▲` U+25B2 | `#047857` emerald-700 |
| Down (bad) | `▼` U+25BC | `#E11D48` rose |
| Flat | `▬` em dash | `#64748B` slate-500 |

**Neutral band:** changes where `abs(val) < 1%` render gray — a +0.3% "trend" is dishonest.

**Inverse metrics:** CPC, CPA, cost-per-result, bounce rate, frequency — **invert** so down = green. Critical when cost metrics sit next to volume metrics on the same scorecard.

**Sparklines.** Tufte: "small, high-resolution graphics embedded in words" ([Edward Tufte](https://www.edwardtufte.com/notebook/sparkline-theory-and-practice-edward-tufte/)). 12-period sparkline per KPI card, ~2" × 0.3", no axes/grid, single 1.2pt line in semantic color, dot at last point. **Single biggest perceived-quality upgrade in this research set.**

**Footers.** Left: client name + period. Right: page number `N / Total`. Center (optional): `Confidential`. 8–10pt Slate-500, never bold. 0.5pt horizontal rule in Slate-200 above. **Fixed dates, never AUTO** — "for client deliverables referencing data 'as of March 2026,' use Fixed" ([Microsoft](https://support.microsoft.com/en-us/office/insert-or-change-the-slide-numbers-date-or-footer-for-on-screen-slides-in-powerpoint-8bad6395-a1f4-4af6-a360-0df412e510bf)). No footer on the title slide.

---

## 3. Marketing Report Content Best Practices

**Standard sections** (universal across [DashThis](https://dashthis.com/blog/what-to-include-in-your-monthly-marketing-report/), [AgencyAnalytics](https://agencyanalytics.com/blog/digital-marketing-report), [Swydo](https://www.swydo.com/blog/client-reporting-best-practices/)):
1. Cover with client logo + period + agency branding
2. Executive summary — ~150 words, "digestible in under 2 minutes" ([Hashmeta](https://hashmeta.com/blog/what-a-high-quality-seo-monthly-report-should-actually-include/))
3. Goals + KPI scorecard vs targets
4. Traffic / GA4 (placed first — represents aggregate impact)
5. Channel breakdowns (SEO, Google Ads, Meta Ads)
6. Wins / what's working
7. Concerns / what needs improvement
8. Recommendations / next steps
9. Optional appendix

**Curate, don't dump:** "Just because a tool gives you 30 charts doesn't mean you must include them all — filter to 5–10 KPIs that reflect performance in the context of the client's goals" ([DashThis](https://dashthis.com/blog/what-to-include-in-your-monthly-marketing-report/)).

**Narrative framework: SCQA** (McKinsey/Bain/BCG via Minto's Pyramid Principle — [SlideModel](https://slidemodel.com/scqa-framework-guide/); [ManagementConsulted](https://managementconsulted.com/scqa-framework/); [Analyst Academy](https://www.theanalystacademy.com/powerpoint-storytelling/)):

- **Situation:** "Your Q1 goal is 15K organic sessions/mo at 3% conversion."
- **Complication:** "March hit 12,200 (−6% MoM) because the Google core update reshuffled rankings for 3 top-5 pages."
- **Question:** "How do we recover and still hit 15K by June?"
- **Answer:** "Three actions: refresh pages, redirect internal links, publish cluster posts."

**KPI selection (3–5 per channel, 6–10 total dashboard):**

- **GA4:** sessions, users, engagement rate, avg engagement time, conversions ("key events"), conversion rate, traffic sources, top pages ([DashThis GA4](https://dashthis.com/blog/ga4-metrics/)).
- **SEO:** organic sessions MoM+YoY, keyword rankings with movement, Search Console impressions/clicks/CTR, organic conversions, backlinks, technical health ([SEO Sherpa](https://seosherpa.com/seo-client-report/); [Nightwatch](https://nightwatch.io/blog/monthly-seo-report-template/)).
- **Google Ads:** **ROAS (hero)**, spend vs budget, CPA, conversions, CTR, CPC, Quality Score ([AgencyAnalytics](https://agencyanalytics.com/blog/google-ads-client-report)).
- **Meta Ads:** reach, impressions, **frequency** (ideal 1–3), CPM, CTR, CPC, conversions, cost per result, ROAS ([AgencyAnalytics](https://agencyanalytics.com/blog/facebook-ads-metrics); [Search Engine Land](https://searchengineland.com/meta-ads-advanced-kpis-track-success-446811)).

**Wins vs concerns framing.** Wins = **business outcomes, not activities**: "184 new qualified leads, up 23% MoM — on track for Q2 target of 600" beats "published 4 blog posts" ([AppsFlyer](https://www.appsflyer.com/blog/tips-strategy/reporting-marketing-results/)). Concerns = **observation + cause hypothesis + planned action**. Never hide, never sugarcoat. "Don't hide bad results. Educate and explain; clients will understand you better" ([DashThis](https://dashthis.com/blog/marketing-results-how-to-communicate-them/)).

**Recommendations — 6 rules** ([BCCampus](https://pressbooks.bccampus.ca/businesswritingessentials2/chapter/12-5-recommendation-reports/); [Nutshell](https://www.nutshell.com/blog/marketing-report-guide); [Funnel.io](https://funnel.io/blog/digital-marketing-reporting-guide)):
1. **2–3 max.** "Two or three are probably plenty."
2. **Future-tense commitments:** "Next month we will…" not "You should consider…"
3. **Traceable to a data point** shown earlier.
4. **Names expected outcome:** "target frequency <3.0 and CPA back to ~$45."
5. **Tied to channel and budget impact.**
6. **No generic advice** — specific enough to copy into a PM tool.

**Period comparison: show MoM + YoY + % of goal**, not just MoM. MoM for feedback loop, YoY for seasonality, vs-goal for agency-value framing ([AgencyAnalytics goal-based reporting](https://agencyanalytics.com/blog/goal-based-reporting); [ContentPowered](https://www.contentpowered.com/blog/mtd-qtd-ytd-mom-yoy/)).

**Bad-month four-beat sequence** ([Planful](https://reactgatsby.planful.com/wp-content/uploads/2023/03/eBook_-Results.pdf); [SMA Marketing](https://www.smamarketing.net/blog/revive-an-underperforming-marketing-campaign)):
1. Lead with the honest number — "Sessions fell 14% MoM."
2. Context — YoY, seasonality, known external events.
3. Cause — specific hypothesis, not "underperformance."
4. What changes next month.

**Plain-language rules** ([WordRake](https://www.wordrake.com/resources/writing-easy-to-read-marketing-reports); [Digital.gov](https://digital.gov/guides/plain-language/principles/avoid-jargon)): define acronyms on first use; replace jargon with outcomes; sentences <20 words; banned words — "synergy," "leverage," "circle back," "low-hanging fruit," "deep dive," "move the needle" ([Readable](https://readable.com/blog/2022-jargon-to-avoid/)).

---

## 4. python-pptx Capabilities & Limitations

**Native API strengths** ([python-pptx docs](https://python-pptx.readthedocs.io/en/latest/)):
- **Shapes:** `add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, ...)`; adjust corner radius via `shape.adjustments[0]`; solid fill, line color/width/dash.
- **Text:** full run-level control — family, size, bold/italic/underline, RGB color, line spacing (`paragraph.line_spacing = 1.45`), `space_before`/`space_after`, alignment. Auto-fit via `MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE` or `text_frame.fit_text(font_file=...)` — **always pass an explicit font path in Docker** ([fit-text analysis](https://python-pptx.readthedocs.io/en/latest/dev/analysis/txt-fit-text.html)).
- **Charts (native OOXML):** series color/line, gridline visibility + color, axis scale + tick label format, data labels with Excel number formats, legend position, chart title ([charts guide](https://python-pptx.readthedocs.io/en/latest/user/charts.html)).
- **Tables:** cell fill, text, margins, vertical anchor, cell merging.
- **Images:** PNG/JPEG/EMF insertion, cropping, rotation, PNG alpha preserved.
- **Layout:** EMU units (914,400/inch); use `Inches()` and `Pt()`, never raw EMU. Widescreen: `prs.slide_width = Inches(13.333)`.
- **Placeholders:** three-level inheritance (master → layout → slide). Iterate runs to replace tokens while preserving character formatting — **never overwrite `shape.text` wholesale**.

**Limitations requiring XML hacks:**
- **Drop shadows** ([#130](https://github.com/scanny/python-pptx/issues/130), [#705](https://github.com/scanny/python-pptx/issues/705)) — only `inherit=False` works natively. For real shadows, write `<a:effectLst><a:outerShdw>` via lxml:

```python
from pptx.oxml.ns import qn
from lxml import etree
def add_outer_shadow(shape, blur_pt=8, dist_pt=3, alpha=40):
    spPr = shape._element.spPr
    effectLst = etree.SubElement(spPr, qn('a:effectLst'))
    outerShdw = etree.SubElement(effectLst, qn('a:outerShdw'),
        {'blurRad': str(int(blur_pt*12700)), 'dist': str(int(dist_pt*12700)),
         'dir': '2700000', 'algn': 'tl', 'rotWithShape': '0'})
    srgb = etree.SubElement(outerShdw, qn('a:srgbClr'), {'val': '000000'})
    etree.SubElement(srgb, qn('a:alpha'), {'val': str(alpha*1000)})
```

- **Gradient fills** — only 2-stop linear at fixed angle ([gradient analysis](https://python-pptx.readthedocs.io/en/latest/dev/analysis/dml-gradient.html)). Any other angle/stops/radial = XML.
- **Table cell borders** ([#71](https://github.com/scanny/python-pptx/issues/71), [#573](https://github.com/scanny/python-pptx/issues/573)) — write `<a:lnL/R/T/B>` under `<a:tcPr>`.
- **Text shadow/outline, letter-spacing, glow, reflection, soft edges, 3D bevels** — XML only.
- **Bullet lists from a blank text box** ([#100](https://github.com/scanny/python-pptx/issues/100)) — set up bulleted placeholder styles in the template master; set `paragraph.level` programmatically. GoReportPilot already does this correctly.
- **Slide duplication** ([#132](https://github.com/scanny/python-pptx/issues/132)) — no native support; `deepcopy` workarounds are fragile, often break charts. **Rule: never duplicate slides at runtime** except the existing CSV path. Template contains one variant per layout; everything else built from layouts.
- **Theme color programmatic editing** — no API. Ship template with correct `<a:clrScheme>`.
- **Hyperlink color override** ([#940](https://github.com/scanny/python-pptx/issues/940)) — setting `run.font.color.rgb` after a hyperlink is overridden by theme hyperlink color.

**Keep matplotlib PNG embedding for charts** — not native OOXML. Matplotlib gives full styling control, renders identically everywhere, and avoids the "last 15% needs XML" problem. This is the right call and Phase 4 confirms it.

---

## 5. Gap Analysis — GoReportPilot vs Best Practices

*Baseline reviewed: `backend/services/report_generator.py` (2,067 lines), `backend/services/chart_generator.py`, `backend/services/slide_selector.py`, the 6 `.pptx` templates in `backend/templates/pptx/`.*

### What's already right — keep as-is

- Template-first architecture with `{{token}}` replacement — same pattern as TapClicks, NinjaCat, Rollstack.
- 19-slide adaptive pool (`slide_selector.py`) — more sophisticated than AgencyAnalytics' rigid layouts.
- Six templates (`modern_clean`, `dark_executive`, `colorful_agency`, `bold_geometric`, `minimal_elegant`, `gradient_modern`) — more variety than DashThis's 12 preset themes.
- Multi-paragraph AI narrative across 6 sections — unmatched at $20–$70/mo.
- Dynamic currency symbols (₹, $, €, £) via `_currency_symbol()`.
- Three chart themes (light / dark / colorful) in `chart_generator.py` with proper spine/grid/text colors.
- Run-level placeholder replacement in `_replace_placeholders_in_slide()` preserves formatting.
- Smart KPI selection via `select_kpis`.
- Matplotlib PNG chart embedding — correct choice per Phase 4.

### Tier 1 — Quick wins (1–2 prompts each, high impact)

1. **Fix emerald contrast.** `_EMERALD` → `RGBColor(0x04, 0x78, 0x57)` (emerald-700, 5.1:1 AA). Same for `_RL_EMERALD` → `#047857`. Current `#059669` fails WCAG AA on small trend labels.
2. **Filled arrow glyphs in KPI changes.** Prepend `▲ ` / `▼ ` / `▬ ` in `_fmt_change()`. Color-only violates color-blind rule.
3. **±1% neutral band.** In `_fmt_change()`, `abs(val) < 1.0` → neutral arrow in Slate-500. A +0.3% "trend" is dishonest.
4. **K/M/B compact formatter.** New `_fmt_compact()` for KPI card big numbers only. `1,234,567` → `1.2M`.
5. **Invert cost-metric color logic.** Add `direction` field in `select_kpis()` (`"negative"` for CPC, CPA, bounce rate, frequency); flip sign in `_colorize_kpi_changes()`.
6. **Explicit line spacing.** Add `p.line_spacing = 1.45` (body), `1.35` (titles), `1.2` (KPI values) in `_populate_text_frame_formatted()`.
7. **Okabe-Ito multi-series palette.** Update `_setup_chart_style()` to cycle `#0072B2 → #D55E00 → #009E73 → #CC79A7 → #E69F00 → #56B4E9` for multi-series charts. Keep the single-series primary as the brand color.
8. **Horizontal-only gridlines + hide top/right spines.** `ax.grid(axis='y', alpha=0.5)`; `ax.spines[['top','right']].set_visible(False)`. Tufte data-ink ratio.

### Tier 2 — Medium effort, highest visual impact (one focused week)

9. **Action-titled charts.** Wire AI-generated takeaways into every chart title. Add `chart_titles` key to the AI narrative JSON schema; pass through `_replace_charts()`. **This is the single biggest perceived-quality lever.**
10. **One-line chart captions.** Add `caption` parameter to every `plot_*()` function; render italic Slate-500 below plot area. AI provides via `chart_captions` JSON key.
11. **Direct-label charts (≤4 series).** Replace legend with inline annotations in `plot_traffic_sources()` and `plot_campaign_performance()`.
12. **Highlight-one bar strategy** in `plot_campaign_performance()`: gray out non-top bars in Slate-300; highlight winner in brand color.
13. **Sparklines on KPI cards.** New `plot_sparkline()` helper: 2" × 0.3", no axes, 1.2pt line in semantic color, dot at last point. Requires 30 days of historical data per KPI — verify `data_snapshots` retains this first.
14. **SCQA executive summary prompt.** Rewrite AI prompt to require Situation → Complication → Question → Answer, 150 words, validate structure.
15. **Enforce 3+3+3 content counts.** AI prompt must return exactly 3 wins, 3 concerns, 3 recommendations. Each recommendation in pattern: "Next month we will [action] on [channel], based on [data point], to achieve [expected change]." Validate programmatically.

### Tier 3 — Template file audits (manual PowerPoint work)

16. **Audit all 6 `.pptx` templates** for: Inter/Arial typography, size hierarchy (Phase 2 table), 0.5" perimeter margins, title zone y=0.4"/height 0.7", footer split left (client + period) / right (`N / Total`).

### Tier 4 — Larger structural changes

17. **MoM + YoY + % of goal scorecard.** Requires historical + target data in the model; redesign scorecard slide layout.
18. **Bad-month detection in AI prompt.** Detect primary-KPI negative MoM; force the four-beat opening sentence.
19. **Ship `xml_effects.py`** (`add_outer_shadow`, `set_cell_border`, `set_gradient_angle`) only when a concrete design need arises.

### What NOT to do

- **Don't switch to native OOXML charts.** Keep matplotlib PNGs.
- **Don't build runtime slide duplication** beyond the existing CSV path.
- **Don't chase shadows/gradients as differentiators.** Flat clean design with good typography + action titles beats ornamented design every time.
- **Don't add animations or transitions.** PDF strips them; async consumption gains nothing.
- **Don't put >4 KPI cards in a scorecard row.** Four is the documented NinjaCat norm.
- **Don't rely on color alone for any signal.** Every up/down color must pair with a glyph.

### Impact / effort priority

| Change | Impact | Effort | Tier |
|---|---|---|---|
| Action-titled charts | ⭐⭐⭐⭐⭐ | Medium | 2 |
| Chart captions (one-line takeaways) | ⭐⭐⭐⭐⭐ | Medium | 2 |
| Sparklines on KPI cards | ⭐⭐⭐⭐⭐ | Medium | 2 |
| Arrow glyphs + neutral band | ⭐⭐⭐⭐ | Low | 1 |
| Okabe-Ito palette | ⭐⭐⭐⭐ | Low | 1 |
| Horizontal-only gridlines | ⭐⭐⭐ | Low | 1 |
| Inverse cost-metric logic | ⭐⭐⭐ | Low | 1 |
| SCQA exec summary | ⭐⭐⭐ | Medium | 2 |
| WCAG emerald fix | ⭐⭐ | Low | 1 |
| K/M/B compact format | ⭐⭐ | Low | 1 |
| Template audit | ⭐⭐⭐ | High (manual) | 3 |
| MoM + YoY + goal scorecard | ⭐⭐⭐⭐ | High | 4 |

**Punchline:** Tier 1 (all 8 items) + the top 3 Tier 2 items (action titles, chart captions, sparklines) delivers the biggest perceived-quality jump available from any ~10-hour investment in the product. That's the "looks like a $300/month tool" threshold.

*End of document. Date of research: April 10, 2026.*
