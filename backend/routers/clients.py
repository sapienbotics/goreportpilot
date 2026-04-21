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

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from slowapi import Limiter

from config import settings as app_settings
from middleware.auth import get_current_user_id
from middleware.plan_enforcement import can_create_client
from middleware.rate_limit import user_rate_limit_key
from models.schemas import (
    ClientCreate, ClientUpdate, ClientResponse, ClientListResponse,
    EnhanceContextRequest, EnhanceContextResponse,
)
from services.context_enhancer import enhance_business_context
from services.supabase_client import get_supabase_admin

# Per-user rate limiter for the AI-assist endpoint. Separate from the
# app-level IP limiter in main.py so the "10 per hour" quota follows the
# agency user, not whatever NAT they're behind. In-memory only — fine for
# a single Railway replica; revisit if we move to multi-replica.
_user_limiter = Limiter(key_func=user_rate_limit_key)

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


# ---------------------------------------------------------------------------
# POST /enhance-context  (Phase 7 UX — AI-assist on Business Context field)
# ---------------------------------------------------------------------------
# Declared BEFORE /{client_id} routes so "enhance-context" is never matched
# as a UUID path param.

@router.post("/enhance-context", response_model=EnhanceContextResponse)
@_user_limiter.limit("10/hour")
async def enhance_context(
    request: Request,  # noqa: ARG001 — required by slowapi for key extraction
    payload: EnhanceContextRequest,
    user_id: str = Depends(get_current_user_id),  # noqa: ARG001 — auth only
) -> EnhanceContextResponse:
    """
    Rewrite the agency's raw client business-context blurb into a concise
    report-ready paragraph. Calls GPT-4.1. Rate-limited to 10/hour per user
    so a single agency can't burn through OpenAI quota on this optional
    convenience endpoint.
    """
    try:
        enhanced = await enhance_business_context(payload.text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("enhance_context failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI enhancement temporarily unavailable. Please try again.",
        ) from exc
    return EnhanceContextResponse(enhanced=enhanced)


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
    # Phase-3 fix v4 — log cover-customisation fields as they arrive from
    # the frontend so we can trace Bug 3 (top-center logo rendering at
    # top-right) end-to-end.
    logger.info(
        "update_client[%s] cover_agency_logo_position=%r cover_client_logo_position=%r "
        "cover_design_preset=%r",
        client_id,
        updates.get("cover_agency_logo_position"),
        updates.get("cover_client_logo_position"),
        updates.get("cover_design_preset"),
    )
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

    filename = f"{uuid.uuid4().hex[:12]}.{final_ext}"

    # Upload to Supabase Storage (persistent across redeployments)
    storage_path = f"{user_id}/clients/{client_id}/{filename}"
    try:
        supabase.storage.from_("logos").upload(
            storage_path,
            processed_bytes,
            {"content-type": f"image/{final_ext}", "upsert": "true"},
        )
        public_url = supabase.storage.from_("logos").get_public_url(storage_path)
    except Exception as exc:
        logger.error("Supabase Storage upload failed for client logo: %s", exc)
        # Fallback: save locally (works for dev, but ephemeral in production)
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

    # Upload to Supabase Storage (persistent across redeployments)
    storage_path = f"{user_id}/custom_sections/{client_id}/{filename}"
    try:
        supabase.storage.from_("logos").upload(
            storage_path,
            contents,
            {"content-type": f"image/{ext}", "upsert": "true"},
        )
        public_url = supabase.storage.from_("logos").get_public_url(storage_path)
    except Exception as exc:
        logger.error("Supabase Storage upload failed for custom section image: %s", exc)
        # Fallback: save locally
        save_dir = os.path.join(_CUSTOM_SECTIONS_DIR, client_id)
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
        with open(save_path, "wb") as f:
            f.write(contents)
        public_url = f"{app_settings.BACKEND_URL}/static/custom_sections/{client_id}/{filename}"

    logger.info("Custom section image uploaded for client %s: %s", client_id, public_url)
    return {"url": public_url}


# ---------------------------------------------------------------------------
# POST /{client_id}/cover-hero  (Phase 3)
# ---------------------------------------------------------------------------

_COVER_HEROES_DIR = os.path.join(_BACKEND_DIR, "static", "cover_heroes")

@router.post("/{client_id}/cover-hero")
async def upload_cover_hero(
    client_id: str,
    image: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Upload a hero image for the client's cover page (Phase 3).

    Written to Supabase Storage `logos` bucket under
    `{user_id}/cover_heroes/{client_id}/{filename}`. Updates
    `clients.cover_hero_image_url` with the returned public URL.

    Max 2MB. Accepted: PNG, JPEG, WEBP.
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
    if len(contents) > _MAX_SIZE_BYTES:  # 2 MB per master prompt
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large. Maximum 2MB.",
        )

    ext = (image.filename or "hero").rsplit(".", 1)[-1].lower()
    if ext not in ("png", "jpg", "jpeg", "webp"):
        ext = "png"

    filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    storage_path = f"{user_id}/cover_heroes/{client_id}/{filename}"
    try:
        supabase.storage.from_("logos").upload(
            storage_path,
            contents,
            {"content-type": f"image/{ext}", "upsert": "true"},
        )
        public_url = supabase.storage.from_("logos").get_public_url(storage_path)
    except Exception as exc:
        logger.error("Supabase Storage upload failed for cover hero: %s", exc)
        save_dir = os.path.join(_COVER_HEROES_DIR, client_id)
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
        with open(save_path, "wb") as f:
            f.write(contents)
        public_url = f"{app_settings.BACKEND_URL}/static/cover_heroes/{client_id}/{filename}"

    supabase.table("clients").update({
        "cover_hero_image_url": public_url,
        "updated_at":           datetime.utcnow().isoformat(),
    }).eq("id", client_id).eq("user_id", user_id).execute()

    logger.info("Cover hero uploaded for client %s: %s", client_id, public_url)
    return {"url": public_url}
