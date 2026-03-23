"""
Platform connection management endpoints.
Link GA4 properties, Meta ad accounts, and Google Ads accounts to clients.
See docs/reportpilot-feature-design-blueprint.md for full specification.

Endpoints:
    POST   /api/connections                       — Save a new connection
    GET    /api/connections/client/{client_id}    — List connections for a client
    DELETE /api/connections/{connection_id}       — Remove a connection
"""
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from middleware.auth import get_current_user_id
from models.schemas import ConnectionCreate, ConnectionListResponse, ConnectionResponse
from services.encryption import decrypt_token, encrypt_token
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# POST /api/connections
# ---------------------------------------------------------------------------

@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    body: ConnectionCreate,
    user_id: str = Depends(get_current_user_id),
) -> ConnectionResponse:
    """
    Persist a new platform connection for a client.

    The `token_handle` is the opaque encrypted blob returned by
    /api/auth/google/callback.  We decrypt it, extract expiry info, then
    re-encrypt the tokens for long-term storage.
    """
    supabase = get_supabase_admin()

    # Verify the client belongs to this user
    client_result = (
        supabase.table("clients")
        .select("id")
        .eq("id", body.client_id)
        .eq("user_id", user_id)
        .eq("is_active", True)
        .single()
        .execute()
    )
    if not client_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found.",
        )

    # Decrypt the token handle to extract expiry
    try:
        token_payload = json.loads(decrypt_token(body.token_handle))
    except Exception:
        logger.exception("Failed to decrypt token_handle for new connection")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token handle — it may have expired or been tampered with.",
        )

    token_expires_ts = token_payload.get("token_expires_at")
    token_expires_at = (
        datetime.fromtimestamp(token_expires_ts, tz=timezone.utc).isoformat()
        if token_expires_ts
        else None
    )

    # Normalise platform value to match the DB CHECK constraint.
    # The frontend sends "google_analytics"; the DB allows "ga4".
    platform = body.platform
    if platform == "google_analytics":
        platform = "ga4"

    # Re-encrypt access_token and refresh_token into their individual DB columns.
    # The auth callback bundles them together for transit; the DB stores them separately.
    raw_access  = token_payload.get("access_token", "")
    raw_refresh = token_payload.get("refresh_token", "")
    access_token_encrypted  = encrypt_token(raw_access)  if raw_access  else ""
    refresh_token_encrypted = encrypt_token(raw_refresh) if raw_refresh else ""

    # Check for an existing connection for the same client + platform + account
    existing = (
        supabase.table("connections")
        .select("id")
        .eq("client_id", body.client_id)
        .eq("platform", platform)
        .eq("account_id", body.account_id)
        .execute()
    )
    connection_id = str(uuid.uuid4())

    insert_payload = {
        "id":                       connection_id,
        "client_id":                body.client_id,
        "platform":                 platform,
        "account_id":               body.account_id,
        "account_name":             body.account_name,
        "currency":                 body.currency,
        "status":                   "active",
        "access_token_encrypted":   access_token_encrypted,
        "refresh_token_encrypted":  refresh_token_encrypted,
        "token_expires_at":         token_expires_at,
        "consecutive_failures":     0,
    }

    if existing.data:
        # Update in place rather than duplicating
        connection_id = existing.data[0]["id"]
        insert_payload["id"] = connection_id
        result = (
            supabase.table("connections")
            .update(insert_payload)
            .eq("id", connection_id)
            .execute()
        )
    else:
        result = supabase.table("connections").insert(insert_payload).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save connection.",
        )

    return ConnectionResponse(**_map_row(result.data[0]))


# ---------------------------------------------------------------------------
# GET /api/connections/client/{client_id}
# ---------------------------------------------------------------------------

@router.get("/client/{client_id}", response_model=ConnectionListResponse)
async def list_client_connections(
    client_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ConnectionListResponse:
    """List all platform connections for a specific client."""
    supabase = get_supabase_admin()

    # Verify ownership
    client_result = (
        supabase.table("clients")
        .select("id")
        .eq("id", client_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not client_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found.",
        )

    result = (
        supabase.table("connections")
        .select("id,client_id,platform,account_id,account_name,currency,status,token_expires_at,created_at,updated_at")
        .eq("client_id", client_id)
        .order("created_at", desc=False)
        .execute()
    )

    items = [ConnectionResponse(**_map_row(row)) for row in (result.data or [])]
    return ConnectionListResponse(connections=items, total=len(items))


# ---------------------------------------------------------------------------
# DELETE /api/connections/{connection_id}
# ---------------------------------------------------------------------------

@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: str,
    user_id: str = Depends(get_current_user_id),
) -> None:
    """
    Remove a platform connection.
    Verifies the connection's client is owned by the requesting user.
    """
    supabase = get_supabase_admin()

    # Fetch connection to get client_id for ownership check
    conn_result = (
        supabase.table("connections")
        .select("id,client_id")
        .eq("id", connection_id)
        .single()
        .execute()
    )
    if not conn_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found.",
        )

    client_id = conn_result.data["client_id"]
    client_result = (
        supabase.table("clients")
        .select("id")
        .eq("id", client_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not client_result.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to delete this connection.",
        )

    supabase.table("connections").delete().eq("id", connection_id).execute()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _map_row(row: dict) -> dict:
    """Map DB column names to ConnectionResponse fields."""
    return {
        "id":               row["id"],
        "client_id":        row["client_id"],
        "platform":         row["platform"],
        "account_id":       row["account_id"],
        "account_name":     row["account_name"],
        "currency":         row.get("currency", "USD"),
        "status":           row["status"],
        "token_expires_at": row.get("token_expires_at"),
        "created_at":       row["created_at"],
        "updated_at":       row["updated_at"],
    }
