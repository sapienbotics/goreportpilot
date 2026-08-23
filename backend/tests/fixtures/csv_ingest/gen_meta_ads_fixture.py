"""
Generate a Meta Ads Manager export fixture, and the true aggregates for it.

Column names follow Meta's own export, not a guess. They were recovered from
R-mangled headers in a real-world Facebook-ads dataset (RickPack/FBadstats,
whose `make.names()` output preserves the originals: AMOUNT.SPENT..USD. is
"Amount spent (USD)", CTR..LINK.CLICK.THROUGH.RATE. is "CTR (link
click-through rate)", RESULT.INDICATOR is "Result indicator") cross-checked
against Meta's documented Ads Manager column set. Capitalisation follows
Meta's sentence case as shown in the Ads Manager UI, which the export mirrors.

The quirks below are the point of the fixture — each is something a naive
parser gets wrong:

  * currency lives in the HEADER, "Amount spent (USD)", not in the cells
  * a date PAIR, "Reporting starts" / "Reporting ends", both valid dates
  * CTR is a bare decimal fraction, 0.0047 meaning 0.47% — no % sign
  * conversions are called "Results", with a separate "Result indicator"
    naming what a result actually was
  * unavailable cells are an em-dash, not blank and not zero
  * campaign / ad set / ad hierarchy, so the entity column is ambiguous

Run:  python tests/fixtures/csv_ingest/gen_meta_ads_fixture.py
"""
from __future__ import annotations

import csv
import os
import random
from datetime import date, timedelta

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meta_ads_export_july2026.csv")

HEADER = [
    "Reporting starts",
    "Reporting ends",
    "Campaign name",
    "Ad set name",
    "Ad name",
    "Delivery",
    "Result indicator",
    "Results",
    "Reach",
    "Impressions",
    "Frequency",
    "Amount spent (USD)",
    "Link clicks",
    "CTR (link click-through rate)",
    "CPC (cost per link click) (USD)",
    "CPM (cost per 1,000 impressions) (USD)",
    "Cost per result (USD)",
    "Post reactions",
    "Post comments",
    "Post shares",
]

EM_DASH = "—"

# (campaign, ad set, ad, result indicator, base impressions/day, ctr, cpm,
#  results-per-click, daily growth factor)
CAMPAIGNS = [
    ("Prospecting | Broad | US", "Broad 25-54 | US", "Carousel — Spring Offer",
     "actions:offsite_conversion.fb_pixel_purchase", 82_000, 0.0091, 7.40, 0.031, 1.0075),
    ("Retargeting | Site Visitors 30d", "Site Visitors 30d", "Single Image — Reminder",
     "actions:offsite_conversion.fb_pixel_purchase", 14_500, 0.0412, 12.80, 0.086, 1.0020),
    ("Lookalike 1% | Purchasers", "LAL 1% Purchasers | US", "Video — Testimonial",
     "actions:offsite_conversion.fb_pixel_purchase", 37_000, 0.0164, 9.15, 0.048, 1.0135),
    ("Video Views | Awareness", "Interest: Home Decor", "Video — Brand Story",
     "actions:video_view", 118_000, 0.0047, 4.20, 0.004, 0.9945),
]

# Days the awareness campaign was paused — a real export writes an em-dash
# across the metric columns for a day with no delivery, not zeros.
PAUSED = {date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 27)}


