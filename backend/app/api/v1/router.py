from fastapi import APIRouter

from app.api.v1.routes import admin, alerts, api_keys, auth, dashboards, health, ingestion, realtime, reports

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api keys"])
api_router.include_router(ingestion.router, prefix="/ingest", tags=["ingestion"])
api_router.include_router(dashboards.router, prefix="/dashboards", tags=["dashboards"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(realtime.router, prefix="/ws", tags=["realtime"])
