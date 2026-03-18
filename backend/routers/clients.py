"""
Client CRUD endpoints.
Create, read, update, soft-delete clients for the authenticated agency user.
All endpoints require a valid Supabase JWT (Bearer token).
RLS is enforced in PostgreSQL, but we also scope every query to user_id
for defence-in-depth.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from middleware.auth import get_current_user_id
from models.schemas import ClientCreate, ClientUpdate, ClientResponse, ClientListResponse
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=ClientListResponse)
async def list_clients(user_id: str = Depends(get_current_user_id)) -> ClientListResponse:
    """Return all active clients for the authenticated user."""
    supabase = get_supabase_admin()
    result = (
        supabase.table("clients")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .order("created_at", desc=True)
        .execute()
    )
    clients = [ClientResponse(**row) for row in result.data]
    return ClientListResponse(clients=clients, total=len(clients))


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    user_id: str = Depends(get_current_user_id),
) -> ClientResponse:
    """Create a new client for the authenticated user."""
    supabase = get_supabase_admin()
    data = {
        "user_id": user_id,
        **payload.model_dump(exclude_none=True),
    }
    result = supabase.table("clients").insert(data).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create client",
        )
    return ClientResponse(**result.data[0])


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ClientResponse:
    """Fetch a single client by ID. Returns 404 if not found or not owned by user."""
    supabase = get_supabase_admin()
    result = (
        supabase.table("clients")
        .select("*")
        .eq("id", client_id)
        .eq("user_id", user_id)
        .eq("is_active", True)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return ClientResponse(**result.data)


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str,
    payload: ClientUpdate,
    user_id: str = Depends(get_current_user_id),
) -> ClientResponse:
    """Partially update a client. Only the provided fields are changed."""
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided to update",
        )
    supabase = get_supabase_admin()
    result = (
        supabase.table("clients")
        .update(updates)
        .eq("id", client_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return ClientResponse(**result.data[0])


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: str,
    user_id: str = Depends(get_current_user_id),
) -> None:
    """Soft-delete a client by setting is_active = False."""
    supabase = get_supabase_admin()
    result = (
        supabase.table("clients")
        .update({"is_active": False})
        .eq("id", client_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
