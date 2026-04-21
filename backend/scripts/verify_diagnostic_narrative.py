"""
Phase 4 verification — Diagnostic AI Narrative v2.

What it does
------------
1. Constructs a realistic Videogenie-shaped fixture (video-marketing SaaS
   with Meta Ads + GA4 + Search Console data).
2. Runs ``compute_top_movers(fixture)`` and prints the extracted movers
   plus the formatted prompt block that will be injected.
3. Runs ``generate_narrative(fixture, ...)`` if ``OPENAI_API_KEY`` is set
   in the environment — otherwise skips the API call.
4. Prints the Phase 4 user prompt so you can eyeball the "TOP MOVERS"
   injection against the old aggregate-only format.

Run
---

    python backend/scripts/verify_diagnostic_narrative.py

Optional:
    OPENAI_API_KEY=sk-...  python backend/scripts/verify_diagnostic_narrative.py --live

``--live`` performs a real GPT-4.1 call and prints the generated JSON.
Without ``--live``, no API call is made and the script is a dry-run of
the prompt assembly.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from pprint import pformat

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


# ─── Fixture ──────────────────────────────────────────────────────────────────


def build_videogenie_fixture() -> dict:
    """
    Realistic shape for a small-to-mid video-content SaaS client.

    Totals chosen so the period-over-period movements are interesting:
      - Meta Ads spend grew 34% but conversions only +12% — CAC crept up
      - One campaign ("Q2 Product Launch") is clearly outperforming
      - GA4 sessions up 19%; organic search is the dominant source
      - Mobile traffic has a high bounce rate — actionable finding
      - SEO: one high-intent query dominates clicks but ranks only #4
    """
    return {
        "period_start": "2026-03-01",
        "period_end":   "2026-03-31",
        "ga4": {
            "summary": {
                "sessions":             48520,
                "sessions_change":      18.9,
                "prev_sessions":        40810,
                "users":                32104,
                "users_change":         15.2,
                "prev_users":           27862,
                "pageviews":            112840,
                "prev_pageviews":       95210,
                "conversions":          742,
                "conversions_change":   7.4,
                "prev_conversions":     691,
                "bounce_rate":          46.2,
                "prev_bounce_rate":     44.8,
                "avg_session_duration": 142,
            },
            "traffic_sources": {
                "Organic":  19810,
                "Direct":   12450,
                "Paid":      9820,
                "Referral":  4120,
                "Social":    2060,
                "Email":      260,
            },
            "top_pages": [
                {"page": "/pricing",        "pageviews": 18420, "sessions": 14210},
                {"page": "/",               "pageviews": 14650, "sessions": 12980},
                {"page": "/features/ai-video","pageviews": 9840, "sessions": 7610},
                {"page": "/blog/viral-hooks","pageviews": 6120, "sessions": 5280},
                {"page": "/signup",         "pageviews": 4890, "sessions": 4120},
                {"page": "/case-studies",   "pageviews": 3210, "sessions": 2640},
            ],
            "device_breakdown": [
                {"device": "Mobile",  "sessions": 30420, "users": 21340, "bounce_rate": 56.1},
                {"device": "Desktop", "sessions": 15780, "users":  9820, "bounce_rate": 31.4},
                {"device": "Tablet",  "sessions":  2320, "users":   944, "bounce_rate": 42.0},
            ],
            "daily": [],  # Not needed for movers
        },
        "meta_ads": {
            "currency": "USD",
            "summary": {
                "spend":                    12840.50,
                "prev_spend":                9580.20,
                "spend_change":             34.0,
                "impressions":             1820500,
                "prev_impressions":        1420300,
                "clicks":                    48210,
                "prev_clicks":               39820,
                "ctr":                       2.65,
                "prev_ctr":                  2.80,
                "cpc":                       0.27,
                "prev_cpc":                  0.24,
                "conversions":                 512,
                "prev_conversions":            458,
                "conversions_change":         11.8,
                "cost_per_conversion":        25.08,
                "prev_cost_per_conversion":   20.92,
                "roas":                       3.42,
                "prev_roas":                  3.85,
            },
            "campaigns": [
                # Star performer
                {"name": "Q2 Product Launch — AI Video",
                 "spend": 4120.00, "impressions": 510200, "clicks": 18420,
                 "conversions": 248, "cpc": 0.22, "roas": 5.41},
                # Budget hog, middling performance
                {"name": "Brand Awareness — Video Editors Broad",
                 "spend": 3680.50, "impressions": 720400, "clicks": 12840,
                 "conversions": 96,  "cpc": 0.29, "roas": 2.12},
                # Underperformer at real spend
                {"name": "Retargeting — Cart Abandoners",
                 "spend": 2410.00, "impressions": 128400, "clicks":  6420,
                 "conversions": 78,  "cpc": 0.38, "roas": 1.84},
                # Decent ROAS at moderate spend
                {"name": "Lookalike — Pro Users 3%",
                 "spend": 1890.00, "impressions": 342100, "clicks":  8210,
                 "conversions": 64,  "cpc": 0.23, "roas": 3.05},
                # Tiny test campaign — should NOT dominate rankings
                {"name": "Creative Test — UGC Vertical",
                 "spend":  740.00, "impressions":  98400, "clicks":  2320,
                 "conversions": 26,  "cpc": 0.32, "roas": 3.18},
            ],
            "daily": [],
        },
        "search_console": {
            "summary": {
                "clicks":            9840,
                "prev_clicks":       7620,
                "impressions":      218400,
                "prev_impressions": 184200,
                "ctr":                 4.5,
                "prev_ctr":            4.1,
                "avg_position":        8.2,
                "prev_avg_position":   9.1,
            },
            "top_queries": [
                {"query": "ai video generator for marketing",
                 "clicks": 1820, "impressions": 21400, "ctr": 8.5, "position": 4.2},
                {"query": "best video editor for startups",
                 "clicks": 1240, "impressions": 15300, "ctr": 8.1, "position": 3.8},
                {"query": "viral tiktok hooks",
                 "clicks":  920, "impressions": 28100, "ctr": 3.3, "position": 7.1},
                {"query": "videogenie pricing",
                 "clicks":  810, "impressions":  4200, "ctr": 19.3, "position": 1.4},
                {"query": "how to make short form video",
                 "clicks":  640, "impressions": 32400, "ctr": 2.0, "position": 11.4},
            ],
            "top_pages": [
                {"page": "/features/ai-video", "clicks": 2410,
                 "impressions": 38200, "ctr": 6.3},
                {"page": "/blog/viral-hooks", "clicks": 1840,
                 "impressions": 46100, "ctr": 4.0},
                {"page": "/pricing", "clicks": 1420,
                 "impressions":  8200, "ctr": 17.3},
            ],
        },
        "csv_sources": [],
    }


# ─── Drivers ──────────────────────────────────────────────────────────────────


def show_movers_block(fixture: dict) -> None:
    from services.top_movers import compute_top_movers, format_movers_for_prompt
    movers = compute_top_movers(fixture)
    print("=" * 72)
    print("STEP 1 — Structured top-movers (compute_top_movers output)")
    print("=" * 72)
    print(json.dumps(movers, indent=2))
    print()
    print("=" * 72)
    print("STEP 2 — Prompt-formatted movers block (what the AI sees)")
    print("=" * 72)
    print(format_movers_for_prompt(movers, currency_symbol="$"))
    print()


def show_prompt_diff(fixture: dict) -> None:
    """Build the v2 user prompt using the production path and print it."""
    # Import inside function so the module load path is right.
    from services import ai_narrative as ai_mod

    # Reuse the production prompt assembly by mocking OpenAI. We don't
    # call the API — we just want to see the string that would be sent.
    # Easiest: introspect the constants + build the same f-string.
    ga4       = fixture.get("ga4", {}).get("summary", {})
    meta      = fixture.get("meta_ads", {}).get("summary", {})
    campaigns = fixture.get("meta_ads", {}).get("campaigns", [])
    traffic_sources = fixture.get("ga4", {}).get("traffic_sources", [])
    currency_code = "USD"
    cur_sym = "$"

    from services.top_movers import compute_top_movers, format_movers_for_prompt
    _movers = compute_top_movers(fixture)
    _movers_block = format_movers_for_prompt(_movers, currency_symbol=cur_sym)

    sections = ["executive_summary", "website_performance", "paid_advertising",
                "engagement_analysis", "seo_performance",
                "key_wins", "concerns", "next_steps"]
    section_instructions = ai_mod._build_section_instructions(sections)

    google_ads = fixture.get("google_ads", {}).get("summary", {})
    search_console = fixture.get("search_console", {}).get("summary", {})
    csv_sources = fixture.get("csv_sources", [])

    user_prompt = f"""CLIENT CONTEXT:
