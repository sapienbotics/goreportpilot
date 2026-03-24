"""
Mock data service — generates realistic marketing data for development.
Returns the same data structure as real GA4 / Meta Ads API services.
Replace with real API calls when OAuth integrations are connected.
"""
import random
from datetime import datetime, timedelta
from typing import Dict, Any


def generate_mock_ga4_data(client_name: str, period_start: str, period_end: str) -> Dict[str, Any]:
    """Generate realistic Google Analytics 4 data with all fields."""

    sessions = random.randint(15000, 60000)
    users = int(sessions * random.uniform(0.65, 0.85))
    new_users = int(users * random.uniform(0.35, 0.55))
    pageviews = int(sessions * random.uniform(1.8, 3.5))
    bounce_rate = round(random.uniform(35, 65), 1)
    avg_session_duration = round(random.uniform(90, 240), 0)
    conversions = int(sessions * random.uniform(0.005, 0.04))
    conversion_rate = round(conversions / max(sessions, 1) * 100, 2)

    # Previous period (for comparison)
    prev_sessions = int(sessions * random.uniform(0.8, 1.15))
    prev_users = int(users * random.uniform(0.8, 1.15))
    prev_pageviews = int(pageviews * random.uniform(0.8, 1.15))
    prev_bounce_rate = round(bounce_rate + random.uniform(-8, 8), 1)
    prev_avg_duration = round(avg_session_duration + random.uniform(-30, 30), 0)
    prev_conversions = int(conversions * random.uniform(0.75, 1.2))
    prev_conversion_rate = round(prev_conversions / max(prev_sessions, 1) * 100, 2)

    # Daily data for charts (30 days)
    daily_sessions = []
    start = datetime.strptime(period_start, "%Y-%m-%d")
    for i in range(30):
        day = start + timedelta(days=i)
        weekday_factor = 0.7 if day.weekday() >= 5 else 1.0
        daily_val = int((sessions / 30) * weekday_factor * random.uniform(0.7, 1.3))
        daily_sessions.append({
            "date": day.strftime("%Y-%m-%d"),
            "sessions": daily_val,
            "users": int(daily_val * random.uniform(0.65, 0.85)),
            "bounce_rate": round(bounce_rate + random.uniform(-5, 5), 1),
        })

    # Traffic sources
    source_total = sessions
    organic = int(source_total * random.uniform(0.25, 0.45))
    paid = int(source_total * random.uniform(0.15, 0.30))
    social = int(source_total * random.uniform(0.08, 0.18))
    direct = int(source_total * random.uniform(0.15, 0.25))
    referral = source_total - organic - paid - social - direct

    traffic_sources = [
        {"source": "Organic Search", "sessions": organic, "users": int(organic * 0.78)},
        {"source": "Paid Search", "sessions": paid, "users": int(paid * 0.82)},
        {"source": "Social", "sessions": social, "users": int(social * 0.85)},
        {"source": "Direct", "sessions": direct, "users": int(direct * 0.72)},
        {"source": "Referral", "sessions": referral, "users": int(referral * 0.68)},
    ]

    # Top pages
    top_pages = [
        {"page": "/", "sessions": int(sessions * 0.25), "bounce_rate": round(random.uniform(30, 50), 1), "conversions": int(conversions * 0.08)},
        {"page": "/products", "sessions": int(sessions * 0.15), "bounce_rate": round(random.uniform(35, 55), 1), "conversions": int(conversions * 0.25)},
        {"page": "/blog/top-tips", "sessions": int(sessions * 0.08), "bounce_rate": round(random.uniform(40, 65), 1), "conversions": int(conversions * 0.05)},
        {"page": "/pricing", "sessions": int(sessions * 0.06), "bounce_rate": round(random.uniform(25, 45), 1), "conversions": int(conversions * 0.20)},
        {"page": "/contact", "sessions": int(sessions * 0.05), "bounce_rate": round(random.uniform(30, 50), 1), "conversions": int(conversions * 0.12)},
        {"page": "/demo", "sessions": int(sessions * 0.04), "bounce_rate": round(random.uniform(25, 40), 1), "conversions": int(conversions * 0.15)},
        {"page": "/about", "sessions": int(sessions * 0.03), "bounce_rate": round(random.uniform(45, 65), 1), "conversions": int(conversions * 0.02)},
    ]

    # Device breakdown
    desktop_pct = random.uniform(0.50, 0.65)
    mobile_pct = random.uniform(0.28, 0.42)
    tablet_pct = 1.0 - desktop_pct - mobile_pct
    device_breakdown = [
        {"device": "Desktop", "sessions": int(sessions * desktop_pct), "users": int(users * desktop_pct), "bounce_rate": round(random.uniform(30, 45), 1)},
        {"device": "Mobile", "sessions": int(sessions * mobile_pct), "users": int(users * mobile_pct), "bounce_rate": round(random.uniform(45, 60), 1)},
        {"device": "Tablet", "sessions": int(sessions * tablet_pct), "users": int(users * tablet_pct), "bounce_rate": round(random.uniform(35, 50), 1)},
    ]

    # New vs returning
    new_sessions = int(sessions * random.uniform(0.55, 0.70))
    returning_sessions = sessions - new_sessions
    new_vs_returning = {
        "new": {"sessions": new_sessions, "users": new_users, "conversions": int(conversions * 0.45)},
        "returning": {"sessions": returning_sessions, "users": users - new_users, "conversions": conversions - int(conversions * 0.45)},
    }

    # Top countries
    us_pct = random.uniform(0.35, 0.50)
    top_countries = [
        {"country": "United States", "sessions": int(sessions * us_pct), "users": int(users * us_pct)},
        {"country": "United Kingdom", "sessions": int(sessions * 0.12), "users": int(users * 0.12)},
        {"country": "India", "sessions": int(sessions * 0.10), "users": int(users * 0.10)},
        {"country": "Canada", "sessions": int(sessions * 0.07), "users": int(users * 0.07)},
        {"country": "Germany", "sessions": int(sessions * 0.06), "users": int(users * 0.06)},
        {"country": "Australia", "sessions": int(sessions * 0.05), "users": int(users * 0.05)},
    ]

    return {
        "platform": "ga4",
        "period": {"start": period_start, "end": period_end},
        "summary": {
            "sessions": sessions,
            "prev_sessions": prev_sessions,
            "sessions_change": round((sessions - prev_sessions) / prev_sessions * 100, 1),
            "users": users,
            "prev_users": prev_users,
            "users_change": round((users - prev_users) / prev_users * 100, 1),
            "new_users": new_users,
            "pageviews": pageviews,
            "prev_pageviews": prev_pageviews,
            "bounce_rate": bounce_rate,
            "prev_bounce_rate": prev_bounce_rate,
            "bounce_rate_change": round(bounce_rate - prev_bounce_rate, 1),
            "avg_session_duration": avg_session_duration,
            "prev_avg_duration": prev_avg_duration,
            "conversions": conversions,
            "prev_conversions": prev_conversions,
            "conversions_change": round((conversions - prev_conversions) / max(prev_conversions, 1) * 100, 1),
            "conversion_rate": conversion_rate,
            "conversion_rate_change": round(conversion_rate - prev_conversion_rate, 2),
        },
        "daily": daily_sessions,
        "traffic_sources": traffic_sources,
        "top_pages": top_pages,
        "device_breakdown": device_breakdown,
        "new_vs_returning": new_vs_returning,
        "top_countries": top_countries,
    }


