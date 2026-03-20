"""
Report generation and management endpoints.
Trigger report generation, list reports, get report details, download files.
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from middleware.auth import get_current_user_id
from models.schemas import (
    ReportGenerateRequest,
    ReportListItem,
    ReportListResponse,
    ReportResponse,
)
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter()


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
        "id":           row["id"],
        "user_id":      row["user_id"],
        "client_id":    row["client_id"],
        "client_name":  client_name,
        "title":        row["title"],
        "status":       row["status"],
        "period_start": str(row["period_start"]),
        "period_end":   str(row["period_end"]),
        "narrative":    row.get("ai_narrative"),
        "data_summary": sections.get("data_summary") if isinstance(sections, dict) else None,
        "pptx_url":     row.get("pptx_file_url"),
        "pdf_url":      row.get("pdf_file_url"),
        "created_at":   row["created_at"],
        "updated_at":   row["updated_at"],
    }

# Local storage directory — lives inside backend/generated_reports/
# Gitignored; move to Supabase Storage in a later phase.
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
REPORTS_BASE_DIR = os.path.join(_HERE, "generated_reports")


# ---------------------------------------------------------------------------
# POST /generate
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    request: ReportGenerateRequest,
    user_id: str = Depends(get_current_user_id),
) -> ReportResponse:
    """
    Full report generation pipeline:
    1. Fetch client  2. Mock data  3. AI narrative  4. Charts
    5. PPTX + PDF    6. Save to disk  7. Store in Supabase
    """
    supabase = get_supabase_admin()

    # 1 — Verify client ownership
    client_result = (
        supabase.table("clients")
        .select("*")
        .eq("id", request.client_id)
        .eq("user_id", user_id)
        .eq("is_active", True)
        .single()
        .execute()
    )
    if not client_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    client = client_result.data

    # 2 — Prefer real GA4 data; fall back to mock data
    from services.mock_data import generate_all_mock_data  # noqa: PLC0415

    # Check for an active GA4 connection for this client
    ga4_conn_result = (
        supabase.table("connections")
        .select("id,account_id,encrypted_tokens")
        .eq("client_id", request.client_id)
        .eq("platform", "google_analytics")
        .eq("status", "active")
        .limit(1)
        .execute()
    )

    ga4_data = None
    if ga4_conn_result.data:
        ga4_conn = ga4_conn_result.data[0]
        try:
            from services.google_analytics import pull_ga4_data  # noqa: PLC0415
            ga4_data = await pull_ga4_data(
                encrypted_tokens=ga4_conn["encrypted_tokens"],
                property_id=ga4_conn["account_id"],
                period_start=request.period_start,
                period_end=request.period_end,
                connection_id=ga4_conn["id"],
                supabase=supabase,
            )
            logger.info("Using real GA4 data for client %s", request.client_id)
        except Exception:
            logger.exception(
                "Real GA4 pull failed for client %s — falling back to mock data",
                request.client_id,
            )
            ga4_data = None

    # Build the combined raw_data dict
    mock_all = generate_all_mock_data(client["name"], request.period_start, request.period_end)
    if ga4_data is not None:
        mock_all["ga4"] = ga4_data   # replace only the GA4 section with real data
    raw_data = mock_all

    # 3 — AI narrative (async I/O)
    from services.ai_narrative import generate_narrative  # noqa: PLC0415
    narrative = await generate_narrative(
        data=raw_data,
        client_name=client["name"],
        client_goals=client.get("goals_context"),
        tone=client.get("ai_tone", "professional"),
    )

    # 4 — Generate charts (sync, run in thread pool)
    report_id = str(uuid.uuid4())
    charts_dir = os.path.join(REPORTS_BASE_DIR, report_id, "charts")

    from services.chart_generator import generate_all_charts  # noqa: PLC0415
    charts = await asyncio.to_thread(generate_all_charts, raw_data, charts_dir)

    # 5 — Build report files (sync, run in thread pool)
    client_info = {
        "name": client["name"],
        "agency_name": "Your Agency",  # White-label customisation in a future phase
    }

    from services.report_generator import generate_pdf_report, generate_pptx_report  # noqa: PLC0415
    pptx_bytes, pdf_bytes = await asyncio.gather(
        asyncio.to_thread(generate_pptx_report, raw_data, narrative, charts, client_info),
        asyncio.to_thread(generate_pdf_report,  raw_data, narrative, charts, client_info),
    )

    # 6 — Save to disk
    report_dir = os.path.join(REPORTS_BASE_DIR, report_id)
    os.makedirs(report_dir, exist_ok=True)

    pptx_path = os.path.join(report_dir, "report.pptx")
    pdf_path  = os.path.join(report_dir, "report.pdf")

    with open(pptx_path, "wb") as f:
        f.write(pptx_bytes)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

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

    # 8 — Human-readable title
    try:
        month_year = datetime.strptime(request.period_start, "%Y-%m-%d").strftime("%B %Y")
    except ValueError:
        month_year = request.period_start
    title = f"{client['name']} — {month_year} Performance Report"

    # 9 — Persist report record in Supabase (use actual DB column names)
    insert_payload = {
        "id":            report_id,
        "user_id":       user_id,
        "client_id":     request.client_id,
        "title":         title,
        "status":        "draft",           # CHECK: generating|draft|approved|sent|failed
        "period_start":  request.period_start,
        "period_end":    request.period_end,
        "pptx_file_url": pptx_path,         # actual DB column name
        "pdf_file_url":  pdf_path,          # actual DB column name
        "ai_narrative":  narrative,         # actual DB column name
        "sections":      {"data_summary": data_summary},  # no data_summary column — store in sections JSONB
    }
    result = supabase.table("reports").insert(insert_payload).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report generated but failed to save to database",
        )

    return ReportResponse(**_map_db_row(result.data[0], client_name=client["name"]))


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PPTX file not found on server")

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF file not found on server")

    safe_title = result.data.get("title", "report").replace(" — ", " - ").replace(" ", "_")[:80]
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{safe_title}.pdf")
