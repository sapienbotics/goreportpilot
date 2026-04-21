"""
Phase 6 — Goals & Alerts CRUD router.
Mounted at /api/clients/{client_id}/goals (nested under clients) plus the
plain catalog endpoint /api/goals/metrics for the UI dropdown.

All endpoints require a valid Supabase JWT. RLS in PostgreSQL enforces
ownership; we additionally scope every query to user_id for defence
in depth, exactly as clients.py does.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from middleware.auth import get_current_user_id
from middleware.plan_enforcement import (
    can_create_goal,
    effective_goal_limit,
    get_user_subscription,
)
from models.schemas import GoalCreate, GoalUpdate, GoalResponse, GoalListResponse
from services.goal_checker import (
    METRIC_REGISTRY,
    evaluate_goal,
    evaluate_goals_for_client,
    list_metrics,
)
from services.plans import get_goal_limit
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET /api/goals/metrics — catalog for the UI
# ---------------------------------------------------------------------------

@router.get("/goals/metrics", response_model=list[dict])
async def list_goal_metrics(
    user_id: str = Depends(get_current_user_id),  # noqa: ARG001
) -> list[dict]:
    """Return the canonical metric catalog (platform, label, unit, direction)."""
    return list_metrics()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_client_owned(supabase, client_id: str, user_id: str) -> dict:
    """Return the client row if owned by user_id, else raise 404."""
    result = (
        supabase.table("clients")
        .select("id,name,is_active")
        .eq("id", client_id)
        .eq("user_id", user_id)
        .eq("is_active", True)
        .maybe_single()
        .execute()
    )
    data = result.data if result else None
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return data


def _row_to_response(row: dict, evaluation: dict | None = None) -> GoalResponse:
    """Merge a DB row + an optional live evaluation into a GoalResponse."""
    meta = METRIC_REGISTRY.get(row["metric"])
    payload = {
        "id":              row["id"],
        "client_id":       row["client_id"],
        "user_id":         row["user_id"],
        "metric":          row["metric"],
        "metric_label":    (meta or {}).get("label"),
        "comparison":      row.get("comparison", "gte"),
        "target_value":    float(row.get("target_value") or 0),
        "tolerance_pct":   float(row.get("tolerance_pct") or 5),
        "period":          row.get("period", "monthly"),
        "is_active":       bool(row.get("is_active", True)),
        "alert_emails":    row.get("alert_emails") or [],
        "last_evaluated_at": row.get("last_evaluated_at"),
        "created_at":      row["created_at"],
        "updated_at":      row["updated_at"],
    }
    if evaluation:
        payload["current_value"] = evaluation.get("actual")
        payload["status"]        = evaluation.get("status")
        payload["period_key"]    = evaluation.get("period_key")
    return GoalResponse(**payload)


# ---------------------------------------------------------------------------
# GET /api/clients/{client_id}/goals
# ---------------------------------------------------------------------------

@router.get("/clients/{client_id}/goals", response_model=GoalListResponse)
async def list_client_goals(
    client_id: str,
    user_id: str = Depends(get_current_user_id),
) -> GoalListResponse:
    """List all goals for a client, with live current_value + status per goal."""
    supabase = get_supabase_admin()
    _ensure_client_owned(supabase, client_id, user_id)

    result = (
        supabase.table("goals")
        .select("*")
        .eq("client_id", client_id)
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    rows = result.data or []

    # Batch-evaluate so the UI can render status without a second round-trip.
    evaluations = {e["goal_id"]: e for e in evaluate_goals_for_client(supabase, client_id)}
    goals = [_row_to_response(r, evaluations.get(r["id"])) for r in rows]

    sub      = get_user_subscription(user_id)
    plan     = sub.get("plan", "trial")
    is_trial = sub.get("status") == "trialing"
    limit    = effective_goal_limit(sub)

    return GoalListResponse(
        goals=goals,
        total=len(goals),
        limit=limit,
        plan=plan,
        is_trial=is_trial,
        # When on trial, expose what the limit will drop to post-trial so the
        # UI can render a heads-up banner like "Trial: 3 available, drops to
        # 1 after trial". When on a paid plan, plan_goal_limit == limit.
        plan_goal_limit=get_goal_limit(plan),
    )


# ---------------------------------------------------------------------------
# POST /api/clients/{client_id}/goals
# ---------------------------------------------------------------------------

@router.post("/clients/{client_id}/goals", response_model=GoalResponse,
             status_code=status.HTTP_201_CREATED)
async def create_goal(
    client_id: str,
    payload: GoalCreate,
    user_id: str = Depends(get_current_user_id),
) -> GoalResponse:
    """Create a goal. Enforces per-client plan limit (Starter=1, Pro=3, Agency=unlimited)."""
    if payload.metric not in METRIC_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown metric '{payload.metric}'. See GET /api/goals/metrics.",
        )

    supabase = get_supabase_admin()
    _ensure_client_owned(supabase, client_id, user_id)

    allowed, msg = can_create_goal(user_id, client_id)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)

    data = {
        "client_id":     client_id,
        "user_id":       user_id,
        "metric":        payload.metric,
        "comparison":    payload.comparison,
        "target_value":  payload.target_value,
        "tolerance_pct": payload.tolerance_pct,
        "period":        payload.period,
        "is_active":     payload.is_active,
        "alert_emails":  payload.alert_emails or [],
    }

    result = supabase.table("goals").insert(data).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create goal",
        )
    row = result.data[0]

    # Evaluate once on creation so the UI shows status immediately.
    evaluation = evaluate_goal(supabase, row)
    return _row_to_response(row, evaluation)


# ---------------------------------------------------------------------------
# PATCH /api/clients/{client_id}/goals/{goal_id}
# ---------------------------------------------------------------------------

@router.patch("/clients/{client_id}/goals/{goal_id}", response_model=GoalResponse)
async def update_goal(
    client_id: str,
    goal_id: str,
    payload: GoalUpdate,
    user_id: str = Depends(get_current_user_id),
) -> GoalResponse:
    """Partial update. Metric changes reset alerts_sent so a retargeted
    goal can re-alert for the current period."""
    supabase = get_supabase_admin()
    _ensure_client_owned(supabase, client_id, user_id)

    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided to update",
        )

    if "metric" in updates and updates["metric"] not in METRIC_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown metric '{updates['metric']}'",
        )

    # Reset idempotency on target/metric/comparison/period change — the old
    # alert state no longer applies.
    if any(k in updates for k in ("metric", "comparison", "target_value", "period")):
        updates["alerts_sent"] = {}

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = (
        supabase.table("goals")
        .update(updates)
        .eq("id", goal_id)
        .eq("client_id", client_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    row = result.data[0]
    evaluation = evaluate_goal(supabase, row)
    return _row_to_response(row, evaluation)


# ---------------------------------------------------------------------------
# DELETE /api/clients/{client_id}/goals/{goal_id}
# ---------------------------------------------------------------------------

@router.delete("/clients/{client_id}/goals/{goal_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    client_id: str,
    goal_id: str,
    user_id: str = Depends(get_current_user_id),
) -> None:
    """Hard-delete a goal (goals are cheap to recreate — no soft-delete needed)."""
    supabase = get_supabase_admin()
    _ensure_client_owned(supabase, client_id, user_id)

    result = (
        supabase.table("goals")
        .delete()
        .eq("id", goal_id)
        .eq("client_id", client_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
