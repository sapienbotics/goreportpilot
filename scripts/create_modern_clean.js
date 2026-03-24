/**
 * ReportPilot — "Modern Clean" PPTX template
 * Light, professional, corporate — consulting-firm quality.
 *
 * Background: #FAFAFA (off-white)
 * Accent: #4338CA (deep indigo)
 * Text: #0F172A (dark) / #64748B (muted)
 * Cards: white with subtle shadow
 */
const pptxgen = require("pptxgenjs");
const path = require("path");

const OUT = path.join(__dirname, "..", "backend", "templates", "pptx", "modern_clean.pptx");

// ── Palette ──────────────────────────────────────────────────────────────────
const C = {
  bg:        "FAFAFA",
  accent:    "4338CA",
  accentLt:  "EEF2FF",
  dark:      "0F172A",
  text:      "334155",
  muted:     "64748B",
  light:     "94A3B8",
  border:    "E2E8F0",
  card:      "FFFFFF",
  green:     "059669",
  greenBg:   "F0FDF4",
  amber:     "D97706",
  amberBg:   "FFFBEB",
  white:     "FFFFFF",
};

const FONT      = "Calibri";
const FONT_BODY = "Calibri Light";
const W = 13.3, H = 7.5;  // LAYOUT_WIDE

// ── Helpers ──────────────────────────────────────────────────────────────────
const shadow = () => ({ type: "outer", blur: 4, offset: 1.5, angle: 135, color: "000000", opacity: 0.08 });
const cardShadow = () => ({ type: "outer", blur: 6, offset: 2, angle: 135, color: "000000", opacity: 0.1 });

function addFooter(slide, pageNum) {
  slide.addText(`{{agency_name}}  \u2022  Confidential  \u2022  Page ${pageNum}`, {
    x: 0.8, y: H - 0.38, w: W - 1.6, h: 0.28,
    fontSize: 8, fontFace: FONT_BODY, color: C.light, align: "left",
  });
}

function addAccentBar(slide) {
  // Thin left accent bar — the visual thread across all content slides
  slide.addShape("rect", {
    x: 0, y: 0, w: 0.06, h: H,
    fill: { color: C.accent },
  });
}

function addTitle(slide, title, opts = {}) {
  slide.addText(title, {
    x: 0.8, y: 0.45, w: W - 1.6, h: 0.7,
    fontSize: 28, fontFace: FONT, bold: true, color: C.dark,
    margin: 0,
    ...opts,
  });
}

