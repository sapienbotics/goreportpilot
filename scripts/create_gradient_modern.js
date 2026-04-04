/**
 * ReportPilot — "Gradient Modern" PPTX template (19 slides)
 * Warm gradient accents — startup/SaaS aesthetic like Linear or Notion.
 *
 * Since pptxgenjs can't do true gradients, we simulate them:
 * - Cover: 3 overlapping semi-transparent coloured bars creating a gradient effect
 * - Accent elements: two thin bars side-by-side (coral + orange or blue + purple)
 * - Warm palette: coral (#F97316) fading to rose (#F43F5E)
 *
 * Background: white
 * Primary accent: coral → rose gradient (simulated)
 * Secondary: indigo highlights for KPI changes
 * Cards: white with warm-tinted subtle shadow
 * Feel: Modern SaaS — Notion, Linear, Vercel energy
 *
 * Slide index map:
 *  0  cover
 *  1  executive_summary
 *  2  kpi_scorecard
 *  3  website_traffic
 *  4  website_engagement
 *  5  website_audience
 *  6  bounce_rate_analysis
 *  7  meta_ads_overview
 *  8  meta_ads_audience
 *  9  meta_ads_creative
 * 10  google_ads_overview
 * 11  google_ads_keywords
 * 12  seo_overview
 * 13  csv_data
 * 14  conversion_funnel
 * 15  key_wins
 * 16  concerns
 * 17  next_steps
 * 18  custom_section
 */
const pptxgen = require("pptxgenjs");
const path    = require("path");

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
const shadow     = () => ({ type: "outer", blur: 5, offset: 2, angle: 135, color: "000000", opacity: 0.06 });

// ── Helpers ───────────────────────────────────────────────────────────────────

function addFooter(slide, pageNum) {
  slide.addText(`{{agency_name}}  \u2022  Confidential  \u2022  Page ${pageNum}`, {
    x: 0.8, y: H - 0.38, w: W - 1.6, h: 0.28,
    fontSize: 8, fontFace: FONT, color: C.light,
  });
}

