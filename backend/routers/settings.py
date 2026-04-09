"""
Agency settings endpoints — profile CRUD + logo upload.
Logos are stored in backend/static/logos/ and served via FastAPI StaticFiles.
"""
import logging
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from config import settings as app_settings
from middleware.auth import get_current_user_id
from models.schemas import ProfileUpdate
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Static file paths ────────────────────────────────────────────────────────
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOGOS_DIR   = os.path.join(_BACKEND_DIR, "static", "logos")

_ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
_MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB


# ---------------------------------------------------------------------------
# GET /api/settings/profile
# ---------------------------------------------------------------------------

@router.get("/profile")
async def get_profile(user_id: str = Depends(get_current_user_id)) -> dict:
    """Return the authenticated user's full agency profile."""
    supabase = get_supabase_admin()
    result = (
        supabase.table("profiles")
        .select("*")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        # Profile should be created by auth trigger — return minimal defaults
        return {
            "id": user_id,
            "agency_name": "",
            "agency_email": "",
            "agency_logo_url": "",
            "brand_color": "#4338CA",
            "agency_website": "",
            "timezone": "UTC",
            "default_ai_tone": "professional",
            "sender_name": "",
            "reply_to_email": "",
            "email_footer": "",
            "notification_report_generated": True,
            "notification_connection_expired": True,
            "notification_payment_failed": True,
        }
    return result.data


# ---------------------------------------------------------------------------
# PATCH /api/settings/profile
# ---------------------------------------------------------------------------

@router.patch("/profile")
async def update_profile(
    payload: ProfileUpdate,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Update the authenticated user's agency profile (any subset of fields)."""
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided to update",
        )

    updates["updated_at"] = datetime.utcnow().isoformat()

    supabase = get_supabase_admin()
    try:
        # Use update().eq() — the profile row always exists (created by auth trigger on signup).
        # Never upsert: it would null-out required columns like email and name.
        result = (
            supabase.table("profiles")
            .update(updates)
            .eq("id", user_id)
            .execute()
        )
    except Exception as exc:
        logger.error("Profile update failed for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {exc}",
        ) from exc

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update returned no data",
        )
    logger.info("Profile updated for user %s — fields: %s", user_id, list(updates.keys()))
    return result.data[0]


# ---------------------------------------------------------------------------
# POST /api/settings/upload-logo
# ---------------------------------------------------------------------------

@router.post("/upload-logo")
async def upload_agency_logo(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Upload an agency logo image.
    Saves to backend/static/logos/agencies/{user_id}/ and serves via /static.
    Updates profiles.agency_logo_url with the public URL.
    """
    # content_type can be None when the browser omits the part Content-Type header
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{content_type or 'unknown'}'. "
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
    supabase = get_supabase_admin()
    storage_path = f"{user_id}/agency/{filename}"
    try:
        supabase.storage.from_("logos").upload(
            storage_path,
            processed_bytes,
            {"content-type": f"image/{final_ext}", "upsert": "true"},
        )
        public_url = supabase.storage.from_("logos").get_public_url(storage_path)
    except Exception as exc:
        logger.error("Supabase Storage upload failed for agency logo: %s", exc)
        # Fallback: save locally (works for dev, but ephemeral in production)
        save_dir  = os.path.join(_LOGOS_DIR, "agencies", user_id)
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
        with open(save_path, "wb") as f:
            f.write(processed_bytes)
        public_url = f"{app_settings.BACKEND_URL}/static/logos/agencies/{user_id}/{filename}"

    # Persist URL to profile — update only, never upsert (would null required columns)
    supabase.table("profiles").update({
        "agency_logo_url": public_url,
        "updated_at":      datetime.utcnow().isoformat(),
    }).eq("id", user_id).execute()

    logger.info("Agency logo uploaded for user %s → %s (bg_removed=%s)", user_id, public_url, bg_removed)
    return {"url": public_url, "bg_removed": bg_removed}


# ---------------------------------------------------------------------------
# DELETE /api/settings/account  — self-service account deletion
# ---------------------------------------------------------------------------

class DeleteAccountPayload(BaseModel):
    confirm_email: str


@router.delete("/account")
async def delete_account(
    payload: DeleteAccountPayload,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Permanently delete the authenticated user's account and all associated data.
    The confirm_email must match the user's actual email as a safety check.
    Deletion of auth.users cascades to profiles, clients, connections, reports,
    shared_reports, scheduled_reports, subscriptions, and payment_history.
    """
    supabase = get_supabase_admin()

    # 1. Verify confirm_email matches the authenticated user's email
    user_result = supabase.auth.admin.get_user_by_id(user_id)
    if not user_result or not user_result.user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user_email = user_result.user.email or ""
    if payload.confirm_email.strip().lower() != user_email.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email does not match your account email",
        )

    # 2. Delete user's logos from Supabase Storage
    try:
        logo_files = supabase.storage.from_("logos").list(f"{user_id}/")
        if logo_files:
            # List all files recursively (agency/ and client/ subfolders)
            for folder in logo_files:
                folder_name = folder.get("name", "")
                if folder_name:
                    sub_files = supabase.storage.from_("logos").list(f"{user_id}/{folder_name}/")
                    if sub_files:
                        paths = [f"{user_id}/{folder_name}/{f['name']}" for f in sub_files if f.get("name")]
                        if paths:
                            supabase.storage.from_("logos").remove(paths)
    except Exception as exc:
        logger.warning("Failed to clean up logos for user %s: %s", user_id, exc)

    # 3. Log the deletion in admin_activity_log BEFORE deleting (so user_id is still valid)
    try:
        supabase.table("admin_activity_log").insert({
            "admin_id": user_id,
            "action": "self_delete",
            "target_type": "user",
            "target_id": user_id,
            "details": {"email": user_email, "reason": "self-service account deletion"},
        }).execute()
    except Exception as exc:
        logger.warning("Failed to log account deletion for user %s: %s", user_id, exc)

    # 4. Delete from auth.users — CASCADE handles all related tables
    try:
        supabase.auth.admin.delete_user(user_id)
    except Exception as exc:
        logger.error("Failed to delete auth user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account. Please try again or contact support.",
        ) from exc

    logger.info("Account self-deleted: user_id=%s, email=%s", user_id, user_email)
    return {"success": True, "message": "Account and all associated data have been permanently deleted."}
