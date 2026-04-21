"""
User-scoped rate-limit key function for slowapi.

The rest of the app uses IP-based limits (slowapi.util.get_remote_address).
For endpoints where one agency's quota should NOT be shared across all users
behind the same NAT / office IP (e.g. the /enhance-context AI helper), we
need to key on the authenticated user instead.

Design:
  * Parse the Supabase JWT payload WITHOUT verification to extract the `sub`
    claim. Verification already happens inside the route via the
    get_current_user_id dependency, so even if a client forges a JWT to
    dodge our rate-limit key, their request still 401s — and 401s don't
    hit OpenAI, so our cost ceiling is preserved.
  * Fall back to IP when there's no Bearer token (unauthenticated callers
    or preflights shouldn't share an unlimited bucket).
  * Prefix the key so user/IP buckets never collide in the in-memory store.

No new dependency required — the JWT payload is just base64url-encoded JSON.
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Any

from fastapi import Request
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def _decode_jwt_payload(token: str) -> dict[str, Any] | None:
    """Extract the middle segment of a JWT and JSON-decode it. No signature check."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        # base64url — pad to a multiple of 4 per RFC 7515
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
        return json.loads(decoded)
    except Exception:
        return None


def user_rate_limit_key(request: Request) -> str:
    """
    Key function for @limiter.limit decorators that should scope per user.
    Shape: 'user:<uuid>' or 'ip:<addr>'.
    """
    auth = request.headers.get("authorization") or request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        payload = _decode_jwt_payload(token)
        sub = (payload or {}).get("sub")
        if sub:
            return f"user:{sub}"
    return f"ip:{get_remote_address(request)}"
