"""
Report generation and management endpoints.
Trigger report generation, list reports, get report details, download files.
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from middleware.auth import get_current_user_id
from middleware.plan_enforcement import get_user_subscription, can_use_feature
from services.plans import get_plan
from models.schemas import (
    ReportGenerateRequest,
    ReportListItem,
    ReportListResponse,
    ReportResponse,
    ReportSectionRegenerateRequest,
    ReportSendRequest,
    ReportUpdateRequest,
)
from services.supabase_client import get_supabase_admin
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)
router = APIRouter()


def _sanitize_data_for_ai(data: dict) -> dict:
    """
    Return a deep copy of *data* with all float values rounded to 2 decimal places.

    Prevents raw floats (e.g. 2.9600000001, 0.030000000000000002) from appearing
    verbatim in AI-generated report text.  NaN and Infinity are replaced with 0.
    """
    import copy
    import math

    def _clean(obj):
        if isinstance(obj, float):
            if not math.isfinite(obj):
                return 0.0
            return round(obj, 2)
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean(item) for item in obj]
        return obj

    return _clean(copy.deepcopy(data))


def _map_db_row(row: dict, client_name: str | None = None) -> dict:
    """
    Translate raw Supabase report row to the field names expected by
    ReportResponse / ReportListItem.

    DB column  →  API field
    ai_narrative  →  narrative
    sections      →  data_summary  (extracted from sections JSONB)
    pptx_file_url →  pptx_url
    pdf_file_url  →  pdf_url
    """
    sections = row.get("sections") or {}
    return {
        "id":            row["id"],
        "user_id":       row["user_id"],
        "client_id":     row["client_id"],
        "client_name":   client_name,
        "title":         row["title"],
        "status":        row["status"],
        "period_start":  str(row["period_start"]),
        "period_end":    str(row["period_end"]),
        "narrative":     row.get("ai_narrative"),
        "data_summary":  sections.get("data_summary") if isinstance(sections, dict) else None,
        "meta_currency": sections.get("meta_currency", "USD") if isinstance(sections, dict) else "USD",
        "user_edits":    row.get("user_edits"),
        "pptx_url":      row.get("pptx_file_url"),
        "pdf_url":       row.get("pdf_file_url"),
        "created_at":    row["created_at"],
        "updated_at":    row["updated_at"],
    }

# Local storage directory — lives inside backend/generated_reports/
# Gitignored; move to Supabase Storage in a later phase.
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
REPORTS_BASE_DIR = os.path.join(_HERE, "generated_reports")


# ---------------------------------------------------------------------------
# _generate_report_internal — shared by the API endpoint and the scheduler
# ---------------------------------------------------------------------------

async def _generate_report_internal(
    *,
    client_id: str,
    user_id: str,
    period_start: str,
    period_end: str,
    template: str = "full",
    visual_template: str = "modern_clean",
    csv_sources: list[dict] | None = None,
    supabase=None,
) -> dict:
    """
    Core report generation pipeline.  Returns the raw DB row dict on success.
    Raises HTTPException (or any exception) on failure.

    Shared between:
      • POST /api/reports/generate  (API endpoint)
      • services/scheduler.py       (automated scheduled reports)
    """
    if supabase is None:
        supabase = get_supabase_admin()

    # 0 — Subscription status check: block expired/cancelled users
    sub = get_user_subscription(user_id)
    if sub.get("status") in ("expired", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your subscription has expired. Please upgrade to continue generating reports.",
        )

    # 0a — Trial report limit (5 reports during free trial)
    if sub.get("status") == "trialing":
        report_count_resp = (
            supabase.table("reports")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        trial_report_count = report_count_resp.count if report_count_resp.count is not None else 0
        if trial_report_count >= 5:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You've used all 5 trial reports. Upgrade to a paid plan for unlimited reports.",
            )

    # 1 — Verify client ownership
    client_result = (
        supabase.table("clients")
        .select("*")
        .eq("id", client_id)
        .eq("user_id", user_id)
        .eq("is_active", True)
        .single()
        .execute()
    )
    if not client_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    client = client_result.data

    # 1a — Plan enforcement: clamp AI tone and visual template to allowed values
    # (sub was fetched above in step 0)
    user_plan = sub.get("plan", "trial")
    plan_cfg = get_plan(user_plan)
    plan_features = plan_cfg.get("features", {})

    allowed_tones = plan_features.get("ai_tones", ["professional"])
    client_tone = client.get("ai_tone", "professional")
    if client_tone not in allowed_tones:
        client["ai_tone"] = allowed_tones[0]  # override to first allowed tone

    allowed_templates = plan_features.get("visual_templates", ["modern_clean"])
    if visual_template not in allowed_templates:
        visual_template = allowed_templates[0]  # override to first allowed template

    show_powered_by = plan_features.get("powered_by_badge", True)

    # 1b — Read report_config (section toggles, KPI selection, template, custom section)
    report_config: dict = client.get("report_config") or {}
    cfg_sections    = report_config.get("sections", {})     # section toggle dict
    cfg_template    = template or report_config.get("template", "full")
    cfg_custom      = {
        "title": report_config.get("custom_section_title", ""),
        "text":  report_config.get("custom_section_text",  ""),
    }

    # 2 — Pull real data from connected platforms only.
    # If a platform is NOT connected, its data is None — no mock/fake data.

    # Check for an active GA4 connection for this client
    ga4_conn_result = (
        supabase.table("connections")
        .select("id,account_id,access_token_encrypted,refresh_token_encrypted,token_expires_at")
        .eq("client_id", client_id)
        .eq("platform", "ga4")
        .eq("status", "active")
        .limit(1)
        .execute()
    )

    ga4_data = None
    if ga4_conn_result.data:
        ga4_conn = ga4_conn_result.data[0]
        try:
            from services.google_analytics import pull_ga4_data  # noqa: PLC0415
            # Parse token_expires_at ISO string → unix timestamp float
            raw_exp = ga4_conn.get("token_expires_at")
            token_expires_ts: float | None = None
            if raw_exp:
                try:
                    from datetime import timezone as _tz  # noqa: PLC0415
                    # Python 3.11+ fromisoformat handles 'Z' and offset suffixes
                    dt = datetime.fromisoformat(str(raw_exp).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=_tz.utc)
                    token_expires_ts = dt.timestamp()
                except Exception:
                    pass
            ga4_data = await pull_ga4_data(
                access_token_encrypted=ga4_conn["access_token_encrypted"],
                refresh_token_encrypted=ga4_conn["refresh_token_encrypted"],
                token_expires_at=token_expires_ts,
                property_id=ga4_conn["account_id"],
                period_start=period_start,
                period_end=period_end,
                connection_id=ga4_conn["id"],
                supabase=supabase,
            )
            logger.info("Using real GA4 data for client %s", client_id)
        except Exception:
            logger.exception(
                "Real GA4 pull failed for client %s — falling back to mock data",
                client_id,
            )
            ga4_data = None

        # Persist snapshot for multi-period trend analysis (non-fatal).
        if ga4_data is not None:
            from services.snapshot_saver import save_snapshot  # noqa: PLC0415
            save_snapshot(
                supabase,
                connection_id=ga4_conn["id"],
                client_id=client_id,
                platform="ga4",
                period_start=period_start,
                period_end=period_end,
                metrics=ga4_data,
            )

    # Check for an active Meta Ads connection for this client
    meta_conn_result = (
        supabase.table("connections")
        .select("id,account_id,currency,access_token_encrypted,refresh_token_encrypted,token_expires_at")
        .eq("client_id", client_id)
        .eq("platform", "meta_ads")
        .eq("status", "active")
        .limit(1)
        .execute()
    )

    meta_data = None
    meta_currency = "USD"  # default; overridden when a real connection exists
    if meta_conn_result.data:
        meta_conn = meta_conn_result.data[0]
        meta_currency = meta_conn.get("currency", "USD") or "USD"
        try:
            from services.meta_ads import pull_meta_ads_data  # noqa: PLC0415
            meta_data = await pull_meta_ads_data(
                account_id=meta_conn["account_id"],
                access_token_encrypted=meta_conn["access_token_encrypted"],
                period_start=period_start,
                period_end=period_end,
                connection_id=meta_conn["id"],
                currency=meta_currency,
            )
            logger.info("Using real Meta Ads data for client %s", client_id)
        except Exception:
            logger.exception(
                "Real Meta Ads pull failed for client %s — falling back to mock data",
                client_id,
            )
            meta_data = None

        # Persist snapshot for multi-period trend analysis (non-fatal).
        if meta_data is not None:
            from services.snapshot_saver import save_snapshot  # noqa: PLC0415
            save_snapshot(
                supabase,
                connection_id=meta_conn["id"],
                client_id=client_id,
                platform="meta_ads",
                period_start=period_start,
                period_end=period_end,
                metrics=meta_data,
            )

    # Build raw_data from ONLY real/connected data — no mock data.
    raw_data: dict = {
        "client_name": client["name"],
        "period_start": period_start,
        "period_end": period_end,
    }
    if ga4_data is not None:
        raw_data["ga4"] = ga4_data
    if meta_data is not None:
        raw_data["meta_ads"] = meta_data
        raw_data["meta_ads"]["currency"] = meta_currency

    # Inject ad-hoc CSV sources supplied at generation time
    if csv_sources:
        raw_data["csv_sources"] = csv_sources

    # Require at least one data source
    has_data = ga4_data is not None or meta_data is not None or bool(csv_sources)
    if not has_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No data sources connected for this client. Connect GA4, Meta Ads, or upload a CSV before generating a report.",
        )

    # 3 — AI narrative (async I/O)
    # Round all floats before passing to GPT-4o so the AI doesn't copy raw
    # floating-point noise (e.g. 2.9600000001) into generated report text.
    from services.ai_narrative import generate_narrative  # noqa: PLC0415
    narrative = await generate_narrative(
        data=_sanitize_data_for_ai(raw_data),
        client_name=client["name"],
        client_goals=client.get("goals_context"),
        tone=client.get("ai_tone", "professional"),
        template=cfg_template,
        language=client.get("report_language", "en") or "en",
    )

    # 4 — Fetch agency branding first (needed for branded charts + reports)
    profile_result = (
        supabase.table("profiles")
        .select("agency_name,agency_logo_url,brand_color,sender_name,agency_email")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    _profile = profile_result.data or {}

    # White-label enforcement: Starter plan gets no custom branding
    has_white_label = plan_features.get("white_label", False)
    branding = {
        "agency_name":     ((_profile.get("agency_name") or "").strip() or "Your Agency") if has_white_label else "Your Agency",
        "agency_logo_url": (_profile.get("agency_logo_url") or "") if has_white_label else "",
        "brand_color":     (_profile.get("brand_color") or "#4338CA") if has_white_label else "#4338CA",
        "client_logo_url": (client.get("logo_url") or "") if has_white_label else "",
        "powered_by_badge": show_powered_by,
    }

    # 5 — Generate charts (sync, run in thread pool)
    report_id = str(uuid.uuid4())
    charts_dir = os.path.join(REPORTS_BASE_DIR, report_id, "charts")

    # Pass AI-generated per-chart action titles (from the narrative engine)
    # so charts render with takeaway headlines instead of generic labels.
    _chart_insights = (narrative or {}).get("chart_insights") or {}

    _report_language = client.get("report_language", "en") or "en"

    from services.chart_generator import generate_all_charts  # noqa: PLC0415
    charts = await asyncio.to_thread(
        generate_all_charts, raw_data, charts_dir, branding["brand_color"], visual_template,
        _chart_insights, _report_language,
    )

    client_info = {
        "name":        client["name"],
        "agency_name": branding["agency_name"],
    }

    # 6 — Build report files (sync, run in thread pool)
    from services.report_generator import generate_pdf_report, generate_pptx_report  # noqa: PLC0415
    pptx_bytes, pdf_bytes = await asyncio.gather(
        asyncio.to_thread(
            generate_pptx_report, raw_data, narrative, charts, client_info,
            cfg_sections if cfg_sections else None,
            cfg_template,
            cfg_custom if cfg_custom.get("title") else None,
            branding,
            visual_template,
            _report_language,
        ),
        asyncio.to_thread(
            generate_pdf_report, raw_data, narrative, charts, client_info,
            cfg_sections if cfg_sections else None,
            cfg_template,
            cfg_custom if cfg_custom.get("title") else None,
            branding,
            visual_template,
            _report_language,
        ),
    )

    # 6 — Save to disk
    report_dir = os.path.join(REPORTS_BASE_DIR, report_id)
    os.makedirs(report_dir, exist_ok=True)

    pptx_path = os.path.join(report_dir, "report.pptx")
    pdf_path  = os.path.join(report_dir, "report.pdf")

    with open(pptx_path, "wb") as f:
        f.write(pptx_bytes)

    if pdf_bytes is not None:
        if not os.path.exists(pdf_path):
            # PDF not yet written (non-trial path, or watermark regen skipped)
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
        db_pdf_path: str | None = pdf_path
    else:
        db_pdf_path = None  # Non-Latin language, LibreOffice unavailable — PPTX only
        logger.info(
            "PDF not saved for report %s — non-Latin language with no LibreOffice. "
            "PPTX download will be offered instead.",
            report_id,
        )

    logger.info("Report files saved to %s", report_dir)

    # 7 — Build data_summary for the DB / frontend preview
    ga4_s  = raw_data.get("ga4",      {}).get("summary", {})
    meta_s = raw_data.get("meta_ads", {}).get("summary", {})
    data_summary = {
        "sessions":            ga4_s.get("sessions"),
        "sessions_change":     ga4_s.get("sessions_change"),
        "users":               ga4_s.get("users"),
        "users_change":        ga4_s.get("users_change"),
        "conversions":         ga4_s.get("conversions"),
        "conversions_change":  ga4_s.get("conversions_change"),
        "pageviews":           ga4_s.get("pageviews"),
        "bounce_rate":         ga4_s.get("bounce_rate"),
        "avg_session_duration": ga4_s.get("avg_session_duration"),
        "spend":               meta_s.get("spend"),
        "spend_change":        meta_s.get("spend_change"),
        "impressions":         meta_s.get("impressions"),
        "clicks":              meta_s.get("clicks"),
        "ctr":                 meta_s.get("ctr"),
        "cpc":                 meta_s.get("cpc"),
        "roas":                meta_s.get("roas"),
        "cost_per_conversion": meta_s.get("cost_per_conversion"),
    }

    # 8 — Human-readable title — use the END month of the reporting period
    # so e.g. "Acme — March 2026 Performance Report" rather than the start.
    # Reports are named by the most recent month they cover.
    try:
        month_year = datetime.strptime(period_end, "%Y-%m-%d").strftime("%B %Y")
    except ValueError:
        month_year = period_end
    title = f"{client['name']} — {month_year} Performance Report"

    # 9 — Persist report record in Supabase (use actual DB column names)
    insert_payload = {
        "id":            report_id,
        "user_id":       user_id,
        "client_id":     client_id,
        "title":         title,
        "status":        "draft",           # CHECK: generating|draft|approved|sent|failed
        "period_start":  period_start,
        "period_end":    period_end,
        "pptx_file_url": pptx_path,         # actual DB column name
        "pdf_file_url":  db_pdf_path,       # None when non-Latin + no LibreOffice
        "ai_narrative":  narrative,         # actual DB column name
        "sections": {
            "data_summary":   data_summary,
            "meta_currency":  meta_currency,
            "ai_model":       "gpt-4.1",
            # Compact raw_data for section regeneration (daily arrays omitted to save space)
            "narrative_data": {
                "ga4": {k: v for k, v in raw_data.get("ga4", {}).items() if k != "daily"},
                "meta_ads": {k: v for k, v in raw_data.get("meta_ads", {}).items() if k != "daily"},
                "period_start": raw_data.get("period_start"),
                "period_end":   raw_data.get("period_end"),
            },
        },
    }
    result = supabase.table("reports").insert(insert_payload).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report generated but failed to save to database",
        )

    # Return raw DB row so callers can map it however they need
    return result.data[0], client["name"]


# ---------------------------------------------------------------------------
# POST /generate  — thin wrapper around _generate_report_internal
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def generate_report(
    request: Request,
    payload: ReportGenerateRequest,
    user_id: str = Depends(get_current_user_id),
) -> ReportResponse:
    """
    Full report generation pipeline:
    1. Fetch client  2. Data pull (real or mock)  3. AI narrative  4. Charts
    5. PPTX + PDF    6. Save to disk  7. Store in Supabase
    """
    row, client_name = await _generate_report_internal(
        client_id=payload.client_id,
        user_id=user_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        template=payload.template,
        visual_template=payload.visual_template,
        csv_sources=payload.csv_sources,
    )
    return ReportResponse(**_map_db_row(row, client_name=client_name))


# ---------------------------------------------------------------------------
# GET /client/{client_id}  — list reports for one client
# ---------------------------------------------------------------------------

@router.get("/client/{client_id}", response_model=ReportListResponse)
async def list_client_reports(
    client_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ReportListResponse:
    """List all reports for a specific client (owned by the authenticated user)."""
    supabase = get_supabase_admin()

    # Verify client ownership
    client_result = (
        supabase.table("clients")
        .select("id,name")
        .eq("id", client_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not client_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    client_name = client_result.data["name"]

    reports_result = (
        supabase.table("reports")
        .select("*")
        .eq("client_id", client_id)
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    items = [
        ReportListItem(**_map_db_row(row, client_name=client_name))
        for row in reports_result.data
    ]
    return ReportListResponse(reports=items, total=len(items))


# ---------------------------------------------------------------------------
# GET /  — list all reports for the authenticated user
# ---------------------------------------------------------------------------

@router.get("", response_model=ReportListResponse)
async def list_all_reports(
    user_id: str = Depends(get_current_user_id),
) -> ReportListResponse:
    """List all reports generated by the authenticated user, newest first."""
    supabase = get_supabase_admin()

    reports_result = (
        supabase.table("reports")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    if not reports_result.data:
        return ReportListResponse(reports=[], total=0)

    # Fetch client names in one query
    client_ids = list({r["client_id"] for r in reports_result.data})
    clients_result = (
        supabase.table("clients")
        .select("id,name")
        .in_("id", client_ids)
        .execute()
    )
    client_map = {c["id"]: c["name"] for c in (clients_result.data or [])}

    items = [
        ReportListItem(**_map_db_row(row, client_name=client_map.get(row["client_id"])))
        for row in reports_result.data
    ]
    return ReportListResponse(reports=items, total=len(items))


# ---------------------------------------------------------------------------
# GET /{report_id}
# ---------------------------------------------------------------------------

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ReportResponse:
    """Fetch a single report with full narrative and data summary."""
    supabase = get_supabase_admin()

    result = (
        supabase.table("reports")
        .select("*")
        .eq("id", report_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    row = result.data
    client_result = (
        supabase.table("clients").select("name").eq("id", row["client_id"]).single().execute()
    )
    client_name = client_result.data["name"] if client_result.data else None

    return ReportResponse(**_map_db_row(row, client_name=client_name))


# ---------------------------------------------------------------------------
# GET /{report_id}/download/pptx
# ---------------------------------------------------------------------------

@router.get("/{report_id}/download/pptx")
async def download_pptx(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
) -> FileResponse:
    """Download the PowerPoint (.pptx) file for a report."""
    # Plan check: PPTX export is Pro+ only
    allowed, reason = can_use_feature(user_id, "pptx_export")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PPTX export is available on Pro and Agency plans. Upgrade to download PowerPoint files.",
        )

    supabase = get_supabase_admin()
    result = (
        supabase.table("reports")
        .select("user_id,title")
        .eq("id", report_id)
        .single()
        .execute()
    )
    if not result.data or result.data["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    pptx_path = os.path.join(REPORTS_BASE_DIR, report_id, "report.pptx")
    if not os.path.exists(pptx_path):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "error": "Report files are no longer available. Please regenerate the report.",
                "code": "FILES_EXPIRED",
            },
        )

    safe_title = result.data.get("title", "report").replace(" — ", " - ").replace(" ", "_")[:80]
    return FileResponse(
        pptx_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"{safe_title}.pptx",
    )


# ---------------------------------------------------------------------------
# GET /{report_id}/download/pdf
# ---------------------------------------------------------------------------

@router.get("/{report_id}/download/pdf")
async def download_pdf(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
) -> FileResponse:
    """Download the PDF file for a report."""
    # Subscription check: block expired/cancelled users
    pdf_sub = get_user_subscription(user_id)
    if pdf_sub.get("status") in ("expired", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your subscription has expired. Please upgrade to continue downloading reports.",
        )

    supabase = get_supabase_admin()
    result = (
        supabase.table("reports")
        .select("user_id,title")
        .eq("id", report_id)
        .single()
        .execute()
    )
    if not result.data or result.data["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    pdf_path = os.path.join(REPORTS_BASE_DIR, report_id, "report.pdf")
    if not os.path.exists(pdf_path):
        # Distinguish between "never had a PDF" (non-Latin) vs "files expired"
        pptx_also_missing = not os.path.exists(
            os.path.join(REPORTS_BASE_DIR, report_id, "report.pptx")
        )
        if pptx_also_missing:
            # Both files missing → ephemeral filesystem wiped after redeployment
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={
                    "error": "Report files are no longer available. Please regenerate the report.",
                    "code": "FILES_EXPIRED",
                },
            )
        # PPTX exists but PDF doesn't → non-Latin language, LibreOffice wasn't available
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not available for this report. The report language may require LibreOffice for PDF rendering — please download the PPTX instead.",
        )

    safe_title = result.data.get("title", "report").replace(" — ", " - ").replace(" ", "_")[:80]
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{safe_title}.pdf")


# ---------------------------------------------------------------------------
# PATCH /{report_id}  — save manual user_edits
# ---------------------------------------------------------------------------

@router.patch("/{report_id}", response_model=ReportResponse)
async def update_report_edits(
    report_id: str,
    payload: ReportUpdateRequest,
    user_id: str = Depends(get_current_user_id),
) -> ReportResponse:
    """
    Persist manual text edits for one or more narrative sections.
    Merges the incoming user_edits dict with any existing edits in the DB,
    so editing section A doesn't wipe a previous edit to section B.
    """
    supabase = get_supabase_admin()

    # Fetch existing report (ownership check)
    existing = (
        supabase.table("reports")
        .select("*")
        .eq("id", report_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    row = existing.data
    merged_edits = dict(row.get("user_edits") or {})
    merged_edits.update(payload.user_edits)

    result = (
        supabase.table("reports")
        .update({"user_edits": merged_edits})
        .eq("id", report_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save edits",
        )

    client_result = (
        supabase.table("clients").select("name").eq("id", row["client_id"]).single().execute()
    )
    client_name = client_result.data["name"] if client_result.data else None
    return ReportResponse(**_map_db_row(result.data[0], client_name=client_name))


# ---------------------------------------------------------------------------
# POST /{report_id}/regenerate-section  — re-run AI for one section
# ---------------------------------------------------------------------------

@router.post("/{report_id}/regenerate-section", response_model=ReportResponse)
async def regenerate_section(
    report_id: str,
    payload: ReportSectionRegenerateRequest,
    user_id: str = Depends(get_current_user_id),
) -> ReportResponse:
    """
    Re-run GPT-4o for a single narrative section.
    Uses the compact narrative_data stored in sections JSONB at generation time.
    """
    valid_sections = {
        "executive_summary", "website_performance", "paid_advertising",
        "key_wins", "concerns", "next_steps",
    }
    if payload.section not in valid_sections:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid section '{payload.section}'. Must be one of: {valid_sections}",
        )

    supabase = get_supabase_admin()

    # Fetch report + client for context
    report_result = (
        supabase.table("reports")
        .select("*")
        .eq("id", report_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not report_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    row = report_result.data
    sections_json = row.get("sections") or {}
    narrative_data = sections_json.get("narrative_data")

    if not narrative_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This report does not have stored narrative data for regeneration. "
                   "Please generate a new report.",
        )

    client_result = (
        supabase.table("clients")
        .select("name,goals_context,ai_tone,report_config")
        .eq("id", row["client_id"])
        .single()
        .execute()
    )
    if not client_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    client = client_result.data
    report_config = client.get("report_config") or {}
    cfg_template  = report_config.get("template", "monthly")

    # Re-run AI for just this one section
    from services.ai_narrative import generate_narrative  # noqa: PLC0415
    new_section_narrative = await generate_narrative(
        data=narrative_data,
        client_name=client["name"],
        client_goals=client.get("goals_context"),
        tone=client.get("ai_tone", "professional"),
        template=cfg_template,
        sections=[payload.section],
    )

    # Merge new section into existing ai_narrative
    existing_narrative = dict(row.get("ai_narrative") or {})
    existing_narrative[payload.section] = new_section_narrative.get(payload.section, "")

    # Clear any user_edit for this section (user requested a fresh AI version)
    existing_user_edits = dict(row.get("user_edits") or {})
    existing_user_edits.pop(payload.section, None)

    result = (
        supabase.table("reports")
        .update({
            "ai_narrative": existing_narrative,
            "user_edits":   existing_user_edits,
        })
        .eq("id", report_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save regenerated section",
        )

    client_name = client.get("name")
    return ReportResponse(**_map_db_row(result.data[0], client_name=client_name))


# ---------------------------------------------------------------------------
# POST /{report_id}/send  — deliver report by email
# ---------------------------------------------------------------------------

@router.post("/{report_id}/send", status_code=status.HTTP_200_OK)
@limiter.limit("20/hour")
async def send_report(
    request: Request,
    report_id: str,
    payload: ReportSendRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Send the report to one or more email addresses via Resend.
    Attaches PDF and/or PPTX depending on payload.attachment.
    Logs the delivery attempt in the report_deliveries table.
    """
    # Subscription check: block expired/cancelled users from sending reports
    send_sub = get_user_subscription(user_id)
    if send_sub.get("status") in ("expired", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your subscription has expired. Please upgrade to continue sending reports.",
        )

    supabase = get_supabase_admin()

    # Fetch report
    report_result = (
        supabase.table("reports")
        .select("*")
        .eq("id", report_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not report_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    row = report_result.data

    # Fetch client for contact email fallback
    client_result = (
        supabase.table("clients")
        .select("name,primary_contact_email")
        .eq("id", row["client_id"])
        .single()
        .execute()
    )
    client = client_result.data or {}
    client_name = client.get("name", "Client")

    # Fetch agency/profile settings for sender customisation
    profile_result = (
        supabase.table("profiles")
        .select("agency_name,agency_email,sender_name,reply_to_email,email_footer")
        .eq("id", user_id)
        .single()
        .execute()
    )
    profile = profile_result.data or {}
    agency_name  = profile.get("agency_name")  or "Your Agency"
    agency_email = profile.get("agency_email") or ""
    sender_name  = payload.sender_name or profile.get("sender_name") or agency_name
    reply_to     = payload.reply_to   or profile.get("reply_to_email") or None
    email_footer = profile.get("email_footer") or ""

    # Resolve files — check if ephemeral filesystem still has them
    attach = payload.attachment.lower()
    pptx_path_resolved = os.path.join(REPORTS_BASE_DIR, report_id, "report.pptx")
    pdf_path_resolved  = os.path.join(REPORTS_BASE_DIR, report_id, "report.pdf")

    pptx_exists = os.path.exists(pptx_path_resolved)
    pdf_exists  = os.path.exists(pdf_path_resolved)

    if not pptx_exists and not pdf_exists:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "error": "Report files are no longer available. Please regenerate the report.",
                "code": "FILES_EXPIRED",
            },
        )

    send_pptx = attach in ("pptx", "both") and pptx_exists
    send_pdf  = attach in ("pdf",  "both") and pdf_exists

    if not send_pptx and not send_pdf:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Requested file format not available for this report.",
        )

    # Build email
    sections_json = row.get("sections") or {}
    meta_currency = sections_json.get("meta_currency", "USD") if isinstance(sections_json, dict) else "USD"

    # Use user_edits-merged narrative for executive_summary snippet
    narrative = dict(row.get("ai_narrative") or {})
    user_edits = row.get("user_edits") or {}
    merged_narrative = {**narrative, **{k: v for k, v in user_edits.items() if v}}
    exec_summary = merged_narrative.get("executive_summary", "")

    title = row.get("title", f"{client_name} Performance Report")
    subject = payload.subject or title

    from services.email_service import build_report_email_html, send_report_email  # noqa: PLC0415
    html_body = build_report_email_html(
        client_name=client_name,
        period_start=str(row.get("period_start", "")),
        period_end=str(row.get("period_end", "")),
        report_title=title,
        executive_summary=exec_summary,
        agency_name=agency_name,
        agency_email=agency_email,
        email_footer=email_footer,
    )

    try:
        resend_result = await send_report_email(
            to_emails=payload.to_emails,
            subject=subject,
            html_body=html_body,
            sender_name=sender_name,
            reply_to=reply_to,
            pptx_path=pptx_path_resolved if send_pptx else None,
            pdf_path=pdf_path_resolved  if send_pdf  else None,
        )
    except Exception as exc:
        logger.error("Email send failed for report %s: %s", report_id, exc)
        # Log failed delivery
        supabase.table("report_deliveries").insert({
            "report_id":       report_id,
            "user_id":         user_id,
            "delivery_method": "email",
            "recipient_emails": payload.to_emails,
            "status":          "failed",
            "error_message":   str(exc),
            "email_subject":   subject,
        }).execute()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email delivery failed: {exc}",
        )

    # Log successful delivery and update report status to "sent"
    supabase.table("report_deliveries").insert({
        "report_id":        report_id,
        "user_id":          user_id,
        "delivery_method":  "email",
        "recipient_emails": payload.to_emails,
        "status":           "sent",
        "resend_id":        resend_result.get("id"),
        "email_subject":    subject,
        "attachment_type":  payload.attachment,
        "sent_at":          datetime.utcnow().isoformat(),
    }).execute()

    supabase.table("reports").update({"status": "sent"}).eq("id", report_id).execute()

    logger.info(
        "Report %s sent to %s (Resend ID: %s)",
        report_id, payload.to_emails, resend_result.get("id"),
    )
    return {
        "success":   True,
        "resend_id": resend_result.get("id"),
        "to":        payload.to_emails,
        "subject":   subject,
    }


