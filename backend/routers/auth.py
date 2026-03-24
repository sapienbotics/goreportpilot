"""
OAuth callback routes for GA4, Meta, and Google Ads.
Handles token exchange and storage after OAuth redirect.
See docs/reportpilot-auth-integration-deepdive.md for full specification.

Endpoints:
    GET  /api/auth/google/url       — Build and return the Google OAuth consent URL
    POST /api/auth/google/callback  — Exchange auth code for tokens, list GA4 properties
    GET  /api/auth/meta/url         — Build and return the Meta OAuth authorization URL
    POST /api/auth/meta/callback    — Exchange auth code for tokens, list Meta ad accounts
"""
import json
import logging
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from config import settings
from middleware.auth import get_current_user_id
from models.schemas import (
    Ga4Property,
    GoogleAuthUrlResponse,
    GoogleCallbackRequest,
    GoogleCallbackResponse,
    MetaAdAccount,
    MetaAuthUrlResponse,
    MetaCallbackRequest,
    MetaCallbackResponse,
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


# ── Meta OAuth constants ─────────────────────────────────────────────────────
_GRAPH_API_VERSION = "v21.0"
_META_AUTH_BASE    = f"https://www.facebook.com/{_GRAPH_API_VERSION}/dialog/oauth"
_META_TOKEN_URL    = f"https://graph.facebook.com/{_GRAPH_API_VERSION}/oauth/access_token"
_META_ME_ACCOUNTS  = f"https://graph.facebook.com/{_GRAPH_API_VERSION}/me/adaccounts"


# ---------------------------------------------------------------------------
# GET /api/auth/meta/url
# ---------------------------------------------------------------------------

@router.get("/meta/url", response_model=MetaAuthUrlResponse)
async def get_meta_auth_url(
    _user_id: str = Depends(get_current_user_id),
) -> MetaAuthUrlResponse:
    """
    Generate a Meta OAuth authorization URL.
    The `state` parameter is a CSRF token the frontend must echo back in the callback.
    """
    if not settings.META_APP_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Meta OAuth is not configured on this server.",
        )

    state = secrets.token_urlsafe(32)

    params = {
        "client_id":     settings.META_APP_ID,
        "redirect_uri":  settings.META_REDIRECT_URI,
        "scope":         "ads_read",
        "response_type": "code",
        "state":         state,
    }
    url = f"{_META_AUTH_BASE}?{urllib.parse.urlencode(params)}"

    return MetaAuthUrlResponse(url=url, state=state)


# ---------------------------------------------------------------------------
# POST /api/auth/meta/callback
# ---------------------------------------------------------------------------

@router.post("/meta/callback", response_model=MetaCallbackResponse)
async def meta_callback(
    body: MetaCallbackRequest,
    _user_id: str = Depends(get_current_user_id),
) -> MetaCallbackResponse:
    """
    Exchange the Meta authorization code for tokens, then list ad accounts.

    1. Exchange code for short-lived token.
    2. Exchange short-lived token for long-lived token (~60 days).
    3. List available ad accounts.
    4. Encrypt tokens into an opaque handle — never returned raw to the frontend.
    """
    if not settings.META_APP_ID or not settings.META_APP_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Meta OAuth is not configured on this server.",
        )

    # 1 — Exchange code for short-lived token
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_resp = await client.get(
            _META_TOKEN_URL,
            params={
                "client_id":     settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "redirect_uri":  settings.META_REDIRECT_URI,
                "code":          body.code,
            },
        )

    if token_resp.status_code != 200:
        logger.warning("Meta token exchange failed: %s", token_resp.status_code)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code with Meta.",
        )

    token_data = token_resp.json()
    if "error" in token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token exchange failed: {token_data['error'].get('message', 'Unknown error')}",
        )

    short_lived_token = token_data["access_token"]

    # 2 — Exchange short-lived token for long-lived token (~60 days)
    access_token = short_lived_token
    expires_in   = token_data.get("expires_in", 3600)

    async with httpx.AsyncClient(timeout=30.0) as client:
        ll_resp = await client.get(
            _META_TOKEN_URL,
            params={
                "grant_type":       "fb_exchange_token",
                "client_id":        settings.META_APP_ID,
                "client_secret":    settings.META_APP_SECRET,
                "fb_exchange_token": short_lived_token,
            },
        )

    if ll_resp.status_code == 200:
        ll_data = ll_resp.json()
        if "error" not in ll_data:
            access_token = ll_data["access_token"]
            expires_in   = ll_data.get("expires_in", 5184000)  # ~60 days
        else:
            logger.warning("Long-lived token exchange failed — using short-lived token")
    else:
        logger.warning("Long-lived token exchange HTTP %s — using short-lived token", ll_resp.status_code)

    # 3 — List available ad accounts
    async with httpx.AsyncClient(timeout=30.0) as client:
        accounts_resp = await client.get(
            _META_ME_ACCOUNTS,
            params={
                "access_token": access_token,
                "fields":       "id,name,account_status,currency,amount_spent",
            },
        )

    if accounts_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to list Meta ad accounts.",
        )

    accounts_data = accounts_resp.json()
    if "error" in accounts_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to list ad accounts: {accounts_data['error'].get('message', 'Unknown error')}",
        )

    ad_accounts: list[MetaAdAccount] = []
    for acct in accounts_data.get("data", []):
        ad_accounts.append(MetaAdAccount(
            account_id=acct["id"],  # e.g. "act_123456789"
            account_name=acct.get("name", "Unnamed Account"),
            currency=acct.get("currency", "USD"),
            status=acct.get("account_status", 0),
        ))

    # 4 — Encrypt tokens into opaque handle (never log raw values)
    token_expires_at = (
        datetime.now(tz=timezone.utc).timestamp() + expires_in
    )
    # Meta doesn't have separate refresh tokens — the long-lived token IS the token.
    # Store same token in both fields for compatibility with the connections schema.
    token_payload = json.dumps({
        "access_token":     access_token,
        "refresh_token":    access_token,
        "token_expires_at": token_expires_at,
    })
    token_handle = encrypt_token(token_payload)

    return MetaCallbackResponse(
        ad_accounts=ad_accounts,
        token_handle=token_handle,
        expires_in=expires_in,
    )


