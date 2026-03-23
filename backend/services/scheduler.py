"""
Background scheduler — checks for due scheduled reports and processes them.
Runs as a long-lived asyncio task launched via FastAPI lifespan.
Checks every hour; uses next_run_at stored in the DB to decide what to run.
"""
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point — called by the lifespan loop
# ---------------------------------------------------------------------------

async def check_and_run_scheduled_reports() -> None:
    """
    Query for all active schedules whose next_run_at is in the past,
    then generate (and optionally send) a report for each one.
    """
    from services.supabase_client import get_supabase_admin  # noqa: PLC0415
    supabase = get_supabase_admin()

    now = datetime.utcnow()

    result = (
        supabase.table("scheduled_reports")
        .select("*, clients(name,report_config,goals_context,primary_contact_email,industry,logo_url)")
        .eq("is_active", True)
        .lte("next_run_at", now.isoformat())
        .execute()
    )

    if not result.data:
        logger.debug("Scheduler: no due schedules at %s", now.isoformat())
        return

    logger.info("Scheduler: found %d due schedule(s)", len(result.data))
    for schedule in result.data:
        try:
            await _process_scheduled_report(schedule, supabase, now)
        except Exception as exc:
            logger.error(
                "Scheduler: failed to process schedule %s — %s",
                schedule.get("id"), exc,
            )


# ---------------------------------------------------------------------------
# Process one schedule
# ---------------------------------------------------------------------------

async def _process_scheduled_report(schedule: dict, supabase, now: datetime) -> None:
    """Generate a report for one schedule and optionally send it via email."""
    from datetime import timedelta  # noqa: PLC0415
    from routers.reports import _generate_report_internal  # noqa: PLC0415

    client_id = schedule["client_id"]
    user_id   = schedule["user_id"]
    template  = schedule.get("template", "full")
    frequency = schedule.get("frequency", "monthly")

    # ── Calculate report period based on frequency ──────────────────────────
    today = now.date()
    if frequency == "weekly":
        period_end   = today
        period_start = today - timedelta(days=7)
    elif frequency == "biweekly":
        period_end   = today
        period_start = today - timedelta(days=14)
    else:  # monthly
        period_end   = today
        period_start = today - timedelta(days=30)

    # ── Generate the report ─────────────────────────────────────────────────
    logger.info(
        "Scheduler: generating %s %s report for client %s (%s → %s)",
        frequency, template, client_id, period_start, period_end,
    )
    row, client_name = await _generate_report_internal(
        client_id=client_id,
        user_id=user_id,
        period_start=str(period_start),
        period_end=str(period_end),
        template=template,
        supabase=supabase,
    )
    report_id = row["id"]

    # ── Auto-send if configured ─────────────────────────────────────────────
    if schedule.get("auto_send") and schedule.get("send_to_emails"):
        await _send_scheduled_report(
            row=row,
            client_name=client_name,
            schedule=schedule,
            user_id=user_id,
            supabase=supabase,
            period_start=str(period_start),
            period_end=str(period_end),
        )

    # ── Advance next_run_at ──────────────────────────────────────────────────
    from routers.scheduled_reports import _calculate_next_run  # noqa: PLC0415
    next_run = _calculate_next_run(
        schedule["frequency"],
        schedule.get("day_of_week"),
        schedule.get("day_of_month"),
        schedule.get("time_utc", "09:00"),
    )
    supabase.table("scheduled_reports").update({
        "last_generated_at": now.isoformat(),
        "next_run_at":       next_run.isoformat(),
        "updated_at":        now.isoformat(),
    }).eq("id", schedule["id"]).execute()

    logger.info(
        "Scheduler: report %s generated for client %s; next run at %s",
        report_id, client_id, next_run,
    )


async def _send_scheduled_report(
    *,
    row: dict,
    client_name: str,
    schedule: dict,
    user_id: str,
    supabase,
    period_start: str,
    period_end: str,
) -> None:
    """Send the generated report files by email."""
    from services.email_service import build_report_email_html, send_report_email  # noqa: PLC0415

    # Fetch user profile for sender settings
    profile_result = (
        supabase.table("profiles")
        .select("agency_name,agency_email,sender_name,reply_to_email,email_footer")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    _p = profile_result.data or {}
    sender_name = _p.get("sender_name") or _p.get("agency_name") or "ReportPilot"
    reply_to    = _p.get("reply_to_email") or _p.get("agency_email") or ""
    agency_name = _p.get("agency_name") or "Your Agency"

    # Build HTML body
    narrative   = row.get("ai_narrative") or {}
    html_body   = build_report_email_html(
        client_name=client_name,
        period_start=period_start,
        period_end=period_end,
        report_title=row.get("title", f"{client_name} — Performance Report"),
        executive_summary=narrative.get("executive_summary", ""),
        agency_name=agency_name,
        agency_email=_p.get("agency_email", ""),
        email_footer=_p.get("email_footer", ""),
    )

    # Attach files from disk
    from routers.reports import REPORTS_BASE_DIR  # noqa: PLC0415
    report_dir = os.path.join(REPORTS_BASE_DIR, row["id"])
    pdf_path   = os.path.join(report_dir, "report.pdf")
    pptx_path  = os.path.join(report_dir, "report.pptx")

    try:
        await send_report_email(
            to_emails=schedule["send_to_emails"],
            subject=f"{client_name} — Performance Report ({period_start} to {period_end})",
            html_body=html_body,
            sender_name=sender_name,
            reply_to=reply_to or None,
            pptx_path=pptx_path if os.path.exists(pptx_path) else None,
            pdf_path=pdf_path  if os.path.exists(pdf_path)  else None,
        )
        supabase.table("reports").update({"status": "sent"}).eq("id", row["id"]).execute()
        logger.info("Scheduled report %s sent to %s", row["id"], schedule["send_to_emails"])
    except Exception as exc:
        logger.error("Scheduler: email send failed for report %s: %s", row["id"], exc)
