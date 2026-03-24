/**
 * ReportPilot — "Minimal Elegant" PPTX template
 * Ultra-minimal, whitespace-heavy, Apple-like restraint.
 *
 * Background: pure white
 * Accent: single thin line (#0F172A)
 * Text: Georgia for titles (serif elegance), Calibri for body
 * KPI cards: no fill, just numbers with thin bottom border
 * Cover: centered client name, nothing else — very Apple
 * Content takes up only ~55% of each slide — rest is breathing room
 */
const pptxgen = require("pptxgenjs");
const path = require("path");

const OUT = path.join(__dirname, "..", "backend", "templates", "pptx", "minimal_elegant.pptx");

const C = {
  bg:     "FFFFFF",
  dark:   "0F172A",
  text:   "334155",
  muted:  "64748B",
  light:  "94A3B8",
  subtle: "CBD5E1",
  border: "E2E8F0",
  card:   "FFFFFF",
  green:  "059669",
  amber:  "D97706",
  white:  "FFFFFF",
};

const FONT_TITLE = "Georgia";  // Serif for titles — elegant touch
const FONT_BODY  = "Calibri";
const W = 13.3, H = 7.5;

function addFooter(slide, pageNum) {
  // Ultra-minimal footer: just a thin line and tiny text
  slide.addShape("rect", { x: 1.5, y: H - 0.55, w: W - 3.0, h: 0.005, fill: { color: C.border } });
  slide.addText(`{{agency_name}}  \u2022  Page ${pageNum}`, {
    x: 1.5, y: H - 0.45, w: W - 3.0, h: 0.28,
    fontSize: 7, fontFace: FONT_BODY, color: C.light, align: "center",
  });
}

function addTitle(slide, title, opts = {}) {
  slide.addText(title, {
    x: 1.5, y: 0.6, w: W - 3.0, h: 0.7,
    fontSize: 26, fontFace: FONT_TITLE, bold: false, color: C.dark,
    margin: 0,
    ...opts,
  });
  // Thin accent line below title
  slide.addShape("rect", {
    x: 1.5, y: 1.35, w: 2.0, h: 0.015,
    fill: { color: C.dark },
  });
}