function addGradientBar(slide) {
  // Simulate gradient: 3 thin bars side by side (coral → rose → purple)
  const barH = 0.06;
  slide.addShape("rect", { x: 0,        y: 0, w: W * 0.4,  h: barH, fill: { color: C.coral  } });
  slide.addShape("rect", { x: W * 0.4,  y: 0, w: W * 0.35, h: barH, fill: { color: C.rose   } });
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

// Two-chart layout helpers (white card fill with shadow)
function addChartLeft(slide, placeholder) {
  slide.addShape("rect", { x: 0.8, y: 1.4, w: 5.6, h: 3.0, fill: { color: C.card }, shadow: shadow() });
  slide.addText(placeholder, {
    x: 0.8, y: 1.4, w: 5.6, h: 3.0,
    fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
  });
}

function addChartRight(slide, placeholder) {
  slide.addShape("rect", { x: 6.8, y: 1.4, w: 5.7, h: 3.0, fill: { color: C.card }, shadow: shadow() });
  slide.addText(placeholder, {
    x: 6.8, y: 1.4, w: 5.7, h: 3.0,
    fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
  });
}

function addNarrativeTwoChart(slide, placeholder) {
  slide.addText(placeholder, {
    x: 0.8, y: 4.7, w: W - 1.6, h: 2.1,
    fontSize: 12, fontFace: FONT_BODY, color: C.text,
    lineSpacingMultiple: 1.35, valign: "top",
  });
}

function addChartFull(slide, placeholder) {
  slide.addShape("rect", { x: 0.8, y: 1.4, w: W - 1.6, h: 4.0, fill: { color: C.card }, shadow: shadow() });
  slide.addText(placeholder, {
    x: 0.8, y: 1.4, w: W - 1.6, h: 4.0,
    fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
  });
}

function addNarrativeFull(slide, placeholder) {
  slide.addText(placeholder, {
    x: 0.8, y: 5.7, w: W - 1.6, h: 1.2,
    fontSize: 12, fontFace: FONT_BODY, color: C.text,
    lineSpacingMultiple: 1.35, valign: "top",
  });
}

// ── Build ─────────────────────────────────────────────────────────────────────
async function build() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = "ReportPilot";
  pres.title  = "Performance Report";

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 0 — COVER (warm gradient feel)
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // Simulated gradient header band (3 overlapping coloured rectangles)
    s.addShape("rect", { x: 0,        y: 0, w: W,        h: 2.6, fill: { color: C.coral  } });
    s.addShape("rect", { x: W * 0.3,  y: 0, w: W * 0.7,  h: 2.6, fill: { color: C.rose   } });
    s.addShape("rect", { x: W * 0.65, y: 0, w: W * 0.35, h: 2.6, fill: { color: C.purple } });

    // "PERFORMANCE REPORT" label in the gradient band
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
    s.addShape("rect", { x: 0,        y: H - 0.08, w: W * 0.4,  h: 0.08, fill: { color: C.coral  } });
    s.addShape("rect", { x: W * 0.4,  y: H - 0.08, w: W * 0.35, h: 0.08, fill: { color: C.rose   } });
    s.addShape("rect", { x: W * 0.75, y: H - 0.08, w: W * 0.25, h: 0.08, fill: { color: C.purple } });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 1 — EXECUTIVE SUMMARY
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
  // SLIDE 2 — KPI SCORECARD
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bgSoft };
    addTitle(s, "Key Performance Indicators");

    const cardW = 3.5, cardH = 2.2;
    const gapX = 0.35, gapY = 0.35;
    const startX = 0.8, startY = 1.45;
    // Alternating warm accent colours for left borders
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
      s.addShape("rect", { x: cx,        y: cy, w: 0.04, h: cardH, fill: { color: accents[i] } });
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
  // SLIDE 3 — WEBSITE TRAFFIC
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Website Performance");

    addChartLeft(s, "{{chart_sessions}}");
    addChartRight(s, "{{chart_traffic}}");
    addNarrativeTwoChart(s, "{{website_narrative}}");

    addFooter(s, 4);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 4 — WEBSITE ENGAGEMENT
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Website Engagement");

    addChartLeft(s, "{{chart_device_breakdown}}");
    addChartRight(s, "{{chart_top_pages}}");
    addNarrativeTwoChart(s, "{{engagement_narrative}}");

    addFooter(s, 5);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 5 — WEBSITE AUDIENCE
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Audience Insights");

    addChartLeft(s, "{{chart_new_vs_returning}}");
    addChartRight(s, "{{chart_top_countries}}");
    addNarrativeTwoChart(s, "{{website_narrative}}");

    addFooter(s, 6);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 6 — BOUNCE RATE ANALYSIS
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Bounce Rate Analysis");

    addChartFull(s, "{{chart_bounce_rate}}");
    addNarrativeFull(s, "{{website_narrative}}");

    addFooter(s, 7);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 7 — META ADS OVERVIEW
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Paid Advertising \u2014 Meta Ads");

    addChartLeft(s, "{{chart_spend}}");
    addChartRight(s, "{{chart_campaigns}}");
    addNarrativeTwoChart(s, "{{ads_narrative}}");

    addFooter(s, 8);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 8 — META ADS AUDIENCE
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Meta Ads \u2014 Audience");

    addChartLeft(s, "{{chart_demographics}}");
    addChartRight(s, "{{chart_placements}}");
    addNarrativeTwoChart(s, "{{ads_narrative}}");

    addFooter(s, 9);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 9 — META ADS CREATIVE
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Meta Ads \u2014 Top Ads");

    addChartFull(s, "{{chart_campaigns}}");
    addNarrativeFull(s, "{{ads_narrative}}");

    addFooter(s, 10);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 10 — GOOGLE ADS OVERVIEW
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Search Advertising \u2014 Google Ads");

    addChartLeft(s, "{{chart_gads_spend}}");
    addChartRight(s, "{{chart_gads_campaigns}}");
    addNarrativeTwoChart(s, "{{google_ads_narrative}}");

    addFooter(s, 11);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 11 — GOOGLE ADS KEYWORDS
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Search Terms Performance");

    addChartFull(s, "{{chart_search_terms}}");
    addNarrativeFull(s, "{{google_ads_narrative}}");

    addFooter(s, 12);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 12 — SEO OVERVIEW
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Organic Search \u2014 SEO");

    addChartLeft(s, "{{chart_seo_trend}}");
    addChartRight(s, "{{chart_top_queries}}");
    addNarrativeTwoChart(s, "{{seo_narrative}}");

    addFooter(s, 13);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 13 — CSV DATA
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bgSoft };
    addTitle(s, "{{csv_source_name}}");

    // 6 KPI label+value pairs in a 2-column grid
    const kpiW = 5.4, kpiH = 0.55;
    const colX = [0.8, 7.0];
    const startY = 1.5;

    for (let i = 0; i < 6; i++) {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const cx  = colX[col];
      const cy  = startY + row * (kpiH + 0.14);

      // KPI card (white bg with warm shadow)
      s.addShape("rect", { x: cx, y: cy, w: kpiW, h: kpiH, fill: { color: C.card }, shadow: warmShadow() });

      // Gradient left border (two thin bars)
      const accent = [C.coral, C.rose, C.purple][i % 3];
      const accentNext = [C.coral, C.rose, C.purple][(i + 1) % 3];
      s.addShape("rect", { x: cx,        y: cy, w: 0.04, h: kpiH, fill: { color: accent     } });
      s.addShape("rect", { x: cx + 0.04, y: cy, w: 0.03, h: kpiH, fill: { color: accentNext } });

      s.addText(`{{csv_kpi_${i}_label}}`, {
        x: cx + 0.2, y: cy + 0.05, w: 2.2, h: kpiH - 0.1,
        fontSize: 9, fontFace: FONT, bold: true, color: C.muted,
        charSpacing: 1, valign: "middle",
      });
      s.addText(`{{csv_kpi_${i}_value}}`, {
        x: cx + 2.5, y: cy + 0.05, w: kpiW - 2.7, h: kpiH - 0.1,
        fontSize: 18, fontFace: FONT, bold: true, color: C.dark, valign: "middle",
      });
    }

    // Full-width chart card
    s.addShape("rect", { x: 0.8, y: 3.65, w: W - 1.6, h: 2.85, fill: { color: C.card }, shadow: shadow() });
    s.addText("{{chart_csv_data}}", {
      x: 0.8, y: 3.65, w: W - 1.6, h: 2.85,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    addFooter(s, 14);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 14 — CONVERSION FUNNEL
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Conversion Funnel");

    addChartFull(s, "{{chart_conversion_funnel}}");
    addNarrativeFull(s, "{{website_narrative}}");

    addFooter(s, 15);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 15 — KEY WINS
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // Green top bar
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

    addFooter(s, 16);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 16 — CONCERNS
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // Amber top bar
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

    addFooter(s, 17);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 17 — NEXT STEPS
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

    // Gradient CTA band at bottom (coral / rose / purple, each ~1.2" tall)
    s.addShape("rect", { x: 0,        y: H - 1.2, w: W * 0.4,  h: 1.2, fill: { color: C.coral  } });
    s.addShape("rect", { x: W * 0.4,  y: H - 1.2, w: W * 0.35, h: 1.2, fill: { color: C.rose   } });
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
  // SLIDE 18 — CUSTOM SECTION
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

    addFooter(s, 19);
  }

  await pres.writeFile({ fileName: OUT });
  console.log("gradient_modern.pptx created:", OUT);
}

build().catch(console.error);
