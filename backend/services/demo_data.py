"""
Rich demo data for generating showcase reports.
Simulates a thriving SaaS client with a recent product launch.
Includes ALL 5 data sources: GA4, Meta Ads, Google Ads, Search Console, CSV.
"""
import math

DEMO_CLIENT = {
    "name": "TechVista Solutions",
    "agency_name": "SapienBotics Agency",
    "industry": "SaaS / B2B Technology",
    "goals_context": (
        "TechVista launched their new AI product 'DataPulse' on Feb 15th. "
        "Goal: 500 trial signups in March. Running Google Ads for brand keywords "
        "and Meta retargeting for website visitors. Also invested in SEO content strategy."
    ),
}

# ── Helper: generate 31 days of daily data with realistic patterns ──────────
def _daily_ga4():
    """31 days of GA4 data with upward trend + mid-month spike."""
    days = []
    for d in range(1, 32):
        # Base: upward trend
        base = 1100 + d * 32
        # Mid-month spike (TechCrunch feature Mar 15-18)
        spike = 350 if 14 <= d <= 18 else 0
        # Weekend dip
        weekday = (d + 5) % 7  # Mar 1, 2026 is Sunday
        weekend_factor = 0.72 if weekday >= 5 else 1.0
        # Slight noise
        noise = (d * 17 % 11) * 8 - 40
        sessions = max(800, int((base + spike + noise) * weekend_factor))
        users = int(sessions * 0.63)
        bounce = round(44.0 - d * 0.15 + (2 if weekday >= 5 else 0), 1)
        days.append({
            "date": f"2026-03-{d:02d}",
            "sessions": sessions,
            "users": users,
            "bounce_rate": max(32.0, min(55.0, bounce)),
        })
    return days


def _daily_meta():
    """31 days of Meta Ads data with gradual optimization."""
    days = []
    for d in range(1, 32):
        base_spend = 225 + d * 5.5
        noise = (d * 13 % 7) * 8
        spend = round(base_spend + noise, 2)
        conv = 10 + int(d * 0.35) + (d % 4) + (3 if d > 15 else 0)
        days.append({
            "date": f"2026-03-{d:02d}",
            "spend": spend,
            "conversions": conv,
            "impressions": int(spend * 62),
            "clicks": int(spend * 1.85),
        })
    return days


def _daily_gads():
    """31 days of Google Ads data."""
    days = []
    for d in range(1, 32):
        base_spend = 140 + d * 4.2
        noise = (d * 11 % 9) * 6
        spend = round(base_spend + noise, 2)
        clicks = int(spend * 1.87)
        conv = 8 + int(d * 0.25) + (d % 3)
        days.append({
            "date": f"2026-03-{d:02d}",
            "spend": spend,
            "clicks": clicks,
            "conversions": conv,
            "impressions": int(spend * 54),
        })
    return days


def _daily_gsc():
    """31 days of Search Console data with organic growth trend."""
    days = []
    for d in range(1, 32):
        base_clicks = 220 + d * 6
        noise = (d * 7 % 5) * 15
        weekday = (d + 5) % 7
        weekend_factor = 0.65 if weekday >= 5 else 1.0
        clicks = max(120, int((base_clicks + noise) * weekend_factor))
        impressions = int(clicks * 14.7)
        ctr = round(clicks / max(impressions, 1) * 100, 2)
        position = round(13.5 - d * 0.04 + (d % 3) * 0.3, 1)
        days.append({
            "date": f"2026-03-{d:02d}",
            "clicks": clicks,
            "impressions": impressions,
            "ctr": ctr,
            "position": max(3.0, position),
        })
    return days


# ═══════════════════════════════════════════════════════════════════════════════
# FULL DEMO DATA — all 5 sources
# ═══════════════════════════════════════════════════════════════════════════════

