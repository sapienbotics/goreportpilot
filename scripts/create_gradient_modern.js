/**
 * ReportPilot — "Gradient Modern" PPTX template
 * Warm gradient accents — startup/SaaS aesthetic like Linear or Notion.
 *
 * Since pptxgenjs can't do true gradients, we simulate them:
 * - Cover: 3 overlapping semi-transparent colored bars creating a gradient effect
 * - Accent elements: two thin bars side-by-side (coral + orange or blue + purple)
 * - Warm palette: coral (#F97316) fading to rose (#F43F5E)
 *
 * Background: white
 * Primary accent: coral → rose gradient (simulated)
 * Secondary: indigo highlights for KPI changes
 * Cards: white with warm-tinted subtle shadow
 * Feel: Modern SaaS — Notion, Linear, Vercel energy
 */
const pptxgen = require("pptxgenjs");
const path = require("path");

const OUT = path.join(__dirname, "..", "backend", "templates", "pptx", "gradient_modern.pptx");

const C = {
  bg:       "FFFFFF",
  bgSoft:   "FFFBF5",  // Very warm off-white
  coral:    "F97316",
  rose:     "F43F5E",
  purple:   "8B5CF6",
  warmLt:   "FFF7ED",
  dark:     "0F172A",
  text:     "334155",
  muted:    "64748B",
  light:    "94A3B8",
  border:   "E2E8F0",
  card:     "FFFFFF",
  green:    "059669",
  greenLt:  "ECFDF5",
  amber:    "D97706",
  amberLt:  "FFFBEB",
  white:    "FFFFFF",
};

const FONT      = "Calibri";
const FONT_BODY = "Calibri";
const W = 13.3, H = 7.5;

const warmShadow = () => ({ type: "outer", blur: 6, offset: 2, angle: 135, color: "F97316", opacity: 0.06 });
const shadow = () => ({ type: "outer", blur: 5, offset: 2, angle: 135, color: "000000", opacity: 0.06 });

function addFooter(slide, pageNum) {
  slide.addText(`{{agency_name}}  \u2022  Confidential  \u2022  Page ${pageNum}`, {
    x: 0.8, y: H - 0.38, w: W - 1.6, h: 0.28,
    fontSize: 8, fontFace: FONT, color: C.light,
  });
}

function addGradientBar(slide) {
  // Simulate gradient: 3 thin bars side by side (coral → rose → purple)
  const barH = 0.06;
  slide.addShape("rect", { x: 0, y: 0, w: W * 0.4, h: barH, fill: { color: C.coral } });
  slide.addShape("rect", { x: W * 0.4, y: 0, w: W * 0.35, h: barH, fill: { color: C.rose } });
  slide.addShape("rect", { x: W * 0.75, y: 0, w: W * 0.25, h: barH, fill: { color: C.purple } });
}

function addTitle(slide, title, opts = {}) {
  addGradientBar(slide);
  slide.addText(title, {
    x: 0.8, y: 0.35, w: W - 1.6, h: 0.7,
    fontSize: 28, fontFace: FONT, bold: true, color: C.dark,
    margin: 0,
    ...opts,
  });
}

