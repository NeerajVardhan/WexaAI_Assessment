import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging

_DESCRIPTION = """
## WexaAI Analytics Platform

A production-grade real-time analytics and reporting API.

### Key capabilities
- **Multi-tenant** organisation isolation with role-based access (Owner → Admin → Analyst → Viewer)
- **Event ingestion** via REST (single / batch / CSV / webhook) with API-key authentication and rate limiting
- **Dashboards & widgets** — line, bar, pie, KPI, table; public sharing; auto-refresh
- **Alerts** — threshold rules evaluated by Celery Beat; in-app, email, and webhook notifications
- **Scheduled reports** — PDF / CSV generation emailed to recipients on a cron schedule
- **Real-time** — WebSocket streams for live events and alert notifications

### Authentication
Most endpoints require a **Bearer** JWT (`Authorization: Bearer <token>`).
Ingestion endpoints accept an **API key** via `X-API-Key` header.
Use `POST /api/v1/auth/login` to obtain a token.
"""

_TAGS = [
    {"name": "auth", "description": "Sign-up, login, refresh, invites"},
    {"name": "api-keys", "description": "API key management"},
    {"name": "ingestion", "description": "Event ingestion — single, batch, CSV, webhook"},
    {"name": "dashboards", "description": "Dashboard & widget CRUD, templates, metrics"},
    {"name": "queries", "description": "Saved query management and execution"},
    {"name": "alerts", "description": "Alert rules, evaluation, muting, history"},
    {"name": "reports", "description": "Scheduled report management and runs"},
    {"name": "admin", "description": "Feature flags, retention, SQL sandbox, webhook deliveries"},
    {"name": "realtime", "description": "WebSocket streams (events, notifications)"},
    {"name": "health", "description": "Health check"},
]


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=_DESCRIPTION,
        openapi_tags=_TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
        swagger_ui_parameters={"persistAuthorization": True, "defaultModelsExpandDepth": 1},
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.backend_cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")

    artifacts_dir = settings.report_artifacts_dir
    os.makedirs(artifacts_dir, exist_ok=True)
    app.mount("/artifacts", StaticFiles(directory=artifacts_dir), name="artifacts")

    if settings.enable_graphql:
        try:
            from app.graphql import graphql_router

            app.include_router(graphql_router, prefix="/graphql")
        except Exception:
            pass

    if settings.enable_otel:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)

    return app


app = create_app()
