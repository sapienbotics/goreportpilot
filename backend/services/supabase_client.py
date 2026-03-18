"""
Shared Supabase admin client for backend services.
Uses the service_role key — bypasses RLS for server-side operations.
NEVER expose this client or its key to the frontend.
"""
import logging
from supabase import create_client, Client
from config import settings

logger = logging.getLogger(__name__)

_supabase_admin: Client | None = None


def get_supabase_admin() -> Client:
    """Return the singleton admin Supabase client (service_role key)."""
    global _supabase_admin
    if _supabase_admin is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        _supabase_admin = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        logger.info("Supabase admin client initialised")
    return _supabase_admin
