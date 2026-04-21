import asyncio
import logging
import os
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings

logging.basicConfig(
    level=logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("reportpilot")

# ── Static directory for logos ────────────────────────────────────────────────
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR  = os.path.join(_BACKEND_DIR, "static")
_LOGOS_DIR   = os.path.join(_STATIC_DIR, "logos")
os.makedirs(os.path.join(_LOGOS_DIR, "agencies"), exist_ok=True)
os.makedirs(os.path.join(_LOGOS_DIR, "clients"),  exist_ok=True)


# ── Background scheduler loop ─────────────────────────────────────────────────

async def _scheduler_loop() -> None:
    """
    Background loop — runs every 15 minutes.

    Each tick:
      * runs due scheduled reports
      * runs connection-health probes (internally short-circuits to a
        6-hour cadence so we don't probe every 15 min)
    """
    while True:
        try:
            from services.scheduler import (  # noqa: PLC0415
                check_and_run_scheduled_reports,
                check_and_run_health_checks,
                check_and_run_goal_checks,
            )
            await check_and_run_scheduled_reports()
            await check_and_run_health_checks()
            # Phase 6 — evaluate goals after the health sweep so alerts
            # benefit from any snapshot refresh a health check might trigger.
            await check_and_run_goal_checks()
        except Exception as exc:
            logger.error("Scheduler loop error: %s", exc)
        await asyncio.sleep(900)  # run every 15 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan — start background tasks on startup, cancel on shutdown."""
    logger.info("ReportPilot API starting — environment=%s", settings.ENVIRONMENT)
    scheduler_task = asyncio.create_task(_scheduler_loop())
    logger.info("Background scheduler started (checks every 15 min)")
    yield
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    logger.info("Background scheduler stopped")


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="ReportPilot API",
    description="Backend API for ReportPilot — AI-powered client reporting",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Rate limiting ────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
_origins = [settings.FRONTEND_URL]
if settings.ENVIRONMENT == "development":
    _origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static file serving (logos) ───────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway deployment monitoring."""
    health: dict = {
        "status": "healthy",
        "service": "reportpilot-api",
        "environment": settings.ENVIRONMENT,
    }

    # Check Supabase connectivity
    try:
        from services.supabase_client import get_supabase_admin  # noqa: PLC0415
        sb = get_supabase_admin()
        sb.table("profiles").select("id").limit(1).execute()
        health["supabase"] = "connected"
    except Exception as e:
        health["supabase"] = f"error: {str(e)[:100]}"
        health["status"] = "degraded"

    # Check OpenAI API key is set
    health["openai"] = "configured" if settings.OPENAI_API_KEY else "missing"

    # Check LibreOffice availability
    health["libreoffice"] = "available" if shutil.which("soffice") or shutil.which("libreoffice") else "unavailable"

    return health


# ── Routers ───────────────────────────────────────────────────────────────────

from routers import auth, clients, connections, reports, settings as settings_router, scheduled_reports, billing, dashboard, admin  # noqa: E402
from routers import csv_upload  # noqa: E402
from routers import admin_analytics  # noqa: E402
from routers import goals as goals_router  # noqa: E402  # Phase 6
from routers.shared import reports_router as shared_reports_router, public_router as shared_public_router  # noqa: E402

# Create custom_sections static dir if not exists
os.makedirs(os.path.join(_STATIC_DIR, "custom_sections"), exist_ok=True)
# Create cover_heroes static dir (Phase 3 fallback when Supabase Storage fails)
os.makedirs(os.path.join(_STATIC_DIR, "cover_heroes"), exist_ok=True)

app.include_router(clients.router,            prefix="/api/clients",            tags=["clients"])
app.include_router(reports.router,            prefix="/api/reports",            tags=["reports"])
app.include_router(auth.router,               prefix="/api/auth",               tags=["auth"])
app.include_router(connections.router,        prefix="/api/connections",        tags=["connections"])
app.include_router(csv_upload.router,         prefix="/api/connections",        tags=["csv"])
app.include_router(settings_router.router,    prefix="/api/settings",           tags=["settings"])
app.include_router(scheduled_reports.router,  prefix="/api/scheduled-reports",  tags=["scheduled-reports"])
app.include_router(billing.router,            prefix="/api/billing",            tags=["billing"])
app.include_router(dashboard.router,          prefix="/api/dashboard",          tags=["dashboard"])
# Sharing: authenticated endpoints under /api/reports, public under /api/shared
app.include_router(admin.router,              prefix="/api/admin",              tags=["admin"])
app.include_router(admin_analytics.router,    prefix="/api/admin",              tags=["admin"])
app.include_router(shared_reports_router,     prefix="/api/reports",            tags=["sharing"])
app.include_router(shared_public_router,      prefix="/api/shared",             tags=["shared-public"])
# Phase 6 — Goals & Alerts. Routes in goals.py carry absolute segments
# (/goals/metrics, /clients/{id}/goals/...) so we mount once at /api.
app.include_router(goals_router.router,       prefix="/api",                    tags=["goals"])
