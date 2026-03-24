# PPTX Generation Research Findings

**Date:** March 24, 2026
**Purpose:** Understand how other products generate PowerPoint presentations to improve ReportPilot's PPTX output quality.

---

## 1. Marketing/Reporting Tools with PPTX Export

### NinjaCat
- **Approach:** Widget-based WYSIWYG template builder (Shinobi). Agencies drag/arrange widgets (charts, tables, KPI cards, text, AI insights) onto a canvas. Templates are reused across hundreds of client accounts with dynamic per-client placeholders.
- **Design:** Pre-designed templates with live data preview during editing. Multi-data-source widgets allow mixing platforms (e.g., Bing + GA) in one table.
- **Branding:** Full white-label. Branding applies globally to reports, dashboards, and emails with one click.
- **Charts:** First-class widget types. Multi-source tables are a differentiator.
- **Unique features:** (1) One template, many accounts via dynamic placeholders. (2) AI Insights Generator widget auto-writes commentary. (3) Report status lifecycle (Running → Ready → Delivered → Error).
- Sources: [NinjaCat Template Builder](https://docs.ninjacat.io/docs/accessing-the-ninjacat-template-builder), [NinjaCat AI Insights](https://docs.ninjacat.io/docs/using-the-text-heading-ai-insights-generator-widgets)

### TapClicks (Report Studio + SmartSlides)
- **Approach:** Two systems: (1) Report Studio for dashboard-to-PPTX, (2) SmartSlides for AI-powered slide deck generation. Agencies upload .potx templates — system fills data into pre-designed layouts.
- **Design:** "Pixel perfect and completely editable" PPTX output. Inherits agency's uploaded PowerPoint design.
- **Branding:** Multi-tier: global templates at platform level + per-business-unit templates for sub-brands.
- **Charts:** Dashboard widgets rendered into export. "Hide Empty Widgets" prevents blank sections.
- **Unique features:** (1) .potx template upload system. (2) SmartReports2 AI agent (Oct 2025) auto-generates full decks. (3) Per-business-unit branding. (4) Hide Empty Widgets in exports.
- Sources: [TapClicks SmartSlides](https://support.tapclicks.com/hc/en-us/articles/41624880687259), [TapClicks PPT Templates](https://support.tapclicks.com/hc/en-us/articles/360039914014)

### Rollstack
- **Approach:** Template-to-data pipeline. Create a PPTX/Google Slides template, Rollstack populates it with BI data (Tableau, Power BI, Looker, Metabase, Snowflake). Auto-refreshes on schedule.
- **Design:** Output inherits BI tool's chart styling exactly. Centralized template governance with locked brand controls.
- **Branding:** Agency-managed templates with slide governance controls for distributed teams.
- **Unique features:** (1) BI-tool-native chart embedding (Tableau chart IS the chart, not a re-rendering). (2) Slide governance for template version management. (3) LLM layer generates executive summaries + anomaly flags. (4) Bulk generation.
- **Pricing:** $750/month — enterprise tier.
- Sources: [Rollstack Product](https://www.rollstack.com/product), [Rollstack AI Guide](https://www.rollstack.com/articles/best-powerpoint-ai-tools-2025-guide-for-ai-reporting-in-powerpoint)

### Slideform
- **Approach:** Pure template-based mail-merge. Upload a standard PPTX, insert `{{placeholder}}` pragmas, connect SQL/data sources (HubSpot, Google Sheets, Looker Studio, Metabase), system fills each placeholder.
- **Design:** 100% controlled by the user's template. Slideform adds zero design — pure data population engine.
- **Branding:** The user's template IS the brand. No Slideform branding appears.
- **Unique features:** (1) SQL-query-per-placeholder architecture for maximum flexibility. (2) Bulk Mode — generate hundreds of client reports from one template. (3) Standard PPTX as template (no vendor lock-in). (4) Data mapping UI shows pragmas as visual blue boxes.
- Sources: [Slideform Data Mapping](https://helpcenter.slideform.co/data-mapping), [Slideform Data Warehouse](https://slideform.co/blog/automate-powerpoint-reports-from-a-data-warehouse)

### Social Status
- **Approach:** Pre-designed social-media-specific templates. Download default PPTX, modify in PowerPoint, re-upload for custom branding.
- **Design:** "Boardroom-ready" templates with social-specific layouts (engagement cards, reach charts).
- **Export formats:** PPTX, PDF, Google Slides, CSV, XLSX from a single data source.
- **Unique features:** (1) Multi-format export. (2) Bring-your-own-template model. (3) White-label on PPTX/PDF only (practical — clients only see exports).
- Sources: [Social Status Reports](https://www.socialstatus.io/reports/)

---

## 2. AI Presentation Generators (Cross-Pollination)

### Gamma.app
- **Approach:** Fully AI-generated from prompts. 20+ AI models simultaneously handle text, images, layout, and brand consistency. Card-based scrollable format (web-native, not PPTX-first).
- **What makes it professional:** Constraint-based layout AI auto-enforces spacing, alignment, visual hierarchy.
- **PPTX export quality:** Generally good but complex card layouts may need manual adjustment. Fonts may substitute. Interactive elements don't translate.
- **Key insight:** Multi-model architecture (specialized models per concern) > single monolithic AI. Design-rule enforcement is the valuable concept.
- Sources: [Gamma Help - Export](https://help.gamma.app/en/articles/8022861), [Gamma AI Presentation Generator](https://gamma.app/ai-presentation-generator)

### Beautiful.ai
- **Approach:** "Smart Slides" — 300+ intelligent layout templates with embedded design-rule engines. Auto-adjusts spacing, alignment, hierarchy, and chart sizing as content changes. Acts as "your own personal creative director."
- **What makes it professional:** Design guardrails prevent bad slides. Users cannot freely position elements — the system controls layout logic. Content-aware reflow when text is added/removed.
- **Key insight:** The concept of content-adaptive layouts is powerful. Our fixed-size text boxes should implement auto-sizing when content is too long.
- Sources: [Beautiful.ai Smart Slides](https://www.beautiful.ai/smart-slides), [Beautiful.ai Blog](https://www.beautiful.ai/blog/what-the-heck-are-smart-slides)

### Tome (DEFUNCT — March 2025)
- **What happened:** Pivoted away from presentations. Team became Lightfield (sales CRM). AngelList acquired the "Tome" brand for legal document summarization.
- **Key lesson:** Pure AI-generated presentations without strong data integration and professional workflow were not a sustainable business. Presentations need real data and a clear business workflow (like client reporting) to succeed.
- Sources: [Tome Pivot Analysis](https://skywork.ai/skypage/en/Tome-AI:-A-2025-Deep-Dive), [Tome Review - Why It Failed](https://slidepeak.com/blog/tome-ai-review)

### SlidesAI
- **Approach:** Google Slides add-on. Enter text → select presentation type (General, Educational, Sales, Conference) → AI generates slides.
- **Unique features:** (1) Outline preview step before generation. (2) Presentation type presets that adapt AI behavior. (3) Works within Google Slides (familiar environment).
- Sources: [SlidesAI Help](https://help.slidesai.io/articles/0023417), [SlidesAI Homepage](https://www.slidesai.io/)

### Canva
- **Approach:** Design-first platform with 12-column grid system. Layouts snap to grid automatically. API supports async PPTX export.
- **PPTX via API:** Async export (start job → poll → download). Rate limits: 750 exports/5min per integration. URLs valid 24 hours.
- **Key insight:** Grid-based constraint system ensures layout quality. Async export pattern is a good API design for batch generation.
- Sources: [Canva Connect API - Exports](https://www.canva.dev/docs/connect/api-reference/exports/), [Canva Design System](https://www.canva.dev/blog/engineering/adding-responsiveness-to-canvas-design-system/)

### Presenton (Open-Source Reference)
- **Approach:** Uses HTML + Tailwind CSS for template design, converts to PPTX at export time. Decouples design system from PPTX format constraints.
- **Features:** Custom themes (classic, modern, professional), local execution, API for programmatic generation, multiple LLM providers.
- **Key insight:** HTML/CSS → PPTX conversion decouples design from format. Worth monitoring for ideas but adds conversion complexity.
- Sources: [Presenton GitHub](https://github.com/presenton/presenton), [Presenton Docs](https://docs.presenton.ai)

---

## 3. Technical Approaches

### Template-First vs Code-Generated

| Approach | Pros | Cons | Who Uses It |
|----------|------|------|-------------|
| **Template-first** (upload .pptx, fill placeholders) | Professional design quality, easy visual iteration, no design-in-code | Fixed layouts, doesn't adapt to content length | TapClicks, Slideform, Rollstack, NinjaCat, **ReportPilot** |
| **Code-generated** (build shapes from scratch) | Full programmatic control, dynamic layouts | Very hard to make look professional | Nobody at premium tier |
| **Hybrid** (design in pptxgenjs, populate in python-pptx) | Design control + data flexibility | Two-step process | **ReportPilot** |
| **AI-generated** (prompt → slides) | Fastest creation, no template needed | Unpredictable output, inconsistent quality | Gamma, Beautiful.ai (with guardrails) |

**Our hybrid approach (pptxgenjs → python-pptx) is confirmed as the strongest approach** because:
1. pptxgenjs generates cleaner XML than PowerPoint's save format
2. Full control over shape positions via code
3. No dependency on unpredictable placeholder IDs from slide masters
4. Easier to maintain and version-control than binary .pptx files
5. No format conversion artifacts (unlike Gamma's card-to-PPTX)

### python-pptx Advanced Capabilities

- **Gradient fills:** `shape.fill.gradient()` → configure stops with position (0.0-1.0) and color. Linear path supported.
- **Shadow effects:** `shape.shadow` → ShadowFormat. If `p:spPr/a:effectLst` is present, ALL effects must be explicit.
- **Rounded rectangles:** `MSO_SHAPE.ROUNDED_RECTANGLE` auto shape.
- **Theme colors:** `MSO_THEME_COLOR` constants (Accent 1-6, Background, Text) with brightness adjustable -1.0 to 1.0.
- **Text autofit:** `text_frame.auto_size` can shrink text to fit containers.
- Sources: [python-pptx Gradient](https://python-pptx.readthedocs.io/en/latest/dev/analysis/dml-gradient.html), [python-pptx Shadow](https://python-pptx.readthedocs.io/en/latest/dev/analysis/shp-shadow.html)

### pptxgenjs Capabilities & Limitations

- **Can do:** Shapes with fills/shadows/rounded corners, text boxes with precise positioning, tables, charts (native OOXML), images, slide backgrounds
- **Cannot do:** True gradient fills on shapes (workaround: overlapping semi-transparent shapes or gradient PNG backgrounds), font embedding, complex animations
- **Slide Masters:** Supports master slide definitions with placeholders for consistent styles and static elements
- Sources: [PptxGenJS GitHub](https://github.com/gitbrent/PptxGenJS), [PptxGenJS Demos](https://gitbrent.github.io/PptxGenJS/demos/)

---

## 4. Key Patterns Across All Tools

### Pattern 1: Template-First is Universal
Every successful reporting tool uses pre-designed templates. Code populates data — it never builds layouts from scratch.

### Pattern 2: AI for Narrative, Not Layout
Best tools use AI for textual insights/commentary, not layout decisions. Layout should be deterministic from templates.

### Pattern 3: Placeholder/Pragma Systems
Slideform's `{{ }}` pragmas and python-pptx's placeholder indices are the most practical for template-to-data binding.

### Pattern 4: Two-Tier Architecture
Separate the design system (template) from the data engine (population code). Agencies own visual brand; tool handles automation.

### Pattern 5: Building in PPTX > Converting to PPTX
Direct PPTX generation (python-pptx) avoids conversion artifacts that plague tools converting from proprietary formats.

---

## 5. What ReportPilot Should Copy

1. **Slideform's bulk generation** — batch 10-50 client reports from one template (for scheduled reports)
2. **Beautiful.ai's content-adaptive layouts** — auto-shrink text when narrative is too long (`text_frame.auto_size`)
3. **TapClicks' user-uploadable templates** (future) — let agencies upload their own .pptx
4. **NinjaCat's report lifecycle** — status tracking (Generating → Ready → Delivered → Error)
5. **Social Status' multi-format export** — PPTX + PDF + Google Slides from one data source
6. **SlidesAI's outline preview** — show report structure before generating
7. **More template variety** — 6 templates is good, 10-12 is better for marketing

## 6. What ReportPilot Should NOT Copy

1. **Gamma/Tome's AI-generated-from-scratch** — too unpredictable for client reports
2. **Web-native formats** — PPTX-first is our differentiator
3. **Native OOXML charts** — matplotlib PNGs give more styling control and consistent rendering

## 7. Confirmed Competitive Advantages

1. **AI narrative + PPTX in one tool** at $19-69/month — no competitor combines this
2. **6 diverse templates** — more visual variety than any affordable reporting tool
3. **Template + populate approach** — produces cleaner output than AI-generated-from-scratch
4. **Charts as images** — render identically on every system, unlike native OOXML charts

---

## Sources

- [NinjaCat Template Builder](https://docs.ninjacat.io/docs/accessing-the-ninjacat-template-builder)
- [NinjaCat AI Insights Widgets](https://docs.ninjacat.io/docs/using-the-text-heading-ai-insights-generator-widgets)
- [TapClicks SmartSlides](https://support.tapclicks.com/hc/en-us/articles/41624880687259)
- [TapClicks PPT Templates](https://support.tapclicks.com/hc/en-us/articles/360039914014)
- [Rollstack Product](https://www.rollstack.com/product)
- [Rollstack AI Reporting Guide](https://www.rollstack.com/articles/best-powerpoint-ai-tools-2025-guide-for-ai-reporting-in-powerpoint)
- [Slideform Data Mapping](https://helpcenter.slideform.co/data-mapping)
- [Slideform Data Warehouse](https://slideform.co/blog/automate-powerpoint-reports-from-a-data-warehouse)
- [Social Status Reports](https://www.socialstatus.io/reports/)
- [Gamma Help - Export](https://help.gamma.app/en/articles/8022861)
- [Beautiful.ai Smart Slides](https://www.beautiful.ai/smart-slides)
- [Beautiful.ai Blog](https://www.beautiful.ai/blog/what-the-heck-are-smart-slides)
- [Tome Pivot Analysis](https://skywork.ai/skypage/en/Tome-AI:-A-2025-Deep-Dive)
- [SlidesAI Help](https://help.slidesai.io/articles/0023417)
- [Canva Connect API - Exports](https://www.canva.dev/docs/connect/api-reference/exports/)
- [Canva Design System](https://www.canva.dev/blog/engineering/adding-responsiveness-to-canvas-design-system/)
- [Presenton GitHub](https://github.com/presenton/presenton)
- [python-pptx Documentation](https://python-pptx.readthedocs.io/en/latest/)
- [PptxGenJS GitHub](https://github.com/gitbrent/PptxGenJS)
- [PptxGenJS Demos](https://gitbrent.github.io/PptxGenJS/demos/)
