"""
Rich demo data for generating showcase reports.
Simulates a thriving SaaS client with a recent product launch.
"""

DEMO_CLIENT = {
    "name": "TechVista Solutions",
    "agency_name": "SapienBotics Agency",
}

DEMO_DATA = {
    "period_start": "Mar 1, 2026",
    "period_end": "Mar 31, 2026",
    "ga4": {
        "summary": {
            "sessions": 45230,
            "sessions_change": 34.2,
            "users": 28450,
            "users_change": 28.7,
            "new_users": 19200,
            "pageviews": 142000,
            "bounce_rate": 42.3,
            "bounce_rate_change": -8.1,
            "avg_session_duration": 185.4,
            "conversions": 1240,
            "conversions_change": 67.5,
            "conversion_rate": 2.74,
        },
        "daily": [
            {"date": f"2026-03-{d:02d}", "sessions": int(1100 + d * 30 + (80 if 14 <= d <= 18 else 0) + (d % 3) * 25)}
            for d in range(1, 32)
        ],
        "traffic_sources": [
            {"source": "Google / Organic", "sessions": 15200},
            {"source": "Google / CPC", "sessions": 12800},
            {"source": "Facebook / Paid", "sessions": 8400},
            {"source": "Direct", "sessions": 5100},
            {"source": "LinkedIn / Social", "sessions": 2100},
            {"source": "Referral / techcrunch.com", "sessions": 1630},
        ],
    },
    "meta_ads": {
        "currency": "USD",
        "summary": {
            "spend": 8450,
            "spend_change": 12.3,
            "impressions": 524000,
            "impressions_change": 18.5,
            "clicks": 15700,
            "clicks_change": 22.1,
            "ctr": 3.0,
            "cpc": 0.54,
            "conversions": 420,
            "conversions_change": 45.8,
            "roas": 3.8,
            "prev_roas": 3.1,
            "cost_per_conversion": 20.12,
            "prev_cost_per_conversion": 23.50,
        },
        "campaigns": [
            {"name": "DataPulse Retargeting", "spend": 3200, "impressions": 180000, "clicks": 7200, "conversions": 210},
            {"name": "Brand Awareness Q1", "spend": 2800, "impressions": 220000, "clicks": 5100, "conversions": 120},
            {"name": "Competitor Targeting", "spend": 1450, "impressions": 84000, "clicks": 2400, "conversions": 65},
            {"name": "Lookalike Audiences", "spend": 1000, "impressions": 40000, "clicks": 1000, "conversions": 25},
        ],
        "daily": [
            {"date": f"2026-03-{d:02d}", "spend": round(220 + d * 6 + (d % 4) * 12, 2), "conversions": 10 + d % 5 + (3 if d > 15 else 0)}
            for d in range(1, 32)
        ],
    },
}


DEMO_NARRATIVE = {
    "executive_summary": (
        "March 2026 was a breakthrough month for TechVista Solutions following the DataPulse "
        "product launch on February 15th. Website sessions surged 34.2% to 45,230, driven "
        "primarily by a well-executed Google Ads campaign and strong organic search performance.\n\n"
        "The combined paid advertising effort across Meta Ads and Google yielded 1,240 conversions "
        "- a 67.5% increase over the previous period. Meta Ads delivered a strong 3.8x ROAS with "
        "the retargeting campaign performing exceptionally well at 4.2x ROAS.\n\n"
        "SEO efforts are paying dividends, with organic traffic now representing 33.6% of total "
        "sessions. The TechCrunch feature on March 12th generated a notable referral traffic spike "
        "that contributed to 950 new users.\n\n"
        "Key areas requiring attention include the Lookalike Audiences campaign which underperformed "
        "at 2.8x ROAS, and the overall bounce rate on mobile devices which remains elevated at "
        "52.1% compared to 38.4% on desktop."
    ),
    "website_performance": (
        "TechVista's website experienced exceptional growth in March, with sessions climbing "
        "from 33,705 to 45,230 - a 34.2% increase. The DataPulse launch on February 15th continued "
        "to drive interest throughout March, with a visible traffic spike during March 15-18 "
        "coinciding with the TechCrunch feature article.\n\n"
        "User acquisition was strong with 19,200 new users (67.5% of total users), indicating "
        "effective top-of-funnel marketing. Returning users also grew by 18.3%, suggesting the "
        "product is generating genuine interest.\n\n"
        "The bounce rate improved significantly from 50.4% to 42.3%, a testament to the landing "
        "page optimizations implemented in late February. Average session duration of 3 minutes "
        "and 5 seconds indicates users are engaging deeply with product content.\n\n"
        "Traffic sources showed healthy diversification: organic search (33.6%), paid search "
        "(28.3%), paid social (18.6%), direct (11.3%), LinkedIn (4.6%), and referrals (3.6%)."
    ),
    "paid_advertising": (
        "Meta Ads investment of $8,450 delivered 420 conversions at a cost per acquisition of "
        "$20.12, generating an overall ROAS of 3.8x. This represents a 45.8% increase in "
        "conversions compared to February.\n\n"
        "The DataPulse Retargeting campaign was the clear winner, generating 210 conversions "
        "at 4.2x ROAS - this campaign alone justified 50% of total conversions at the lowest CPA. "
        "The Brand Awareness campaign reached 220,000 impressions and contributed 120 conversions.\n\n"
        "The Competitor Targeting campaign showed promising results with a 3.5x ROAS, successfully "
        "capturing users researching alternative solutions. However, the Lookalike Audiences campaign "
        "underperformed at 2.8x ROAS and warrants creative refresh or audience refinement.\n\n"
        "CTR across all campaigns averaged 3.0%, above the industry benchmark of 2.1% for B2B SaaS. "
        "CPC remained efficient at $0.54, down from $0.62 in February."
    ),
    "key_wins": [
        "Sessions surged 34.2% to 45,230, marking the highest traffic month in company history",
        "Conversions jumped 67.5% to 1,240, exceeding the monthly target of 500 trial signups by 148%",
        "Meta Ads retargeting campaign delivered exceptional 4.2x ROAS with 210 conversions",
        "Bounce rate improved from 50.4% to 42.3%, indicating stronger landing page performance",
        "TechCrunch feature generated 950 referral users and boosted brand authority",
    ],
    "concerns": [
        "Lookalike Audiences campaign underperforming at 2.8x ROAS - recommend pausing and testing new audience segments based on DataPulse trial signups",
        "Mobile bounce rate at 52.1% vs 38.4% desktop - the DataPulse landing page needs mobile optimization, particularly the signup form",
        "LinkedIn organic traffic represents only 4.6% despite B2B audience - recommend increasing LinkedIn content frequency from 2x to 4x weekly",
    ],
    "next_steps": [
        "1. Pause Lookalike Audiences campaign and create new audience based on March trial signups - implement by April 5",
        "2. A/B test mobile landing page with simplified signup form - launch test by April 3",
        "3. Increase Meta retargeting budget by 25% ($800) given strong 4.2x ROAS - effective immediately",
        "4. Develop LinkedIn thought leadership content calendar for April - draft by April 7",
        "5. Schedule Google Ads keyword expansion targeting DataPulse competitor terms - launch April 10",
    ],
}