async function build() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = "ReportPilot";
  pres.title  = "Performance Report";

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 1 — COVER (warm gradient feel)
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // Simulated gradient header band (3 overlapping colored rectangles)
    s.addShape("rect", { x: 0, y: 0, w: W, h: 2.6, fill: { color: C.coral } });
    // Second layer — offset slightly, creates depth
    s.addShape("rect", { x: W * 0.3, y: 0, w: W * 0.7, h: 2.6, fill: { color: C.rose } });
    // Third layer
    s.addShape("rect", { x: W * 0.65, y: 0, w: W * 0.35, h: 2.6, fill: { color: C.purple } });

    // "PERFORMANCE REPORT" in the gradient band
    s.addText("PERFORMANCE REPORT", {
      x: 0.8, y: 0.6, w: 6, h: 0.4,
      fontSize: 12, fontFace: FONT, bold: true, color: C.white,
      charSpacing: 5,
    });

    // Agency name
    s.addText("Prepared by {{agency_name}}", {
      x: 0.8, y: 1.2, w: 6, h: 0.35,
      fontSize: 11, fontFace: FONT, color: "FECDD3",
    });

    // Agency logo
    s.addText("{{agency_logo}}", {
      x: W - 3.0, y: 0.5, w: 2.2, h: 1.0,
      fontSize: 9, fontFace: FONT, color: "FECDD3", align: "right", valign: "middle",
    });

    // Client name — below gradient band
    s.addText("{{client_name}}", {
      x: 0.8, y: 3.1, w: W - 1.6, h: 1.5,
      fontSize: 42, fontFace: FONT, bold: true, color: C.dark,
    });

    // Report period
    s.addText("{{report_period}}", {
      x: 0.8, y: 4.7, w: 8, h: 0.45,
      fontSize: 16, fontFace: FONT, color: C.muted,
    });

    // Report type
    s.addText("{{report_type}}", {
      x: 0.8, y: 5.25, w: 8, h: 0.35,
      fontSize: 12, fontFace: FONT, color: C.light,
    });

    // Client logo
    s.addText("{{client_logo}}", {
      x: W - 3.5, y: 4.5, w: 2.5, h: 1.5,
      fontSize: 9, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    // Bottom gradient bar
    s.addShape("rect", { x: 0, y: H - 0.08, w: W * 0.4, h: 0.08, fill: { color: C.coral } });
    s.addShape("rect", { x: W * 0.4, y: H - 0.08, w: W * 0.35, h: 0.08, fill: { color: C.rose } });
    s.addShape("rect", { x: W * 0.75, y: H - 0.08, w: W * 0.25, h: 0.08, fill: { color: C.purple } });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 2 — EXECUTIVE SUMMARY
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Executive Summary");

    s.addText("{{executive_summary}}", {
      x: 0.8, y: 1.4, w: W - 1.6, h: 5.2,
      fontSize: 13, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.45, valign: "top",
    });

    addFooter(s, 2);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 3 — KPI SCORECARD
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bgSoft };
    addTitle(s, "Key Performance Indicators");

    const cardW = 3.5, cardH = 2.2;
    const gapX = 0.35, gapY = 0.35;
    const startX = 0.8, startY = 1.45;
    // Alternating warm accent colors for left borders
    const accents = [C.coral, C.rose, C.purple, C.coral, C.rose, C.purple];

    for (let i = 0; i < 6; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const cx = startX + col * (cardW + gapX);
      const cy = startY + row * (cardH + gapY);

      // Card
      s.addShape("rect", {
        x: cx, y: cy, w: cardW, h: cardH,
        fill: { color: C.card }, shadow: warmShadow(),
      });

      // Simulated gradient left border (two thin bars)
      s.addShape("rect", { x: cx, y: cy, w: 0.04, h: cardH, fill: { color: accents[i] } });
      s.addShape("rect", { x: cx + 0.04, y: cy, w: 0.03, h: cardH, fill: { color: accents[(i + 1) % 3] } });

      // Label
      s.addText(`{{kpi_${i}_label}}`, {
        x: cx + 0.25, y: cy + 0.2, w: cardW - 0.45, h: 0.3,
        fontSize: 10, fontFace: FONT, bold: true, color: C.muted,
        charSpacing: 2,
      });

      // Value
      s.addText(`{{kpi_${i}_value}}`, {
        x: cx + 0.25, y: cy + 0.6, w: cardW - 0.45, h: 0.7,
        fontSize: 30, fontFace: FONT, bold: true, color: C.dark,
      });

      // Change
      s.addText(`{{kpi_${i}_change}}`, {
        x: cx + 0.25, y: cy + 1.4, w: cardW - 0.45, h: 0.35,
        fontSize: 13, fontFace: FONT, bold: true, color: C.muted,
      });
    }

    addFooter(s, 3);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 4 — WEBSITE PERFORMANCE
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Website Performance");

    s.addShape("rect", { x: 0.8, y: 1.4, w: 5.6, h: 3.0, fill: { color: C.card }, shadow: shadow() });
    s.addText("{{chart_sessions}}", {
      x: 0.8, y: 1.4, w: 5.6, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    s.addShape("rect", { x: 6.8, y: 1.4, w: 5.7, h: 3.0, fill: { color: C.card }, shadow: shadow() });
    s.addText("{{chart_traffic}}", {
      x: 6.8, y: 1.4, w: 5.7, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    s.addText("{{website_narrative}}", {
      x: 0.8, y: 4.7, w: W - 1.6, h: 2.1,
      fontSize: 12, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.35, valign: "top",
    });

    addFooter(s, 4);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 5 — META ADS
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Paid Advertising \u2014 Meta Ads");

    s.addShape("rect", { x: 0.8, y: 1.4, w: 5.6, h: 3.0, fill: { color: C.card }, shadow: shadow() });
    s.addText("{{chart_spend}}", {
      x: 0.8, y: 1.4, w: 5.6, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    s.addShape("rect", { x: 6.8, y: 1.4, w: 5.7, h: 3.0, fill: { color: C.card }, shadow: shadow() });
    s.addText("{{chart_campaigns}}", {
      x: 6.8, y: 1.4, w: 5.7, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    s.addText("{{ads_narrative}}", {
      x: 0.8, y: 4.7, w: W - 1.6, h: 2.1,
      fontSize: 12, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.35, valign: "top",
    });

    addFooter(s, 5);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 6 — KEY WINS
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // Green gradient bar
    s.addShape("rect", { x: 0, y: 0, w: W, h: 0.06, fill: { color: C.green } });

    s.addText("Key Wins & Highlights", {
      x: 0.8, y: 0.35, w: W - 1.6, h: 0.7,
      fontSize: 28, fontFace: FONT, bold: true, color: C.green, margin: 0,
    });

    s.addText("{{key_wins}}", {
      x: 0.8, y: 1.4, w: W - 1.6, h: 5.2,
      fontSize: 13, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.5, valign: "top",
    });

    addFooter(s, 6);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 7 — CONCERNS
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    s.addShape("rect", { x: 0, y: 0, w: W, h: 0.06, fill: { color: C.amber } });

    s.addText("Concerns & Recommendations", {
      x: 0.8, y: 0.35, w: W - 1.6, h: 0.7,
      fontSize: 28, fontFace: FONT, bold: true, color: C.amber, margin: 0,
    });

    s.addText("{{concerns}}", {
      x: 0.8, y: 1.4, w: W - 1.6, h: 5.2,
      fontSize: 13, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.5, valign: "top",
    });

    addFooter(s, 7);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 8 — NEXT STEPS
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Next Steps & Action Items");

    s.addText("{{next_steps}}", {
      x: 0.8, y: 1.4, w: W - 1.6, h: 4.2,
      fontSize: 13, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.5, valign: "top",
    });

    // CTA with gradient band
    s.addShape("rect", { x: 0, y: H - 1.2, w: W * 0.4, h: 1.2, fill: { color: C.coral } });
    s.addShape("rect", { x: W * 0.4, y: H - 1.2, w: W * 0.35, h: 1.2, fill: { color: C.rose } });
    s.addShape("rect", { x: W * 0.75, y: H - 1.2, w: W * 0.25, h: 1.2, fill: { color: C.purple } });
    s.addText("Questions? Reply to this email or schedule a call.", {
      x: 0.8, y: H - 1.15, w: W - 1.6, h: 0.45,
      fontSize: 13, fontFace: FONT, bold: true, color: C.white,
    });
    s.addText("{{agency_name}}  \u2022  {{agency_email}}", {
      x: 0.8, y: H - 0.65, w: W - 1.6, h: 0.35,
      fontSize: 11, fontFace: FONT, color: "FECDD3",
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 9 — CUSTOM SECTION
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addGradientBar(s);

    s.addText("{{custom_section_title}}", {
      x: 0.8, y: 0.35, w: W - 1.6, h: 0.7,
      fontSize: 28, fontFace: FONT, bold: true, color: C.dark,
    });

    s.addText("{{custom_section_text}}", {
      x: 0.8, y: 1.4, w: W - 1.6, h: 5.2,
      fontSize: 13, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.4, valign: "top",
    });

    addFooter(s, 9);
  }

  await pres.writeFile({ fileName: OUT });
  console.log("gradient_modern.pptx created:", OUT);
}

build().catch(console.error);
