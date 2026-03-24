/**
 * ReportPilot — "Bold Geometric" PPTX template
 * Strong visual impact — angled shapes, bold color blocks, pitch-deck energy.
 *
 * Background: white
 * Accent: #4338CA (deep indigo) — used at full strength for headers
 * Cards: white with thick left borders (4px)
 * Cover: full-bleed brand color, diagonal accent, white text
 * Feel: Like a VC pitch deck — confident, bold, memorable
 */
const pptxgen = require("pptxgenjs");
const path = require("path");

const OUT = path.join(__dirname, "..", "backend", "templates", "pptx", "bold_geometric.pptx");

const C = {
  bg:       "FFFFFF",
  bgSoft:   "F8FAFC",
  accent:   "4338CA",
  accentLt: "EEF2FF",
  accentDk: "3730A3",
  dark:     "0F172A",
  text:     "334155",
  muted:    "64748B",
  light:    "94A3B8",
  border:   "E2E8F0",
  card:     "FFFFFF",
  green:    "059669",
  greenBg:  "ECFDF5",
  amber:    "D97706",
  amberBg:  "FFFBEB",
  white:    "FFFFFF",
};

const FONT      = "Calibri";
const FONT_BODY = "Calibri";
const W = 13.3, H = 7.5;

const shadow = () => ({ type: "outer", blur: 6, offset: 2, angle: 135, color: "000000", opacity: 0.08 });

function addFooter(slide, pageNum) {
  slide.addText(`{{agency_name}}  \u2022  Confidential  \u2022  Page ${pageNum}`, {
    x: 0.8, y: H - 0.38, w: W - 1.6, h: 0.28,
    fontSize: 8, fontFace: FONT, color: C.light,
  });
}