async function build() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = "ReportPilot";
  pres.title  = "Performance Report";

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 1 — COVER (centered, minimal)
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // Agency logo — small, top-left
    s.addText("{{agency_logo}}", {
      x: 1.5, y: 0.8, w: 2.0, h: 0.8,
      fontSize: 9, fontFace: FONT_BODY, color: C.light, align: "left", valign: "middle",
    });

    // Client name — centered, dominant
    s.addText("{{client_name}}", {
      x: 1.5, y: 2.4, w: W - 3.0, h: 1.4,
      fontSize: 40, fontFace: FONT_TITLE, bold: false, color: C.dark, align: "center",
    });

    // Thin divider
    s.addShape("rect", { x: (W - 2) / 2, y: 4.0, w: 2.0, h: 0.01, fill: { color: C.dark } });

    // Report period
    s.addText("{{report_period}}", {
      x: 1.5, y: 4.3, w: W - 3.0, h: 0.4,
      fontSize: 14, fontFace: FONT_BODY, color: C.muted, align: "center",
    });

    // Report type
    s.addText("{{report_type}}", {
      x: 1.5, y: 4.8, w: W - 3.0, h: 0.35,
      fontSize: 11, fontFace: FONT_BODY, color: C.light, align: "center",
    });

    // Client logo — centered below
    s.addText("{{client_logo}}", {
      x: (W - 2.5) / 2, y: 5.5, w: 2.5, h: 1.0,
      fontSize: 9, fontFace: FONT_BODY, color: C.light, align: "center", valign: "middle",
    });

    // Agency attribution
    s.addText("Prepared by {{agency_name}}", {
      x: 1.5, y: H - 0.6, w: W - 3.0, h: 0.3,
      fontSize: 9, fontFace: FONT_BODY, color: C.light, align: "center",
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 2 — EXECUTIVE SUMMARY
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Executive Summary");

    // Wide margins for elegance — content centered in a narrow column
    s.addText("{{executive_summary}}", {
      x: 1.5, y: 1.7, w: W - 3.0, h: 5.0,
      fontSize: 13, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.5, valign: "top",
    });

    addFooter(s, 2);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 3 — KPI SCORECARD (borderless, numbers-only)
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Key Metrics");

    const cardW = 3.2, cardH = 2.0;
    const gapX = 0.5, gapY = 0.5;
    const startX = 1.5, startY = 1.7;

    for (let i = 0; i < 6; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const cx = startX + col * (cardW + gapX);
      const cy = startY + row * (cardH + gapY);

      // No card background — just the data
      // Label
      s.addText(`{{kpi_${i}_label}}`, {
        x: cx, y: cy + 0.05, w: cardW, h: 0.25,
        fontSize: 9, fontFace: FONT_BODY, bold: true, color: C.light,
        charSpacing: 2,
      });

      // Value — large and prominent
      s.addText(`{{kpi_${i}_value}}`, {
        x: cx, y: cy + 0.35, w: cardW, h: 0.8,
        fontSize: 32, fontFace: FONT_BODY, bold: true, color: C.dark,
      });

      // Change
      s.addText(`{{kpi_${i}_change}}`, {
        x: cx, y: cy + 1.2, w: cardW, h: 0.3,
        fontSize: 12, fontFace: FONT_BODY, bold: true, color: C.muted,
      });

      // Thin bottom border
      s.addShape("rect", {
        x: cx, y: cy + cardH - 0.05, w: cardW, h: 0.01,
        fill: { color: C.border },
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

    // Charts — no borders, no card background, clean
    s.addText("{{chart_sessions}}", {
      x: 0.8, y: 1.6, w: 5.6, h: 3.0,
      fontSize: 10, fontFace: FONT_BODY, color: C.light, align: "center", valign: "middle",
    });

    s.addText("{{chart_traffic}}", {
      x: 6.8, y: 1.6, w: 5.7, h: 3.0,
      fontSize: 10, fontFace: FONT_BODY, color: C.light, align: "center", valign: "middle",
    });

    s.addText("{{website_narrative}}", {
      x: 1.5, y: 4.9, w: W - 3.0, h: 1.9,
      fontSize: 12, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.4, valign: "top",
    });

    addFooter(s, 4);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 5 — META ADS
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Paid Advertising");

    s.addText("{{chart_spend}}", {
      x: 0.8, y: 1.6, w: 5.6, h: 3.0,
      fontSize: 10, fontFace: FONT_BODY, color: C.light, align: "center", valign: "middle",
    });

    s.addText("{{chart_campaigns}}", {
      x: 6.8, y: 1.6, w: 5.7, h: 3.0,
      fontSize: 10, fontFace: FONT_BODY, color: C.light, align: "center", valign: "middle",
    });

    s.addText("{{ads_narrative}}", {
      x: 1.5, y: 4.9, w: W - 3.0, h: 1.9,
      fontSize: 12, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.4, valign: "top",
    });

    addFooter(s, 5);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 6 — KEY WINS
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    s.addText("Key Wins", {
      x: 1.5, y: 0.6, w: W - 3.0, h: 0.7,
      fontSize: 26, fontFace: FONT_TITLE, bold: false, color: C.green, margin: 0,
    });
    s.addShape("rect", { x: 1.5, y: 1.35, w: 2.0, h: 0.015, fill: { color: C.green } });

    s.addText("{{key_wins}}", {
      x: 1.5, y: 1.7, w: W - 3.0, h: 5.0,
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

    s.addText("Concerns & Recommendations", {
      x: 1.5, y: 0.6, w: W - 3.0, h: 0.7,
      fontSize: 26, fontFace: FONT_TITLE, bold: false, color: C.amber, margin: 0,
    });
    s.addShape("rect", { x: 1.5, y: 1.35, w: 2.0, h: 0.015, fill: { color: C.amber } });

    s.addText("{{concerns}}", {
      x: 1.5, y: 1.7, w: W - 3.0, h: 5.0,
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
    addTitle(s, "Next Steps");

    s.addText("{{next_steps}}", {
      x: 1.5, y: 1.7, w: W - 3.0, h: 4.0,
      fontSize: 13, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.5, valign: "top",
    });

    // Minimal CTA — just text, no band
    s.addShape("rect", { x: 1.5, y: H - 1.3, w: W - 3.0, h: 0.01, fill: { color: C.dark } });
    s.addText("Questions? {{agency_name}}  \u2022  {{agency_email}}", {
      x: 1.5, y: H - 1.1, w: W - 3.0, h: 0.35,
      fontSize: 11, fontFace: FONT_BODY, color: C.muted, align: "center",
    });

    addFooter(s, 8);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 9 — CUSTOM SECTION
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    s.addText("{{custom_section_title}}", {
      x: 1.5, y: 0.6, w: W - 3.0, h: 0.7,
      fontSize: 26, fontFace: FONT_TITLE, bold: false, color: C.dark, margin: 0,
    });
    s.addShape("rect", { x: 1.5, y: 1.35, w: 2.0, h: 0.015, fill: { color: C.dark } });

    s.addText("{{custom_section_text}}", {
      x: 1.5, y: 1.7, w: W - 3.0, h: 5.0,
      fontSize: 13, fontFace: FONT_BODY, color: C.text,
      lineSpacingMultiple: 1.4, valign: "top",
    });

    addFooter(s, 9);
  }

  await pres.writeFile({ fileName: OUT });
  console.log("minimal_elegant.pptx created:", OUT);
}

build().catch(console.error);
