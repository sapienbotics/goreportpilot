"""
JWT authentication dependency for FastAPI endpoints.
Verifies the Supabase-issued JWT in the Authorization header
and returns the authenticated user's ID.

Usage in a router:
    from middleware.auth import get_current_user_id

    @router.get("/")
    async def list_items(user_id: str = Depends(get_current_user_id)):
        ...
"""
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

_bearer = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """
    FastAPI dependency — validates the Bearer JWT and returns the user's UUID.
    Raises 401 if the token is missing, expired, or invalid.
    """
    token = credentials.credentials
    try:
        supabase = get_supabase_admin()
        response = supabase.auth.get_user(token)
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        return response.user.id
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Token verification failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc
