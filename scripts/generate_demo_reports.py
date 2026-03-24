"""
Generate demo reports for all 6 visual templates using rich demo data.
Run: python scripts/generate_demo_reports.py
"""
import sys
import os

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.demo_data import DEMO_CLIENT, DEMO_DATA, DEMO_NARRATIVE
from services.chart_generator import generate_all_charts
from services.report_generator import generate_pptx_report, VISUAL_TEMPLATES

import tempfile


def main():
    # Output directory
    out_dir = os.path.join(os.path.dirname(__file__), "..", "demo_reports")
    os.makedirs(out_dir, exist_ok=True)

    # Generate charts once (shared across all templates)
    chart_dir = tempfile.mkdtemp()
    charts = generate_all_charts(DEMO_DATA, chart_dir)
    print(f"Generated {len(charts)} charts: {list(charts.keys())}")

    # Generate a report for each visual template
    templates = list(VISUAL_TEMPLATES.keys())
    print(f"\nGenerating reports for {len(templates)} templates...")

    for vt in templates:
        try:
            pptx_bytes = generate_pptx_report(
                data=DEMO_DATA,
                narrative=DEMO_NARRATIVE,
                charts=charts,
                client_info=DEMO_CLIENT,
                visual_template=vt,
            )
            filename = f"TechVista_March_2026_{vt}.pptx"
            filepath = os.path.join(out_dir, filename)
            with open(filepath, "wb") as f:
                f.write(pptx_bytes)
            print(f"  \u2713 {filename} ({len(pptx_bytes):,} bytes)")
        except Exception as exc:
            print(f"  \u2717 {vt} FAILED: {exc}")
            import traceback
            traceback.print_exc()

    print(f"\nAll demo reports saved to: {os.path.abspath(out_dir)}")


if __name__ == "__main__":
    main()
