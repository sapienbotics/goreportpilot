"""
Phase 5 — Client comments on shared reports.

Public endpoints (NO auth required):
    POST   /api/shares/{share_token}/comments   — post a new comment (rate-limited 5/h/IP)
    GET    /api/shares/{share_token}/comments   — list comments on this share

Authenticated endpoints (Supabase JWT):
    GET    /api/comments/unread                  — unresolved count grouped by report
    PATCH  /api/comments/{comment_id}/resolve    — toggle is_resolved

Targeting:
    * slide_number (int, nullable) — per-slide comment
    * section_key  (str, nullable) — per-section comment (e.g. "executive_summary")
    * both null ⇒ general feedback on the whole report

All writes go through the supabase admin client (service_role), so RLS is
bypassed — we therefore scope every query by user_id in the agency endpoints
for defence in depth, mirroring the pattern already used in shared.py.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings
from middleware.auth import get_current_user_id
from services.email_service import (
    build_comment_notification_email_html,
    send_plain_email,
)
from services.supabase_client import get_supabase_admin

logger  = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# Two routers — public under /api/shares, agency under /api/comments
public_router = APIRouter()
agency_router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class CommentCreateRequest(BaseModel):
    client_name:  str = Field(..., min_length=1, max_length=120)
    client_email: str = Field(..., min_length=3, max_length=254)
    comment_text: str = Field(..., min_length=1, max_length=2000)
    slide_number: Optional[int] = Field(None, ge=1, le=999)
    section_key:  Optional[str] = Field(None, max_length=80)

    @field_validator("client_email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("invalid email address")
        return v


class CommentResponse(BaseModel):
    id:             str
    share_id:       str
    report_id:      str
    client_name:    str
    client_email:   str
    slide_number:   Optional[int] = None
    section_key:    Optional[str] = None
    comment_text:   str
    is_resolved:    bool
    resolved_at:    Optional[str] = None
    created_at:     str


class CommentListResponse(BaseModel):
    comments: list[CommentResponse]
    total:    int


class ResolveRequest(BaseModel):
    is_resolved: bool = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SECTION_KEY_RE = re.compile(r"^[a-z0-9_\-]{1,80}$")


def _normalise_section_key(raw: Optional[str]) -> Optional[str]:
    """Lowercase + validate shape. Return None for empty / invalid strings."""
    if not raw:
        return None
    v = raw.strip().lower()
    if not v:
        return None
    if not _SECTION_KEY_RE.match(v):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="section_key must be lowercase alphanumeric (plus _ or -), up to 80 chars.",
        )
    return v


def _load_active_share(supabase, share_token: str) -> dict:
    """Look up a shared_reports row by share_hash, reject if revoked/expired."""
    res = (
        supabase.table("shared_reports")
        .select("id,report_id,user_id,expires_at,is_active")
        .eq("share_hash", share_token)
        .maybe_single()
        .execute()
    )
    row = res.data if res else None
    if not row or not row.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or has been revoked.",
        )

    expires_at = row.get("expires_at")
    if expires_at:
        try:
            expires_dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
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
            pass
    return row


def _row_to_response(row: dict) -> CommentResponse:
    return CommentResponse(
        id             = row["id"],
        share_id       = row["share_id"],
        report_id      = row["report_id"],
        client_name    = row["client_name"],
        client_email   = row["client_email"],
        slide_number   = row.get("slide_number"),
        section_key    = row.get("section_key"),
        comment_text   = row["comment_text"],
        is_resolved    = bool(row.get("is_resolved", False)),
        resolved_at    = row.get("resolved_at"),
        created_at     = row["created_at"],
    )


def _target_label(slide_number: Optional[int], section_key: Optional[str]) -> str:
    """Human-readable target string for the agency email body."""
    if slide_number:
        return f"Slide {slide_number}"
    if section_key:
        return f"Section: {section_key}"
    return "General feedback"


async def _notify_agency_of_comment(
    *,
    supabase,
    user_id: str,
    report_id: str,
    share_id: str,
    commenter_name: str,
    commenter_email: str,
    comment_text: str,
    slide_number: Optional[int],
    section_key: Optional[str],
) -> None:
    """
    Send the agency a notification email when a new comment arrives.
    Swallows all errors — a comment POST must never fail because email broke.
    """
    try:
        if not settings.RESEND_API_KEY:
            return  # email not configured in this env

        profile_res = (
            supabase.table("profiles")
            .select("agency_name,agency_email,comment_notifications_enabled")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        profile = (profile_res.data if profile_res else None) or {}

        if profile.get("comment_notifications_enabled") is False:
            return  # agency has muted these

        # Prefer agency_email, fall back to the auth user's login email
        recipient = (profile.get("agency_email") or "").strip()
        if not recipient:
            try:
                user_res = supabase.auth.admin.get_user_by_id(user_id)
                recipient = (user_res.user.email if user_res.user else "") or ""
            except Exception:
                recipient = ""

        if not recipient:
            logger.info("No recipient email for user %s — skipping comment notification", user_id)
            return

        # Report + client context for the email subject/header
        report_res = (
            supabase.table("reports")
            .select("title,client_id")
            .eq("id", report_id)
            .maybe_single()
            .execute()
        )
        report = (report_res.data if report_res else None) or {}
        client_name = ""
        if report.get("client_id"):
            client_res = (
                supabase.table("clients")
                .select("name")
                .eq("id", report["client_id"])
                .maybe_single()
                .execute()
            )
            client_name = ((client_res.data if client_res else None) or {}).get("name", "")

        sender_name = profile.get("agency_name") or "GoReportPilot"
        report_title = report.get("title") or "Report"

        comments_url = f"{settings.FRONTEND_URL}/dashboard/reports/{report_id}?tab=comments"

        html = build_comment_notification_email_html(
            client_name     = client_name,
            report_title    = report_title,
            commenter_name  = commenter_name,
            commenter_email = commenter_email,
            comment_text    = comment_text,
            target_label    = _target_label(slide_number, section_key),
            comments_url    = comments_url,
        )

        await send_plain_email(
            to_emails   = [recipient],
            subject     = f"New comment on {report_title} — {client_name}".strip(" —"),
            html_body   = html,
            sender_name = sender_name,
            reply_to    = commenter_email,
        )
    except Exception as exc:
        logger.warning("Comment notification email failed: %s", exc)


# ---------------------------------------------------------------------------
# Public endpoint: POST /api/shares/{share_token}/comments
# ---------------------------------------------------------------------------

@public_router.post(
    "/{share_token}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/hour")
async def post_comment(
    share_token: str,
    body: CommentCreateRequest,
    request: Request,
) -> CommentResponse:
    """
    Public endpoint — clients post comments without logging in.
    Rate-limited to 5/hour per IP to prevent spam.
    """
    supabase = get_supabase_admin()
    shared   = _load_active_share(supabase, share_token)

    section_key = _normalise_section_key(body.section_key)
    viewer_ip   = request.client.host if request.client else None

    insert_payload = {
        "share_id":     shared["id"],
        "report_id":    shared["report_id"],
        "user_id":      shared["user_id"],
        "client_name":  body.client_name.strip(),
        "client_email": body.client_email,  # already normalised by validator
        "slide_number": body.slide_number,
        "section_key":  section_key,
        "comment_text": body.comment_text.strip(),
        "commenter_ip": viewer_ip,
    }

    result = supabase.table("report_comments").insert(insert_payload).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save comment.",
        )

    row = result.data[0]
    logger.info(
        "Comment posted on share %s by %s (slide=%s section=%s)",
        share_token, insert_payload["client_email"], body.slide_number, section_key,
    )

    # Fire-and-forget notification — never bubble errors up
    await _notify_agency_of_comment(
        supabase        = supabase,
        user_id         = shared["user_id"],
        report_id       = shared["report_id"],
        share_id        = shared["id"],
        commenter_name  = insert_payload["client_name"],
        commenter_email = insert_payload["client_email"],
        comment_text    = insert_payload["comment_text"],
        slide_number    = body.slide_number,
        section_key     = section_key,
    )

    return _row_to_response(row)


# ---------------------------------------------------------------------------
# Public endpoint: GET /api/shares/{share_token}/comments
# ---------------------------------------------------------------------------

@public_router.get(
    "/{share_token}/comments",
    response_model=CommentListResponse,
)
@limiter.limit("60/minute")
async def list_share_comments(
    share_token: str,
    request: Request,  # noqa: ARG001 — required by slowapi key_func
) -> CommentListResponse:
    """Public list of all comments on a share link (oldest → newest)."""
    supabase = get_supabase_admin()
    shared   = _load_active_share(supabase, share_token)

    res = (
        supabase.table("report_comments")
        .select("id,share_id,report_id,client_name,client_email,slide_number,"
                "section_key,comment_text,is_resolved,resolved_at,created_at")
        .eq("share_id", shared["id"])
        .order("created_at", desc=False)
        .execute()
    )
    rows = res.data or []
    items = [_row_to_response(r) for r in rows]
    return CommentListResponse(comments=items, total=len(items))


# ---------------------------------------------------------------------------
# Agency endpoint: GET /api/comments/unread
# ---------------------------------------------------------------------------

@agency_router.get("/unread")
async def list_unread_comments(
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Return unresolved-comment counts grouped by report plus a grand total.

    Response shape:
        {
          "total": 7,
          "by_report": [
            { "report_id": "...", "unresolved_count": 3, "last_comment_at": "..." },
            ...
          ]
        }
    """
    supabase = get_supabase_admin()

    res = (
        supabase.table("report_comments")
        .select("report_id,created_at")
        .eq("user_id", user_id)
        .eq("is_resolved", False)
        .order("created_at", desc=True)
        .execute()
    )
    rows = res.data or []

    buckets: dict[str, dict] = {}
    for r in rows:
        rid = r["report_id"]
        entry = buckets.setdefault(rid, {"report_id": rid, "unresolved_count": 0, "last_comment_at": r["created_at"]})
        entry["unresolved_count"] += 1
        # rows ordered desc by created_at → the first one we see per report is the latest
        if not entry.get("last_comment_at") or r["created_at"] > entry["last_comment_at"]:
            entry["last_comment_at"] = r["created_at"]

    by_report = sorted(
        buckets.values(),
        key=lambda x: x.get("last_comment_at") or "",
        reverse=True,
    )
    return {"total": len(rows), "by_report": by_report}


