"""
Google Search Console API service — pulls organic search performance.
Uses the google-api-python-client library.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx
from config import settings
from services.encryption import decrypt_token

logger = logging.getLogger(__name__)

_GSC_BASE = "https://www.googleapis.com/webmasters/v3"
_TOKEN_REFRESH_URL = "https://oauth2.googleapis.com/token"
_TOKEN_EXPIRY_BUFFER_SECONDS = 300  # refresh if expiring within 5 minutes


# ---------------------------------------------------------------------------
# Token refresh helper
# ---------------------------------------------------------------------------

async def _maybe_refresh_token(
    access_token: str,
    refresh_token: str,
    token_expires_at: Optional[float],
) -> str:
    """
    Return a valid access token, refreshing it if it is about to expire.

    Parameters
    ----------
    access_token:
        Plaintext (already decrypted) access token.
    refresh_token:
        Plaintext refresh token.
    token_expires_at:
        Unix timestamp when the current access token expires.
        If None the token is assumed to still be valid.

    Returns
    -------
    A valid access token (either the original or a freshly obtained one).
    """
    if token_expires_at is None:
        return access_token

    if time.time() < token_expires_at - _TOKEN_EXPIRY_BUFFER_SECONDS:
        return access_token

    logger.info("Access token near expiry — refreshing via OAuth2 token endpoint.")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            _TOKEN_REFRESH_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        data = response.json()
        new_token: str = data["access_token"]
        logger.info("Access token refreshed successfully.")
        return new_token


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

async def list_verified_sites(access_token: str) -> list[dict]:
    """
    Return all Search Console properties verified for the given access token.

    Calls ``GET https://www.googleapis.com/webmasters/v3/sites`` and returns
    a list of dicts::

        [{"site_url": str, "permission_level": str}]

    ``permission_level`` is one of: siteOwner, siteFullUser, siteRestrictedUser,
    siteUnverifiedUser.

    Returns an empty list on any HTTP or parsing error.
    """
    url = f"{_GSC_BASE}/sites"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        sites = data.get("siteEntry", [])
        result = [
            {
                "site_url": entry.get("siteUrl", ""),
                "permission_level": entry.get("permissionLevel", ""),
            }
            for entry in sites
            if entry.get("siteUrl")
        ]
        logger.info("Found %d verified Search Console sites.", len(result))
        return result

    except httpx.HTTPStatusError as exc:
        logger.error(
            "list_verified_sites HTTP error %s: %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        return []
    except Exception as exc:
        logger.error("list_verified_sites failed: %s", exc)
        return []


async def list_verified_sites_from_encrypted(
    access_token_encrypted: str,
    refresh_token_encrypted: str,
) -> list[dict]:
    """
    Decrypt tokens and return verified Search Console properties.

    Convenience wrapper around :func:`list_verified_sites` for callers that
    hold encrypted tokens from the connections table.
    """
    access_token = decrypt_token(access_token_encrypted)
    refresh_token = decrypt_token(refresh_token_encrypted)  # noqa: F841 — available for future refresh logic
    return await list_verified_sites(access_token)


# ---------------------------------------------------------------------------
# Main data pull
# ---------------------------------------------------------------------------

async def pull_search_console_data(
    access_token_encrypted: str,
    refresh_token_encrypted: str,
    site_url: str,
    period_start: str,
    period_end: str,
    token_expires_at: Optional[float] = None,
) -> dict:
    """
    Pull organic search performance data from Google Search Console.

    Parameters
    ----------
    access_token_encrypted:
        AES-256-GCM encrypted access token.
    refresh_token_encrypted:
        AES-256-GCM encrypted refresh token.
    site_url:
        The verified property URL, e.g. ``https://example.com/`` or
        ``sc-domain:example.com``.
    period_start:
        Start date in 'YYYY-MM-DD' format (inclusive).
    period_end:
        End date in 'YYYY-MM-DD' format (inclusive).
    token_expires_at:
        Unix timestamp of access-token expiry.  The token is refreshed
        automatically if it expires within 5 minutes.

    Returns
    -------
    dict matching the demo_data.py search_console structure::

        {
            "summary": {
                "clicks": int,
                "prev_clicks": int,
                "impressions": int,
                "ctr": float,
                "avg_position": float,
            },
            "top_queries": [{"query", "clicks", "impressions", "ctr", "position"}],
            "top_pages":   [{"page",  "clicks", "impressions", "ctr"}],
            "daily":       [{"date",  "clicks", "impressions", "ctr"}],
        }

    Returns an empty dict on any failure.
    """
    try:
        access_token = decrypt_token(access_token_encrypted)
        refresh_token = decrypt_token(refresh_token_encrypted)

        # Refresh token if near expiry
        access_token = await _maybe_refresh_token(
            access_token, refresh_token, token_expires_at
        )

        # URL-encode the site_url for use in the path segment
        site_url_encoded = quote(site_url, safe="")
        query_url = (
            f"{_GSC_BASE}/sites/{site_url_encoded}/searchAnalytics/query"
        )
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # ------------------------------------------------------------------
        # Previous period — same duration as the requested period
        # ------------------------------------------------------------------
        start_dt = datetime.strptime(period_start, "%Y-%m-%d")
        end_dt = datetime.strptime(period_end, "%Y-%m-%d")
        duration = (end_dt - start_dt).days + 1
        prev_end_dt = start_dt - timedelta(days=1)
        prev_start_dt = prev_end_dt - timedelta(days=duration - 1)
        prev_start = prev_start_dt.strftime("%Y-%m-%d")
        prev_end = prev_end_dt.strftime("%Y-%m-%d")

        # ------------------------------------------------------------------
        # Helper: run a single Search Analytics query
        # ------------------------------------------------------------------
        async def _query(payload: dict) -> list[dict]:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(query_url, headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json().get("rows", [])

        # ------------------------------------------------------------------
        # 1. Top queries (current period)
        # ------------------------------------------------------------------
        top_queries_raw = await _query(
            {
                "startDate": period_start,
                "endDate": period_end,
                "dimensions": ["query"],
                "rowLimit": 20,
                "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
            }
        )

        top_queries = [
            {
                "query": row.get("keys", [""])[0],
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "ctr": round(float(row.get("ctr", 0)) * 100, 2),
                "position": round(float(row.get("position", 0)), 1),
            }
            for row in top_queries_raw
        ]

        # ------------------------------------------------------------------
        # 2. Top pages (current period)
        # ------------------------------------------------------------------
        top_pages_raw = await _query(
            {
                "startDate": period_start,
                "endDate": period_end,
                "dimensions": ["page"],
                "rowLimit": 10,
                "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
            }
        )

        top_pages = [
            {
                "page": row.get("keys", [""])[0],
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "ctr": round(float(row.get("ctr", 0)) * 100, 2),
            }
            for row in top_pages_raw
        ]

        # ------------------------------------------------------------------
        # 3. Daily breakdown (current period)
        # ------------------------------------------------------------------
        daily_raw = await _query(
            {
                "startDate": period_start,
                "endDate": period_end,
                "dimensions": ["date"],
                "orderBy": [{"fieldName": "date", "sortOrder": "ASCENDING"}],
            }
        )

        daily = [
            {
                "date": row.get("keys", [""])[0],
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "ctr": round(float(row.get("ctr", 0)) * 100, 2),
            }
            for row in daily_raw
        ]

        # ------------------------------------------------------------------
        # 4. Current-period summary (aggregate — no dimensions)
        # ------------------------------------------------------------------
        summary_raw = await _query(
            {
                "startDate": period_start,
                "endDate": period_end,
            }
        )

        total_clicks = 0
        total_impressions = 0
        total_ctr = 0.0
        avg_position = 0.0

        if summary_raw:
            row = summary_raw[0]
            total_clicks = int(row.get("clicks", 0))
            total_impressions = int(row.get("impressions", 0))
            total_ctr = round(float(row.get("ctr", 0)) * 100, 2)
            avg_position = round(float(row.get("position", 0)), 1)
        else:
            # Derive from daily rows when aggregate query returns no rows
            for d in daily:
                total_clicks += d["clicks"]
                total_impressions += d["impressions"]
            total_ctr = (
                round(total_clicks / total_impressions * 100, 2)
                if total_impressions > 0
                else 0.0
            )

        # ------------------------------------------------------------------
        # 5. Previous period — clicks only (for summary comparison)
        # ------------------------------------------------------------------
        prev_clicks = 0
        try:
            prev_summary_raw = await _query(
                {
                    "startDate": prev_start,
                    "endDate": prev_end,
                }
            )
            if prev_summary_raw:
                prev_clicks = int(prev_summary_raw[0].get("clicks", 0))
            else:
                # Fallback: sum daily rows for previous period
                prev_daily_raw = await _query(
                    {
                        "startDate": prev_start,
                        "endDate": prev_end,
                        "dimensions": ["date"],
                    }
                )
                prev_clicks = sum(int(r.get("clicks", 0)) for r in prev_daily_raw)
        except Exception as prev_exc:
            logger.warning("Could not fetch previous period clicks: %s", prev_exc)

        # ------------------------------------------------------------------
        # Assemble result
        # ------------------------------------------------------------------
        result = {
            "summary": {
                "clicks": total_clicks,
                "prev_clicks": prev_clicks,
                "impressions": total_impressions,
                "ctr": total_ctr,
                "avg_position": avg_position,
            },
            "top_queries": top_queries,
            "top_pages": top_pages,
            "daily": daily,
        }

        logger.info(
            "Search Console data pulled for %s: clicks=%d, queries=%d, pages=%d",
            site_url,
            total_clicks,
            len(top_queries),
            len(top_pages),
        )
        return result

    except httpx.HTTPStatusError as exc:
        logger.error(
            "pull_search_console_data HTTP error %s for site %s: %s",
            exc.response.status_code,
            site_url,
            exc.response.text[:300],
        )
        return {}
    except Exception as exc:
        logger.error(
            "pull_search_console_data failed for site %s: %s",
            site_url,
            exc,
        )
        return {}
