"""
Scheduled report CRUD endpoints.
Create, read, update, delete per-client report schedules.
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from middleware.auth import get_current_user_id
from models.schemas import (
    ScheduledReportCreate,
    ScheduledReportResponse,
    ScheduledReportUpdate,
)
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helper: calculate next_run_at
# ---------------------------------------------------------------------------

def _calculate_next_run(
    frequency: str,
    day_of_week: int | None,
    day_of_month: int | None,
    time_utc: str,
) -> datetime:
    """
    Calculate the next UTC datetime this schedule should run.
    Always returns a future datetime (at least a moment ahead of now).
    """
    now = datetime.utcnow()

    # Parse HH:MM time string
    parts = time_utc.split(":")
    hour   = int(parts[0]) if len(parts) > 0 else 9
    minute = int(parts[1]) if len(parts) > 1 else 0

    if frequency in ("weekly", "biweekly"):
        target_dow = day_of_week if day_of_week is not None else 0  # 0 = Monday
        days_ahead  = (target_dow - now.weekday()) % 7
        # biweekly uses 14-day cycles; push ahead by 14 if same-day
        step = 14 if frequency == "biweekly" else 7
        if days_ahead == 0:
            days_ahead = step
        next_date = (now + timedelta(days=days_ahead)).date()

    else:  # monthly
        target_day = day_of_month if day_of_month is not None else 1
        target_day = min(target_day, 28)  # guard against February edge cases

        # Try current month first
        try:
            candidate = now.replace(day=target_day, hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError:
            candidate = now.replace(day=28, hour=hour, minute=minute, second=0, microsecond=0)

        if candidate <= now:
            # Move to next month
            month = now.month + 1 if now.month < 12 else 1
            year  = now.year + 1 if now.month == 12 else now.year
            candidate = candidate.replace(year=year, month=month)

        return candidate

    return datetime.combine(next_date, datetime.min.time().replace(hour=hour, minute=minute))


def _row_to_response(row: dict) -> ScheduledReportResponse:
    """Convert raw DB row to ScheduledReportResponse, normalising list fields."""
    row = dict(row)
    emails = row.get("send_to_emails") or []
    if isinstance(emails, str):
        import json
        try:
            emails = json.loads(emails)
        except Exception:
            emails = []
    row["send_to_emails"] = emails
    return ScheduledReportResponse(**row)


# ---------------------------------------------------------------------------
# POST /api/scheduled-reports  — create schedule
# ---------------------------------------------------------------------------

@router.post("", response_model=ScheduledReportResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: ScheduledReportCreate,
    user_id: str = Depends(get_current_user_id),
) -> ScheduledReportResponse:
    """Create an automated report schedule for a client."""
    supabase = get_supabase_admin()

    # Verify client ownership
    client_check = (
        supabase.table("clients")
        .select("id,primary_contact_email")
        .eq("id", payload.client_id)
        .eq("user_id", user_id)
        .eq("is_active", True)
        .single()
        .execute()
    )
    if not client_check.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    next_run = _calculate_next_run(
        payload.frequency,
        payload.day_of_week,
        payload.day_of_month,
        payload.time_utc,
    )

    insert_data = {
        "client_id":      payload.client_id,
        "user_id":        user_id,
        "frequency":      payload.frequency,
        "day_of_week":    payload.day_of_week,
        "day_of_month":   payload.day_of_month,
        "time_utc":       payload.time_utc,
        "template":       payload.template,
        "auto_send":      payload.auto_send,
        "send_to_emails": payload.send_to_emails,
        "is_active":      True,
        "next_run_at":    next_run.isoformat(),
    }

    result = supabase.table("scheduled_reports").insert(insert_data).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create schedule",
        )
    logger.info("Schedule created for client %s, next run: %s", payload.client_id, next_run)
    return _row_to_response(result.data[0])


# ---------------------------------------------------------------------------
# GET /api/scheduled-reports/client/{client_id}
# ---------------------------------------------------------------------------

@router.get("/client/{client_id}", response_model=list[ScheduledReportResponse])
async def get_client_schedules(
    client_id: str,
    user_id: str = Depends(get_current_user_id),
) -> list[ScheduledReportResponse]:
    """Return all schedules for a specific client (owned by the user)."""
    supabase = get_supabase_admin()
    result = (
        supabase.table("scheduled_reports")
        .select("*")
        .eq("client_id", client_id)
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    return [_row_to_response(row) for row in (result.data or [])]


# ---------------------------------------------------------------------------
# GET /api/scheduled-reports  — list all user's schedules
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ScheduledReportResponse])
async def list_schedules(
    user_id: str = Depends(get_current_user_id),
) -> list[ScheduledReportResponse]:
    """List all active report schedules for the authenticated user."""
    supabase = get_supabase_admin()
    result = (
        supabase.table("scheduled_reports")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [_row_to_response(row) for row in (result.data or [])]


# ---------------------------------------------------------------------------
# PATCH /api/scheduled-reports/{schedule_id}
# ---------------------------------------------------------------------------

@router.patch("/{schedule_id}", response_model=ScheduledReportResponse)
async def update_schedule(
    schedule_id: str,
    payload: ScheduledReportUpdate,
    user_id: str = Depends(get_current_user_id),
) -> ScheduledReportResponse:
    """Update schedule fields. Recalculates next_run_at if timing fields change."""
    supabase = get_supabase_admin()

    # Fetch existing schedule
    existing_result = (
        supabase.table("scheduled_reports")
        .select("*")
        .eq("id", schedule_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not existing_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    existing = existing_result.data
    updates  = payload.model_dump(exclude_none=True)
    if not updates:
        return _row_to_response(existing)

    updates["updated_at"] = datetime.utcnow().isoformat()

    # Recalculate next_run_at if any timing field changed
    timing_fields = {"frequency", "day_of_week", "day_of_month", "time_utc"}
    if timing_fields & set(updates.keys()):
        new_freq    = updates.get("frequency",    existing.get("frequency", "monthly"))
        new_dow     = updates.get("day_of_week",  existing.get("day_of_week"))
        new_dom     = updates.get("day_of_month", existing.get("day_of_month"))
        new_time    = updates.get("time_utc",     existing.get("time_utc", "09:00"))
        next_run    = _calculate_next_run(new_freq, new_dow, new_dom, new_time)
        updates["next_run_at"] = next_run.isoformat()

    result = (
        supabase.table("scheduled_reports")
        .update(updates)
        .eq("id", schedule_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update schedule",
        )
    return _row_to_response(result.data[0])


# ---------------------------------------------------------------------------
# DELETE /api/scheduled-reports/{schedule_id}
# ---------------------------------------------------------------------------

@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: str,
    user_id: str = Depends(get_current_user_id),
) -> None:
    """Delete a schedule."""
    supabase = get_supabase_admin()
    result = (
        supabase.table("scheduled_reports")
        .delete()
        .eq("id", schedule_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
