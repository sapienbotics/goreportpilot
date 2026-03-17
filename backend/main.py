from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings

app = FastAPI(
    title="ReportPilot API",
    description="Backend API for ReportPilot — AI-powered client reporting",
    version="0.1.0"
)

# CORS — allow frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "reportpilot-api"}


# Routers will be included here as they are built:
# from routers import auth, clients, connections, reports, data_pull, webhooks
# app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
# app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
# app.include_router(connections.router, prefix="/api/connections", tags=["connections"])
# app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
# app.include_router(data_pull.router, prefix="/api/data", tags=["data"])
# app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