function addSectionHeader(slide, title, opts = {}) {
  // Full-width indigo header band
  slide.addShape("rect", {
    x: 0, y: 0, w: W, h: 1.3,
    fill: { color: C.accent },
  });
  // Diagonal accent triangle
  slide.addShape("rtTriangle", {
    x: W - 3.5, y: 0, w: 3.5, h: 1.3,
    fill: { color: C.accentDk },
    rotate: 0,
  });
  slide.addText(title, {
    x: 0.8, y: 0.25, w: W - 5, h: 0.8,
    fontSize: 28, fontFace: FONT, bold: true, color: C.white,
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
  // SLIDE 1 — COVER (full-bleed brand color)
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.accent };

    // Large diagonal shape for visual drama
    s.addShape("rtTriangle", {
      x: W - 6, y: 0, w: 6, h: H,
      fill: { color: C.accentDk },
    });

    // "PERFORMANCE REPORT" label
    s.addText("PERFORMANCE REPORT", {
      x: 0.8, y: 0.8, w: 6, h: 0.4,
      fontSize: 13, fontFace: FONT, bold: true, color: C.white,
      charSpacing: 6,
    });

    // Thin white accent line
    s.addShape("rect", { x: 0.8, y: 1.5, w: 3.0, h: 0.04, fill: { color: C.white } });

    // Agency logo placeholder
    s.addText("{{agency_logo}}", {
      x: W - 3.0, y: 0.5, w: 2.2, h: 1.0,
      fontSize: 9, fontFace: FONT, color: "C7D2FE", align: "right", valign: "middle",
    });

    // Client name — large white text
    s.addText("{{client_name}}", {
      x: 0.8, y: 2.0, w: 7, h: 1.8,
      fontSize: 44, fontFace: FONT, bold: true, color: C.white,
    });

    // Report period
    s.addText("{{report_period}}", {
      x: 0.8, y: 3.9, w: 6, h: 0.45,
      fontSize: 16, fontFace: FONT, color: "C7D2FE",
    });

    // Report type
    s.addText("{{report_type}}", {
      x: 0.8, y: 4.45, w: 6, h: 0.35,
      fontSize: 12, fontFace: FONT, color: "A5B4FC",
    });

    // Client logo
    s.addText("{{client_logo}}", {
      x: W - 3.5, y: 4.0, w: 2.5, h: 1.8,
      fontSize: 9, fontFace: FONT, color: "C7D2FE", align: "center", valign: "middle",
    });

    // Prepared by at bottom
    s.addText("Prepared by {{agency_name}}", {
      x: 0.8, y: H - 0.7, w: 8, h: 0.35,
      fontSize: 11, fontFace: FONT, color: "A5B4FC",
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 2 — EXECUTIVE SUMMARY
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addSectionHeader(s, "Executive Summary");

    s.addText("{{executive_summary}}", {
      x: 0.8, y: 1.6, w: W - 1.6, h: 5.0,
      fontSize: 13, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.45, valign: "top",
    });

    addFooter(s, 2);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 3 — KPI SCORECARD (thick left-border cards)
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bgSoft };
    addSectionHeader(s, "Key Performance Indicators");

    const cardW = 3.5, cardH = 2.2;
    const gapX = 0.35, gapY = 0.35;
    const startX = 0.8, startY = 1.65;
    const accentColors = [C.accent, C.accent, C.accent, C.accent, C.accent, C.accent];

    for (let i = 0; i < 6; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const cx = startX + col * (cardW + gapX);
      const cy = startY + row * (cardH + gapY);

      // Card bg
      s.addShape("rect", {
        x: cx, y: cy, w: cardW, h: cardH,
        fill: { color: C.card }, shadow: shadow(),
      });

      // Thick left accent border (instead of top stripe)
      s.addShape("rect", {
        x: cx, y: cy, w: 0.08, h: cardH,
        fill: { color: accentColors[i] },
      });

      // Label
      s.addText(`{{kpi_${i}_label}}`, {
        x: cx + 0.28, y: cy + 0.2, w: cardW - 0.48, h: 0.3,
        fontSize: 10, fontFace: FONT, bold: true, color: C.muted,
        charSpacing: 2,
      });

      // Value
      s.addText(`{{kpi_${i}_value}}`, {
        x: cx + 0.28, y: cy + 0.6, w: cardW - 0.48, h: 0.7,
        fontSize: 32, fontFace: FONT, bold: true, color: C.dark,
      });

      // Change
      s.addText(`{{kpi_${i}_change}}`, {
        x: cx + 0.28, y: cy + 1.45, w: cardW - 0.48, h: 0.35,
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
    addSectionHeader(s, "Website Performance");

    // Chart cards with rounded corners simulated by shadow
    s.addShape("roundRect", { x: 0.8, y: 1.6, w: 5.6, h: 3.0, fill: { color: C.card }, shadow: shadow(), rectRadius: 0.1 });
    s.addText("{{chart_sessions}}", {
      x: 0.8, y: 1.6, w: 5.6, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    s.addShape("roundRect", { x: 6.8, y: 1.6, w: 5.7, h: 3.0, fill: { color: C.card }, shadow: shadow(), rectRadius: 0.1 });
    s.addText("{{chart_traffic}}", {
      x: 6.8, y: 1.6, w: 5.7, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    s.addText("{{website_narrative}}", {
      x: 0.8, y: 4.9, w: W - 1.6, h: 1.9,
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
    addSectionHeader(s, "Paid Advertising \u2014 Meta Ads");

    s.addShape("roundRect", { x: 0.8, y: 1.6, w: 5.6, h: 3.0, fill: { color: C.card }, shadow: shadow(), rectRadius: 0.1 });
    s.addText("{{chart_spend}}", {
      x: 0.8, y: 1.6, w: 5.6, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    s.addShape("roundRect", { x: 6.8, y: 1.6, w: 5.7, h: 3.0, fill: { color: C.card }, shadow: shadow(), rectRadius: 0.1 });
    s.addText("{{chart_campaigns}}", {
      x: 6.8, y: 1.6, w: 5.7, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    s.addText("{{ads_narrative}}", {
      x: 0.8, y: 4.9, w: W - 1.6, h: 1.9,
      fontSize: 12, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.35, valign: "top",
    });

    addFooter(s, 5);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 6 — KEY WINS (green header)
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // Green header band
    s.addShape("rect", { x: 0, y: 0, w: W, h: 1.3, fill: { color: C.green } });
    s.addShape("rtTriangle", { x: W - 3.5, y: 0, w: 3.5, h: 1.3, fill: { color: "047857" } });
    s.addText("Key Wins & Highlights", {
      x: 0.8, y: 0.25, w: W - 5, h: 0.8,
      fontSize: 28, fontFace: FONT, bold: true, color: C.white, margin: 0,
    });

    s.addText("{{key_wins}}", {
      x: 0.8, y: 1.6, w: W - 1.6, h: 5.0,
      fontSize: 13, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.5, valign: "top",
    });

    addFooter(s, 6);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 7 — CONCERNS (amber header)
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    s.addShape("rect", { x: 0, y: 0, w: W, h: 1.3, fill: { color: C.amber } });
    s.addShape("rtTriangle", { x: W - 3.5, y: 0, w: 3.5, h: 1.3, fill: { color: "B45309" } });
    s.addText("Concerns & Recommendations", {
      x: 0.8, y: 0.25, w: W - 5, h: 0.8,
      fontSize: 28, fontFace: FONT, bold: true, color: C.white, margin: 0,
    });

    s.addText("{{concerns}}", {
      x: 0.8, y: 1.6, w: W - 1.6, h: 5.0,
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
    addSectionHeader(s, "Next Steps & Action Items");

    s.addText("{{next_steps}}", {
      x: 0.8, y: 1.6, w: W - 1.6, h: 4.0,
      fontSize: 13, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.5, valign: "top",
    });

    // CTA band
    s.addShape("rect", { x: 0, y: H - 1.2, w: W, h: 1.2, fill: { color: C.accent } });
    s.addShape("rtTriangle", { x: W - 3, y: H - 1.2, w: 3, h: 1.2, fill: { color: C.accentDk } });
    s.addText("Questions? Reply to this email or schedule a call.", {
      x: 0.8, y: H - 1.15, w: W - 1.6, h: 0.45,
      fontSize: 13, fontFace: FONT, bold: true, color: C.white,
    });
    s.addText("{{agency_name}}  \u2022  {{agency_email}}", {
      x: 0.8, y: H - 0.65, w: W - 1.6, h: 0.35,
      fontSize: 11, fontFace: FONT, color: "C7D2FE",
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 9 — CUSTOM SECTION
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addSectionHeader(s, "{{custom_section_title}}");

    s.addText("{{custom_section_text}}", {
      x: 0.8, y: 1.6, w: W - 1.6, h: 5.0,
      fontSize: 13, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.4, valign: "top",
    });

    addFooter(s, 9);
  }

  await pres.writeFile({ fileName: OUT });
  console.log("bold_geometric.pptx created:", OUT);
}

build().catch(console.error);
