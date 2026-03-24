import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings

logger = logging.getLogger(__name__)

# ── Static directory for logos ────────────────────────────────────────────────
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR  = os.path.join(_BACKEND_DIR, "static")
_LOGOS_DIR   = os.path.join(_STATIC_DIR, "logos")
os.makedirs(os.path.join(_LOGOS_DIR, "agencies"), exist_ok=True)
os.makedirs(os.path.join(_LOGOS_DIR, "clients"),  exist_ok=True)


# ── Background scheduler loop ─────────────────────────────────────────────────

async def _scheduler_loop() -> None:
    """Check for due scheduled reports every hour."""
    while True:
        try:
            from services.scheduler import check_and_run_scheduled_reports  # noqa: PLC0415
            await check_and_run_scheduled_reports()
        except Exception as exc:
            logger.error("Scheduler loop error: %s", exc)
        await asyncio.sleep(3600)  # run every hour


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan — start background tasks on startup, cancel on shutdown."""
    scheduler_task = asyncio.create_task(_scheduler_loop())
    logger.info("Background scheduler started (checks every 60 min)")
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

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static file serving (logos) ───────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "reportpilot-api"}


# ── Routers ───────────────────────────────────────────────────────────────────

from routers import auth, clients, connections, reports, settings as settings_router, scheduled_reports, billing, dashboard  # noqa: E402
from routers import csv_upload  # noqa: E402
from routers.shared import reports_router as shared_reports_router, public_router as shared_public_router  # noqa: E402

# Create custom_sections static dir if not exists
os.makedirs(os.path.join(_STATIC_DIR, "custom_sections"), exist_ok=True)

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
app.include_router(shared_reports_router,     prefix="/api/reports",            tags=["sharing"])
app.include_router(shared_public_router,      prefix="/api/shared",             tags=["shared-public"])
