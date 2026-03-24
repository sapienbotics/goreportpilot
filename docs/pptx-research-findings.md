# PPTX Generation Research Findings

**Date:** March 24, 2026
**Purpose:** Understand how other products generate PowerPoint presentations to improve ReportPilot's PPTX output quality.

---

## 1. Marketing/Reporting Tools with PPTX Export

### NinjaCat
- **Approach:** Template-based generation. Users create or select PowerPoint templates, and the system populates them with campaign data.
- **Design:** Pre-designed templates with placeholder regions. Output is fully editable PPTX.
- **Charts:** Embedded as images from their visualization engine.
- **Branding:** Custom templates uploaded by agencies — full white-label control.
- **Unique feature:** One-click export — agency can go from dashboard to client-ready PPTX instantly.
- **Pricing:** Enterprise-only, not published publicly.
- Source: [NinjaCat Reporting](https://www.ninjacat.io/resources/optimized-client-reporting-for-agencies)

### TapClicks (Report Studio)
- **Approach:** Template-based with "pixel perfect" editable PPTX output. Users can upload their own PowerPoint templates.
- **Design:** Supports custom PPT templates — agencies design in PowerPoint, then TapClicks fills in the data.
- **Charts:** Generated server-side, embedded as images.
- **Branding:** Full white-label via custom templates. Upload your PPT with your brand, fonts, layout.
- **Unique feature:** The template approach means agencies get exactly the design they want — no compromise.
- Source: [TapClicks Report Studio](https://www.tapclicks.com/tapclicks-report-studio)

### Rollstack
- **Approach:** Template-based with live data binding. Users map BI data (Tableau, Power BI, Looker) to pre-designed PPTX templates. Slides refresh on schedule.
- **Design:** Centralized template governance — brand controls are locked. Design consistency comes from the template, not the tool.
- **Charts:** Screenshots/exports from BI tools, auto-embedded in designated template regions.
- **Branding:** Agency-managed templates with locked brand elements.
- **Unique feature:** LLM layer generates executive summaries and anomaly flags from the live data. Scheduled auto-refresh means reports are always current.
- **Pricing:** Starts at $750/month — enterprise tier.
- Source: [Rollstack Product](https://www.rollstack.com/product)

### Slideform
- **Approach:** Pure template-based mail-merge. Upload a standard PPTX as template, insert placeholders, connect SQL/data sources (HubSpot, Google Sheets), and Slideform populates each placeholder.
- **Design:** 100% controlled by the user's template. Slideform adds zero design — it's a pure data population engine.
- **Charts:** Generated from data and embedded as images in template placeholder regions.
- **Branding:** The user's template IS the brand. No Slideform branding appears.
- **Unique feature:** Bulk generation — produce hundreds of client-specific reports from one template in a single run. Agency sends one template, gets 50 client reports back.
- Source: [Slideform Marketing Reports](https://slideform.co/blog/automate-marketing-reports-with-slideform-ai)

### Social Status
- **Approach:** Pre-built report templates optimized for social media metrics. One-click PPTX download.
- **Design:** Pre-designed templates with social-media-specific layouts (engagement cards, reach charts).
- **Unique feature:** Competitor benchmarking slides included automatically.

---

## 2. AI Presentation Generators (Cross-Pollination)

### Gamma.app
- **Approach:** Fully AI-generated from prompts. NOT template-based. Runs 20+ AI models simultaneously for text, images, layout, and brand consistency.
- **Design:** AI selects layout, typography, color, and imagery. Output is web-native (not PPTX-first). PPTX export is secondary.
- **What makes it look professional:** Constraint-based layout AI that enforces spacing, alignment, and visual hierarchy rules automatically.
- **Unique insight for ReportPilot:** Their multi-model approach is overkill for reports, but the concept of design-rule enforcement (auto-spacing, auto-alignment) is valuable. We could add basic layout validation in our population engine.
- Source: [Gamma.app Review](https://skywork.ai/skypage/en/Gamma-App-In-Depth-Review-2025-The-Ultimate-Guide-to-AI-Presentations/1973913493482172416)

### Beautiful.ai
- **Approach:** "Smart Slides" — 60+ layout templates with embedded design-rule engines. Each Smart Slide auto-adjusts spacing, alignment, and chart sizing as content changes.
- **Design:** Built-in layout logic enforces design principles in real-time. Users cannot break the design — the engine maintains visual hierarchy no matter what content is added.
- **Key insight for ReportPilot:** The concept of Smart Slides — where the layout adapts to content length — is powerful. Our PPTX templates currently have fixed-size text boxes. If narrative text is too long, it gets cut off. We should consider auto-sizing text or splitting long content across slides.
- Source: [Beautiful.ai Smart Slides](https://www.beautiful.ai/smart-slides)

### Tome
- **Approach:** AI-first document creation. Users provide a prompt and Tome generates a complete "tome" (a hybrid of slides + documents). Web-native format with PPTX export.
- **Design:** Clean, modern layouts with generous whitespace. Layouts are dynamic — they flex based on content.
- **Key insight:** Their "document + slides" hybrid format is interesting. For long narratives, a document-style page might work better than cramming text into a slide.

### SlidesAI
- **Approach:** Google Slides add-on. Users provide text, SlidesAI generates a presentation from it.
- **Design:** Template-based — users select a theme, then AI populates slides.
- **Limited control:** The output quality depends heavily on the input text quality.

### Canva
- **Approach:** Design-first platform with programmatic export via API. Templates are designed by professionals, users customize via drag-and-drop.
- **PPTX export:** Available but lossy — some Canva-specific effects (animations, custom fonts) don't survive PPTX conversion.
- **Key insight:** Canva's strength is having thousands of professionally-designed templates. For ReportPilot, having MORE template variety (6+ options) gives users the feeling of a premium tool.

---

## 3. Technical Approaches

### Template-First vs Code-Generated

**Template-first (recommended — what we use):**
- Create a fully designed PPTX in PowerPoint or pptxgenjs
- Load it as the starting point in python-pptx
- Replace placeholders with data
- **Pro:** Professional design quality, easy to iterate on visuals
- **Con:** Fixed layouts — doesn't adapt to variable content length
- **Who uses this:** TapClicks, Slideform, Rollstack, NinjaCat, ReportPilot

**Code-generated:**
- Build every shape, text box, and image from scratch in code
- **Pro:** Full programmatic control, dynamic layouts
- **Con:** Very difficult to make look professional — design is in code
- **Who uses this:** Nobody at the premium tier. It's used for quick/dirty generation only.

**Hybrid (our approach):**
- Templates designed in pptxgenjs (code, but design-focused code)
- Population via python-pptx (data insertion)
- Charts via matplotlib (image generation)
- This is the right approach — keep it.

### python-pptx Best Practices

**Slide Master approach:**
- Create a PPTX in PowerPoint with slide masters containing all brand elements (logos, colors, fonts)
- Delete all slides, save as template
- In python-pptx, use `prs.slide_layouts[n]` to add slides with the correct master layout
- Placeholders in slide masters have predictable IDs — use them for data population
- **Key limitation:** python-pptx's slide master API is limited. Complex masters with custom placeholders can be fragile.

**Our approach (pptxgenjs → python-pptx) is actually better because:**
- pptxgenjs generates cleaner XML than PowerPoint's save format
- We have full control over shape positions via code
- No dependency on unpredictable placeholder IDs from slide masters
- Easier to maintain and version-control than binary .pptx template files

### pptxgenjs Capabilities

**What it can do well:**
- Shapes with fills, shadows, rounded corners
- Text boxes with precise positioning, font control, line spacing
- Tables with cell-level styling
- Charts (native OOXML charts — live, editable in PowerPoint)
- Images (embedded PNGs)
- Slide backgrounds (solid color)

**What it can't do:**
- True gradient fills on shapes (workaround: overlapping semi-transparent shapes)
- Embedded videos (technically possible but fragile)
- Complex animations/transitions
- Font embedding (uses system fonts only)

---

## 4. Key Takeaways for ReportPilot

### What We Should Copy

1. **Slideform's bulk generation concept.** When we add scheduled reports, generating 10-50 client reports in one batch is a clear value proposition.

2. **Beautiful.ai's content-adaptive layouts.** Our current templates have fixed text boxes. We should add auto-text-size reduction when content is too long (python-pptx can set `autofit` on text frames).

3. **Rollstack's AI summary layer.** We already do this with GPT-4o. We're ahead of most competitors here.

4. **TapClicks' user-uploadable templates.** Future feature: let agencies upload their own PPTX template and map our placeholders to it. This is the ultimate white-label feature.

5. **More template variety.** Canva wins partly because they have thousands of templates. Going from 3 to 6 is good. Going to 10-12 would be better for marketing.

### What We Should NOT Copy

1. **Gamma/Tome's AI-generated-from-scratch approach.** Too unpredictable for client reports where consistency matters.

2. **Web-native formats.** Our PPTX-first approach is the differentiator. Don't dilute it with a web viewer.

3. **Native OOXML charts in pptxgenjs.** While technically possible, matplotlib charts rendered as high-res PNGs give us more styling control and consistent rendering across platforms.

### Our Competitive Advantages (Confirmed)

1. **AI narrative + PPTX in one tool** — No competitor combines GPT-4o-quality narrative with branded editable PowerPoint at $19-69/month.
2. **6 diverse templates** — More visual variety than any affordable reporting tool.
3. **Template + populate approach** — Produces cleaner, more consistent output than AI-generated-from-scratch tools.
4. **Charts as images** — Renders identically on every system, unlike native OOXML charts which can look different depending on the PowerPoint version.

---

## Sources

- [NinjaCat Reporting](https://www.ninjacat.io/resources/optimized-client-reporting-for-agencies)
- [TapClicks Report Studio](https://www.tapclicks.com/tapclicks-report-studio)
- [Rollstack Product](https://www.rollstack.com/product)
- [Rollstack AI Reporting Guide](https://www.rollstack.com/articles/best-powerpoint-ai-tools-2025-guide-for-ai-reporting-in-powerpoint)
- [Slideform Marketing Reports](https://slideform.co/blog/automate-marketing-reports-with-slideform-ai)
- [Slideform Scheduled Generation](https://slideform.co/blog/autogenerate-slides-on-a-schedule)
- [Gamma.app Review](https://skywork.ai/skypage/en/Gamma-App-In-Depth-Review-2025-The-Ultimate-Guide-to-AI-Presentations/1973913493482172416)
- [Beautiful.ai Smart Slides](https://www.beautiful.ai/smart-slides)
- [python-pptx Documentation](https://python-pptx.readthedocs.io/en/latest/)
- [python-pptx Slide Layouts](https://python-pptx.readthedocs.io/en/latest/user/slides.html)