def build() -> tuple[list[list[str]], dict]:
    rng = random.Random(20260701)
    rows: list[list[str]] = []
    totals = {
        "impressions": 0, "link_clicks": 0, "results": 0, "reach": 0,
        "spend": 0.0, "paused_rows": 0, "em_dash_cells": 0,
    }

    start = date(2026, 7, 1)
    for offset in range(31):
        day = start + timedelta(days=offset)
        weekend = day.weekday() >= 5

        for (campaign, adset, ad, indicator, base_impr, ctr, cpm,
             result_rate, growth) in CAMPAIGNS:

            if campaign.startswith("Video Views") and day in PAUSED:
                # Paused day: delivery off, every metric unavailable.
                rows.append([
                    day.isoformat(), day.isoformat(), campaign, adset, ad,
                    "inactive", indicator,
                    EM_DASH, EM_DASH, EM_DASH, EM_DASH, EM_DASH, EM_DASH,
                    EM_DASH, EM_DASH, EM_DASH, EM_DASH, EM_DASH, EM_DASH, EM_DASH,
                ])
                totals["paused_rows"] += 1
                totals["em_dash_cells"] += 13
                continue

            trend = growth ** offset
            season = 0.58 if weekend else 1.0
            jitter = rng.uniform(0.94, 1.06)

            impressions = int(base_impr * trend * season * jitter)
            # Reach is always below impressions; frequency follows from the two.
            reach = int(impressions / rng.uniform(1.18, 1.52))
            link_clicks = max(1, round(impressions * ctr * rng.uniform(0.93, 1.07)))
            spend = round(impressions / 1000 * cpm * rng.uniform(0.96, 1.04), 2)
            results = round(link_clicks * result_rate * rng.uniform(0.85, 1.15))

            # Every derived column is computed from the raw three, so the file
            # is internally consistent — a reader recomputing CPC from spend
            # and clicks gets exactly the printed CPC.
            actual_ctr = round(link_clicks / impressions, 6)
            cpc = round(spend / link_clicks, 2)
            actual_cpm = round(spend / impressions * 1000, 2)
            frequency = round(impressions / reach, 2)
            cost_per_result = round(spend / results, 2) if results else EM_DASH
            if results == 0:
                totals["em_dash_cells"] += 1

            rows.append([
                day.isoformat(), day.isoformat(), campaign, adset, ad,
                "active", indicator,
                str(results), str(reach), str(impressions), f"{frequency:.2f}",
                f"{spend:.2f}", str(link_clicks), f"{actual_ctr:.6f}",
                f"{cpc:.2f}", f"{actual_cpm:.2f}",
                cost_per_result if cost_per_result == EM_DASH else f"{cost_per_result:.2f}",
                str(round(link_clicks * rng.uniform(0.18, 0.34))),
                str(round(link_clicks * rng.uniform(0.01, 0.05))),
                str(round(link_clicks * rng.uniform(0.02, 0.07))),
            ])

            totals["impressions"] += impressions
            totals["link_clicks"] += link_clicks
            totals["results"] += results
            totals["reach"] += reach
            totals["spend"] = round(totals["spend"] + spend, 2)

    return rows, totals


def main() -> None:
    rows, totals = build()
    with open(OUT, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(rows)

    impressions = totals["impressions"]
    clicks = totals["link_clicks"]
    results = totals["results"]
    spend = totals["spend"]
    reach = totals["reach"]

    print(f"wrote {OUT}")
    print(f"rows: {len(rows)}  columns: {len(HEADER)}")
    print(f"paused rows (all em-dash): {totals['paused_rows']}")
    print(f"em-dash cells total: {totals['em_dash_cells']}")
    print()
    print("TRUE AGGREGATES (whole period, 2026-07-01..2026-07-31)")
    print(f"  Impressions          {impressions:,}")
    print(f"  Link clicks          {clicks:,}")
    print(f"  Results              {results:,}")
    print(f"  Reach (summed)       {reach:,}")
    print(f"  Amount spent (USD)   {spend:,.2f}")
    print(f"  CTR                  {clicks / impressions * 100:.4f}%  "
          f"(as a fraction: {clicks / impressions:.6f})")
    print(f"  CPC                  {spend / clicks:.4f}")
    print(f"  CPM                  {spend / impressions * 1000:.4f}")
    print(f"  Cost per result      {spend / results:.4f}")
    print(f"  Frequency            {impressions / reach:.4f}")


if __name__ == "__main__":
    main()
