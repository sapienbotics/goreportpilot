"""
Google Ads API service — pulls campaign performance data.
Uses the google-ads Python client library.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from config import settings
from services.encryption import decrypt_token

logger = logging.getLogger(__name__)


def _build_credentials(access_token: str, refresh_token: str) -> dict:
    """
    Build a credential configuration dict suitable for GoogleAdsClient.

    The dict follows the format expected by
    ``google.ads.googleads.client.GoogleAdsClient.load_from_dict()``.
    """
    return {
        "developer_token": settings.google_ads_developer_token,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "refresh_token": refresh_token,
        "access_token": access_token,
        "use_proto_plus": True,
    }


def list_accessible_accounts(
    access_token_encrypted: str,
    refresh_token_encrypted: str,
) -> list[dict]:
    """
    Return a list of Google Ads accounts accessible to the authenticated user.

    Each entry contains:
        customer_id   — numeric string (without hyphens)
        name          — descriptive account name
        currency_code — ISO 4217 currency code (e.g. 'USD', 'INR')
        time_zone     — IANA time zone string (e.g. 'America/New_York')

    Returns up to 20 accounts.  Returns an empty list on failure rather than
    raising, so the caller can surface a graceful error to the user.
    """
    try:
        from google.ads.googleads.client import GoogleAdsClient  # type: ignore

        access_token = decrypt_token(access_token_encrypted)
        refresh_token = decrypt_token(refresh_token_encrypted)

        credentials = _build_credentials(access_token, refresh_token)
        client = GoogleAdsClient.load_from_dict(credentials)

        customer_service = client.get_service("CustomerService")
        response = customer_service.list_accessible_customers()

        resource_names: list[str] = list(response.resource_names)[:20]
        if not resource_names:
            return []

        accounts: list[dict] = []
        ga_service = client.get_service("GoogleAdsService")

        for resource_name in resource_names:
            # resource_name format: "customers/{customer_id}"
            customer_id = resource_name.split("/")[-1]
            try:
                query = """
                    SELECT
                        customer.id,
                        customer.descriptive_name,
                        customer.currency_code,
                        customer.time_zone
                    FROM customer
                    LIMIT 1
                """
                stream = ga_service.search_stream(
                    customer_id=customer_id, query=query
                )
                for batch in stream:
                    for row in batch.results:
                        accounts.append(
                            {
                                "customer_id": str(row.customer.id),
                                "name": row.customer.descriptive_name or customer_id,
                                "currency_code": row.customer.currency_code or "USD",
                                "time_zone": row.customer.time_zone or "UTC",
                            }
                        )
                        break  # only one row expected
            except Exception as inner_exc:
                logger.warning(
                    "Could not fetch details for customer %s: %s",
                    customer_id,
                    inner_exc,
                )
                # Still include the account with minimal info
                accounts.append(
                    {
                        "customer_id": customer_id,
                        "name": customer_id,
                        "currency_code": "USD",
                        "time_zone": "UTC",
                    }
                )

        logger.info("Found %d accessible Google Ads accounts.", len(accounts))
        return accounts

    except Exception as exc:
        logger.error("list_accessible_accounts failed: %s", exc)
        return []


def pull_google_ads_data(
    access_token_encrypted: str,
    refresh_token_encrypted: str,
    customer_id: str,
    period_start: str,
    period_end: str,
    token_expires_at: Optional[float] = None,
) -> dict:
    """
    Pull Google Ads campaign performance data for a given date range.

    Parameters
    ----------
    access_token_encrypted:
        AES-256-GCM encrypted access token (from the connections table).
    refresh_token_encrypted:
        AES-256-GCM encrypted refresh token.
    customer_id:
        Google Ads customer ID (numeric string, with or without hyphens).
    period_start:
        Start date in 'YYYY-MM-DD' format (inclusive).
    period_end:
        End date in 'YYYY-MM-DD' format (inclusive).
    token_expires_at:
        Unix timestamp of access-token expiry.  Not used directly here
        because the google-ads client handles refresh automatically via
        the refresh_token; included for interface consistency.

    Returns
    -------
    dict matching the demo_data.py google_ads structure:

        {
            "currency": "USD",
            "summary": {
                "spend": float,
                "prev_spend": float,
                "spend_change": float,
                "impressions": int,
                "clicks": int,
                "ctr": float,
                "conversions": float,
                "cost_per_conversion": float,
                "roas": float,
            },
            "campaigns": [
                {
                    "name": str,
                    "spend": float,
                    "impressions": int,
                    "clicks": int,
                    "conversions": float,
                    "ctr": float,
                    "cpc": float,
                }
            ],
            "daily": [{"date": str, "spend": float, "clicks": int, "conversions": float}],
            "search_terms": [{"term": str, "impressions": int, "clicks": int,
                               "conversions": float, "ctr": float}],
        }

    Returns an empty dict on any failure.
    """
    try:
        from google.ads.googleads.client import GoogleAdsClient  # type: ignore

        access_token = decrypt_token(access_token_encrypted)
        refresh_token = decrypt_token(refresh_token_encrypted)

        # Strip hyphens — GoogleAdsClient expects plain numeric ID
        customer_id_clean = customer_id.replace("-", "")

        credentials = _build_credentials(access_token, refresh_token)
        client = GoogleAdsClient.load_from_dict(credentials)
        ga_service = client.get_service("GoogleAdsService")

        # ------------------------------------------------------------------
        # Helper: micros → currency float
        # ------------------------------------------------------------------
        def _micros(val: Any) -> float:
            return float(val) / 1_000_000

        # ------------------------------------------------------------------
        # 1. Campaign performance for the current period
        # ------------------------------------------------------------------
        campaign_query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.all_conversions_value
            FROM campaign
            WHERE segments.date BETWEEN '{period_start}' AND '{period_end}'
              AND campaign.status = 'ENABLED'
            ORDER BY metrics.cost_micros DESC
            LIMIT 20
        """

        campaigns: list[dict] = []
        total_spend = 0.0
        total_impressions = 0
        total_clicks = 0
        total_conversions = 0.0
        total_conversion_value = 0.0
        currency_code = "USD"

        stream = ga_service.search_stream(
            customer_id=customer_id_clean, query=campaign_query
        )
        for batch in stream:
            for row in batch.results:
                spend = _micros(row.metrics.cost_micros)
                impressions = int(row.metrics.impressions)
                clicks = int(row.metrics.clicks)
                conversions = float(row.metrics.conversions)
                conv_value = float(row.metrics.all_conversions_value)
                ctr = (clicks / impressions * 100) if impressions > 0 else 0.0
                cpc = (spend / clicks) if clicks > 0 else 0.0

                campaigns.append(
                    {
                        "name": row.campaign.name,
                        "spend": round(spend, 2),
                        "impressions": impressions,
                        "clicks": clicks,
                        "conversions": round(conversions, 2),
                        "ctr": round(ctr, 2),
                        "cpc": round(cpc, 2),
                    }
                )

                total_spend += spend
                total_impressions += impressions
                total_clicks += clicks
                total_conversions += conversions
                total_conversion_value += conv_value

        # ------------------------------------------------------------------
        # 2. Account-level summary (also gives currency code)
        # ------------------------------------------------------------------
        account_query = """
            SELECT
                customer.currency_code,
                metrics.cost_micros
            FROM customer
            LIMIT 1
        """
        try:
            stream = ga_service.search_stream(
                customer_id=customer_id_clean, query=account_query
            )
            for batch in stream:
                for row in batch.results:
                    currency_code = row.customer.currency_code or "USD"
                    break
        except Exception as acc_exc:
            logger.warning("Could not fetch account currency: %s", acc_exc)

        # ------------------------------------------------------------------
        # 3. Daily breakdown
        # ------------------------------------------------------------------
        daily_query = f"""
            SELECT
                segments.date,
                metrics.cost_micros,
                metrics.clicks,
                metrics.conversions
            FROM campaign
            WHERE segments.date BETWEEN '{period_start}' AND '{period_end}'
              AND campaign.status = 'ENABLED'
            ORDER BY segments.date ASC
        """

        daily_map: dict[str, dict] = {}
        stream = ga_service.search_stream(
            customer_id=customer_id_clean, query=daily_query
        )
        for batch in stream:
            for row in batch.results:
                date_str = row.segments.date
                if date_str not in daily_map:
                    daily_map[date_str] = {
                        "date": date_str,
                        "spend": 0.0,
                        "clicks": 0,
                        "conversions": 0.0,
                    }
                daily_map[date_str]["spend"] += _micros(row.metrics.cost_micros)
                daily_map[date_str]["clicks"] += int(row.metrics.clicks)
                daily_map[date_str]["conversions"] += float(row.metrics.conversions)

        daily = [
            {
                "date": d["date"],
                "spend": round(d["spend"], 2),
                "clicks": d["clicks"],
                "conversions": round(d["conversions"], 2),
            }
            for d in sorted(daily_map.values(), key=lambda x: x["date"])
        ]

        # ------------------------------------------------------------------
        # 4. Search terms
        # ------------------------------------------------------------------
        search_term_query = f"""
            SELECT
                segments.keyword.text,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions
            FROM search_term_view
            WHERE segments.date BETWEEN '{period_start}' AND '{period_end}'
            ORDER BY metrics.clicks DESC
            LIMIT 20
        """

        search_terms: list[dict] = []
        try:
            stream = ga_service.search_stream(
                customer_id=customer_id_clean, query=search_term_query
            )
            for batch in stream:
                for row in batch.results:
                    imp = int(row.metrics.impressions)
                    clk = int(row.metrics.clicks)
                    ctr = (clk / imp * 100) if imp > 0 else 0.0
                    search_terms.append(
                        {
                            "term": row.segments.keyword.text or "(not provided)",
                            "impressions": imp,
                            "clicks": clk,
                            "conversions": round(float(row.metrics.conversions), 2),
                            "ctr": round(ctr, 2),
                        }
                    )
        except Exception as st_exc:
            logger.warning("Could not fetch search terms: %s", st_exc)

        # ------------------------------------------------------------------
        # 5. Previous period — same duration
        # ------------------------------------------------------------------
        prev_spend = 0.0
        try:
            start_dt = datetime.strptime(period_start, "%Y-%m-%d")
            end_dt = datetime.strptime(period_end, "%Y-%m-%d")
            duration = (end_dt - start_dt).days + 1
            prev_end_dt = start_dt - timedelta(days=1)
            prev_start_dt = prev_end_dt - timedelta(days=duration - 1)
            prev_start = prev_start_dt.strftime("%Y-%m-%d")
            prev_end = prev_end_dt.strftime("%Y-%m-%d")

            prev_query = f"""
                SELECT
                    metrics.cost_micros
                FROM campaign
                WHERE segments.date BETWEEN '{prev_start}' AND '{prev_end}'
                  AND campaign.status = 'ENABLED'
            """
            stream = ga_service.search_stream(
                customer_id=customer_id_clean, query=prev_query
            )
            for batch in stream:
                for row in batch.results:
                    prev_spend += _micros(row.metrics.cost_micros)
        except Exception as prev_exc:
            logger.warning("Could not fetch previous period data: %s", prev_exc)

        # ------------------------------------------------------------------
        # Assemble summary
        # ------------------------------------------------------------------
        spend_change = 0.0
        if prev_spend > 0:
            spend_change = round(
                ((total_spend - prev_spend) / abs(prev_spend)) * 100, 2
            )

        overall_ctr = (
            (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0
        )
        cost_per_conversion = (
            (total_spend / total_conversions) if total_conversions > 0 else 0.0
        )
        roas = (
            (total_conversion_value / total_spend) if total_spend > 0 else 0.0
        )

        result = {
            "currency": currency_code,
            "summary": {
                "spend": round(total_spend, 2),
                "prev_spend": round(prev_spend, 2),
                "spend_change": spend_change,
                "impressions": total_impressions,
                "clicks": total_clicks,
                "ctr": round(overall_ctr, 2),
                "conversions": round(total_conversions, 2),
                "cost_per_conversion": round(cost_per_conversion, 2),
                "roas": round(roas, 2),
            },
            "campaigns": campaigns,
            "daily": daily,
            "search_terms": search_terms,
        }

        logger.info(
            "Google Ads data pulled for customer %s: spend=%.2f, campaigns=%d",
            customer_id_clean,
            total_spend,
            len(campaigns),
        )
        return result

    except Exception as exc:
        logger.error(
            "pull_google_ads_data failed for customer %s: %s",
            customer_id,
            exc,
        )
        return {}
