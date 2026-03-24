"""
Generate demo reports for all data combinations and visual templates.
Produces a comprehensive set of demo reports for showcase purposes.

Usage:
    python scripts/generate_demo_reports.py
"""
import sys
import os
import tempfile

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.demo_data import (
    DEMO_DATA, DEMO_CLIENT, DEMO_NARRATIVE,
    demo_full, demo_ga4_only, demo_ga4_meta,
)
from services.chart_generator import generate_all_charts
from services.report_generator import generate_pptx_report, VISUAL_TEMPLATES

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "demo_reports")


def _generate_report(
    data: dict,
    narrative: dict,
    template: str,
    visual_template: str,
    filename: str,
):
    """Generate one report and save it."""
    charts_dir = tempfile.mkdtemp()
    charts = generate_all_charts(
        data, charts_dir,
        brand_color="#4338CA",
        visual_template=visual_template,
    )

    pptx_bytes = generate_pptx_report(
        data=data,
        narrative=narrative,
        charts=charts,
        client_info=DEMO_CLIENT,
        template=template,
        visual_template=visual_template,
    )

    outpath = os.path.join(OUTPUT_DIR, filename)
    with open(outpath, "wb") as f:
        f.write(pptx_bytes)

    print(f"  {filename}: {len(pptx_bytes) // 1024}KB ({len(charts)} charts)")
    return outpath


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("ReportPilot Demo Report Generator")
    print("=" * 60)

    # 1. Full data x all 6 visual templates
    print("\n1. Full Data (all 5 sources) x 6 templates:")
    full_data = demo_full()
    for vt in VISUAL_TEMPLATES:
        _generate_report(
            full_data, DEMO_NARRATIVE, "full", vt,
            f"TechVista_FULL_DATA_{vt}.pptx",
        )

    # 2. Data combinations (modern_clean only)
    print("\n2. Data Combinations (modern_clean):")

    ga4_data = demo_ga4_only()
    ga4_narrative = {k: v for k, v in DEMO_NARRATIVE.items()
                     if k not in ("paid_advertising", "google_ads_performance", "seo_performance")}
    _generate_report(
        ga4_data, ga4_narrative, "full", "modern_clean",
        "TechVista_GA4_ONLY_modern_clean.pptx",
    )

    gm_data = demo_ga4_meta()
    gm_narrative = {k: v for k, v in DEMO_NARRATIVE.items()
                    if k not in ("google_ads_performance", "seo_performance")}
    _generate_report(
        gm_data, gm_narrative, "full", "modern_clean",
        "TechVista_GA4_META_modern_clean.pptx",
    )

    # 3. Detail levels (full data, modern_clean)
    print("\n3. Detail Levels (full data, modern_clean):")
    _generate_report(
        full_data, DEMO_NARRATIVE, "summary", "modern_clean",
        "TechVista_SUMMARY_modern_clean.pptx",
    )
    _generate_report(
        full_data, DEMO_NARRATIVE, "brief", "modern_clean",
        "TechVista_BRIEF_modern_clean.pptx",
    )

    print("\n" + "=" * 60)
    total = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".pptx")])
    print(f"Done! {total} reports generated in {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