Name: Videogenie
Goals: Grow MRR via AI video generation; focus on SMB video creators
Report Period: {fixture.get('period_start')} to {fixture.get('period_end')}

GOOGLE ANALYTICS DATA:
Sessions: {ga4.get('sessions')} (prev: {ga4.get('prev_sessions')}, change: {ga4.get('sessions_change')}%)
Users: {ga4.get('users')} (prev: {ga4.get('prev_users')}, change: {ga4.get('users_change')}%)
Pageviews: {ga4.get('pageviews')} (prev: {ga4.get('prev_pageviews')})
Bounce Rate: {ga4.get('bounce_rate')}% (prev: {ga4.get('prev_bounce_rate')}%)
Avg Session Duration: {ga4.get('avg_session_duration')}s
Conversions: {ga4.get('conversions')} (prev: {ga4.get('prev_conversions')}, change: {ga4.get('conversions_change')}%)
Traffic Sources: {json.dumps(list(traffic_sources)[:5] if isinstance(traffic_sources, list) else traffic_sources)}

META ADS DATA (Currency: {currency_code}):
Total Spend: {cur_sym}{meta.get('spend')} (prev: {cur_sym}{meta.get('prev_spend')}, change: {meta.get('spend_change')}%)
Impressions: {meta.get('impressions')} (prev: {meta.get('prev_impressions')})
Clicks: {meta.get('clicks')} (prev: {meta.get('prev_clicks')})
CTR: {meta.get('ctr')}% (prev: {meta.get('prev_ctr')}%)
CPC: {cur_sym}{meta.get('cpc')} (prev: {cur_sym}{meta.get('prev_cpc')})
Conversions: {meta.get('conversions')} (prev: {meta.get('prev_conversions')}, change: {meta.get('conversions_change')}%)
Cost Per Conversion: {cur_sym}{meta.get('cost_per_conversion')} (prev: {cur_sym}{meta.get('prev_cost_per_conversion')})
ROAS: {meta.get('roas')}x (prev: {meta.get('prev_roas')}x)
Top Campaigns: {json.dumps(campaigns[:3])}

