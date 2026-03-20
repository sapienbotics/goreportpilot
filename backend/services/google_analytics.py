"""
Google Analytics 4 (GA4) Data API client.
Pulls session, user, conversion, and traffic data for a given property and date range.
Falls back to mock data when a real connection is not available.

See docs/reportpilot-auth-integration-deepdive.md for the full OAuth + data flow.
"""
import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from config import settings
from services.encryption import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

_GA4_DATA_URL = "https://analyticsdata.googleapis.com/v1beta/{property}:runReport"
_TOKEN_URL    = "https://oauth2.googleapis.com/token"


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

async def _refresh_access_token(refresh_token: str) -> tuple[str, float]:
    """
    Use the stored refresh token to get a new access token.
    Returns (new_access_token, new_expires_at_unix_timestamp).
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "client_id":     settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type":    "refresh_token",
            },
        )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Token refresh failed with status {resp.status_code}: {resp.text}"
        )
    data         = resp.json()
    access_token = data["access_token"]
    expires_in   = data.get("expires_in", 3600)
    expires_at   = datetime.now(tz=timezone.utc).timestamp() + expires_in
    return access_token, expires_at


async def _get_valid_access_token(
    access_token_encrypted: str,
    refresh_token_encrypted: str,
    token_expires_at: float | None,
    supabase: Any,
    connection_id: str,
) -> str:
    """
    Return a valid access token, refreshing automatically when expired.

    Accepts the two separate DB columns (access_token_encrypted,
    refresh_token_encrypted) and the token_expires_at unix timestamp.
    Persists the refreshed access token back to Supabase if a refresh occurs.
    """
    now        = datetime.now(tz=timezone.utc).timestamp()
    expires_at = token_expires_at or 0

    # Refresh 60 seconds before actual expiry as a buffer
    if now >= expires_at - 60:
        logger.info("GA4 access token expired for connection %s — refreshing", connection_id)

        if not refresh_token_encrypted:
            raise RuntimeError(
                "No refresh token stored — the user must re-authorise the GA4 connection."
            )
        refresh_token = decrypt_token(refresh_token_encrypted)
        new_access_token, new_expires_at = await _refresh_access_token(refresh_token)

        # Write the refreshed access token back to DB
        supabase.table("connections").update({
            "access_token_encrypted": encrypt_token(new_access_token),
            "token_expires_at": datetime.fromtimestamp(
                new_expires_at, tz=timezone.utc
            ).isoformat(),
            "status": "active",
        }).eq("id", connection_id).execute()

        return new_access_token

    return decrypt_token(access_token_encrypted)


# ---------------------------------------------------------------------------
# GA4 Data API helpers
# ---------------------------------------------------------------------------

async def _run_ga4_report(
    access_token: str,
    property_id: str,
    request_body: dict,
) -> dict:
    """Execute a single GA4 runReport call and return the JSON response."""
    url = _GA4_DATA_URL.format(property=property_id)
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            json=request_body,
        )
    if resp.status_code == 401:
        raise PermissionError("GA4 access token is invalid or expired.")
    if resp.status_code != 200:
        raise RuntimeError(
            f"GA4 API error {resp.status_code}: {resp.text[:400]}"
        )
    return resp.json()


def _dim_val(row: dict, index: int) -> str:
    dims = row.get("dimensionValues", [])
    return dims[index]["value"] if index < len(dims) else ""


def _met_val(row: dict, index: int) -> float:
    mets = row.get("metricValues", [])
    return float(mets[index]["value"]) if index < len(mets) else 0.0


def _parse_ga4_responses(
    main_resp: dict,
    prev_resp: dict,
    daily_resp: dict,
    sources_resp: dict,
    pages_resp: dict,
) -> dict:
    """
    Normalise GA4 API responses into the same dict shape that mock_data.py produces
    so the rest of the pipeline (AI narrative, charts, report generator) is unchanged.
    """

    def _totals(resp: dict) -> dict:
        rows = resp.get("rows", [])
        if not rows:
            return {}
        row = rows[0]
        return {
            "sessions":             _met_val(row, 0),
            "users":                _met_val(row, 1),
            "pageviews":            _met_val(row, 2),
            "conversions":          _met_val(row, 3),
            "bounce_rate":          _met_val(row, 4),
            "avg_session_duration": _met_val(row, 5),
        }

    current  = _totals(main_resp)
    previous = _totals(prev_resp)

    def _pct_change(curr: float, prev: float) -> float | None:
        if prev == 0:
            return None
        return round((curr - prev) / prev * 100, 1)

    summary = {
        "sessions":             round(current.get("sessions", 0)),
        "sessions_change":      _pct_change(current.get("sessions", 0),   previous.get("sessions", 0)),
        "users":                round(current.get("users", 0)),
        "users_change":         _pct_change(current.get("users", 0),      previous.get("users", 0)),
        "pageviews":            round(current.get("pageviews", 0)),
        "conversions":          round(current.get("conversions", 0)),
        "conversions_change":   _pct_change(current.get("conversions", 0), previous.get("conversions", 0)),
        "bounce_rate":          round(current.get("bounce_rate", 0), 1),
        "avg_session_duration": round(current.get("avg_session_duration", 0), 1),
    }

    # Daily time series
    daily_data = []
    for row in daily_resp.get("rows", []):
        date_raw = _dim_val(row, 0)   # "YYYYMMDD"
        try:
            formatted = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:]}"
        except Exception:
            formatted = date_raw
        daily_data.append({
            "date":     formatted,
            "sessions": round(_met_val(row, 0)),
            "users":    round(_met_val(row, 1)),
        })
    daily_data.sort(key=lambda x: x["date"])

    # Traffic sources
    traffic_sources: dict[str, int] = {}
    for row in sources_resp.get("rows", []):
        medium   = _dim_val(row, 0) or "other"
        sessions = round(_met_val(row, 0))
        traffic_sources[medium] = traffic_sources.get(medium, 0) + sessions

    # Top pages
    top_pages = []
    for row in pages_resp.get("rows", [])[:10]:
        top_pages.append({
            "page":      _dim_val(row, 0),
            "sessions":  round(_met_val(row, 0)),
            "pageviews": round(_met_val(row, 1)),
        })

    return {
        "summary":         summary,
        "daily_data":      daily_data,
        "traffic_sources": traffic_sources,
        "top_pages":       top_pages,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def pull_ga4_data(
    access_token_encrypted: str,
    refresh_token_encrypted: str,
    token_expires_at: float | None,
    property_id: str,
    period_start: str,   # "YYYY-MM-DD"
    period_end: str,
    connection_id: str,
    supabase: Any,
) -> dict:
    """
    Pull real GA4 data for the given property and date range.

    Accepts the two separate DB columns (access_token_encrypted,
    refresh_token_encrypted) and the token_expires_at unix timestamp.

    Returns the same dict shape as services.mock_data.generate_mock_ga4_data()
    so the report pipeline requires no changes.

    Raises RuntimeError / PermissionError on unrecoverable API failures.
    """
    access_token = await _get_valid_access_token(
        access_token_encrypted=access_token_encrypted,
        refresh_token_encrypted=refresh_token_encrypted,
        token_expires_at=token_expires_at,
        supabase=supabase,
        connection_id=connection_id,
    )

    metrics_base = [
        {"name": "sessions"},
        {"name": "totalUsers"},
        {"name": "screenPageViews"},
        {"name": "conversions"},
        {"name": "bounceRate"},
        {"name": "averageSessionDuration"},
    ]

    current_range  = [{"startDate": period_start, "endDate": period_end}]

    # Previous period — same length, immediately before
    start_dt   = date.fromisoformat(period_start)
    end_dt     = date.fromisoformat(period_end)
    span       = (end_dt - start_dt).days + 1
    prev_end   = start_dt - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span - 1)
    prev_range = [{"startDate": prev_start.isoformat(), "endDate": prev_end.isoformat()}]

    main_resp, prev_resp, daily_resp, sources_resp, pages_resp = await asyncio.gather(
        _run_ga4_report(access_token, property_id, {
            "dateRanges": current_range,
            "metrics":    metrics_base,
        }),
        _run_ga4_report(access_token, property_id, {
            "dateRanges": prev_range,
            "metrics":    metrics_base,
        }),
        _run_ga4_report(access_token, property_id, {
            "dateRanges": current_range,
            "dimensions": [{"name": "date"}],
            "metrics":    [{"name": "sessions"}, {"name": "totalUsers"}],
            "orderBys":   [{"dimension": {"dimensionName": "date"}}],
        }),
        _run_ga4_report(access_token, property_id, {
            "dateRanges": current_range,
            "dimensions": [{"name": "sessionMedium"}],
            "metrics":    [{"name": "sessions"}],
            "orderBys":   [{"metric": {"metricName": "sessions"}, "desc": True}],
            "limit":      10,
        }),
        _run_ga4_report(access_token, property_id, {
            "dateRanges": current_range,
            "dimensions": [{"name": "pagePath"}],
            "metrics":    [{"name": "sessions"}, {"name": "screenPageViews"}],
            "orderBys":   [{"metric": {"metricName": "sessions"}, "desc": True}],
            "limit":      10,
        }),
    )

    return _parse_ga4_responses(main_resp, prev_resp, daily_resp, sources_resp, pages_resp)
