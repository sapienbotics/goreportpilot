/**
 * ReportPilot — "Bold Geometric" PPTX template
 * Strong visual impact — angled shapes, bold color blocks, pitch-deck energy.
 *
 * Background: white
 * Accent: #4338CA (deep indigo) — used at full strength for headers
 * Cards: white with thick left borders (4px)
 * Cover: full-bleed brand color, diagonal accent, white text
 * Feel: Like a VC pitch deck — confident, bold, memorable
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

// Helper: two-chart layout with narrative (header band takes y=0..1.3, charts start at 1.6)
function addTwoChartSlide(pres, titleText, chartL, chartR, narrativePlaceholder, footerNum) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addSectionHeader(s, titleText);

  s.addShape("roundRect", { x: 0.8, y: 1.6, w: 5.6, h: 3.0, fill: { color: C.card }, shadow: shadow(), rectRadius: 0.1 });
  s.addText(chartL, {
    x: 0.8, y: 1.6, w: 5.6, h: 3.0,
    fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
  });

  s.addShape("roundRect", { x: 6.8, y: 1.6, w: 5.7, h: 3.0, fill: { color: C.card }, shadow: shadow(), rectRadius: 0.1 });
  s.addText(chartR, {
    x: 6.8, y: 1.6, w: 5.7, h: 3.0,
    fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
  });

  s.addText(narrativePlaceholder, {
    x: 0.8, y: 4.9, w: W - 1.6, h: 1.9,
    fontSize: 12, fontFace: FONT_BODY, color: C.text,
    lineSpacingMultiple: 1.35, valign: "top",
  });

  addFooter(s, footerNum);
  return s;
}

// Helper: full-width chart with narrative below (header at y=0..1.3, chart at y=1.6)
function addFullChartSlide(pres, titleText, chartPlaceholder, narrativePlaceholder, footerNum) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addSectionHeader(s, titleText);

  s.addShape("roundRect", { x: 0.8, y: 1.6, w: W - 1.6, h: 4.0, fill: { color: C.card }, shadow: shadow(), rectRadius: 0.1 });
  s.addText(chartPlaceholder, {
    x: 0.8, y: 1.6, w: W - 1.6, h: 4.0,
    fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
  });

  s.addText(narrativePlaceholder, {
    x: 0.8, y: 5.9, w: W - 1.6, h: 1.2,
    fontSize: 12, fontFace: FONT_BODY, color: C.text,
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
  // SLIDE 0 (index 0) — COVER (full-bleed brand color)
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
  // SLIDE 1 (index 1) — EXECUTIVE SUMMARY
  // Footer page: 2
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
  // SLIDE 2 (index 2) — KPI SCORECARD (thick left-border cards)
  // Footer page: 3
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bgSoft };
    addSectionHeader(s, "Key Performance Indicators");

    const cardW = 3.5, cardH = 2.2;
    const gapX = 0.35, gapY = 0.35;
    const startX = 0.8, startY = 1.65;

    for (let i = 0; i < 6; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const cx = startX + col * (cardW + gapX);
      const cy = startY + row * (cardH + gapY);

      // Card bg
      s.addShape("rect", {
        x: cx, y: cy, w: cardW, h: cardH,
        fill: { color: C.card }, shadow: shadow(),
      });

      // Thick left accent border
      s.addShape("rect", {
        x: cx, y: cy, w: 0.08, h: cardH,
        fill: { color: C.accent },
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
  // SLIDE 3 (index 3) — WEBSITE TRAFFIC
  // Footer page: 4
  // ══════════════════════════════════════════════════════════════════════════
  addTwoChartSlide(
    pres, "Website Performance",
    "{{chart_sessions}}", "{{chart_traffic}}",
    "{{website_narrative}}", 4
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 4 (index 4) — WEBSITE ENGAGEMENT
  // Footer page: 5
  // ══════════════════════════════════════════════════════════════════════════
  addTwoChartSlide(
    pres, "Website Engagement",
    "{{chart_device_breakdown}}", "{{chart_top_pages}}",
    "{{engagement_narrative}}", 5
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 5 (index 5) — WEBSITE AUDIENCE
  // Footer page: 6
  // ══════════════════════════════════════════════════════════════════════════
  addTwoChartSlide(
    pres, "Audience Insights",
    "{{chart_new_vs_returning}}", "{{chart_top_countries}}",
    "{{website_narrative}}", 6
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 6 (index 6) — BOUNCE RATE ANALYSIS
  // Footer page: 7
  // ══════════════════════════════════════════════════════════════════════════
  addFullChartSlide(
    pres, "Bounce Rate Analysis",
    "{{chart_bounce_rate}}", "{{website_narrative}}", 7
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 7 (index 7) — META ADS OVERVIEW
  // Footer page: 8
  // ══════════════════════════════════════════════════════════════════════════
  addTwoChartSlide(
    pres, "Paid Advertising \u2014 Meta Ads",
    "{{chart_spend}}", "{{chart_campaigns}}",
    "{{ads_narrative}}", 8
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 8 (index 8) — META ADS AUDIENCE
  // Footer page: 9
  // ══════════════════════════════════════════════════════════════════════════
  addTwoChartSlide(
    pres, "Meta Ads \u2014 Audience",
    "{{chart_demographics}}", "{{chart_placements}}",
    "{{ads_narrative}}", 9
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 9 (index 9) — META ADS CREATIVE
  // Footer page: 10
  // ══════════════════════════════════════════════════════════════════════════
  addFullChartSlide(
    pres, "Meta Ads \u2014 Top Ads",
    "{{chart_campaigns}}", "{{ads_narrative}}", 10
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 10 (index 10) — GOOGLE ADS OVERVIEW
  // Footer page: 11
  // ══════════════════════════════════════════════════════════════════════════
  addTwoChartSlide(
    pres, "Search Advertising \u2014 Google Ads",
    "{{chart_gads_spend}}", "{{chart_gads_campaigns}}",
    "{{google_ads_narrative}}", 11
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 11 (index 11) — GOOGLE ADS KEYWORDS
  // Footer page: 12
  // ══════════════════════════════════════════════════════════════════════════
  addFullChartSlide(
    pres, "Search Terms Performance",
    "{{chart_search_terms}}", "{{google_ads_narrative}}", 12
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 12 (index 12) — SEO OVERVIEW
  // Footer page: 13
  // ══════════════════════════════════════════════════════════════════════════
  addTwoChartSlide(
    pres, "Organic Search \u2014 SEO",
    "{{chart_seo_trend}}", "{{chart_top_queries}}",
    "{{seo_narrative}}", 13
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 13 (index 13) — CSV DATA
  // Footer page: 14
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addSectionHeader(s, "{{csv_source_name}}");

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
    const csvRowY = [1.6, 2.5, 3.4];
    const csvColX = [0.8, 7.2];
    const csvKpiW = 5.5;
    const csvKpiH = 0.75;

    csvKpis.forEach((kpi) => {
      const x = csvColX[kpi.col];
      const y = csvRowY[kpi.row];

      s.addShape("roundRect", {
        x, y, w: csvKpiW, h: csvKpiH,
        fill: { color: C.card }, shadow: shadow(), rectRadius: 0.1,
      });
      s.addShape("rect", {
        x, y, w: 0.08, h: csvKpiH,
        fill: { color: C.accent },
      });
      s.addText(kpi.label, {
        x: x + 0.22, y: y + 0.05, w: csvKpiW - 0.32, h: 0.25,
        fontSize: 9, fontFace: FONT, bold: true, color: C.muted, charSpacing: 1,
      });
      s.addText(kpi.value, {
        x: x + 0.22, y: y + 0.3, w: csvKpiW - 0.32, h: 0.38,
        fontSize: 20, fontFace: FONT, bold: true, color: C.dark,
      });
    });

    // Full-width chart below the KPI grid
    s.addShape("roundRect", { x: 0.8, y: 4.1, w: W - 1.6, h: 2.5, fill: { color: C.card }, shadow: shadow(), rectRadius: 0.1 });
    s.addText("{{chart_csv_data}}", {
      x: 0.8, y: 4.1, w: W - 1.6, h: 2.5,
      fontSize: 10, fontFace: FONT, color: C.light, align: "center", valign: "middle",
    });

    addFooter(s, 14);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 14 (index 14) — CONVERSION FUNNEL
  // Footer page: 15
  // ══════════════════════════════════════════════════════════════════════════
  addFullChartSlide(
    pres, "Conversion Funnel",
    "{{chart_conversion_funnel}}", "{{website_narrative}}", 15
  );

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 15 (index 15) — KEY WINS (green header)
  // Footer page: 16
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

    addFooter(s, 16);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 16 (index 16) — CONCERNS (amber header)
  // Footer page: 17
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

    addFooter(s, 17);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 17 (index 17) — NEXT STEPS
  // Footer page: 18
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

    // CTA band — indigo with darker triangle
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
  // SLIDE 18 (index 18) — CUSTOM SECTION
  // Footer page: 19
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

    addFooter(s, 19);
  }

  await pres.writeFile({ fileName: OUT });
  console.log("bold_geometric.pptx created:", OUT);
}

build().catch(console.error);