SEO DATA (Google Search Console):
Clicks: {search_console.get('clicks')} (prev: {search_console.get('prev_clicks')})
Impressions: {search_console.get('impressions')}
CTR: {search_console.get('ctr')}% | Avg Position: {search_console.get('avg_position')}

CSV SOURCES: {len(csv_sources)} additional data source(s) connected

{_movers_block}

TONE: Professional / diagnostic

Generate the following sections as a JSON object:
{section_instructions}
"""
    print("=" * 72)
    print("STEP 3 — Assembled user prompt (Phase 4 v2 — with TOP MOVERS)")
    print("=" * 72)
    print(user_prompt)
    print()


async def run_live_generation(fixture: dict) -> None:
    """Optional — call GPT-4.1 with the fixture and print the JSON output."""
    from services.ai_narrative import generate_narrative
    print("=" * 72)
    print("STEP 4 — Live GPT-4.1 call (Phase 4 diagnostic output)")
    print("=" * 72)
    narrative = await generate_narrative(
        data=fixture,
        client_name="Videogenie",
        client_goals="Grow MRR via AI video generation; focus on SMB video creators",
        tone="professional",
        template="full",
        language="en",
    )
    print(json.dumps(narrative, indent=2))


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="Actually call OpenAI (requires OPENAI_API_KEY)")
    args = ap.parse_args()

    fixture = build_videogenie_fixture()
    show_movers_block(fixture)
    show_prompt_diff(fixture)

    if args.live:
        if not os.environ.get("OPENAI_API_KEY"):
            print("[ERR] --live requested but OPENAI_API_KEY is not set", file=sys.stderr)
            return 2
        asyncio.run(run_live_generation(fixture))
    else:
        print("=" * 72)
        print("Live GPT-4.1 call SKIPPED (run with --live to actually call OpenAI)")
        print("=" * 72)

    return 0


if __name__ == "__main__":
    sys.exit(main())
