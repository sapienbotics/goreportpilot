"""
Shared Google OAuth token refresh.

Lifted from services/google_analytics.py:_get_valid_access_token, which was the
only complete implementation — google_ads.py and search_console.py each had
their own partial copy. All three now call this.

The refresh is *self-healing*: when a token is refreshed the new value is
written straight back to the connections row, so the next pull starts valid.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from config import settings
from services.encryption import decrypt_token, encrypt_token
from services.sources.base import SourceError

logger = logging.getLogger(__name__)

_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Refresh this many seconds before the recorded expiry, so a long pull can't
# expire mid-flight.
_EXPIRY_BUFFER_SECONDS = 60


def parse_expiry(raw: Any) -> float | None:
    """
    Convert a stored ``token_expires_at`` value into a unix timestamp.

    Accepts an ISO-8601 string (with or without a 'Z' suffix), a numeric
    timestamp, or None. Returns None when the value is missing or unparseable —
    callers treat None as "expired", which triggers a refresh rather than a
    failed API call.
    """
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Unparseable token_expires_at value %r — forcing refresh", raw)
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


async def _request_google_refresh(refresh_token: str) -> tuple[str, float]:
    """Exchange a refresh token for a new access token. Returns (token, expires_at)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "client_id":     settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type":    "refresh_token",
            },
        )
    if resp.status_code != 200:
        # invalid_grant means the user revoked access or the token was already
        # rotated away — no retry will fix it.
        body = resp.text[:400]
        raise SourceError(
            f"Google token refresh failed ({resp.status_code}): {body}",
            reauth_required="invalid_grant" in body,
        )
    data = resp.json()
    expires_in = data.get("expires_in", 3600)
    return data["access_token"], datetime.now(tz=timezone.utc).timestamp() + expires_in


async def get_valid_google_access_token(
    *,
    access_token_encrypted: str,
    refresh_token_encrypted: str | None,
    token_expires_at: Any,
    supabase: Any,
    connection_id: str,
    source_id: str = "google",
) -> str:
    """
    Return a usable Google access token, refreshing and persisting when needed.

    ``token_expires_at`` may be an ISO string, a unix timestamp, or None.
    """
    expires_at = parse_expiry(token_expires_at) or 0.0
    now = datetime.now(tz=timezone.utc).timestamp()

    if now < expires_at - _EXPIRY_BUFFER_SECONDS:
        return decrypt_token(access_token_encrypted)

    logger.info(
        "%s access token expired for connection %s — refreshing",
        source_id, connection_id,
    )

    if not refresh_token_encrypted:
        raise SourceError(
            "No refresh token stored — the connection must be re-authorised.",
            source_id=source_id,
            reauth_required=True,
        )

    try:
        new_token, new_expires_at = await _request_google_refresh(
            decrypt_token(refresh_token_encrypted)
        )
    except SourceError as exc:
        exc.source_id = exc.source_id or source_id
        raise

    # Persist so the next pull starts from a valid token. A write failure here
    # is non-fatal: the token in hand is still good for this request.
    try:
        supabase.table("connections").update({
            "access_token_encrypted": encrypt_token(new_token),
            "token_expires_at": datetime.fromtimestamp(
                new_expires_at, tz=timezone.utc
            ).isoformat(),
            "status": "active",
        }).eq("id", connection_id).execute()
    except Exception:  # noqa: BLE001
        logger.exception(
            "Refreshed %s token for connection %s but could not persist it",
            source_id, connection_id,
        )

    return new_token
