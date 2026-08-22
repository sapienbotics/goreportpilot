"""
Universal CSV/XLSX ingestion endpoints.

    POST   /api/connections/csv/analyze          upload -> profile + proposed mapping
    POST   /api/connections/csv/commit           confirmed mapping -> report data
    GET    /api/connections/csv/mappings         saved mappings for a client
    DELETE /api/connections/csv/mappings/{id}    forget a saved mapping

The legacy endpoints in routers/csv_upload.py are untouched and keep working;
this router is additive.

Two-step by design. ``analyze`` never writes anything and never commits a
reading of the data — it proposes. ``commit`` applies a mapping the user has
seen and confirmed. A low-confidence guess can therefore never reach a client
report without a human looking at it first.
"""
#
# NOTE: deliberately no "from __future__ import annotations" in this module.
# Under PEP 563 every annotation becomes a string, and FastAPI resolves route
# return annotations to infer a response model. "-> None" on the 204 route then
# reads as a response body, which trips
#     AssertionError: Status code 204 must not have a response body
# at import time — taking the whole app down at startup rather than failing at
# request time. routers/connections.py uses the same "-> None" pattern safely
# precisely because it does not have the future import.
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from middleware.auth import get_current_user_id
from services.csv_ingest import (
    CONFIDENCE_THRESHOLD,
    IngestError,
    MAX_FILE_BYTES,
    MappingProposal,
    NormalizationError,
    normalize,
    preview_rows,
    profile_file,
    propose_mapping,
)
from services.csv_ingest import templates as mapping_store
from services.csv_ingest.profiler import TableProfile
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter()

# Per-user daily cap on AI mapping calls. Replaying a saved mapping does not
# count — only genuinely new export formats do, so a normal month of uploads
# never approaches this.
DAILY_MAPPING_LIMIT = 25

# Profiles are held in memory between analyze and commit rather than re-uploaded.
# Short-lived: the user confirms a mapping within a minute or two.
_PROFILE_TTL = timedelta(minutes=30)
_MAX_CACHED_PROFILES = 200
_profile_cache: dict[str, tuple[datetime, str, TableProfile, str]] = {}


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class AnalyzeResponse(BaseModel):
    analysis_id: str
    filename: str
    sheets: list[str]
    active_sheet: str
    row_count: int
    columns: list[dict]
    mapping: dict
    preview: list[dict]
    requires_confirmation: bool
    confidence_threshold: float = CONFIDENCE_THRESHOLD
    warnings: list[str] = Field(default_factory=list)
    saved_mapping_name: str | None = None


class CommitRequest(BaseModel):
    analysis_id: str
    client_id: str
    mapping: dict
    source_name: str = ""
    save_as: str = Field(
        default="",
        description="Name to store this mapping under for one-click reuse. Empty = do not save.",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prune_cache() -> None:
    now = datetime.now(timezone.utc)
    expired = [k for k, (ts, *_rest) in _profile_cache.items() if now - ts > _PROFILE_TTL]
    for key in expired:
        _profile_cache.pop(key, None)
    # Hard ceiling so a burst of uploads cannot grow the process unbounded.
    while len(_profile_cache) > _MAX_CACHED_PROFILES:
        oldest = min(_profile_cache, key=lambda k: _profile_cache[k][0])
        _profile_cache.pop(oldest, None)


def _cache_profile(user_id: str, filename: str, profile: TableProfile) -> str:
    import uuid

    _prune_cache()
    analysis_id = str(uuid.uuid4())
    _profile_cache[analysis_id] = (
        datetime.now(timezone.utc), user_id, profile, filename,
    )
    return analysis_id


def _get_cached_profile(analysis_id: str, user_id: str) -> tuple[TableProfile, str]:
    entry = _profile_cache.get(analysis_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                "That upload has expired. Upload the file again — it only takes "
                "a moment, and your saved mappings still apply."
            ),
        )
    stamped_at, owner, profile, filename = entry
    if owner != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found.")
    if datetime.now(timezone.utc) - stamped_at > _PROFILE_TTL:
        _profile_cache.pop(analysis_id, None)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="That upload has expired. Please upload the file again.",
        )
    return profile, filename


def _verify_client(supabase, client_id: str, user_id: str) -> dict:
    result = (
        supabase.table("clients")
        .select("id,name")
        .eq("id", client_id)
        .eq("user_id", user_id)
        .eq("is_active", True)
        .maybe_single()
        .execute()
    )
    data = result.data if result else None
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    return data


def _check_mapping_quota(supabase, user_id: str) -> None:
    """Enforce the per-user daily AI-mapping cap with an explanatory message."""
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    try:
        result = (
            supabase.table("csv_mapping_usage")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", since)
            .execute()
        )
        used = result.count or 0
    except Exception:  # noqa: BLE001 — never block an upload on a metering failure
        logger.exception("Could not read csv_mapping_usage for user %s", user_id)
        return

    if used >= DAILY_MAPPING_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"You've used all {DAILY_MAPPING_LIMIT} automatic column mappings "
                "for today. Uploads that match a mapping you've already saved "
                "still work normally — this limit only applies to file layouts "
                "we haven't seen before. It resets 24 hours after your first "
                "mapping today."
            ),
        )


def _record_mapping_use(supabase, user_id: str, fingerprint: str) -> None:
    try:
        supabase.table("csv_mapping_usage").insert({
            "user_id": user_id,
            "column_fingerprint": fingerprint,
        }).execute()
    except Exception:  # noqa: BLE001
        logger.exception("Could not record csv mapping usage for user %s", user_id)