// ── Build ────────────────────────────────────────────────────────────────────
async function build() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = "ReportPilot";
  pres.title  = "Performance Report";

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 1 — COVER
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.white };

    // Indigo band — top 2.2"
    s.addShape("rect", { x: 0, y: 0, w: W, h: 2.2, fill: { color: C.accent } });

    // "PERFORMANCE REPORT" label in band
    s.addText("PERFORMANCE REPORT", {
      x: 0.8, y: 0.55, w: 6, h: 0.4,
      fontSize: 12, fontFace: FONT, bold: true, color: C.white,
      charSpacing: 4,
    });

    // Agency name in band
    s.addText("Prepared by {{agency_name}}", {
      x: 0.8, y: 1.15, w: 6, h: 0.35,
      fontSize: 11, fontFace: FONT_BODY, color: "C7D2FE",
    });

    // Agency logo placeholder — top right inside band
    s.addText("{{agency_logo}}", {
      x: W - 2.8, y: 0.4, w: 2.0, h: 1.0,
      fontSize: 9, fontFace: FONT_BODY, color: "C7D2FE", align: "right", valign: "middle",
    });

    // Client name — large, below band
    s.addText("{{client_name}}", {
      x: 0.8, y: 2.7, w: W - 1.6, h: 1.5,
      fontSize: 40, fontFace: FONT, bold: true, color: C.dark,
    });

    // Report period
    s.addText("{{report_period}}", {
      x: 0.8, y: 4.35, w: W - 1.6, h: 0.5,
      fontSize: 14, fontFace: FONT_BODY, color: C.muted,
    });

    // Report type
    s.addText("{{report_type}}", {
      x: 0.8, y: 4.95, w: W - 1.6, h: 0.4,
      fontSize: 12, fontFace: FONT_BODY, color: C.light,
    });

    // Client logo placeholder
    s.addText("{{client_logo}}", {
      x: W - 3.5, y: 4.5, w: 2.5, h: 1.5,
      fontSize: 9, fontFace: FONT_BODY, color: C.light, align: "center", valign: "middle",
    });

    // Subtle bottom line
    s.addShape("rect", { x: 0.8, y: H - 0.5, w: W - 1.6, h: 0.015, fill: { color: C.border } });
    s.addText("{{agency_name}}", {
      x: 0.8, y: H - 0.45, w: W - 1.6, h: 0.3,
      fontSize: 9, fontFace: FONT_BODY, color: C.light,
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 2 — EXECUTIVE SUMMARY
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addAccentBar(s);
    addTitle(s, "Executive Summary");

    // Large text area
    s.addText("{{executive_summary}}", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 5.0,
      fontSize: 12, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.4, valign: "top",
    });

    addFooter(s, 2);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 3 — KPI SCORECARD
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addAccentBar(s);
    addTitle(s, "Key Performance Indicators");

    const cardW = 3.5, cardH = 2.2;
    const gapX = 0.35, gapY = 0.35;
    const startX = 0.8, startY = 1.55;

    for (let i = 0; i < 6; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const cx = startX + col * (cardW + gapX);
      const cy = startY + row * (cardH + gapY);

      // Card background
      s.addShape("rect", {
        x: cx, y: cy, w: cardW, h: cardH,
        fill: { color: C.card },
        shadow: cardShadow(),
      });

      // Top accent stripe
      s.addShape("rect", {
        x: cx, y: cy, w: cardW, h: 0.05,
        fill: { color: C.accent },
      });

      // Label
      s.addText(`{{kpi_${i}_label}}`, {
        x: cx + 0.2, y: cy + 0.2, w: cardW - 0.4, h: 0.3,
        fontSize: 10, fontFace: FONT, bold: true, color: C.muted,
        charSpacing: 2,
      });

      // Value
      s.addText(`{{kpi_${i}_value}}`, {
        x: cx + 0.2, y: cy + 0.6, w: cardW - 0.4, h: 0.7,
        fontSize: 32, fontFace: FONT, bold: true, color: C.dark,
      });

      // Change
      s.addText(`{{kpi_${i}_change}}`, {
        x: cx + 0.2, y: cy + 1.4, w: cardW - 0.4, h: 0.35,
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
    addAccentBar(s);
    addTitle(s, "Website Performance");

    // Left chart area
    s.addShape("rect", {
      x: 0.8, y: 1.5, w: 5.6, h: 3.0,
      fill: { color: C.card }, shadow: shadow(),
    });
    s.addText("{{chart_sessions}}", {
      x: 0.8, y: 1.5, w: 5.6, h: 3.0,
      fontSize: 10, fontFace: FONT_BODY, color: C.light, align: "center", valign: "middle",
    });

    // Right chart area
    s.addShape("rect", {
      x: 6.8, y: 1.5, w: 5.7, h: 3.0,
      fill: { color: C.card }, shadow: shadow(),
    });
    s.addText("{{chart_traffic}}", {
      x: 6.8, y: 1.5, w: 5.7, h: 3.0,
      fontSize: 10, fontFace: FONT_BODY, color: C.light, align: "center", valign: "middle",
    });

    // Narrative
    s.addText("{{website_narrative}}", {
      x: 0.8, y: 4.8, w: W - 1.6, h: 2.0,
      fontSize: 12, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.35, valign: "top",
    });

    addFooter(s, 4);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 5 — META ADS PERFORMANCE
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addAccentBar(s);
    addTitle(s, "Paid Advertising \u2014 Meta Ads");

    s.addShape("rect", {
      x: 0.8, y: 1.5, w: 5.6, h: 3.0,
      fill: { color: C.card }, shadow: shadow(),
    });
    s.addText("{{chart_spend}}", {
      x: 0.8, y: 1.5, w: 5.6, h: 3.0,
      fontSize: 10, fontFace: FONT_BODY, color: C.light, align: "center", valign: "middle",
    });

    s.addShape("rect", {
      x: 6.8, y: 1.5, w: 5.7, h: 3.0,
      fill: { color: C.card }, shadow: shadow(),
    });
    s.addText("{{chart_campaigns}}", {
      x: 6.8, y: 1.5, w: 5.7, h: 3.0,
      fontSize: 10, fontFace: FONT_BODY, color: C.light, align: "center", valign: "middle",
    });

    s.addText("{{ads_narrative}}", {
      x: 0.8, y: 4.8, w: W - 1.6, h: 2.0,
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

    // Green accent bar instead of indigo
    s.addShape("rect", { x: 0, y: 0, w: 0.06, h: H, fill: { color: C.green } });

    // Green tinted header band
    s.addShape("rect", {
      x: 0.06, y: 0, w: W - 0.06, h: 1.15,
      fill: { color: C.greenBg },
    });

    addTitle(s, "Key Wins & Highlights", { color: "065F46" });

    s.addText("{{key_wins}}", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 5.0,
      fontSize: 12, fontFace: FONT_BODY, color: C.text,
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

    // Amber accent bar
    s.addShape("rect", { x: 0, y: 0, w: 0.06, h: H, fill: { color: C.amber } });

    // Amber tinted header band
    s.addShape("rect", {
      x: 0.06, y: 0, w: W - 0.06, h: 1.15,
      fill: { color: C.amberBg },
    });

    addTitle(s, "Concerns & Recommendations", { color: "92400E" });

    s.addText("{{concerns}}", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 5.0,
      fontSize: 12, fontFace: FONT_BODY, color: C.text,
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
    addAccentBar(s);
    addTitle(s, "Next Steps & Action Items");

    s.addText("{{next_steps}}", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 4.0,
      fontSize: 12, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.5, valign: "top",
    });

    // Contact CTA band at bottom
    s.addShape("rect", {
      x: 0, y: H - 1.2, w: W, h: 1.2,
      fill: { color: C.accent },
    });
    s.addText("Questions? Reply to this email or schedule a call.", {
      x: 0.8, y: H - 1.15, w: W - 1.6, h: 0.45,
      fontSize: 13, fontFace: FONT_BODY, color: C.white, bold: true,
    });
    s.addText("{{agency_name}}  \u2022  {{agency_email}}", {
      x: 0.8, y: H - 0.65, w: W - 1.6, h: 0.35,
      fontSize: 11, fontFace: FONT_BODY, color: "C7D2FE",
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 9 — CUSTOM SECTION
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addAccentBar(s);

    s.addText("{{custom_section_title}}", {
      x: 0.8, y: 0.45, w: W - 1.6, h: 0.7,
      fontSize: 28, fontFace: FONT, bold: true, color: C.dark,
    });

    s.addText("{{custom_section_text}}", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 5.0,
      fontSize: 12, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.4, valign: "top",
    });

    addFooter(s, 9);
  }

  await pres.writeFile({ fileName: OUT });
  console.log("modern_clean.pptx created:", OUT);
}

build().catch(console.error);
