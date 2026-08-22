"""
Saved mappings — the reason next month's upload is one click.

A confirmed mapping is stored with a fingerprint of the file's header row. When
a file with the same headers arrives again we replay the saved mapping and skip
the LLM entirely: no cost, no waiting, no re-confirming.

The five original KPI templates (linkedin_ads, tiktok_ads, mailchimp, shopify,
generic) are represented here as *system mappings*, not as a separate parsing
path. They keep working exactly as before, because a file matching their column
layout matches their fingerprint.
"""
from __future__ import annotations

import logging
from typing import Any

from services.csv_ingest.schema import ColumnMapping, MappingProposal

logger = logging.getLogger(__name__)

TABLE = "csv_mappings"


# ---------------------------------------------------------------------------
# System mappings — the legacy 4-column KPI layout
# ---------------------------------------------------------------------------

def _kpi_columns() -> list[ColumnMapping]:
    """
    The legacy layout: metric_name | current_value | previous_value | unit.

    Confidence is 1.0 because this is a layout we defined ourselves, not a guess.
    """
    return [
        ColumnMapping(
            source_column="current_value",
            target_metric="current_value",
            label="Current",
            unit="number",
            confidence=1.0,
            reasoning="GoReportPilot KPI template column",
        ),
        ColumnMapping(
            source_column="previous_value",
            target_metric="previous_value",
            label="Previous",
            unit="number",
            confidence=1.0,
            reasoning="GoReportPilot KPI template column",
        ),
    ]


SYSTEM_MAPPINGS: dict[str, dict[str, Any]] = {
    "linkedin_ads": {
        "label": "LinkedIn Ads",
        "description": "LinkedIn Campaign Manager export — impressions, clicks, spend, leads",
    },
    "tiktok_ads": {
        "label": "TikTok Ads",
        "description": "TikTok Ads Manager export — views, clicks, spend, conversions",
    },
    "mailchimp": {
        "label": "Mailchimp",
        "description": "Mailchimp campaign report — sends, opens, clicks, unsubscribes",
    },
    "shopify": {
        "label": "Shopify",
        "description": "Shopify analytics export — sessions, orders, revenue, conversion rate",
    },
    "generic": {
        "label": "Custom KPIs",
        "description": "Generic KPI template — name, value, previous_value, unit columns",
    },
}


def system_mapping(slug: str) -> MappingProposal | None:
    """Build the system mapping for one of the five bundled templates."""
    spec = SYSTEM_MAPPINGS.get(slug)
    if not spec:
        return None
    return MappingProposal(
        table_shape="long_kpi",
        source_label=spec["label"],
        columns=_kpi_columns(),
        origin="system_template",
        column_fingerprint=LEGACY_KPI_FINGERPRINT,
    )


def _fingerprint_of(headers: list[str]) -> str:
    """Same algorithm as TableProfile.column_fingerprint, for seeding."""
    import hashlib
    import re

    normalised = sorted(re.sub(r"[^a-z0-9]+", "", h.lower()) for h in headers)
    return hashlib.sha256("|".join(normalised).encode("utf-8")).hexdigest()[:32]


LEGACY_KPI_FINGERPRINT = _fingerprint_of(
    ["metric_name", "current_value", "previous_value", "unit"]
)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def find_by_fingerprint(
    supabase: Any, *, user_id: str, client_id: str, fingerprint: str
) -> dict[str, Any] | None:
    """
    Look for a saved mapping matching this file's headers.

    Client-scoped first, then user-scoped — an agency that maps a LinkedIn
    export once should not have to map it again for their next client.
    """
    try:
        result = (
            supabase.table(TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("column_fingerprint", fingerprint)
            .order("client_id", desc=False)
            .execute()
        )
    except Exception:  # noqa: BLE001 — a missing mapping must never block an upload
        logger.exception("csv_mappings lookup failed")
        return None

    rows = result.data or []
    if not rows:
        return None
    for row in rows:
        if row.get("client_id") == client_id:
            return row
    return rows[0]


def load_proposal(row: dict[str, Any]) -> MappingProposal | None:
    """Rehydrate a stored mapping. A corrupt row degrades to a fresh AI mapping."""
    try:
        proposal = MappingProposal.model_validate(row.get("mapping") or {})
    except Exception:  # noqa: BLE001
        logger.exception("Stored csv_mapping %s is unreadable", row.get("id"))
        return None
    proposal.origin = "system_template" if row.get("is_system") else "saved_template"
    proposal.column_fingerprint = row.get("column_fingerprint") or proposal.column_fingerprint
    return proposal


def save(
    supabase: Any,
    *,
    user_id: str,
    client_id: str,
    name: str,
    fingerprint: str,
    proposal: MappingProposal,
) -> dict[str, Any] | None:
    """
    Store a confirmed mapping, replacing any earlier one with the same
    fingerprint for this client.
    """
    payload = {
        "user_id":            user_id,
        "client_id":          client_id,
        "name":               name[:120],
        "column_fingerprint": fingerprint,
        "mapping":            proposal.model_dump(mode="json"),
        "is_system":          False,
    }
    try:
        return (
            supabase.table(TABLE)
            .upsert(payload, on_conflict="client_id,column_fingerprint")
            .execute()
        ).data
    except Exception:  # noqa: BLE001 — failing to save must not fail the upload
        logger.exception("Could not save csv_mapping for client %s", client_id)
        return None


def list_for_client(supabase: Any, *, user_id: str, client_id: str) -> list[dict[str, Any]]:
    try:
        result = (
            supabase.table(TABLE)
            .select("id,name,column_fingerprint,is_system,created_at,updated_at")
            .eq("user_id", user_id)
            .eq("client_id", client_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:  # noqa: BLE001
        logger.exception("csv_mappings list failed for client %s", client_id)
        return []


def delete(supabase: Any, *, user_id: str, mapping_id: str) -> bool:
    try:
        result = (
            supabase.table(TABLE)
            .delete()
            .eq("id", mapping_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(result.data)
    except Exception:  # noqa: BLE001
        logger.exception("csv_mappings delete failed for %s", mapping_id)
        return False