# ---------------------------------------------------------------------------
# POST /csv/analyze
# ---------------------------------------------------------------------------

@router.post("/csv/analyze", response_model=AnalyzeResponse)
async def analyze_csv(
    file: UploadFile = File(...),
    client_id: str = Form(...),
    sheet: str = Form(""),
    user_id: str = Depends(get_current_user_id),
) -> AnalyzeResponse:
    """
    Profile an uploaded file and propose a column mapping.

    Writes nothing. If a saved mapping matches the file's headers it is replayed
    and no AI call is made at all — that is the one-click path for a recurring
    monthly export.
    """
    filename = file.filename or "upload.csv"
    content = await file.read()

    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"That file is {len(content) / 1024 / 1024:.1f} MB. The limit is "
                f"{MAX_FILE_BYTES // 1024 // 1024} MB — try a shorter date range."
            ),
        )

    supabase = get_supabase_admin()
    client = _verify_client(supabase, client_id, user_id)

    try:
        profiles = profile_file(content, filename)
    except IngestError as exc:
        # IngestError messages are written for users and say what to do next.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    sheet_names = [p.sheet_name for p in profiles]
    profile = next((p for p in profiles if p.sheet_name == sheet), profiles[0])

    # 1 — A mapping we already know beats an AI call.
    saved_row = mapping_store.find_by_fingerprint(
        supabase, user_id=user_id, client_id=client_id,
        fingerprint=profile.column_fingerprint,
    )
    proposal: MappingProposal | None = None
    saved_name: str | None = None
    if saved_row:
        proposal = mapping_store.load_proposal(saved_row)
        saved_name = saved_row.get("name")

    # 2 — Otherwise ask the model.
    if proposal is None:
        _check_mapping_quota(supabase, user_id)
        proposal = await propose_mapping(
            profile, filename, source_label_hint=client.get("name", "")
        )
        _record_mapping_use(supabase, user_id, profile.column_fingerprint)

    analysis_id = _cache_profile(user_id, filename, profile)

    warnings = list(profile.warnings) + [
        w for w in proposal.warnings if w not in profile.warnings
    ]
    if len(profiles) > 1:
        warnings.append(
            f"This workbook has {len(profiles)} sheets. Showing '{profile.sheet_name}' "
            "— switch sheets above if that's the wrong one."
        )

    return AnalyzeResponse(
        analysis_id=analysis_id,
        filename=filename,
        sheets=sheet_names,
        active_sheet=profile.sheet_name,
        row_count=profile.data_row_count,
        columns=[c.for_prompt() for c in profile.columns],
        mapping=proposal.model_dump(mode="json"),
        preview=preview_rows(profile, proposal),
        requires_confirmation=proposal.requires_user_input,
        warnings=warnings,
        saved_mapping_name=saved_name,
    )


# ---------------------------------------------------------------------------
# POST /csv/commit
# ---------------------------------------------------------------------------

@router.post("/csv/commit")
async def commit_csv(
    body: CommitRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Apply a user-confirmed mapping and return report-pipeline data.

    The returned ``source`` object is what the report generation request carries
    in ``csv_sources``. Optionally saves the mapping for one-click reuse.
    """
    supabase = get_supabase_admin()
    _verify_client(supabase, body.client_id, user_id)
    profile, filename = _get_cached_profile(body.analysis_id, user_id)

    try:
        proposal = MappingProposal.model_validate(body.mapping)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"That mapping could not be read: {exc}",
        ) from exc

    # The confirm button is disabled client-side when anything is unresolved;
    # this is the server-side half of the same rule, because a low-confidence
    # mapping must never be accepted without a human having seen it.
    unconfirmed = [c.source_column for c in proposal.columns if c.needs_confirmation]
    if unconfirmed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "These columns still need confirming before we can use them: "
                + ", ".join(unconfirmed)
                + ". Set the right metric for each, or remove them."
            ),
        )

    try:
        source = normalize(
            profile,
            proposal,
            source_name=body.source_name or proposal.source_label or filename,
        )
    except NormalizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    saved = None
    if body.save_as.strip():
        saved = mapping_store.save(
            supabase,
            user_id=user_id,
            client_id=body.client_id,
            name=body.save_as.strip(),
            fingerprint=profile.column_fingerprint,
            proposal=proposal,
        )

    logger.info(
        "CSV committed for client %s — source=%r metrics=%d dated=%s saved=%s",
        body.client_id, source["source_name"], len(source["metrics"]),
        "daily" in source, bool(saved),
    )

    return {
        "source": source,
        "saved_mapping": bool(saved),
        "column_fingerprint": profile.column_fingerprint,
    }


# ---------------------------------------------------------------------------
# Saved mappings
# ---------------------------------------------------------------------------

@router.get("/csv/mappings")
async def list_mappings(
    client_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    supabase = get_supabase_admin()
    _verify_client(supabase, client_id, user_id)
    return {
        "mappings": mapping_store.list_for_client(
            supabase, user_id=user_id, client_id=client_id
        )
    }


@router.delete("/csv/mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    mapping_id: str,
    user_id: str = Depends(get_current_user_id),
) -> None:
    supabase = get_supabase_admin()
    if not mapping_store.delete(supabase, user_id=user_id, mapping_id=mapping_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found."
        )
