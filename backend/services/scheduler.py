"""
Background scheduler — checks for due scheduled reports and processes them.
Runs as a long-lived asyncio task launched via FastAPI lifespan.
Checks every hour; uses next_run_at stored in the DB to decide what to run.
"""
import logging
import os
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection health cadence (Phase 2)
# ---------------------------------------------------------------------------
# Health probes run AT MOST once every HEALTH_CHECK_INTERVAL_SECONDS across
# the whole process. The main scheduler loop (every 15 min) calls
# check_and_run_health_checks() each tick; this module-level timestamp
# short-circuits until the interval has elapsed.

HEALTH_CHECK_INTERVAL_SECONDS = 6 * 3600   # 6 hours
_last_health_check_ts: float = 0.0


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
        logger.info("Scheduler: no due schedules at %s", now.isoformat())
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

    client_id       = schedule["client_id"]
    user_id         = schedule["user_id"]
    template        = schedule.get("template", "full")
    frequency       = schedule.get("frequency", "monthly")
    visual_template = schedule.get("visual_template") or "modern_clean"

    # ── Plan pre-check for the visual template ────────────────────────────
    # _generate_report_internal will also clamp internally, but we
    # log a warning here for operator visibility when a schedule
    # references a template the user's current plan no longer allows
    # (e.g. downgraded from Pro to Starter).
    try:
        from middleware.plan_enforcement import get_user_subscription  # noqa: PLC0415
        from services.plans import get_plan  # noqa: PLC0415
        _sub = get_user_subscription(user_id)
        _plan_name = _sub.get("plan", "trial")
        _allowed = (
            get_plan(_plan_name).get("features", {}).get("visual_templates")
            or ["modern_clean"]
        )
        if visual_template not in _allowed:
            logger.warning(
                "Scheduler: plan %s does not allow visual_template=%s for "
                "schedule %s — overriding to modern_clean",
                _plan_name, visual_template, schedule.get("id"),
            )
            visual_template = "modern_clean"
    except Exception as exc:
        logger.debug("Scheduler: plan pre-check skipped — %s", exc)

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
        "Scheduler: generating %s %s report for client %s (%s → %s, visual=%s)",
        frequency, template, client_id, period_start, period_end, visual_template,
    )
    row, client_name = await _generate_report_internal(
        client_id=client_id,
        user_id=user_id,
        period_start=str(period_start),
        period_end=str(period_end),
        template=template,
        visual_template=visual_template,
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

    # Attach files from disk — honor the schedule's attachment_type setting
    # so "pdf only" schedules don't also ship a 2 MB PPTX the user didn't ask
    # for. Defaults to "both" for legacy rows.
    from routers.reports import REPORTS_BASE_DIR  # noqa: PLC0415
    report_dir = os.path.join(REPORTS_BASE_DIR, row["id"])
    pdf_path   = os.path.join(report_dir, "report.pdf")
    pptx_path  = os.path.join(report_dir, "report.pptx")

    attachment_type = (schedule.get("attachment_type") or "both").lower()
    if attachment_type not in ("pdf", "pptx", "both"):
        attachment_type = "both"

    send_pdf  = attachment_type in ("pdf",  "both") and os.path.exists(pdf_path)
    send_pptx = attachment_type in ("pptx", "both") and os.path.exists(pptx_path)

    try:
        await send_report_email(
            to_emails=schedule["send_to_emails"],
            subject=f"{client_name} — Performance Report ({period_start} to {period_end})",
            html_body=html_body,
            sender_name=sender_name,
            reply_to=reply_to or None,
            pptx_path=pptx_path if send_pptx else None,
            pdf_path=pdf_path  if send_pdf  else None,
        )
        supabase.table("reports").update({"status": "sent"}).eq("id", row["id"]).execute()
        logger.info(
            "Scheduled report %s sent to %s (attachment_type=%s)",
            row["id"], schedule["send_to_emails"], attachment_type,
        )
    except Exception as exc:
        logger.error("Scheduler: email send failed for report %s: %s", row["id"], exc)


# ---------------------------------------------------------------------------
# Connection health monitor (Phase 2)
# ---------------------------------------------------------------------------


async def check_and_run_health_checks() -> None:
    """
    Run a sweep of connection health probes.

    Short-circuits if fewer than HEALTH_CHECK_INTERVAL_SECONDS seconds have
    elapsed since the last successful sweep. Safe to call every scheduler
    tick — the cadence lives here, not at the caller.
    """
    global _last_health_check_ts  # noqa: PLW0603

    now = time.monotonic()
    if (now - _last_health_check_ts) < HEALTH_CHECK_INTERVAL_SECONDS:
        remaining = int(HEALTH_CHECK_INTERVAL_SECONDS - (now - _last_health_check_ts))
        logger.debug("Health check skipped — %d seconds until next sweep", remaining)
        return

    try:
        from services.health_check import check_all_connections_health  # noqa: PLC0415
        from services.supabase_client import get_supabase_admin         # noqa: PLC0415
        supabase = get_supabase_admin()
        await check_all_connections_health(supabase)
        _last_health_check_ts = now
    except Exception as exc:
        logger.error("Health check sweep failed: %s", exc)
        # Do NOT advance _last_health_check_ts on failure so we retry next tick.
