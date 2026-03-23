"""
Meta Ads API client.
Pulls real ad performance data using stored OAuth tokens.
Returns the same dict shape as mock_data.generate_mock_meta_ads_data().
"""
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from services.encryption import decrypt_token

logger = logging.getLogger(__name__)

_GRAPH_API_VERSION = "v21.0"
_BASE_URL = f"https://graph.facebook.com/{_GRAPH_API_VERSION}"


async def pull_meta_ads_data(
    account_id: str,
    access_token_encrypted: str,
    period_start: str,
    period_end: str,
    connection_id: str | None = None,
    currency: str = "USD",
) -> dict[str, Any]:
    """
    Pull ad performance data from Meta Marketing API.
    Returns data in the same format as mock_data.generate_mock_meta_ads_data().
    """
    access_token = decrypt_token(access_token_encrypted)

    # Calculate previous period for comparison
    start = datetime.strptime(period_start, "%Y-%m-%d")
    end   = datetime.strptime(period_end,   "%Y-%m-%d")
    period_days = (end - start).days
    prev_end    = start - timedelta(days=1)
    prev_start  = prev_end - timedelta(days=period_days)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1 — Account-level insights — current period
        current_resp = await client.get(
            f"{_BASE_URL}/{account_id}/insights",
            params={
                "access_token": access_token,
                "time_range":   f'{{"since":"{period_start}","until":"{period_end}"}}',
                "fields":       "spend,impressions,clicks,ctr,cpc,cpm,actions,cost_per_action_type,purchase_roas",
                "level":        "account",
            },
        )
        if current_resp.status_code != 200:
            error_data = current_resp.json()
            raise Exception(
                f"Meta API error: {error_data.get('error', {}).get('message', 'Unknown error')}"
            )
        current_data = current_resp.json().get("data", [])

        # 2 — Account-level insights — previous period
        prev_resp = await client.get(
            f"{_BASE_URL}/{account_id}/insights",
            params={
                "access_token": access_token,
                "time_range":   f'{{"since":"{prev_start.strftime("%Y-%m-%d")}","until":"{prev_end.strftime("%Y-%m-%d")}"}}',
                "fields":       "spend,impressions,clicks,ctr,cpc,cpm,actions,cost_per_action_type,purchase_roas",
                "level":        "account",
            },
        )
        prev_data = prev_resp.json().get("data", []) if prev_resp.status_code == 200 else []

        # 3 — Daily breakdown for charts
        daily_resp = await client.get(
            f"{_BASE_URL}/{account_id}/insights",
            params={
                "access_token":   access_token,
                "time_range":     f'{{"since":"{period_start}","until":"{period_end}"}}',
                "fields":         "spend,impressions,clicks,actions",
                "time_increment": 1,
                "level":          "account",
            },
        )
        daily_data = daily_resp.json().get("data", []) if daily_resp.status_code == 200 else []

        # 4 — Campaign-level breakdown (top 10 by spend)
        campaign_resp = await client.get(
            f"{_BASE_URL}/{account_id}/insights",
            params={
                "access_token": access_token,
                "time_range":   f'{{"since":"{period_start}","until":"{period_end}"}}',
                "fields":       "campaign_name,spend,impressions,clicks,actions,cost_per_action_type,purchase_roas",
                "level":        "campaign",
                "sort":         "spend_descending",
                "limit":        10,
            },
        )
        campaign_data = campaign_resp.json().get("data", []) if campaign_resp.status_code == 200 else []

    return _parse_meta_responses(
        current_data, prev_data, daily_data, campaign_data,
        period_start, period_end, currency,
    )


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _get_action_value(actions_list: list | None, *action_types: str) -> int:
    """Extract a specific action value from Meta's actions array."""
    if not actions_list:
        return 0
    for action_type in action_types:
        for action in actions_list:
            if action.get("action_type") == action_type:
                return int(float(action.get("value", 0)))
    return 0