# ---------------------------------------------------------------------------
# POST /{report_id}/regenerate  — re-run full pipeline, reuse same report ID
# ---------------------------------------------------------------------------

@router.post("/{report_id}/regenerate", response_model=ReportResponse)
@limiter.limit("10/hour")
async def regenerate_report(
    request: Request,
    report_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ReportResponse:
    """
    Re-run the full report generation pipeline for an existing report.
    Reuses the same report ID — fetches client_id, period_start, period_end,
    template, and visual_template from the existing record, then overwrites
    the DB row with fresh files and narrative.

    Use case: report files were lost after a container redeployment and the
    user clicks "Regenerate Report" in the frontend.
    """
    supabase = get_supabase_admin()

    # Fetch existing report
    existing = (
        supabase.table("reports")
        .select("*")
        .eq("id", report_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    row = existing.data
    client_id    = row["client_id"]
    period_start = str(row["period_start"])
    period_end   = str(row["period_end"])

    # Recover template settings from the sections JSONB if available
    sections_json = row.get("sections") or {}
    # The visual_template and template are not stored separately in the DB,
    # so we use sensible defaults; the user can always generate a new report
    # with different settings if needed.

    # ── Run the same pipeline as generate, but with a FIXED report_id ──
    # 1 — Verify client ownership
    client_result = (
        supabase.table("clients")
        .select("*")
        .eq("id", client_id)
        .eq("user_id", user_id)
        .eq("is_active", True)
        .single()
        .execute()
    )
    if not client_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found or deleted")
    client = client_result.data

    report_config: dict = client.get("report_config") or {}
    cfg_sections  = report_config.get("sections", {})
    cfg_template  = report_config.get("template", "full")
    cfg_custom    = {
        "title": report_config.get("custom_section_title", ""),
        "text":  report_config.get("custom_section_text",  ""),
    }

    # 2 — Data pull — real connections only, no mock data

    ga4_conn_result = (
        supabase.table("connections")
        .select("id,account_id,access_token_encrypted,refresh_token_encrypted,token_expires_at")
        .eq("client_id", client_id)
        .eq("platform", "ga4")
        .eq("status", "active")
        .limit(1)
        .execute()
    )

    ga4_data = None
    if ga4_conn_result.data:
        ga4_conn = ga4_conn_result.data[0]
        try:
            from services.google_analytics import pull_ga4_data  # noqa: PLC0415
            raw_exp = ga4_conn.get("token_expires_at")
            token_expires_ts: float | None = None
            if raw_exp:
                try:
                    from datetime import timezone as _tz  # noqa: PLC0415
                    dt = datetime.fromisoformat(str(raw_exp).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=_tz.utc)
                    token_expires_ts = dt.timestamp()
                except Exception:
                    pass
            ga4_data = await pull_ga4_data(
                access_token_encrypted=ga4_conn["access_token_encrypted"],
                refresh_token_encrypted=ga4_conn["refresh_token_encrypted"],
                token_expires_at=token_expires_ts,
                property_id=ga4_conn["account_id"],
                period_start=period_start,
                period_end=period_end,
                connection_id=ga4_conn["id"],
                supabase=supabase,
            )
        except Exception:
            logger.exception("GA4 pull failed during regenerate for client %s", client_id)

        # Persist snapshot for multi-period trend analysis (non-fatal).
        if ga4_data is not None:
            from services.snapshot_saver import save_snapshot  # noqa: PLC0415
            save_snapshot(
                supabase,
                connection_id=ga4_conn["id"],
                client_id=client_id,
                platform="ga4",
                period_start=period_start,
                period_end=period_end,
                metrics=ga4_data,
            )

    meta_conn_result = (
        supabase.table("connections")
        .select("id,account_id,currency,access_token_encrypted,refresh_token_encrypted,token_expires_at")
        .eq("client_id", client_id)
        .eq("platform", "meta_ads")
        .eq("status", "active")
        .limit(1)
        .execute()
    )

    meta_data = None
    meta_currency = "USD"
    if meta_conn_result.data:
        meta_conn = meta_conn_result.data[0]
        meta_currency = meta_conn.get("currency", "USD") or "USD"
        try:
            from services.meta_ads import pull_meta_ads_data  # noqa: PLC0415
            meta_data = await pull_meta_ads_data(
                account_id=meta_conn["account_id"],
                access_token_encrypted=meta_conn["access_token_encrypted"],
                period_start=period_start,
                period_end=period_end,
                connection_id=meta_conn["id"],
                currency=meta_currency,
            )
        except Exception:
            logger.exception("Meta Ads pull failed during regenerate for client %s", client_id)

        # Persist snapshot for multi-period trend analysis (non-fatal).
        if meta_data is not None:
            from services.snapshot_saver import save_snapshot  # noqa: PLC0415
            save_snapshot(
                supabase,
                connection_id=meta_conn["id"],
                client_id=client_id,
                platform="meta_ads",
                period_start=period_start,
                period_end=period_end,
                metrics=meta_data,
            )

    raw_data: dict = {
        "client_name": client["name"],
        "period_start": period_start,
        "period_end": period_end,
    }
    if ga4_data is not None:
        raw_data["ga4"] = ga4_data
    if meta_data is not None:
        raw_data["meta_ads"] = meta_data
        raw_data["meta_ads"]["currency"] = meta_currency

    has_data = ga4_data is not None or meta_data is not None
    if not has_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No data sources connected. Connect at least one platform to regenerate.",
        )

    # 3 — AI narrative
    from services.ai_narrative import generate_narrative  # noqa: PLC0415
    narrative = await generate_narrative(
        data=_sanitize_data_for_ai(raw_data),
        client_name=client["name"],
        client_goals=client.get("goals_context"),
        tone=client.get("ai_tone", "professional"),
        template=cfg_template,
        language=client.get("report_language", "en") or "en",
    )

    # 4 — Branding
    profile_result = (
        supabase.table("profiles")
        .select("agency_name,agency_logo_url,brand_color,sender_name,agency_email")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    _profile = profile_result.data or {}
    branding = {
        "agency_name":     (_profile.get("agency_name") or "").strip() or "Your Agency",
        "agency_logo_url": _profile.get("agency_logo_url") or "",
        "brand_color":     _profile.get("brand_color") or "#4338CA",
        "client_logo_url": client.get("logo_url") or "",
    }

    # 5 — Charts
    charts_dir = os.path.join(REPORTS_BASE_DIR, report_id, "charts")
    _chart_insights = (narrative or {}).get("chart_insights") or {}
    _report_language2 = client.get("report_language", "en") or "en"
    from services.chart_generator import generate_all_charts  # noqa: PLC0415
    charts = await asyncio.to_thread(
        generate_all_charts, raw_data, charts_dir, branding["brand_color"], "modern_clean",
        _chart_insights, _report_language2,
    )

    client_info = {"name": client["name"], "agency_name": branding["agency_name"]}

    # 6 — PPTX + PDF
    from services.report_generator import generate_pdf_report, generate_pptx_report  # noqa: PLC0415
    pptx_bytes, pdf_bytes = await asyncio.gather(
        asyncio.to_thread(
            generate_pptx_report, raw_data, narrative, charts, client_info,
            cfg_sections if cfg_sections else None,
            cfg_template,
            cfg_custom if cfg_custom.get("title") else None,
            branding, "modern_clean",
            _report_language2,
        ),
        asyncio.to_thread(
            generate_pdf_report, raw_data, narrative, charts, client_info,
            cfg_sections if cfg_sections else None,
            cfg_template,
            cfg_custom if cfg_custom.get("title") else None,
            branding, "modern_clean",
            _report_language2,
        ),
    )

    # Save to disk
    report_dir = os.path.join(REPORTS_BASE_DIR, report_id)
    os.makedirs(report_dir, exist_ok=True)

    pptx_path = os.path.join(report_dir, "report.pptx")
    pdf_path  = os.path.join(report_dir, "report.pdf")

    with open(pptx_path, "wb") as f:
        f.write(pptx_bytes)

    # Subscription check for regenerated reports
    regen_sub = get_user_subscription(user_id)
    if regen_sub.get("status") in ("expired", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your subscription has expired. Please upgrade to continue generating reports.",
        )

    if pdf_bytes is not None:
        if not os.path.exists(pdf_path):
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
        db_pdf_path: str | None = pdf_path
    else:
        db_pdf_path = None

    # Build data_summary
    ga4_s  = raw_data.get("ga4", {}).get("summary", {})
    meta_s = raw_data.get("meta_ads", {}).get("summary", {})
    data_summary = {
        "sessions":            ga4_s.get("sessions"),
        "sessions_change":     ga4_s.get("sessions_change"),
        "users":               ga4_s.get("users"),
        "users_change":        ga4_s.get("users_change"),
        "conversions":         ga4_s.get("conversions"),
        "conversions_change":  ga4_s.get("conversions_change"),
        "pageviews":           ga4_s.get("pageviews"),
        "bounce_rate":         ga4_s.get("bounce_rate"),
        "avg_session_duration": ga4_s.get("avg_session_duration"),
        "spend":               meta_s.get("spend"),
        "spend_change":        meta_s.get("spend_change"),
        "impressions":         meta_s.get("impressions"),
        "clicks":              meta_s.get("clicks"),
        "ctr":                 meta_s.get("ctr"),
        "cpc":                 meta_s.get("cpc"),
        "roas":                meta_s.get("roas"),
        "cost_per_conversion": meta_s.get("cost_per_conversion"),
    }

    # Update existing report record (not insert)
    update_payload = {
        "pptx_file_url": pptx_path,
        "pdf_file_url":  db_pdf_path,
        "ai_narrative":  narrative,
        "user_edits":    None,   # clear stale edits
        "status":        "draft",
        "sections": {
            "data_summary":   data_summary,
            "meta_currency":  meta_currency,
            "ai_model":       "gpt-4.1",
            "narrative_data": {
                "ga4": {k: v for k, v in raw_data.get("ga4", {}).items() if k != "daily"},
                "meta_ads": {k: v for k, v in raw_data.get("meta_ads", {}).items() if k != "daily"},
                "period_start": raw_data.get("period_start"),
                "period_end":   raw_data.get("period_end"),
            },
        },
        "updated_at": datetime.utcnow().isoformat(),
    }
    result = (
        supabase.table("reports")
        .update(update_payload)
        .eq("id", report_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report regenerated but failed to update database",
        )

    client_name = client["name"]
    logger.info("Report %s regenerated for client %s", report_id, client_id)
    return ReportResponse(**_map_db_row(result.data[0], client_name=client_name))
