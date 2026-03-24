"""
Report sharing endpoints — create public links, log views, get analytics.

Authenticated endpoints (require JWT):
    POST   /api/reports/{report_id}/share        — Create share link
    GET    /api/reports/{report_id}/share        — Get existing share links
    DELETE /api/reports/{report_id}/share/{hash} — Revoke share link
    GET    /api/reports/{report_id}/analytics    — View tracking data

Public endpoints (NO auth required):
    GET    /api/shared/{hash}          — Get report data for public viewing
    POST   /api/shared/{hash}/verify   — Verify password
    POST   /api/shared/{hash}/view     — Log a view event
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from config import settings
from middleware.auth import get_current_user_id
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

# Two routers — one for /api/reports (authenticated), one for /api/shared (public)
reports_router = APIRouter()
public_router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ShareCreateRequest(BaseModel):
    password: Optional[str] = None
    expires_days: Optional[int] = None  # None = never expire; 7 / 30 / 90


class PasswordVerifyRequest(BaseModel):
    password: str


class ViewLogRequest(BaseModel):
    duration_seconds: Optional[int] = None
    device_type: Optional[str] = None  # "mobile" | "desktop" | "tablet"


# ---------------------------------------------------------------------------
# Helper — mask IP: keep only the first two octets
# ---------------------------------------------------------------------------

def _mask_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.*.*"
    return ip  # IPv6 or unexpected format — return as-is


# ---------------------------------------------------------------------------
# Authenticated endpoint: POST /{report_id}/share
# ---------------------------------------------------------------------------

@reports_router.post("/{report_id}/share", status_code=status.HTTP_201_CREATED)
async def create_share_link(
    report_id: str,
    body: ShareCreateRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Generate a public share link for a report.
    Optionally password-protect it and/or set an expiry window.
    """
    supabase = get_supabase_admin()

    # Verify report ownership
    report_result = (
        supabase.table("reports")
        .select("id")
        .eq("id", report_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not report_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    share_hash = secrets.token_urlsafe(16)

    password_hash: str | None = None
    if body.password:
        password_hash = hashlib.sha256(body.password.encode()).hexdigest()

    expires_at: str | None = None
    if body.expires_days is not None:
        expires_at = (
            datetime.now(timezone.utc) + timedelta(days=body.expires_days)
        ).isoformat()

    insert_payload = {
        "report_id":     report_id,
        "user_id":       user_id,
        "share_hash":    share_hash,
        "password_hash": password_hash,
        "expires_at":    expires_at,
        "is_active":     True,
    }

    result = supabase.table("shared_reports").insert(insert_payload).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create share link.",
        )

    share_url = f"{settings.FRONTEND_URL}/shared/{share_hash}"
    logger.info("Share link created for report %s: %s", report_id, share_hash)

    return {
        "share_hash":    share_hash,
        "share_url":     share_url,
        "expires_at":    expires_at,
        "has_password":  password_hash is not None,
    }


# ---------------------------------------------------------------------------
# Authenticated endpoint: GET /{report_id}/share
# ---------------------------------------------------------------------------

@reports_router.get("/{report_id}/share")
async def get_share_links(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Return all active share links for a report owned by the authenticated user."""
    supabase = get_supabase_admin()

    # Verify ownership
    report_result = (
        supabase.table("reports")
        .select("id")
        .eq("id", report_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not report_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    result = (
        supabase.table("shared_reports")
        .select("share_hash,expires_at,is_active,password_hash,created_at")
        .eq("report_id", report_id)
        .eq("is_active", True)
        .order("created_at", desc=True)
        .execute()
    )

    links = [
        {
            "share_hash":  row["share_hash"],
            "share_url":   f"{settings.FRONTEND_URL}/shared/{row['share_hash']}",
            "expires_at":  row.get("expires_at"),
            "has_password": row.get("password_hash") is not None,
            "created_at":  row["created_at"],
        }
        for row in (result.data or [])
    ]

    return {"share_links": links, "total": len(links)}


# ---------------------------------------------------------------------------
# Authenticated endpoint: DELETE /{report_id}/share/{share_hash}
# ---------------------------------------------------------------------------

@reports_router.delete(
    "/{report_id}/share/{share_hash}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_share_link(
    report_id: str,
    share_hash: str,
    user_id: str = Depends(get_current_user_id),
) -> None:
    """Revoke a share link by marking it inactive."""
    supabase = get_supabase_admin()

    # Verify the share link belongs to a report the user owns
    result = (
        supabase.table("shared_reports")
        .select("id,report_id")
        .eq("share_hash", share_hash)
        .eq("report_id", report_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found.",
        )

    supabase.table("shared_reports").update({"is_active": False}).eq(
        "share_hash", share_hash
    ).execute()

    logger.info("Share link %s revoked for report %s", share_hash, report_id)


# ---------------------------------------------------------------------------
# Authenticated endpoint: GET /{report_id}/analytics
# ---------------------------------------------------------------------------

@reports_router.get("/{report_id}/analytics")
async def get_report_analytics(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Return view tracking analytics for all share links belonging to this report.
    Viewer IPs are masked to the first two octets for privacy.
    """
    supabase = get_supabase_admin()

    # Verify ownership
    report_result = (
        supabase.table("reports")
        .select("id")
        .eq("id", report_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not report_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    # Fetch all share link IDs for this report
    shared_result = (
        supabase.table("shared_reports")
        .select("id")
        .eq("report_id", report_id)
        .execute()
    )
    share_ids = [row["id"] for row in (shared_result.data or [])]

    if not share_ids:
        return {
            "total_views":          0,
            "unique_viewers":       0,
            "last_viewed_at":       None,
            "avg_duration_seconds": None,
            "recent_views":         [],
        }

    # Fetch all views for these share links
    views_result = (
        supabase.table("report_views")
        .select("viewed_at,device_type,duration_seconds,viewer_ip")
        .in_("shared_report_id", share_ids)
        .order("viewed_at", desc=True)
        .execute()
    )
    views = views_result.data or []

    total_views = len(views)
    unique_viewers = len({v.get("viewer_ip") for v in views if v.get("viewer_ip")})
    last_viewed_at = views[0]["viewed_at"] if views else None

    durations = [v["duration_seconds"] for v in views if v.get("duration_seconds") is not None]
    avg_duration = round(sum(durations) / len(durations)) if durations else None

    recent_views = [
        {
            "viewed_at":        v["viewed_at"],
            "device_type":      v.get("device_type"),
            "duration_seconds": v.get("duration_seconds"),
            "viewer_ip":        _mask_ip(v.get("viewer_ip")),
        }
        for v in views[:50]  # cap at 50 most recent
    ]

    return {
        "total_views":          total_views,
        "unique_viewers":       unique_viewers,
        "last_viewed_at":       last_viewed_at,
        "avg_duration_seconds": avg_duration,
        "recent_views":         recent_views,
    }


# ---------------------------------------------------------------------------
# Public endpoint: GET /api/shared/{hash}
# ---------------------------------------------------------------------------

@public_router.get("/{share_hash}")
async def get_shared_report(share_hash: str) -> dict:
    """
    Fetch a publicly shared report by its hash.

    Returns 401 with {requires_password: true} if the link is password-protected.
    Returns 410 if the link has expired.
    Returns 404 if the link is not found or has been revoked.
    """
    supabase = get_supabase_admin()

    shared_result = (
        supabase.table("shared_reports")
        .select("id,report_id,password_hash,expires_at,is_active")
        .eq("share_hash", share_hash)
        .single()
        .execute()
    )
    if not shared_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or has been revoked.",
        )

    shared = shared_result.data

    if not shared["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or has been revoked.",
        )

    # Check expiry
    if shared.get("expires_at"):
        try:
            expires_dt = datetime.fromisoformat(
                str(shared["expires_at"]).replace("Z", "+00:00")
            )
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            if expires_dt < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="This share link has expired.",
                )
        except HTTPException:
            raise
        except Exception:
            pass  # If we can't parse the date, allow access

    # Password-protected: return minimal response prompting for verification
    if shared.get("password_hash"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This report is password-protected.",
            headers={"X-Requires-Password": "true"},
        )

    # Fetch the report
    report_id = shared["report_id"]
    report_result = (
        supabase.table("reports")
        .select("id,user_id,client_id,title,period_start,period_end,ai_narrative,sections,status")
        .eq("id", report_id)
        .single()
        .execute()
    )
    if not report_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    report = report_result.data
    sections = report.get("sections") or {}

    # Fetch client name
    client_result = (
        supabase.table("clients")
        .select("name,report_config")
        .eq("id", report["client_id"])
        .single()
        .execute()
    )
    client = client_result.data or {}
    client_name = client.get("name", "")

    # Fetch agency branding
    profile_result = (
        supabase.table("profiles")
        .select("agency_name")
        .eq("id", report["user_id"])
        .maybe_single()
        .execute()
    )
    profile = profile_result.data or {}
    agency_name = profile.get("agency_name") or ""

    return {
        "report_id":        report["id"],
        "client_name":      client_name,
        "period_start":     str(report.get("period_start", "")),
        "period_end":       str(report.get("period_end", "")),
        "agency_name":      agency_name,
        "narrative":        report.get("ai_narrative"),
        "kpi_summary":      sections.get("data_summary") if isinstance(sections, dict) else None,
        "meta_currency":    sections.get("meta_currency", "USD") if isinstance(sections, dict) else "USD",
        "title":            report.get("title", ""),
        "requires_password": False,
    }


# ---------------------------------------------------------------------------
# Public endpoint: POST /api/shared/{hash}/verify
# ---------------------------------------------------------------------------

@public_router.post("/{share_hash}/verify")
async def verify_share_password(
    share_hash: str,
    body: PasswordVerifyRequest,
) -> dict:
    """
    Verify the password for a password-protected share link.
    Returns {verified: true} on success, 401 on mismatch.
    """
    supabase = get_supabase_admin()

    shared_result = (
        supabase.table("shared_reports")
        .select("password_hash,is_active,expires_at")
        .eq("share_hash", share_hash)
        .single()
        .execute()
    )
    if not shared_result.data or not shared_result.data["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or has been revoked.",
        )

    stored_hash = shared_result.data.get("password_hash")
    if not stored_hash:
        # Link has no password — verification always succeeds
        return {"verified": True}

    submitted_hash = hashlib.sha256(body.password.encode()).hexdigest()
    if submitted_hash != stored_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password.",
        )

    return {"verified": True}


# ---------------------------------------------------------------------------
# Public endpoint: POST /api/shared/{hash}/view
# ---------------------------------------------------------------------------

@public_router.post("/{share_hash}/view")
async def log_share_view(
    share_hash: str,
    request: Request,
    body: ViewLogRequest,
) -> dict:
    """
    Log a view event for a shared report link.
    Records the viewer's IP, user-agent, device type, and optional duration.
    """
    supabase = get_supabase_admin()

    shared_result = (
        supabase.table("shared_reports")
        .select("id,is_active")
        .eq("share_hash", share_hash)
        .single()
        .execute()
    )
    if not shared_result.data or not shared_result.data["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or has been revoked.",
        )

    shared_report_id = shared_result.data["id"]
    viewer_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")

    view_payload = {
        "shared_report_id": shared_report_id,
        "viewer_ip":        viewer_ip,
        "user_agent":       user_agent,
        "device_type":      body.device_type,
        "duration_seconds": body.duration_seconds,
        "viewed_at":        datetime.now(timezone.utc).isoformat(),
    }

    result = supabase.table("report_views").insert(view_payload).execute()
    if not result.data:
        logger.warning("Failed to log view for share_hash %s", share_hash)

    return {"logged": True}
