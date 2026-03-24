"""
CSV upload endpoints for custom data sources.

Endpoints:
    POST /api/connections/csv-upload         — Upload and parse a CSV file
    GET  /api/connections/csv-templates      — List available CSV templates
    GET  /api/connections/csv-templates/{name} — Download a CSV template
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import PlainTextResponse

from middleware.auth import get_current_user_id
from services.csv_parser import generate_template_csv, parse_kpi_csv
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter()

TEMPLATE_NAMES = ["linkedin_ads", "tiktok_ads", "mailchimp", "shopify", "generic"]
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB

_TEMPLATE_DESCRIPTIONS: dict[str, str] = {
    "linkedin_ads":  "LinkedIn Campaign Manager export — impressions, clicks, spend, leads",
    "tiktok_ads":    "TikTok Ads Manager export — views, clicks, spend, conversions",
    "mailchimp":     "Mailchimp campaign report — sends, opens, clicks, unsubscribes",
    "shopify":       "Shopify analytics export — sessions, orders, revenue, conversion rate",
    "generic":       "Generic KPI template — name, value, previous_value, unit columns",
}


# ---------------------------------------------------------------------------
# POST /csv-upload
# ---------------------------------------------------------------------------

@router.post("/csv-upload", status_code=status.HTTP_201_CREATED)
async def upload_csv(
    file: UploadFile = File(...),
    client_id: str = Form(...),
    source_name: str = Form(None),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Upload and parse a CSV file containing KPI data for a client.

    1. Validate file type and size.
    2. Parse the CSV with parse_kpi_csv().
    3. Create a connection record (platform = csv_<slug>).
    4. Save parsed data as a data_snapshot linked to that connection.
    """
    # --- Validate file extension ---
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only .csv files are accepted.",
        )

    # --- Read and size-check ---
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the 1 MB limit ({len(content):,} bytes received).",
        )

    supabase = get_supabase_admin()

    # --- Verify client ownership ---
    client_result = (
        supabase.table("clients")
        .select("id,name")
        .eq("id", client_id)
        .eq("user_id", user_id)
        .eq("is_active", True)
        .single()
        .execute()
    )
    if not client_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found.",
        )

    # --- Parse CSV ---
    try:
        csv_text = content.decode("utf-8-sig")  # strip BOM if present
        parsed = parse_kpi_csv(csv_text)
    except Exception as exc:
        logger.warning("CSV parse error for client %s: %s", client_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse CSV: {exc}",
        )

    metrics: list = parsed.get("metrics", [])
    resolved_source = source_name or parsed.get("source_name", filename.removesuffix(".csv"))

    # Build a URL-safe slug for display / account_id
    slug = resolved_source.lower().replace(" ", "_")
    slug = "".join(c if c.isalnum() or c == "_" else "_" for c in slug)

    # Map known template slugs to canonical platform names used in the DB.
    # All CSV sources are stored as csv_<slug> — see migration 009 which
    # widens the connections.platform CHECK constraint to allow csv_* values.
    _KNOWN_SLUGS: set[str] = {
        "linkedin_ads", "tiktok_ads", "mailchimp", "shopify", "generic",
    }
    # Normalise the slug to one of the known template slugs, or keep as-is
    # (will still be prefixed with csv_).
    canonical_slug = slug if slug in _KNOWN_SLUGS else slug[:50]  # guard length
    platform = f"csv_{canonical_slug}"

    # --- Create connection record ---
    connection_id = str(uuid.uuid4())

    conn_payload = {
        "id":           connection_id,
        "client_id":    client_id,
        "platform":     platform,
        "account_id":   resolved_source,
        "account_name": resolved_source,
        "status":       "active",
        # CSV connections carry no OAuth tokens
        "access_token_encrypted":  "",
        "refresh_token_encrypted": "",
        "consecutive_failures":    0,
    }

    conn_result = supabase.table("connections").insert(conn_payload).execute()
    if not conn_result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save connection record.",
        )

    # --- Create data_snapshot linked to the new connection ---
    # data_snapshots requires: connection_id, client_id, platform, period_start,
    # period_end, metrics (JSONB).  We use today as both start and end dates
    # since CSV uploads are point-in-time imports.
    today = datetime.now(timezone.utc).date().isoformat()

    snapshot_payload = {
        "connection_id": connection_id,
        "client_id":     client_id,
        "platform":      platform,
        "period_start":  today,
        "period_end":    today,
        "metrics": {
            "source_name": resolved_source,
            "kpi_rows":    metrics,
        },
    }

    snap_result = supabase.table("data_snapshots").insert(snapshot_payload).execute()
    if not snap_result.data:
        # Non-fatal: connection was saved; log and continue
        logger.error(
            "Connection %s created but data_snapshot insert failed for client %s",
            connection_id, client_id,
        )

    logger.info(
        "CSV uploaded for client %s — source=%s, metrics=%d",
        client_id, resolved_source, len(metrics),
    )

    return {
        "connection_id": connection_id,
        "source_name":   resolved_source,
        "metric_count":  len(metrics),
        "metrics":       metrics,
    }


# ---------------------------------------------------------------------------
# GET /csv-templates
# ---------------------------------------------------------------------------

@router.get("/csv-templates")
async def list_csv_templates(
    _user_id: str = Depends(get_current_user_id),
) -> dict:
    """Return the list of available CSV template names with descriptions."""
    templates = [
        {"name": name, "description": _TEMPLATE_DESCRIPTIONS.get(name, "")}
        for name in TEMPLATE_NAMES
    ]
    return {"templates": templates}


# ---------------------------------------------------------------------------
# GET /csv-templates/{name}
# ---------------------------------------------------------------------------

@router.get("/csv-templates/{name}")
async def download_csv_template(
    name: str,
    _user_id: str = Depends(get_current_user_id),
) -> PlainTextResponse:
    """
    Download a pre-built CSV template as a text/csv file.
    The template shows the expected column headers and one example row.
    """
    if name not in TEMPLATE_NAMES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{name}' not found. Available templates: {TEMPLATE_NAMES}",
        )

    try:
        csv_content = generate_template_csv(name)
    except Exception as exc:
        logger.error("Failed to generate template '%s': %s", name, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate template file.",
        )

    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{name}_template.csv"',
        },
    )