DEMO_DATA = {
    "period_start": "Mar 1, 2026",
    "period_end": "Mar 31, 2026",

    # ── GA4 (Website Analytics) ──────────────────────────────────────────────
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
            "conversion_rate_change": 0.82,
        },
        "daily": _daily_ga4(),
        "traffic_sources": [
            {"source": "Google / Organic", "sessions": 15200, "users": 12100},
            {"source": "Google / CPC", "sessions": 12800, "users": 10500},
            {"source": "Facebook / Paid", "sessions": 8400, "users": 7200},
            {"source": "Direct", "sessions": 5100, "users": 3800},
            {"source": "LinkedIn / Social", "sessions": 2100, "users": 1900},
            {"source": "Referral / techcrunch.com", "sessions": 1630, "users": 950},
        ],
        "device_breakdown": [
            {"device": "Desktop", "sessions": 24876, "users": 15500, "bounce_rate": 38.4},
            {"device": "Mobile", "sessions": 17549, "users": 11200, "bounce_rate": 52.1},
            {"device": "Tablet", "sessions": 2805, "users": 1750, "bounce_rate": 41.8},
        ],
        "top_pages": [
            {"page": "/products/datapulse", "sessions": 8200, "bounce_rate": 28.5, "conversions": 380},
            {"page": "/", "sessions": 6800, "bounce_rate": 45.2, "conversions": 85},
            {"page": "/pricing", "sessions": 5200, "bounce_rate": 32.1, "conversions": 290},
            {"page": "/blog/ai-analytics-guide", "sessions": 3800, "bounce_rate": 38.7, "conversions": 42},
            {"page": "/demo", "sessions": 3100, "bounce_rate": 25.4, "conversions": 185},
            {"page": "/blog/data-visualization-tips", "sessions": 2400, "bounce_rate": 41.3, "conversions": 28},
            {"page": "/about", "sessions": 1900, "bounce_rate": 52.8, "conversions": 12},
            {"page": "/case-studies", "sessions": 1600, "bounce_rate": 35.6, "conversions": 35},
            {"page": "/integrations", "sessions": 1200, "bounce_rate": 39.2, "conversions": 22},
            {"page": "/contact", "sessions": 980, "bounce_rate": 30.1, "conversions": 68},
        ],
        "new_vs_returning": {
            "new": {"sessions": 29400, "users": 19200, "conversions": 620},
            "returning": {"sessions": 15830, "users": 9250, "conversions": 620},
        },
        "top_countries": [
            {"country": "United States", "sessions": 18900, "users": 12200},
            {"country": "United Kingdom", "sessions": 5600, "users": 3500},
            {"country": "India", "sessions": 4800, "users": 3100},
            {"country": "Canada", "sessions": 3200, "users": 2100},
            {"country": "Germany", "sessions": 2800, "users": 1800},
            {"country": "Australia", "sessions": 2400, "users": 1600},
            {"country": "France", "sessions": 1800, "users": 1100},
            {"country": "Netherlands", "sessions": 1500, "users": 950},
            {"country": "Singapore", "sessions": 1200, "users": 780},
            {"country": "Brazil", "sessions": 980, "users": 620},
        ],
    },

    # ── Meta Ads ─────────────────────────────────────────────────────────────
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
            {"name": "DataPulse Retargeting", "spend": 3200, "impressions": 180000, "clicks": 7200, "conversions": 210, "roas": 4.2},
            {"name": "Brand Awareness Q1", "spend": 2800, "impressions": 220000, "clicks": 5100, "conversions": 120, "roas": 3.1},
            {"name": "Competitor Targeting", "spend": 1450, "impressions": 84000, "clicks": 2400, "conversions": 65, "roas": 3.5},
            {"name": "Lookalike Audiences", "spend": 1000, "impressions": 40000, "clicks": 1000, "conversions": 25, "roas": 2.8},
        ],
        "daily": _daily_meta(),
        "age_gender": [
            {"age": "25-34", "gender": "male", "spend": 2800, "impressions": 168000, "clicks": 5200, "conversions": 155},
            {"age": "25-34", "gender": "female", "spend": 1900, "impressions": 120000, "clicks": 3600, "conversions": 95},
            {"age": "35-44", "gender": "male", "spend": 1600, "impressions": 92000, "clicks": 2900, "conversions": 78},
            {"age": "35-44", "gender": "female", "spend": 1100, "impressions": 68000, "clicks": 2000, "conversions": 48},
            {"age": "18-24", "gender": "male", "spend": 450, "impressions": 32000, "clicks": 850, "conversions": 18},
            {"age": "18-24", "gender": "female", "spend": 300, "impressions": 22000, "clicks": 600, "conversions": 12},
            {"age": "45-54", "gender": "male", "spend": 200, "impressions": 14000, "clicks": 380, "conversions": 10},
            {"age": "45-54", "gender": "female", "spend": 100, "impressions": 8000, "clicks": 170, "conversions": 4},
        ],
        "placements": [
            {"placement": "Facebook Feed", "spend": 3800, "impressions": 240000, "clicks": 7200, "conversions": 195},
            {"placement": "Instagram Feed", "spend": 2200, "impressions": 140000, "clicks": 4100, "conversions": 110},
            {"placement": "Instagram Stories", "spend": 1400, "impressions": 95000, "clicks": 2800, "conversions": 72},
            {"placement": "Facebook Reels", "spend": 650, "impressions": 32000, "clicks": 1000, "conversions": 28},
            {"placement": "Audience Network", "spend": 400, "impressions": 17000, "clicks": 600, "conversions": 15},
        ],
        "top_ads": [
            {"ad_name": "DataPulse Demo Video - 30s", "spend": 1800, "impressions": 95000, "clicks": 3800, "conversions": 120, "ctr": 4.0},
            {"ad_name": "Customer Testimonial Carousel", "spend": 1500, "impressions": 82000, "clicks": 3200, "conversions": 95, "ctr": 3.9},
            {"ad_name": "Free Trial CTA - Static", "spend": 1200, "impressions": 68000, "clicks": 2400, "conversions": 78, "ctr": 3.5},
            {"ad_name": "AI Analytics Infographic", "spend": 900, "impressions": 55000, "clicks": 1600, "conversions": 42, "ctr": 2.9},
            {"ad_name": "Competitor Comparison Chart", "spend": 750, "impressions": 42000, "clicks": 1200, "conversions": 35, "ctr": 2.9},
        ],
    },

    # ── Google Ads ────────────────────────────────────────────────────────────
    "google_ads": {
        "currency": "USD",
        "summary": {
            "impressions": 285000,
            "clicks": 9800,
            "spend": 5240.00,
            "conversions": 340,
            "conversion_value": 42500.00,
            "ctr": 3.44,
            "avg_cpc": 0.53,
            "roas": 8.11,
            "cost_per_conversion": 15.41,
            "search_impression_share": 0.52,
            "spend_change": 11.2,
            "conversions_change": 28.5,
            "clicks_change": 15.8,
            "impressions_change": 22.0,
        },
        "campaigns": [
            {"name": "Brand Search - DataPulse", "spend": 1800, "clicks": 4200, "conversions": 180, "ctr": 12.5, "avg_cpc": 0.43, "impressions": 33600},
            {"name": "Non-Brand - AI Analytics", "spend": 1600, "clicks": 2800, "conversions": 85, "ctr": 2.1, "avg_cpc": 0.57, "impressions": 133333},
            {"name": "Competitor Keywords", "spend": 1200, "clicks": 1800, "conversions": 52, "ctr": 1.8, "avg_cpc": 0.67, "impressions": 100000},
            {"name": "Remarketing - Site Visitors", "spend": 640, "clicks": 1000, "conversions": 23, "ctr": 4.2, "avg_cpc": 0.64, "impressions": 23810},
        ],
        "daily": _daily_gads(),
        "search_terms": [
            {"term": "datapulse ai analytics", "impressions": 12000, "clicks": 2800, "conversions": 120, "cpc": 0.38},
            {"term": "ai data analytics tool", "impressions": 8500, "clicks": 1200, "conversions": 45, "cpc": 0.62},
            {"term": "best analytics platform 2026", "impressions": 6200, "clicks": 800, "conversions": 28, "cpc": 0.71},
            {"term": "datapulse pricing", "impressions": 4800, "clicks": 1500, "conversions": 65, "cpc": 0.32},
            {"term": "analytics dashboard saas", "impressions": 3500, "clicks": 420, "conversions": 12, "cpc": 0.85},
            {"term": "marketing analytics software", "impressions": 3200, "clicks": 380, "conversions": 15, "cpc": 0.78},
            {"term": "datapulse vs mixpanel", "impressions": 2800, "clicks": 620, "conversions": 22, "cpc": 0.45},
            {"term": "real time analytics tool", "impressions": 2500, "clicks": 310, "conversions": 10, "cpc": 0.92},
            {"term": "datapulse demo", "impressions": 2200, "clicks": 850, "conversions": 38, "cpc": 0.28},
            {"term": "business intelligence dashboard", "impressions": 1800, "clicks": 220, "conversions": 8, "cpc": 1.05},
        ],
    },

    # ── Search Console (SEO) ─────────────────────────────────────────────────
    "search_console": {
        "summary": {
            "clicks": 8500,
            "impressions": 125000,
            "ctr": 6.8,
            "average_position": 12.3,
            "clicks_change": 22.4,
            "impressions_change": 35.1,
            "ctr_change": -1.2,
            "position_change": -2.1,
        },
        "top_queries": [
            {"query": "ai analytics tool", "clicks": 1200, "impressions": 8500, "ctr": 14.1, "position": 3.2},
            {"query": "datapulse review", "clicks": 890, "impressions": 3200, "ctr": 27.8, "position": 1.8},
            {"query": "best data analytics platform", "clicks": 680, "impressions": 12000, "ctr": 5.7, "position": 8.5},
            {"query": "marketing analytics software", "clicks": 520, "impressions": 15000, "ctr": 3.5, "position": 14.2},
            {"query": "ai reporting tool", "clicks": 450, "impressions": 6800, "ctr": 6.6, "position": 6.1},
            {"query": "datapulse ai", "clicks": 420, "impressions": 2100, "ctr": 20.0, "position": 2.3},
            {"query": "data visualization platform", "clicks": 380, "impressions": 9500, "ctr": 4.0, "position": 11.5},
            {"query": "real time analytics dashboard", "clicks": 350, "impressions": 8200, "ctr": 4.3, "position": 9.8},
            {"query": "business intelligence tool comparison", "clicks": 310, "impressions": 11000, "ctr": 2.8, "position": 16.4},
            {"query": "saas analytics pricing", "clicks": 280, "impressions": 4500, "ctr": 6.2, "position": 7.2},
        ],
        "top_pages": [
            {"page": "/products/datapulse", "clicks": 2800, "impressions": 22000, "ctr": 12.7, "position": 4.1},
            {"page": "/blog/ai-analytics-guide", "clicks": 1500, "impressions": 18000, "ctr": 8.3, "position": 7.2},
            {"page": "/pricing", "clicks": 1200, "impressions": 8500, "ctr": 14.1, "position": 3.5},
            {"page": "/", "clicks": 1100, "impressions": 35000, "ctr": 3.1, "position": 18.4},
            {"page": "/blog/data-visualization-tips", "clicks": 680, "impressions": 12000, "ctr": 5.7, "position": 9.8},
            {"page": "/case-studies", "clicks": 420, "impressions": 5500, "ctr": 7.6, "position": 5.9},
            {"page": "/demo", "clicks": 380, "impressions": 4200, "ctr": 9.0, "position": 4.8},
            {"page": "/integrations", "clicks": 220, "impressions": 6800, "ctr": 3.2, "position": 14.2},
            {"page": "/about", "clicks": 120, "impressions": 8500, "ctr": 1.4, "position": 22.1},
            {"page": "/blog/saas-metrics-guide", "clicks": 80, "impressions": 4500, "ctr": 1.8, "position": 19.5},
        ],
        "daily": _daily_gsc(),
    },

    # ── CSV Sources (Custom Data) ────────────────────────────────────────────
    "csv_sources": [
        {
            "name": "LinkedIn Ads",
            "metrics": [
                {"name": "Impressions", "current_value": 45000, "previous_value": 38000, "unit": "number"},
                {"name": "Clicks", "current_value": 1200, "previous_value": 980, "unit": "number"},
                {"name": "Spend", "current_value": 2800, "previous_value": 2400, "unit": "currency"},
                {"name": "Leads", "current_value": 85, "previous_value": 62, "unit": "number"},
                {"name": "CTR", "current_value": 2.67, "previous_value": 2.58, "unit": "percent"},
                {"name": "Cost per Lead", "current_value": 32.94, "previous_value": 38.71, "unit": "currency"},
            ],
        },
        {
            "name": "Email Marketing",
            "metrics": [
                {"name": "Emails Sent", "current_value": 12500, "previous_value": 11000, "unit": "number"},
                {"name": "Open Rate", "current_value": 28.4, "previous_value": 26.1, "unit": "percent"},
                {"name": "Click Rate", "current_value": 4.2, "previous_value": 3.8, "unit": "percent"},
                {"name": "Unsubscribes", "current_value": 23, "previous_value": 31, "unit": "number"},
                {"name": "Revenue", "current_value": 8500, "previous_value": 6200, "unit": "currency"},
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# Subset builders — for testing different data combinations
# ═══════════════════════════════════════════════════════════════════════════════

def demo_ga4_only() -> dict:
    """GA4 data only — no ads, no SEO, no CSV."""
    return {
        "period_start": DEMO_DATA["period_start"],
        "period_end": DEMO_DATA["period_end"],
        "ga4": DEMO_DATA["ga4"],
    }


def demo_ga4_meta() -> dict:
    """GA4 + Meta Ads only."""
    return {
        "period_start": DEMO_DATA["period_start"],
        "period_end": DEMO_DATA["period_end"],
        "ga4": DEMO_DATA["ga4"],
        "meta_ads": DEMO_DATA["meta_ads"],
    }


def demo_full() -> dict:
    """All 5 data sources."""
    return dict(DEMO_DATA)


# ═══════════════════════════════════════════════════════════════════════════════
# Demo narrative — pre-written fallback if GPT-4o is unavailable
# ═══════════════════════════════════════════════════════════════════════════════

DEMO_NARRATIVE = {
    "executive_summary": (
        "March 2026 was a breakthrough month for TechVista Solutions following the DataPulse "
        "product launch on February 15th. Website sessions surged 34.2% to 45,230, driven "
        "primarily by a well-executed Google Ads campaign and strong organic search performance.\n\n"
        "The combined paid advertising effort across Meta Ads and Google yielded 1,240 conversions "
        "- a 67.5% increase over the previous period. Meta Ads delivered a strong 3.8x ROAS with "
        "the retargeting campaign performing exceptionally well at 4.2x ROAS. Google Ads achieved "
        "an impressive 8.1x ROAS driven by strong brand search performance.\n\n"
        "SEO efforts are paying dividends, with organic clicks up 22.4% to 8,500 and average position "
        "improving by 2.1 spots. The TechCrunch feature on March 12th generated a notable referral "
        "traffic spike that contributed to 950 new users.\n\n"
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
    "google_ads_performance": (
        "Google Ads delivered exceptional results in March with $5,240 in spend generating 340 "
        "conversions at an impressive 8.1x ROAS. Brand search remained the strongest performer "
        "with 180 conversions at a $0.43 CPC.\n\n"
        "Non-brand campaigns targeting 'AI analytics' keywords delivered 85 conversions, showing "
        "strong intent-based acquisition. The competitor keyword strategy captured 52 conversions "
        "from users actively evaluating alternatives.\n\n"
        "Search impression share of 52% indicates significant room for growth - increasing budgets "
        "on high-performing brand terms could capture an additional 30-40% of available traffic."
    ),
    "seo_performance": (
        "Organic search performance strengthened considerably in March. Total clicks reached 8,500 "
        "(up 22.4%) with impressions growing 35.1% to 125,000. Average position improved by 2.1 "
        "spots to 12.3.\n\n"
        "The blog post 'AI Analytics Guide' continues to be the top organic traffic driver with "
        "1,500 clicks. The DataPulse product page ranks well for branded terms with an average "
        "position of 4.1. The pricing page achieves a strong 14.1% CTR at position 3.5.\n\n"
        "Key opportunity areas include 'marketing analytics software' (position 14.2) and "
        "'business intelligence tool comparison' (position 16.4) where improved content and "
        "link building could push into the top 10."
    ),
    "key_wins": [
        "Sessions surged 34.2% to 45,230, marking the highest traffic month in company history",
        "Conversions jumped 67.5% to 1,240, exceeding the monthly target of 500 trial signups by 148%",
        "Meta Ads retargeting campaign delivered exceptional 4.2x ROAS with 210 conversions",
        "Google Ads achieved 8.1x ROAS with brand search driving 180 conversions at $0.43 CPC",
        "Organic clicks grew 22.4% to 8,500 with average position improving 2.1 spots",
        "Bounce rate improved from 50.4% to 42.3%, indicating stronger landing page performance",
        "TechCrunch feature generated 950 referral users and boosted brand authority",
    ],
    "concerns": [
        "Lookalike Audiences campaign underperforming at 2.8x ROAS - recommend pausing and testing new audience segments based on DataPulse trial signups",
        "Mobile bounce rate at 52.1% vs 38.4% desktop - the DataPulse landing page needs mobile optimization, particularly the signup form",
        "LinkedIn organic traffic represents only 4.6% despite B2B audience - recommend increasing LinkedIn content frequency from 2x to 4x weekly",
        "Search impression share at 52% means nearly half of potential Google Ads traffic is missed - budget increase needed for brand terms",
        "Email unsubscribe rate needs monitoring - 23 unsubscribes in March across 12,500 sends",
    ],
    "next_steps": [
        "1. Pause Lookalike Audiences campaign and create new audience based on March trial signups - implement by April 5",
        "2. A/B test mobile landing page with simplified signup form - launch test by April 3",
        "3. Increase Meta retargeting budget by 25% ($800) given strong 4.2x ROAS - effective immediately",
        "4. Increase Google Ads brand search budget by 40% to capture more impression share - by April 7",
        "5. Develop LinkedIn thought leadership content calendar for April - draft by April 7",
        "6. Optimize content for 'marketing analytics software' keyword (currently position 14.2) - by April 15",
        "7. Create email re-engagement campaign for lapsed subscribers - launch April 10",
    ],
}