# ---------------------------------------------------------------------------
# Agency endpoint: GET /api/comments/report/{report_id}
# Convenience for the dashboard: owner-scoped list of all comments on a report.
# ---------------------------------------------------------------------------

@agency_router.get("/report/{report_id}", response_model=CommentListResponse)
async def list_report_comments(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
) -> CommentListResponse:
    """List every comment on a report the agency owns (newest first)."""
    supabase = get_supabase_admin()

    # Defence-in-depth ownership check
    owner = (
        supabase.table("reports")
        .select("id")
        .eq("id", report_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not (owner.data if owner else None):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    res = (
        supabase.table("report_comments")
        .select("id,share_id,report_id,client_name,client_email,slide_number,"
                "section_key,comment_text,is_resolved,resolved_at,created_at")
        .eq("report_id", report_id)
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    rows = res.data or []
    return CommentListResponse(
        comments=[_row_to_response(r) for r in rows],
        total=len(rows),
    )


# ---------------------------------------------------------------------------
# Agency endpoint: PATCH /api/comments/{comment_id}/resolve
# ---------------------------------------------------------------------------

@agency_router.patch("/{comment_id}/resolve", response_model=CommentResponse)
async def resolve_comment(
    comment_id: str,
    body: ResolveRequest,
    user_id: str = Depends(get_current_user_id),
) -> CommentResponse:
    """Mark a comment as resolved (or un-resolve it by passing is_resolved=false)."""
    supabase = get_supabase_admin()

    # Verify ownership
    existing = (
        supabase.table("report_comments")
        .select("id,user_id")
        .eq("id", comment_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not (existing.data if existing else None):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found.",
        )

    update_payload: dict = {
        "is_resolved":         body.is_resolved,
        "resolved_at":         datetime.now(timezone.utc).isoformat() if body.is_resolved else None,
        "resolved_by_user_id": user_id if body.is_resolved else None,
    }

    result = (
        supabase.table("report_comments")
        .update(update_payload)
        .eq("id", comment_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update comment.",
        )

    return _row_to_response(result.data[0])


# ---------------------------------------------------------------------------
# Agency endpoint: DELETE /api/comments/{comment_id}
# ---------------------------------------------------------------------------

@agency_router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: str,
    user_id: str = Depends(get_current_user_id),
) -> None:
    """Hard-delete a comment (owner only). Useful for spam triage."""
    supabase = get_supabase_admin()

    existing = (
        supabase.table("report_comments")
        .select("id")
        .eq("id", comment_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not (existing.data if existing else None):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found.",
        )

    supabase.table("report_comments").delete().eq("id", comment_id).eq("user_id", user_id).execute()
    logger.info("Comment %s deleted by user %s", comment_id, user_id)
