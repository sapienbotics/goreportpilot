/**
 * ReportPilot — "Dark Executive" PPTX template
 * Dark, premium, executive — Bloomberg-terminal-meets-presentation.
 *
 * Background: #0F172A (deep navy)
 * Cards: #1E293B (slightly lighter navy)
 * Accent: #06B6D4 (bright teal)
 * Text: #F8FAFC (near-white) / #94A3B8 (muted)
 */
const pptxgen = require("pptxgenjs");
const path = require("path");

const OUT = path.join(__dirname, "..", "backend", "templates", "pptx", "dark_executive.pptx");

const C = {
  bg:       "0F172A",
  bgCard:   "1E293B",
  bgDeep:   "020617",
  accent:   "06B6D4",
  accentLt: "164E63",
  white:    "F8FAFC",
  text:     "CBD5E1",
  muted:    "64748B",
  dimmed:   "475569",
  border:   "334155",
  green:    "10B981",
  greenBg:  "064E3B",
  amber:    "F59E0B",
  amberBg:  "78350F",
};

const FONT = "Calibri";
const W = 13.3, H = 7.5;

const shadow = () => ({ type: "outer", blur: 8, offset: 2, angle: 135, color: "000000", opacity: 0.3 });

function addFooter(slide, pageNum) {
  slide.addShape("rect", { x: 0, y: H - 0.02, w: W, h: 0.02, fill: { color: C.accent } });
  slide.addText(`{{agency_name}}  \u2022  Confidential  \u2022  Page ${pageNum}`, {
    x: 0.8, y: H - 0.38, w: W - 1.6, h: 0.28,
    fontSize: 8, fontFace: FONT, color: C.dimmed,
  });
}

