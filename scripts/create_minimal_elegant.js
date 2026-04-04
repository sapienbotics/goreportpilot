/**
 * ReportPilot — "Minimal Elegant" PPTX template (19 slides)
 * Ultra-minimal, whitespace-heavy, Apple-like restraint.
 *
 * Background: pure white
 * Accent: single thin line (#0F172A)
 * Text: Georgia for titles (serif elegance), Calibri for body
 * KPI cards: no fill, just numbers with thin bottom border
 * Cover: centered client name — very Apple
 * Content takes up only ~55% of each slide — rest is breathing room
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

// ── Helpers ───────────────────────────────────────────────────────────────────

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

// Two-chart layout helpers (no card bg, just placeholder text)
function addChartLeft(slide, placeholder) {
  slide.addText(placeholder, {
    x: 0.8, y: 1.6, w: 5.6, h: 3.0,
    fontSize: 10, fontFace: FONT_BODY, color: C.light, align: "center", valign: "middle",
  });
}

function addChartRight(slide, placeholder) {
  slide.addText(placeholder, {
    x: 6.8, y: 1.6, w: 5.7, h: 3.0,
    fontSize: 10, fontFace: FONT_BODY, color: C.light, align: "center", valign: "middle",
  });
}

function addNarrativeTwoChart(slide, placeholder) {
  slide.addText(placeholder, {
    x: 1.5, y: 4.9, w: W - 3.0, h: 1.9,
    fontSize: 12, fontFace: FONT_BODY, color: C.text,
    lineSpacingMultiple: 1.4, valign: "top",
  });
}

function addChartFull(slide, placeholder) {
  slide.addText(placeholder, {
    x: 1.5, y: 1.6, w: W - 3.0, h: 4.0,
    fontSize: 10, fontFace: FONT_BODY, color: C.light, align: "center", valign: "middle",
  });
}

function addNarrativeFull(slide, placeholder) {
  slide.addText(placeholder, {
    x: 1.5, y: 5.9, w: W - 3.0, h: 1.2,
    fontSize: 12, fontFace: FONT_BODY, color: C.text,
    lineSpacingMultiple: 1.4, valign: "top",
  });
}

// ── Build ─────────────────────────────────────────────────────────────────────
async function build() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = "ReportPilot";
  pres.title  = "Performance Report";

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 0 — COVER (centered, minimal)
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
  // SLIDE 1 — EXECUTIVE SUMMARY
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
  // SLIDE 2 — KPI SCORECARD (borderless, numbers-only)
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
    s.background = { color: C.bg };

    // Dynamic title from CSV source name
    s.addText("{{csv_source_name}}", {
      x: 1.5, y: 0.6, w: W - 3.0, h: 0.7,
      fontSize: 26, fontFace: FONT_TITLE, bold: false, color: C.dark, margin: 0,
    });
    s.addShape("rect", { x: 1.5, y: 1.35, w: 2.0, h: 0.015, fill: { color: C.dark } });

    // 6 KPI label+value pairs in a 2-column grid
    const kpiW = 4.5, kpiH = 0.55;
    const colX = [1.5, 6.4];
    const startY = 1.55;

    for (let i = 0; i < 6; i++) {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const cx  = colX[col];
      const cy  = startY + row * (kpiH + 0.12);

      s.addText(`{{csv_kpi_${i}_label}}`, {
        x: cx, y: cy, w: 2.0, h: kpiH,
        fontSize: 9, fontFace: FONT_BODY, bold: true, color: C.light,
        charSpacing: 1, valign: "middle",
      });
      s.addText(`{{csv_kpi_${i}_value}}`, {
        x: cx + 2.1, y: cy, w: kpiW - 2.1, h: kpiH,
        fontSize: 18, fontFace: FONT_BODY, bold: true, color: C.dark, valign: "middle",
      });
      // Thin separator line
      s.addShape("rect", {
        x: cx, y: cy + kpiH + 0.05, w: kpiW, h: 0.008,
        fill: { color: C.border },
      });
    }

    // Full-width chart
    s.addText("{{chart_csv_data}}", {
      x: 1.5, y: 3.65, w: W - 3.0, h: 2.85,
      fontSize: 10, fontFace: FONT_BODY, color: C.light, align: "center", valign: "middle",
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

    addFooter(s, 16);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 16 — CONCERNS
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

    addFooter(s, 17);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 17 — NEXT STEPS
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

    // Minimal CTA — just a horizontal line + text, no colour band
    s.addShape("rect", { x: 1.5, y: H - 1.3, w: W - 3.0, h: 0.01, fill: { color: C.dark } });
    s.addText("Questions? {{agency_name}}  \u2022  {{agency_email}}", {
      x: 1.5, y: H - 1.1, w: W - 3.0, h: 0.35,
      fontSize: 11, fontFace: FONT_BODY, color: C.muted, align: "center",
    });

    addFooter(s, 18);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 18 — CUSTOM SECTION
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

    addFooter(s, 19);
  }

  await pres.writeFile({ fileName: OUT });
  console.log("minimal_elegant.pptx created:", OUT);
}

build().catch(console.error);
