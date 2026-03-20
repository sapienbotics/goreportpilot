"""
OAuth callback routes for GA4, Meta, and Google Ads.
Handles token exchange and storage after OAuth redirect.
See docs/reportpilot-auth-integration-deepdive.md for full specification.

Endpoints:
    GET  /api/auth/google/url       — Build and return the Google OAuth consent URL
    POST /api/auth/google/callback  — Exchange auth code for tokens, list GA4 properties
"""
import json
import logging
import secrets
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from config import settings
from middleware.auth import get_current_user_id
from models.schemas import (
    Ga4Property,
    GoogleAuthUrlResponse,
    GoogleCallbackRequest,
    GoogleCallbackResponse,
)
from services.encryption import encrypt_token

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Google OAuth constants ───────────────────────────────────────────────────
_GOOGLE_AUTH_BASE  = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL  = "https://oauth2.googleapis.com/token"
_GA4_ADMIN_URL     = "https://analyticsadmin.googleapis.com/v1beta/accountSummaries"

_SCOPES = " ".join([
    "https://www.googleapis.com/auth/analytics.readonly",
    "openid",
    "email",
])


# ---------------------------------------------------------------------------
# GET /api/auth/google/url
# ---------------------------------------------------------------------------

@router.get("/google/url", response_model=GoogleAuthUrlResponse)
async def get_google_auth_url(
    _user_id: str = Depends(get_current_user_id),
) -> GoogleAuthUrlResponse:
    """
    Generate a Google OAuth consent URL.
    The `state` parameter is a CSRF token the frontend must echo back in the callback.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured on this server.",
        )

    state = secrets.token_urlsafe(32)

    params = {
        "client_id":     settings.GOOGLE_CLIENT_ID,
        "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         _SCOPES,
        "access_type":   "offline",   # request refresh token
        "prompt":        "consent",   # always show consent screen → guarantees refresh token
        "state":         state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{_GOOGLE_AUTH_BASE}?{query}"

    return GoogleAuthUrlResponse(url=url, state=state)


# ---------------------------------------------------------------------------
# POST /api/auth/google/callback
# ---------------------------------------------------------------------------

@router.post("/google/callback", response_model=GoogleCallbackResponse)
async def google_callback(
    body: GoogleCallbackRequest,
    _user_id: str = Depends(get_current_user_id),
) -> GoogleCallbackResponse:
    """
    Exchange the authorization code for tokens, then list GA4 properties.

    The raw tokens are NEVER returned to the frontend.
    Instead we return:
    - A list of available GA4 properties for the user to select from.
    - An opaque `token_handle` (AES-256-GCM encrypted blob) the frontend
      echoes back when saving the connection.  The backend decrypts it then.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured on this server.",
        )

    # 1 — Exchange auth code for tokens
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code":          body.code,
                "client_id":     settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
                "grant_type":    "authorization_code",
            },
        )

    if token_resp.status_code != 200:
        logger.warning("Google token exchange failed: %s", token_resp.status_code)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code with Google.",
        )

    token_data = token_resp.json()
    access_token  = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in    = token_data.get("expires_in", 3600)

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google did not return an access token.",
        )

    # 2 — Fetch GA4 account summaries (lists all properties the user can access)
    properties: list[Ga4Property] = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            admin_resp = await client.get(
                _GA4_ADMIN_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"pageSize": 200},
            )
        if admin_resp.status_code == 200:
            summaries = admin_resp.json().get("accountSummaries", [])
            for account in summaries:
                for prop in account.get("propertySummaries", []):
                    properties.append(Ga4Property(
                        property_id=prop.get("property", ""),
                        display_name=prop.get("displayName", "Unknown Property"),
                        time_zone=None,
                        currency_code=None,
                    ))
        else:
            logger.warning(
                "GA4 Admin API returned %s — returning empty property list",
                admin_resp.status_code,
            )
    except Exception:
        logger.exception("Error fetching GA4 properties — returning empty list")

    # 3 — Encrypt tokens into an opaque handle (never log the raw values)
    token_expires_at = (
        datetime.now(tz=timezone.utc).timestamp() + expires_in
    )
    token_payload = json.dumps({
        "access_token":    access_token,
        "refresh_token":   refresh_token or "",
        "token_expires_at": token_expires_at,
    })
    token_handle = encrypt_token(token_payload)

    return GoogleCallbackResponse(
        properties=properties,
        token_handle=token_handle,
    )