def _get_conversions(actions_list: list | None) -> int:
    """Best-effort conversion count from Meta actions array."""
    return _get_action_value(
        actions_list,
        "offsite_conversion",
        "offsite_conversion.fb_pixel_purchase",
        "purchase",
        "lead",
        "complete_registration",
    )


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def _pct_change(current: float, previous: float) -> float | None:
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def _parse_meta_responses(
    current: list,
    prev: list,
    daily: list,
    campaigns: list,
    period_start: str,
    period_end: str,
    currency: str = "USD",
) -> dict[str, Any]:
    """Parse Meta API responses into the standard report data format."""

    # Current period summary
    c = current[0] if current else {}
    spend       = _safe_float(c.get("spend"))
    impressions = int(_safe_float(c.get("impressions")))
    clicks      = int(_safe_float(c.get("clicks")))
    ctr         = _safe_float(c.get("ctr"))
    cpc         = _safe_float(c.get("cpc"))
    cpm         = _safe_float(c.get("cpm"))
    conversions = _get_conversions(c.get("actions"))
    cost_per_conv = round(spend / max(conversions, 1), 2)

    roas_data = c.get("purchase_roas", [])
    roas = (
        _safe_float(roas_data[0].get("value")) if roas_data
        else (0.0 if spend == 0 else round(conversions * 50 / max(spend, 1), 2))
    )

    # Previous period
    p = prev[0] if prev else {}
    prev_spend       = _safe_float(p.get("spend"))
    prev_impressions = int(_safe_float(p.get("impressions")))
    prev_clicks      = int(_safe_float(p.get("clicks")))
    prev_ctr         = _safe_float(p.get("ctr"))
    prev_cpc         = _safe_float(p.get("cpc"))
    prev_conversions = _get_conversions(p.get("actions"))
    prev_cost_per_conv = round(prev_spend / max(prev_conversions, 1), 2)
    prev_roas_data   = p.get("purchase_roas", [])
    prev_roas        = _safe_float(prev_roas_data[0].get("value")) if prev_roas_data else 0.0

    # Daily data for charts
    daily_parsed = [
        {
            "date":        day.get("date_start", ""),
            "spend":       _safe_float(day.get("spend")),
            "conversions": _get_conversions(day.get("actions")),
            "impressions": int(_safe_float(day.get("impressions"))),
            "clicks":      int(_safe_float(day.get("clicks"))),
        }
        for day in daily
    ]

    # Campaign breakdown
    campaigns_parsed = []
    for camp in campaigns[:5]:
        c_spend  = _safe_float(camp.get("spend"))
        c_clicks = int(_safe_float(camp.get("clicks")))
        c_conv   = _get_conversions(camp.get("actions"))
        c_roas_data = camp.get("purchase_roas", [])
        c_roas = _safe_float(c_roas_data[0].get("value")) if c_roas_data else 0.0
        campaigns_parsed.append({
            "name":        camp.get("campaign_name", "Unknown Campaign"),
            "spend":       c_spend,
            "impressions": int(_safe_float(camp.get("impressions"))),
            "clicks":      c_clicks,
            "conversions": c_conv,
            "cpc":         round(c_spend / max(c_clicks, 1), 2),
            "roas":        c_roas,
        })

    return {
        "platform": "meta_ads",
        "currency": currency,
        "period":   {"start": period_start, "end": period_end},
        "summary": {
            "spend":                    spend,
            "prev_spend":               prev_spend,
            "spend_change":             _pct_change(spend, prev_spend),
            "impressions":              impressions,
            "prev_impressions":         prev_impressions,
            "clicks":                   clicks,
            "prev_clicks":              prev_clicks,
            "ctr":                      ctr,
            "prev_ctr":                 prev_ctr,
            "cpc":                      cpc,
            "prev_cpc":                 prev_cpc,
            "cpm":                      cpm,
            "conversions":              conversions,
            "prev_conversions":         prev_conversions,
            "conversions_change":       _pct_change(conversions, prev_conversions),
            "cost_per_conversion":      cost_per_conv,
            "prev_cost_per_conversion": prev_cost_per_conv,
            "revenue":                  0.0,  # Requires value tracking configured in Meta
            "roas":                     roas,
            "prev_roas":                prev_roas,
        },
        "daily":     daily_parsed,
        "campaigns": campaigns_parsed,
    }