def generate_mock_meta_ads_data(client_name: str, period_start: str, period_end: str) -> Dict[str, Any]:
    """Generate realistic Meta Ads (Facebook/Instagram) data with all fields."""

    spend = round(random.uniform(1500, 8000), 2)
    impressions = int(spend * random.uniform(800, 1500))
    clicks = int(impressions * random.uniform(0.008, 0.025))
    ctr = round(clicks / max(impressions, 1) * 100, 2)
    cpc = round(spend / max(clicks, 1), 2)
    cpm = round(spend / max(impressions, 1) * 1000, 2)
    conversions = int(clicks * random.uniform(0.02, 0.08))
    cost_per_conv = round(spend / max(conversions, 1), 2)
    revenue = round(conversions * random.uniform(40, 150), 2)
    roas = round(revenue / max(spend, 1), 2)

    # Previous period
    prev_spend = round(spend * random.uniform(0.85, 1.15), 2)
    prev_impressions = int(prev_spend * random.uniform(800, 1500))
    prev_clicks = int(prev_impressions * random.uniform(0.008, 0.025))
    prev_ctr = round(prev_clicks / max(prev_impressions, 1) * 100, 2)
    prev_cpc = round(prev_spend / max(prev_clicks, 1), 2)
    prev_conversions = int(prev_clicks * random.uniform(0.02, 0.08))
    prev_cost_per_conv = round(prev_spend / max(prev_conversions, 1), 2)
    prev_roas = round((prev_conversions * random.uniform(40, 150)) / max(prev_spend, 1), 2)

    # Daily spend + conversions for chart
    daily_data = []
    start = datetime.strptime(period_start, "%Y-%m-%d")
    for i in range(30):
        day = start + timedelta(days=i)
        daily_spend = round(spend / 30 * random.uniform(0.6, 1.4), 2)
        daily_conv = max(0, int(conversions / 30 * random.uniform(0.3, 1.7)))
        daily_data.append({
            "date": day.strftime("%Y-%m-%d"),
            "spend": daily_spend,
            "conversions": daily_conv,
            "impressions": int(daily_spend * random.uniform(800, 1500)),
            "clicks": int(daily_spend / max(cpc, 0.5)),
        })

    # Top campaigns
    campaign_names = [
        f"{client_name} - Prospecting",
        f"{client_name} - Retargeting",
        f"{client_name} - Brand Awareness",
        f"{client_name} - Lookalike",
    ]
    campaigns = []
    remaining_spend = spend
    for i, name in enumerate(campaign_names):
        if i == len(campaign_names) - 1:
            c_spend = round(remaining_spend, 2)
        else:
            c_spend = round(remaining_spend * random.uniform(0.2, 0.4), 2)
            remaining_spend -= c_spend
        c_clicks = int(c_spend / max(cpc * random.uniform(0.8, 1.2), 0.5))
        c_conv = int(c_clicks * random.uniform(0.02, 0.08))
        c_roas = round((c_conv * random.uniform(40, 150)) / max(c_spend, 1), 2)
        campaigns.append({
            "name": name,
            "spend": c_spend,
            "impressions": int(c_spend * random.uniform(800, 1500)),
            "clicks": c_clicks,
            "conversions": c_conv,
            "cpc": round(c_spend / max(c_clicks, 1), 2),
            "roas": c_roas,
        })

    # Age & gender breakdown
    age_gender = [
        {"age": "25-34", "gender": "male", "spend": round(spend * 0.28, 2), "impressions": int(impressions * 0.28), "clicks": int(clicks * 0.30), "conversions": int(conversions * 0.32)},
        {"age": "25-34", "gender": "female", "spend": round(spend * 0.22, 2), "impressions": int(impressions * 0.22), "clicks": int(clicks * 0.24), "conversions": int(conversions * 0.22)},
        {"age": "35-44", "gender": "male", "spend": round(spend * 0.18, 2), "impressions": int(impressions * 0.18), "clicks": int(clicks * 0.16), "conversions": int(conversions * 0.18)},
        {"age": "35-44", "gender": "female", "spend": round(spend * 0.14, 2), "impressions": int(impressions * 0.14), "clicks": int(clicks * 0.12), "conversions": int(conversions * 0.12)},
        {"age": "18-24", "gender": "male", "spend": round(spend * 0.08, 2), "impressions": int(impressions * 0.08), "clicks": int(clicks * 0.08), "conversions": int(conversions * 0.07)},
        {"age": "18-24", "gender": "female", "spend": round(spend * 0.05, 2), "impressions": int(impressions * 0.05), "clicks": int(clicks * 0.05), "conversions": int(conversions * 0.04)},
        {"age": "45-54", "gender": "male", "spend": round(spend * 0.03, 2), "impressions": int(impressions * 0.03), "clicks": int(clicks * 0.03), "conversions": int(conversions * 0.03)},
        {"age": "45-54", "gender": "female", "spend": round(spend * 0.02, 2), "impressions": int(impressions * 0.02), "clicks": int(clicks * 0.02), "conversions": int(conversions * 0.02)},
    ]

    # Placement breakdown
    placements = [
        {"placement": "Facebook Feed", "spend": round(spend * 0.42, 2), "impressions": int(impressions * 0.40), "clicks": int(clicks * 0.44), "conversions": int(conversions * 0.45)},
        {"placement": "Instagram Feed", "spend": round(spend * 0.25, 2), "impressions": int(impressions * 0.26), "clicks": int(clicks * 0.24), "conversions": int(conversions * 0.25)},
        {"placement": "Instagram Stories", "spend": round(spend * 0.18, 2), "impressions": int(impressions * 0.18), "clicks": int(clicks * 0.18), "conversions": int(conversions * 0.17)},
        {"placement": "Facebook Reels", "spend": round(spend * 0.10, 2), "impressions": int(impressions * 0.10), "clicks": int(clicks * 0.09), "conversions": int(conversions * 0.08)},
        {"placement": "Audience Network", "spend": round(spend * 0.05, 2), "impressions": int(impressions * 0.06), "clicks": int(clicks * 0.05), "conversions": int(conversions * 0.05)},
    ]

    # Top ads
    top_ads = [
        {"ad_name": f"{client_name} Video Ad - 30s", "spend": round(spend * 0.22, 2), "impressions": int(impressions * 0.20), "clicks": int(clicks * 0.24), "conversions": int(conversions * 0.28), "ctr": round(random.uniform(3.0, 5.0), 1)},
        {"ad_name": f"{client_name} Carousel", "spend": round(spend * 0.18, 2), "impressions": int(impressions * 0.18), "clicks": int(clicks * 0.20), "conversions": int(conversions * 0.22), "ctr": round(random.uniform(3.0, 4.5), 1)},
        {"ad_name": f"{client_name} Static CTA", "spend": round(spend * 0.15, 2), "impressions": int(impressions * 0.15), "clicks": int(clicks * 0.16), "conversions": int(conversions * 0.18), "ctr": round(random.uniform(2.5, 4.0), 1)},
        {"ad_name": f"{client_name} Infographic", "spend": round(spend * 0.12, 2), "impressions": int(impressions * 0.12), "clicks": int(clicks * 0.10), "conversions": int(conversions * 0.10), "ctr": round(random.uniform(2.0, 3.5), 1)},
        {"ad_name": f"{client_name} Testimonial", "spend": round(spend * 0.10, 2), "impressions": int(impressions * 0.10), "clicks": int(clicks * 0.08), "conversions": int(conversions * 0.08), "ctr": round(random.uniform(2.0, 3.5), 1)},
    ]

    return {
        "platform": "meta_ads",
        "currency": "USD",
        "period": {"start": period_start, "end": period_end},
        "summary": {
            "spend": spend,
            "prev_spend": prev_spend,
            "spend_change": round((spend - prev_spend) / max(prev_spend, 1) * 100, 1),
            "impressions": impressions,
            "prev_impressions": prev_impressions,
            "clicks": clicks,
            "prev_clicks": prev_clicks,
            "ctr": ctr,
            "prev_ctr": prev_ctr,
            "cpc": cpc,
            "prev_cpc": prev_cpc,
            "cpm": cpm,
            "conversions": conversions,
            "prev_conversions": prev_conversions,
            "conversions_change": round((conversions - prev_conversions) / max(prev_conversions, 1) * 100, 1),
            "cost_per_conversion": cost_per_conv,
            "prev_cost_per_conversion": prev_cost_per_conv,
            "revenue": revenue,
            "roas": roas,
            "prev_roas": prev_roas,
        },
        "daily": daily_data,
        "campaigns": campaigns,
        "age_gender": age_gender,
        "placements": placements,
        "top_ads": top_ads,
    }


def generate_all_mock_data(client_name: str, period_start: str, period_end: str) -> Dict[str, Any]:
    """Generate mock data from all platforms for a client."""
    return {
        "client_name": client_name,
        "period_start": period_start,
        "period_end": period_end,
        "ga4": generate_mock_ga4_data(client_name, period_start, period_end),
        "meta_ads": generate_mock_meta_ads_data(client_name, period_start, period_end),
    }
