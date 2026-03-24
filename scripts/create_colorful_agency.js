/**
 * ReportPilot — "Colorful Agency" PPTX template
 * Vibrant, modern, creative — Stripe/Linear-style SaaS aesthetic.
 *
 * Background: white
 * Accents: coral (#F97316), purple (#8B5CF6), teal (#14B8A6)
 * Cards: white with colorful left accent bars
 * Feel: Bold color blocks, playful but professional
 */
const pptxgen = require("pptxgenjs");
const path = require("path");

const OUT = path.join(__dirname, "..", "backend", "templates", "pptx", "colorful_agency.pptx");

const C = {
  bg:       "FFFFFF",
  bgSoft:   "F8FAFC",
  coral:    "F97316",
  coralLt:  "FFF7ED",
  purple:   "8B5CF6",
  purpleLt: "F5F3FF",
  teal:     "14B8A6",
  tealLt:   "F0FDFA",
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
};

const FONT = "Calibri";
const W = 13.3, H = 7.5;

// Each KPI card gets a different accent color
const CARD_COLORS = [C.coral, C.purple, C.teal, C.coral, C.purple, C.teal];

const shadow = () => ({ type: "outer", blur: 5, offset: 2, angle: 135, color: "000000", opacity: 0.07 });

function addFooter(slide, pageNum) {
  slide.addText(`{{agency_name}}  \u2022  Confidential  \u2022  Page ${pageNum}`, {
    x: 0.8, y: H - 0.38, w: W - 1.6, h: 0.28,
    fontSize: 8, fontFace: FONT, color: C.light,
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
    s.background = { color: C.bg };

    // Diagonal-feel color blocks — stacked bands at top
    s.addShape("rect", { x: 0,   y: 0, w: 4.5, h: 0.18, fill: { color: C.coral } });
    s.addShape("rect", { x: 4.5, y: 0, w: 4.5, h: 0.18, fill: { color: C.purple } });
    s.addShape("rect", { x: 9.0, y: 0, w: 4.3, h: 0.18, fill: { color: C.teal } });

    // Colored left column — visual anchor
    s.addShape("rect", { x: 0, y: 0.18, w: 0.4, h: H - 0.18, fill: { color: C.coral } });

    // "PERFORMANCE REPORT" label
    s.addText("PERFORMANCE REPORT", {
      x: 0.8, y: 0.8, w: 6, h: 0.4,
      fontSize: 12, fontFace: FONT, bold: true, color: C.coral,
      charSpacing: 5,
    });

    // Agency logo placeholder
    s.addText("{{agency_logo}}", {
      x: W - 3.0, y: 0.5, w: 2.2, h: 1.0,
      fontSize: 9, fontFace: FONT, color: C.light, align: "right", valign: "middle",
    });

    // Client name — bold and large
    s.addText("{{client_name}}", {
      x: 0.8, y: 1.8, w: W - 1.6, h: 1.6,
      fontSize: 40, fontFace: FONT, bold: true, color: C.dark,
    });

    // Report period
    s.addText("{{report_period}}", {
      x: 0.8, y: 3.6, w: 8, h: 0.45,
      fontSize: 14, fontFace: FONT, color: C.muted,
    });

    // Report type
    s.addText("{{report_type}}", {
      x: 0.8, y: 4.15, w: 8, h: 0.4,
      fontSize: 12, fontFace: FONT, color: C.light,
    });

    // Client logo
    s.addText("{{client_logo}}", {
      x: W - 3.5, y: 3.8, w: 2.5, h: 1.8,
      fontSize: 9, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    // Agency attribution at bottom
    s.addText("Prepared by {{agency_name}}", {
      x: 0.8, y: H - 0.7, w: 8, h: 0.35,
      fontSize: 11, fontFace: FONT, color: C.light,
    });

    // Bottom color bar
    s.addShape("rect", { x: 0, y: H - 0.12, w: W, h: 0.12, fill: { color: C.purple } });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 2 — EXECUTIVE SUMMARY
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bgSoft };

    // Purple left accent bar
    s.addShape("rect", { x: 0, y: 0, w: 0.06, h: H, fill: { color: C.purple } });

    addTitle(s, "Executive Summary");

    s.addText("{{executive_summary}}", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 5.0,
      fontSize: 12, fontFace: FONT, color: C.text,
      lineSpacingMultiple: 1.4, valign: "top",
    });

    addFooter(s, 2);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 3 — KPI SCORECARD
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bgSoft };

    // Teal left accent
    s.addShape("rect", { x: 0, y: 0, w: 0.06, h: H, fill: { color: C.teal } });

    addTitle(s, "Key Performance Indicators");

    const cardW = 3.5, cardH = 2.2;
    const gapX = 0.35, gapY = 0.35;
    const startX = 0.8, startY = 1.55;

    for (let i = 0; i < 6; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const cx = startX + col * (cardW + gapX);
      const cy = startY + row * (cardH + gapY);
      const accentColor = CARD_COLORS[i];

      // Card
      s.addShape("rect", {
        x: cx, y: cy, w: cardW, h: cardH,
        fill: { color: C.card }, shadow: shadow(),
      });

      // Colored left accent bar on each card
      s.addShape("rect", {
        x: cx, y: cy, w: 0.07, h: cardH,
        fill: { color: accentColor },
      });

      // Label
      s.addText(`{{kpi_${i}_label}}`, {
        x: cx + 0.25, y: cy + 0.2, w: cardW - 0.45, h: 0.3,
        fontSize: 10, fontFace: FONT, bold: true, color: C.muted,
        charSpacing: 2,
      });

      // Value
      s.addText(`{{kpi_${i}_value}}`, {
        x: cx + 0.25, y: cy + 0.6, w: cardW - 0.45, h: 0.7,
        fontSize: 32, fontFace: FONT, bold: true, color: C.dark,
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
    s.background = { color: C.bgSoft };
    s.addShape("rect", { x: 0, y: 0, w: 0.06, h: H, fill: { color: C.coral } });
    addTitle(s, "Website Performance");

    // Chart areas with subtle card
    s.addShape("rect", { x: 0.8, y: 1.5, w: 5.6, h: 3.0, fill: { color: C.card }, shadow: shadow() });
    s.addText("{{chart_sessions}}", {
      x: 0.8, y: 1.5, w: 5.6, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    s.addShape("rect", { x: 6.8, y: 1.5, w: 5.7, h: 3.0, fill: { color: C.card }, shadow: shadow() });
    s.addText("{{chart_traffic}}", {
      x: 6.8, y: 1.5, w: 5.7, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    s.addText("{{website_narrative}}", {
      x: 0.8, y: 4.8, w: W - 1.6, h: 2.0,
      fontSize: 12, fontFace: FONT, color: C.text,
      lineSpacingMultiple: 1.35, valign: "top",
    });

    addFooter(s, 4);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 5 — META ADS
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bgSoft };
    s.addShape("rect", { x: 0, y: 0, w: 0.06, h: H, fill: { color: C.purple } });
    addTitle(s, "Paid Advertising \u2014 Meta Ads");

    s.addShape("rect", { x: 0.8, y: 1.5, w: 5.6, h: 3.0, fill: { color: C.card }, shadow: shadow() });
    s.addText("{{chart_spend}}", {
      x: 0.8, y: 1.5, w: 5.6, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    s.addShape("rect", { x: 6.8, y: 1.5, w: 5.7, h: 3.0, fill: { color: C.card }, shadow: shadow() });
    s.addText("{{chart_campaigns}}", {
      x: 6.8, y: 1.5, w: 5.7, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    s.addText("{{ads_narrative}}", {
      x: 0.8, y: 4.8, w: W - 1.6, h: 2.0,
      fontSize: 12, fontFace: FONT, color: C.text,
      lineSpacingMultiple: 1.35, valign: "top",
    });

    addFooter(s, 5);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 6 — KEY WINS (green theme)
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bgSoft };

    // Green accent and header band
    s.addShape("rect", { x: 0, y: 0, w: 0.06, h: H, fill: { color: C.green } });
    s.addShape("rect", { x: 0.06, y: 0, w: W - 0.06, h: 1.15, fill: { color: C.greenLt } });

    addTitle(s, "Key Wins & Highlights", { color: "065F46" });

    s.addText("{{key_wins}}", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 5.0,
      fontSize: 12, fontFace: FONT, color: C.text,
      lineSpacingMultiple: 1.5, valign: "top",
    });

    addFooter(s, 6);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 7 — CONCERNS (amber theme)
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bgSoft };

    s.addShape("rect", { x: 0, y: 0, w: 0.06, h: H, fill: { color: C.amber } });
    s.addShape("rect", { x: 0.06, y: 0, w: W - 0.06, h: 1.15, fill: { color: C.amberLt } });

    addTitle(s, "Concerns & Recommendations", { color: "92400E" });

    s.addText("{{concerns}}", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 5.0,
      fontSize: 12, fontFace: FONT, color: C.text,
      lineSpacingMultiple: 1.5, valign: "top",
    });

    addFooter(s, 7);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 8 — NEXT STEPS
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bgSoft };
    s.addShape("rect", { x: 0, y: 0, w: 0.06, h: H, fill: { color: C.teal } });
    addTitle(s, "Next Steps & Action Items");

    s.addText("{{next_steps}}", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 4.0,
      fontSize: 12, fontFace: FONT, color: C.text,
      lineSpacingMultiple: 1.5, valign: "top",
    });

    // CTA band — gradient-like with coral
    s.addShape("rect", { x: 0, y: H - 1.2, w: W, h: 1.2, fill: { color: C.coral } });
    s.addText("Questions? Reply to this email or schedule a call.", {
      x: 0.8, y: H - 1.15, w: W - 1.6, h: 0.45,
      fontSize: 13, fontFace: FONT, bold: true, color: C.bg,
    });
    s.addText("{{agency_name}}  \u2022  {{agency_email}}", {
      x: 0.8, y: H - 0.65, w: W - 1.6, h: 0.35,
      fontSize: 11, fontFace: FONT, color: "FED7AA",
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 9 — CUSTOM SECTION
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bgSoft };
    s.addShape("rect", { x: 0, y: 0, w: 0.06, h: H, fill: { color: C.purple } });

    s.addText("{{custom_section_title}}", {
      x: 0.8, y: 0.45, w: W - 1.6, h: 0.7,
      fontSize: 28, fontFace: FONT, bold: true, color: C.dark,
    });

    s.addText("{{custom_section_text}}", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 5.0,
      fontSize: 12, fontFace: FONT, color: C.text,
      lineSpacingMultiple: 1.4, valign: "top",
    });

    addFooter(s, 9);
  }

  await pres.writeFile({ fileName: OUT });
  console.log("colorful_agency.pptx created:", OUT);
}

build().catch(console.error);
