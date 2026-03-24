"""
Client CRUD endpoints.
Create, read, update, soft-delete clients for the authenticated agency user.
All endpoints require a valid Supabase JWT (Bearer token).
RLS is enforced in PostgreSQL, but we also scope every query to user_id
for defence-in-depth.
"""
import logging
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from config import settings as app_settings
from middleware.auth import get_current_user_id
from middleware.plan_enforcement import can_create_client
from models.schemas import ClientCreate, ClientUpdate, ClientResponse, ClientListResponse
from services.supabase_client import get_supabase_admin

_BACKEND_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CLIENT_LOGOS   = os.path.join(_BACKEND_DIR, "static", "logos", "clients")
_ALLOWED_TYPES  = {"image/png", "image/jpeg", "image/gif", "image/webp"}
_MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB

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
    allowed, msg = can_create_client(user_id)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)

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


# ---------------------------------------------------------------------------
# POST /{client_id}/upload-logo
# ---------------------------------------------------------------------------

@router.post("/{client_id}/upload-logo")
async def upload_client_logo(
    client_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Upload a client logo image.
    Saves to backend/static/logos/clients/{client_id}/ and serves via /static.
    Updates clients.logo_url with the public URL.
    """
    # Verify ownership first
    supabase = get_supabase_admin()
    check = (
        supabase.table("clients")
        .select("id")
        .eq("id", client_id)
        .eq("user_id", user_id)
        .eq("is_active", True)
        .single()
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{file.content_type}'. "
                   "Allowed: image/png, image/jpeg, image/gif, image/webp",
        )

    contents = await file.read()
    if len(contents) > _MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum allowed size is 2 MB.",
        )

    ext = (file.filename or "logo").rsplit(".", 1)[-1].lower()
    if ext not in ("png", "jpg", "jpeg", "gif", "webp"):
        ext = "png"

    # Auto-remove background for best results on all slide themes
    from services.logo_processor import process_logo_upload
    processed_bytes, final_ext, bg_removed = process_logo_upload(contents, ext)

    filename  = f"{uuid.uuid4().hex[:12]}.{final_ext}"
    save_dir  = os.path.join(_CLIENT_LOGOS, client_id)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)

    with open(save_path, "wb") as f:
        f.write(processed_bytes)

    public_url = f"{app_settings.BACKEND_URL}/static/logos/clients/{client_id}/{filename}"

    supabase.table("clients").update({
        "logo_url":   public_url,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", client_id).eq("user_id", user_id).execute()

    logger.info("Client logo uploaded for client %s → %s (bg_removed=%s)", client_id, public_url, bg_removed)
    return {"url": public_url, "bg_removed": bg_removed}


# ---------------------------------------------------------------------------
# POST /{client_id}/custom-section-image
# ---------------------------------------------------------------------------

_CUSTOM_SECTIONS_DIR = os.path.join(_BACKEND_DIR, "static", "custom_sections")
_MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB

@router.post("/{client_id}/custom-section-image")
async def upload_custom_section_image(
    client_id: str,
    image: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Upload an image for the custom section slide.
    Saves to backend/static/custom_sections/{client_id}/ and returns the URL.
    """
    supabase = get_supabase_admin()
    check = (
        supabase.table("clients")
        .select("id")
        .eq("id", client_id)
        .eq("user_id", user_id)
        .eq("is_active", True)
        .single()
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    if image.content_type not in {"image/png", "image/jpeg", "image/jpg", "image/webp"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported file type. Allowed: PNG, JPEG, WEBP",
        )

    contents = await image.read()
    if len(contents) > _MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large. Maximum 5MB.",
        )

    ext = (image.filename or "image").rsplit(".", 1)[-1].lower()
    if ext not in ("png", "jpg", "jpeg", "webp"):
        ext = "png"

    filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    save_dir = os.path.join(_CUSTOM_SECTIONS_DIR, client_id)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)

    with open(save_path, "wb") as f:
        f.write(contents)

    public_url = f"{app_settings.BACKEND_URL}/static/custom_sections/{client_id}/{filename}"
    logger.info("Custom section image uploaded for client %s: %s", client_id, public_url)
    return {"url": public_url}