function addTitle(slide, title, opts = {}) {
  // Thin teal top line as title accent
  slide.addShape("rect", {
    x: 0.8, y: 0.4, w: 1.5, h: 0.035,
    fill: { color: C.accent },
  });
  slide.addText(title, {
    x: 0.8, y: 0.55, w: W - 1.6, h: 0.7,
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
  // SLIDE 1 — COVER
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bgDeep };

    // Accent line — thin teal horizontal stripe
    s.addShape("rect", { x: 0, y: 2.0, w: W, h: 0.04, fill: { color: C.accent } });

    // "PERFORMANCE REPORT" — above the accent line
    s.addText("PERFORMANCE REPORT", {
      x: 0.8, y: 0.8, w: 6, h: 0.4,
      fontSize: 12, fontFace: FONT, bold: true, color: C.accent,
      charSpacing: 6,
    });

    // Agency logo placeholder — top right
    s.addText("{{agency_logo}}", {
      x: W - 3.0, y: 0.5, w: 2.2, h: 1.0,
      fontSize: 9, fontFace: FONT, color: C.dimmed, align: "right", valign: "middle",
    });

    // Client name — large, below accent line
    s.addText("{{client_name}}", {
      x: 0.8, y: 2.5, w: W - 1.6, h: 1.5,
      fontSize: 44, fontFace: FONT, bold: true, color: C.white,
    });

    // Report period
    s.addText("{{report_period}}", {
      x: 0.8, y: 4.15, w: 8, h: 0.45,
      fontSize: 16, fontFace: FONT, color: C.text,
    });

    // Report type
    s.addText("{{report_type}}", {
      x: 0.8, y: 4.7, w: 8, h: 0.35,
      fontSize: 12, fontFace: FONT, color: C.muted,
    });

    // Agency attribution
    s.addText("Prepared by {{agency_name}}", {
      x: 0.8, y: H - 0.8, w: 8, h: 0.35,
      fontSize: 11, fontFace: FONT, color: C.dimmed,
    });

    // Client logo
    s.addText("{{client_logo}}", {
      x: W - 3.5, y: 4.0, w: 2.5, h: 1.8,
      fontSize: 9, fontFace: FONT, color: C.dimmed, align: "center", valign: "middle",
    });

    // Bottom teal line
    s.addShape("rect", { x: 0, y: H - 0.04, w: W, h: 0.04, fill: { color: C.accent } });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 2 — EXECUTIVE SUMMARY
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Executive Summary");

    // Dark card for text
    s.addShape("rect", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 5.0,
      fill: { color: C.bgCard }, shadow: shadow(),
    });
    s.addText("{{executive_summary}}", {
      x: 1.1, y: 1.7, w: W - 2.2, h: 4.5,
      fontSize: 13, fontFace: FONT, color: C.text,
      lineSpacingMultiple: 1.45, valign: "top",
    });

    addFooter(s, 2);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 3 — KPI SCORECARD
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Key Performance Indicators");

    const cardW = 3.5, cardH = 2.2;
    const gapX = 0.35, gapY = 0.35;
    const startX = 0.8, startY = 1.55;

    for (let i = 0; i < 6; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const cx = startX + col * (cardW + gapX);
      const cy = startY + row * (cardH + gapY);

      // Dark card
      s.addShape("rect", {
        x: cx, y: cy, w: cardW, h: cardH,
        fill: { color: C.bgCard }, shadow: shadow(),
      });

      // Teal top stripe
      s.addShape("rect", {
        x: cx, y: cy, w: cardW, h: 0.05,
        fill: { color: C.accent },
      });

      // Label
      s.addText(`{{kpi_${i}_label}}`, {
        x: cx + 0.22, y: cy + 0.2, w: cardW - 0.44, h: 0.3,
        fontSize: 10, fontFace: FONT, bold: true, color: C.muted,
        charSpacing: 2,
      });

      // Value
      s.addText(`{{kpi_${i}_value}}`, {
        x: cx + 0.22, y: cy + 0.6, w: cardW - 0.44, h: 0.7,
        fontSize: 30, fontFace: FONT, bold: true, color: C.white,
      });

      // Change
      s.addText(`{{kpi_${i}_change}}`, {
        x: cx + 0.22, y: cy + 1.4, w: cardW - 0.44, h: 0.35,
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

    // Chart cards
    s.addShape("rect", { x: 0.8, y: 1.5, w: 5.6, h: 3.0, fill: { color: C.bgCard }, shadow: shadow() });
    s.addText("{{chart_sessions}}", {
      x: 0.8, y: 1.5, w: 5.6, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.dimmed, align: "center", valign: "middle",
    });

    s.addShape("rect", { x: 6.8, y: 1.5, w: 5.7, h: 3.0, fill: { color: C.bgCard }, shadow: shadow() });
    s.addText("{{chart_traffic}}", {
      x: 6.8, y: 1.5, w: 5.7, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.dimmed, align: "center", valign: "middle",
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
    s.background = { color: C.bg };
    addTitle(s, "Paid Advertising \u2014 Meta Ads");

    s.addShape("rect", { x: 0.8, y: 1.5, w: 5.6, h: 3.0, fill: { color: C.bgCard }, shadow: shadow() });
    s.addText("{{chart_spend}}", {
      x: 0.8, y: 1.5, w: 5.6, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.dimmed, align: "center", valign: "middle",
    });

    s.addShape("rect", { x: 6.8, y: 1.5, w: 5.7, h: 3.0, fill: { color: C.bgCard }, shadow: shadow() });
    s.addText("{{chart_campaigns}}", {
      x: 6.8, y: 1.5, w: 5.7, h: 3.0,
      fontSize: 10, fontFace: FONT, color: C.dimmed, align: "center", valign: "middle",
    });

    s.addText("{{ads_narrative}}", {
      x: 0.8, y: 4.8, w: W - 1.6, h: 2.0,
      fontSize: 12, fontFace: FONT, color: C.text,
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

    // Green accent top line
    s.addShape("rect", { x: 0.8, y: 0.4, w: 1.5, h: 0.035, fill: { color: C.green } });
    s.addText("Key Wins & Highlights", {
      x: 0.8, y: 0.55, w: W - 1.6, h: 0.7,
      fontSize: 28, fontFace: FONT, bold: true, color: C.green, margin: 0,
    });

    // Content card
    s.addShape("rect", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 5.0,
      fill: { color: C.bgCard }, shadow: shadow(),
    });
    s.addText("{{key_wins}}", {
      x: 1.1, y: 1.7, w: W - 2.2, h: 4.5,
      fontSize: 13, fontFace: FONT, color: C.text,
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

    // Amber accent
    s.addShape("rect", { x: 0.8, y: 0.4, w: 1.5, h: 0.035, fill: { color: C.amber } });
    s.addText("Concerns & Recommendations", {
      x: 0.8, y: 0.55, w: W - 1.6, h: 0.7,
      fontSize: 28, fontFace: FONT, bold: true, color: C.amber, margin: 0,
    });

    s.addShape("rect", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 5.0,
      fill: { color: C.bgCard }, shadow: shadow(),
    });
    s.addText("{{concerns}}", {
      x: 1.1, y: 1.7, w: W - 2.2, h: 4.5,
      fontSize: 13, fontFace: FONT, color: C.text,
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

    s.addShape("rect", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 4.0,
      fill: { color: C.bgCard }, shadow: shadow(),
    });
    s.addText("{{next_steps}}", {
      x: 1.1, y: 1.7, w: W - 2.2, h: 3.5,
      fontSize: 13, fontFace: FONT, color: C.text,
      lineSpacingMultiple: 1.5, valign: "top",
    });

    // CTA band
    s.addShape("rect", {
      x: 0, y: H - 1.2, w: W, h: 1.2,
      fill: { color: C.accentLt },
    });
    s.addText("Questions? Reply to this email or schedule a call.", {
      x: 0.8, y: H - 1.15, w: W - 1.6, h: 0.45,
      fontSize: 13, fontFace: FONT, bold: true, color: C.accent,
    });
    s.addText("{{agency_name}}  \u2022  {{agency_email}}", {
      x: 0.8, y: H - 0.65, w: W - 1.6, h: 0.35,
      fontSize: 11, fontFace: FONT, color: C.text,
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 9 — CUSTOM SECTION
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    s.addShape("rect", { x: 0.8, y: 0.4, w: 1.5, h: 0.035, fill: { color: C.accent } });
    s.addText("{{custom_section_title}}", {
      x: 0.8, y: 0.55, w: W - 1.6, h: 0.7,
      fontSize: 28, fontFace: FONT, bold: true, color: C.white, margin: 0,
    });

    s.addShape("rect", {
      x: 0.8, y: 1.5, w: W - 1.6, h: 5.0,
      fill: { color: C.bgCard }, shadow: shadow(),
    });
    s.addText("{{custom_section_text}}", {
      x: 1.1, y: 1.7, w: W - 2.2, h: 4.5,
      fontSize: 13, fontFace: FONT, color: C.text,
      lineSpacingMultiple: 1.4, valign: "top",
    });

    addFooter(s, 9);
  }

  await pres.writeFile({ fileName: OUT });
  console.log("dark_executive.pptx created:", OUT);
}

build().catch(console.error);
