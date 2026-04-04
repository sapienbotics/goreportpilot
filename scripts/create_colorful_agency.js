/**
 * ReportPilot — "Colorful Agency" PPTX template
 * Vibrant, modern, creative — Stripe/Linear-style SaaS aesthetic.
 *
 * Background: white
 * Accents: coral (#F97316), purple (#8B5CF6), teal (#14B8A6)
 * Cards: white with colorful left accent bars
 * Feel: Bold color blocks, playful but professional
 *
 * 19 slides (indices 0-18):
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

// Helper: two-chart layout with narrative
function addTwoChartSlide(pres, accentColor, titleText, chartL, chartR, narrativePlaceholder, footerNum) {
  const s = pres.addSlide();
  s.background = { color: C.bgSoft };
  s.addShape("rect", { x: 0, y: 0, w: 0.06, h: H, fill: { color: accentColor } });
  addTitle(s, titleText);

  s.addShape("rect", { x: 0.8, y: 1.5, w: 5.6, h: 3.0, fill: { color: C.card }, shadow: shadow() });
  s.addText(chartL, {
    x: 0.8, y: 1.5, w: 5.6, h: 3.0,
    fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
  });

  s.addShape("rect", { x: 6.8, y: 1.5, w: 5.7, h: 3.0, fill: { color: C.card }, shadow: shadow() });
  s.addText(chartR, {
    x: 6.8, y: 1.5, w: 5.7, h: 3.0,
    fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
  });

  s.addText(narrativePlaceholder, {
    x: 0.8, y: 4.8, w: W - 1.6, h: 2.0,
    fontSize: 12, fontFace: FONT, color: C.text,
    lineSpacingMultiple: 1.35, valign: "top",
  });

  addFooter(s, footerNum);
  return s;
}

// Helper: full-width chart with narrative below
function addFullChartSlide(pres, accentColor, titleText, chartPlaceholder, narrativePlaceholder, footerNum) {
  const s = pres.addSlide();
  s.background = { color: C.bgSoft };
  s.addShape("rect", { x: 0, y: 0, w: 0.06, h: H, fill: { color: accentColor } });
  addTitle(s, titleText);

  s.addShape("rect", { x: 0.8, y: 1.5, w: 11.7, h: 4.0, fill: { color: C.card }, shadow: shadow() });
  s.addText(chartPlaceholder, {
    x: 0.8, y: 1.5, w: 11.7, h: 4.0,
    fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
  });

  s.addText(narrativePlaceholder, {
    x: 0.8, y: 5.75, w: W - 1.6, h: 1.2,
    fontSize: 12, fontFace: FONT, color: C.text,
    lineSpacingMultiple: 1.35, valign: "top",
  });

  addFooter(s, footerNum);
  return s;
}

async function build() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = "ReportPilot";
  pres.title  = "Performance Report";

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 0 (index 0) — COVER
  // Footer page: (no footer on cover)
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
  // SLIDE 1 (index 1) — EXECUTIVE SUMMARY
  // Footer page: 2
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
  // SLIDE 2 (index 2) — KPI SCORECARD
  // Footer page: 3
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
  // SLIDE 3 (index 3) — WEBSITE TRAFFIC
  // Footer page: 4
  // ══════════════════════════════════════════════════════════════════════════
  addTwoChartSlide(
    pres, C.coral, "Website Performance",
    "{{chart_sessions}}", "{{chart_traffic}}",
    "{{website_narrative}}", 4
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 4 (index 4) — WEBSITE ENGAGEMENT
  // Footer page: 5
  // ══════════════════════════════════════════════════════════════════════════
  addTwoChartSlide(
    pres, C.coral, "Website Engagement",
    "{{chart_device_breakdown}}", "{{chart_top_pages}}",
    "{{engagement_narrative}}", 5
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 5 (index 5) — WEBSITE AUDIENCE
  // Footer page: 6
  // ══════════════════════════════════════════════════════════════════════════
  addTwoChartSlide(
    pres, C.coral, "Audience Insights",
    "{{chart_new_vs_returning}}", "{{chart_top_countries}}",
    "{{website_narrative}}", 6
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 6 (index 6) — BOUNCE RATE ANALYSIS
  // Footer page: 7
  // ══════════════════════════════════════════════════════════════════════════
  addFullChartSlide(
    pres, C.coral, "Bounce Rate Analysis",
    "{{chart_bounce_rate}}", "{{website_narrative}}", 7
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 7 (index 7) — META ADS OVERVIEW
  // Footer page: 8
  // ══════════════════════════════════════════════════════════════════════════
  addTwoChartSlide(
    pres, C.purple, "Paid Advertising \u2014 Meta Ads",
    "{{chart_spend}}", "{{chart_campaigns}}",
    "{{ads_narrative}}", 8
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 8 (index 8) — META ADS AUDIENCE
  // Footer page: 9
  // ══════════════════════════════════════════════════════════════════════════
  addTwoChartSlide(
    pres, C.purple, "Meta Ads \u2014 Audience",
    "{{chart_demographics}}", "{{chart_placements}}",
    "{{ads_narrative}}", 9
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 9 (index 9) — META ADS CREATIVE
  // Footer page: 10
  // ══════════════════════════════════════════════════════════════════════════
  addFullChartSlide(
    pres, C.purple, "Meta Ads \u2014 Top Ads",
    "{{chart_campaigns}}", "{{ads_narrative}}", 10
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 10 (index 10) — GOOGLE ADS OVERVIEW
  // Footer page: 11
  // ══════════════════════════════════════════════════════════════════════════
  addTwoChartSlide(
    pres, C.teal, "Search Advertising \u2014 Google Ads",
    "{{chart_gads_spend}}", "{{chart_gads_campaigns}}",
    "{{google_ads_narrative}}", 11
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 11 (index 11) — GOOGLE ADS KEYWORDS
  // Footer page: 12
  // ══════════════════════════════════════════════════════════════════════════
  addFullChartSlide(
    pres, C.teal, "Search Terms Performance",
    "{{chart_search_terms}}", "{{google_ads_narrative}}", 12
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 12 (index 12) — SEO OVERVIEW
  // Footer page: 13
  // ══════════════════════════════════════════════════════════════════════════
  addTwoChartSlide(
    pres, C.coral, "Organic Search \u2014 SEO",
    "{{chart_seo_trend}}", "{{chart_top_queries}}",
    "{{seo_narrative}}", 13
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 13 (index 13) — CSV DATA
  // Footer page: 14
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bgSoft };
    s.addShape("rect", { x: 0, y: 0, w: 0.06, h: H, fill: { color: C.purple } });

    // Dynamic title from CSV source name
    addTitle(s, "{{csv_source_name}}");

    // 6 KPI label+value boxes in 2-column grid
    // Rows at y=1.6, 2.5, 3.4 — left col x=0.8, right col x=7.2 — each 5.5" wide
    const csvKpis = [
      { label: "{{csv_kpi_0_label}}", value: "{{csv_kpi_0_value}}", col: 0, row: 0 },
      { label: "{{csv_kpi_1_label}}", value: "{{csv_kpi_1_value}}", col: 1, row: 0 },
      { label: "{{csv_kpi_2_label}}", value: "{{csv_kpi_2_value}}", col: 0, row: 1 },
      { label: "{{csv_kpi_3_label}}", value: "{{csv_kpi_3_value}}", col: 1, row: 1 },
      { label: "{{csv_kpi_4_label}}", value: "{{csv_kpi_4_value}}", col: 0, row: 2 },
      { label: "{{csv_kpi_5_label}}", value: "{{csv_kpi_5_value}}", col: 1, row: 2 },
    ];
    const csvRowY  = [1.6, 2.5, 3.4];
    const csvColX  = [0.8, 7.2];
    const csvKpiW  = 5.5;
    const csvKpiH  = 0.75;
    const csvColors = [C.coral, C.purple, C.teal, C.coral, C.purple, C.teal];

    csvKpis.forEach((kpi, i) => {
      const x = csvColX[kpi.col];
      const y = csvRowY[kpi.row];

      s.addShape("rect", {
        x, y, w: csvKpiW, h: csvKpiH,
        fill: { color: C.card }, shadow: shadow(),
      });
      s.addShape("rect", {
        x, y, w: 0.07, h: csvKpiH,
        fill: { color: csvColors[i] },
      });
      s.addText(kpi.label, {
        x: x + 0.2, y: y + 0.05, w: csvKpiW - 0.3, h: 0.25,
        fontSize: 9, fontFace: FONT, bold: true, color: C.muted, charSpacing: 1,
      });
      s.addText(kpi.value, {
        x: x + 0.2, y: y + 0.3, w: csvKpiW - 0.3, h: 0.38,
        fontSize: 20, fontFace: FONT, bold: true, color: C.dark,
      });
    });

    // Full-width chart below
    s.addShape("rect", { x: 0.8, y: 4.1, w: 11.7, h: 2.5, fill: { color: C.card }, shadow: shadow() });
    s.addText("{{chart_csv_data}}", {
      x: 0.8, y: 4.1, w: 11.7, h: 2.5,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    addFooter(s, 14);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 14 (index 14) — CONVERSION FUNNEL
  // Footer page: 15
  // ══════════════════════════════════════════════════════════════════════════
  addFullChartSlide(
    pres, C.coral, "Conversion Funnel",
    "{{chart_conversion_funnel}}", "{{website_narrative}}", 15
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 15 (index 15) — KEY WINS (green theme)
  // Footer page: 16
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

    addFooter(s, 16);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 16 (index 16) — CONCERNS (amber theme)
  // Footer page: 17
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

    addFooter(s, 17);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 17 (index 17) — NEXT STEPS
  // Footer page: 18
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

    // CTA band — coral
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
  // SLIDE 18 (index 18) — CUSTOM SECTION
  // Footer page: 19
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

    addFooter(s, 19);
  }

  await pres.writeFile({ fileName: OUT });
  console.log("colorful_agency.pptx created:", OUT);
}

build().catch(console.error);