# ── Google Ads + Search Console OAuth ────────────────────────────────────────
# Uses the same Google OAuth flow but requests additional scopes.
# Clients must separately initiate a Google Ads / GSC OAuth to grant these scopes.

_GOOGLE_ADS_SCOPES = " ".join([
    "https://www.googleapis.com/auth/adwords",
    "openid",
    "email",
])

_SEARCH_CONSOLE_SCOPES = " ".join([
    "https://www.googleapis.com/auth/webmasters.readonly",
    "openid",
    "email",
])


# ---------------------------------------------------------------------------
# GET /api/auth/google-ads/url
# ---------------------------------------------------------------------------

@router.get("/google-ads/url")
async def get_google_ads_auth_url(
    _user_id: str = Depends(get_current_user_id),
) -> dict:
    """Generate a Google OAuth URL requesting Google Ads scopes."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Google OAuth is not configured.")

    state = secrets.token_urlsafe(32)
    params = {
        "client_id":     settings.GOOGLE_CLIENT_ID,
        "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         _GOOGLE_ADS_SCOPES,
        "access_type":   "offline",
        "prompt":        "consent",
        "state":         state,
    }
    url = _GOOGLE_AUTH_BASE + "?" + "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    return {"url": url, "state": state}


# ---------------------------------------------------------------------------
# POST /api/auth/google-ads/callback
# ---------------------------------------------------------------------------

@router.post("/google-ads/callback")
async def google_ads_callback(
    body: GoogleCallbackRequest,
    _user_id: str = Depends(get_current_user_id),
) -> dict:
    """Exchange auth code for Google Ads tokens and list accessible accounts."""
    # Token exchange (same as GA4)
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_resp = await client.post(_GOOGLE_TOKEN_URL, data={
            "code":          body.code,
            "client_id":     settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
            "grant_type":    "authorization_code",
        })
    if token_resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Failed to exchange Google Ads auth code.")
    token_data = token_resp.json()
    access_token  = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in    = int(token_data.get("expires_in", 3600))

    # List accessible Google Ads accounts
    try:
        from services.google_ads import list_accessible_accounts  # noqa: PLC0415
        from services.encryption import encrypt_token as _enc  # noqa: PLC0415
        import json as _json  # noqa: PLC0415
        # Temporarily encrypt tokens to pass to service
        _payload = _json.dumps({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expires_at": (datetime.now(tz=timezone.utc).timestamp() + expires_in),
        })
        _handle = encrypt_token(_payload)
        accounts = await list_accessible_accounts(_handle, _handle)
    except Exception as exc:
        logger.warning("Could not list Google Ads accounts: %s", exc)
        accounts = []

    token_payload = json.dumps({
        "access_token":     access_token,
        "refresh_token":    refresh_token,
        "token_expires_at": datetime.now(tz=timezone.utc).timestamp() + expires_in,
    })
    token_handle = encrypt_token(token_payload)

    return {
        "accounts":     accounts,
        "token_handle": token_handle,
        "expires_in":   expires_in,
    }


# ---------------------------------------------------------------------------
# GET /api/auth/search-console/url
# ---------------------------------------------------------------------------

@router.get("/search-console/url")
async def get_search_console_auth_url(
    _user_id: str = Depends(get_current_user_id),
) -> dict:
    """Generate a Google OAuth URL requesting Search Console scopes."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Google OAuth is not configured.")

    state = secrets.token_urlsafe(32)
    params = {
        "client_id":     settings.GOOGLE_CLIENT_ID,
        "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         _SEARCH_CONSOLE_SCOPES,
        "access_type":   "offline",
        "prompt":        "consent",
        "state":         state,
    }
    url = _GOOGLE_AUTH_BASE + "?" + "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    return {"url": url, "state": state}


# ---------------------------------------------------------------------------
# POST /api/auth/search-console/callback
# ---------------------------------------------------------------------------

@router.post("/search-console/callback")
async def search_console_callback(
    body: GoogleCallbackRequest,
    _user_id: str = Depends(get_current_user_id),
) -> dict:
    """Exchange auth code for Search Console tokens and list verified sites."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_resp = await client.post(_GOOGLE_TOKEN_URL, data={
            "code":          body.code,
            "client_id":     settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
            "grant_type":    "authorization_code",
        })
    if token_resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Failed to exchange Search Console auth code.")
    token_data    = token_resp.json()
    access_token  = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in    = int(token_data.get("expires_in", 3600))

    # List verified sites
    try:
        from services.search_console import list_verified_sites  # noqa: PLC0415
        sites = await list_verified_sites(access_token)
    except Exception as exc:
        logger.warning("Could not list Search Console sites: %s", exc)
        sites = []

    token_payload = json.dumps({
        "access_token":     access_token,
        "refresh_token":    refresh_token,
        "token_expires_at": datetime.now(tz=timezone.utc).timestamp() + expires_in,
    })
    token_handle = encrypt_token(token_payload)

    return {
        "sites":        sites,
        "token_handle": token_handle,
        "expires_in":   expires_in,
    }
