from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, require_role
from app.core.database import get_session
from app.core.permissions import Role
from app.models import User
from app.schemas import (
    DashboardCreate,
    DashboardRead,
    QueryResult,
    SavedQueryCreate,
    SavedQueryRead,
    WidgetCreate,
    WidgetRead,
)
from app.services import DashboardService

router = APIRouter()

TEMPLATE_KEYS = ["web_analytics", "sales", "devops"]


@router.get("", response_model=list[DashboardRead], tags=["dashboards"])
async def list_dashboards(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[DashboardRead]:
    items = await DashboardService(session).list_dashboards(user.organization_id)
    return [DashboardRead.model_validate(item) for item in items]


@router.post("", response_model=DashboardRead, status_code=status.HTTP_201_CREATED, tags=["dashboards"])
async def create_dashboard(
    payload: DashboardCreate,
    user: User = Depends(require_role(Role.ANALYST)),
    session: AsyncSession = Depends(get_session),
) -> DashboardRead:
    return DashboardRead.model_validate(await DashboardService(session).create_dashboard(user, payload))


@router.get("/metrics", tags=["dashboards"])
async def get_metrics(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await DashboardService(session).get_metrics(user.organization_id)


@router.get("/sources", tags=["dashboards"])
async def get_source_breakdown(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    return await DashboardService(session).get_source_breakdown(user.organization_id)


@router.post(
    "/templates/{template_key}",
    response_model=DashboardRead,
    status_code=status.HTTP_201_CREATED,
    tags=["dashboards"],
)
async def create_from_template(
    template_key: str,
    user: User = Depends(require_role(Role.ANALYST)),
    session: AsyncSession = Depends(get_session),
) -> DashboardRead:
    return DashboardRead.model_validate(
        await DashboardService(session).create_from_template(user, template_key)
    )


@router.get("/templates", tags=["dashboards"])
async def list_templates() -> list[dict[str, str]]:
    return [
        {"key": "web_analytics", "name": "Web Analytics", "description": "Page views, sessions, conversions"},
        {"key": "sales", "name": "Sales Dashboard", "description": "Revenue, funnel, signups"},
        {"key": "devops", "name": "DevOps Monitoring", "description": "Errors, latency, system health"},
    ]


@router.get("/public/{token}", response_model=DashboardRead, tags=["dashboards"])
async def public_dashboard(token: str, session: AsyncSession = Depends(get_session)) -> DashboardRead:
    return DashboardRead.model_validate(await DashboardService(session).public_dashboard(token))


@router.get("/{dashboard_id}", response_model=DashboardRead, tags=["dashboards"])
async def get_dashboard(
    dashboard_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardRead:
    return DashboardRead.model_validate(
        await DashboardService(session).get_dashboard(user.organization_id, dashboard_id)
    )


@router.post(
    "/{dashboard_id}/widgets",
    response_model=WidgetRead,
    status_code=status.HTTP_201_CREATED,
    tags=["dashboards"],
)
async def add_widget(
    dashboard_id: str,
    payload: WidgetCreate,
    user: User = Depends(require_role(Role.ANALYST)),
    session: AsyncSession = Depends(get_session),
) -> WidgetRead:
    return WidgetRead.model_validate(
        await DashboardService(session).add_widget(user.organization_id, dashboard_id, payload)
    )


@router.get("/queries/saved", response_model=list[SavedQueryRead], tags=["queries"])
async def list_queries(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SavedQueryRead]:
    queries = await DashboardService(session).list_queries(user.organization_id)
    return [SavedQueryRead.model_validate(query) for query in queries]


@router.post(
    "/queries/saved",
    response_model=SavedQueryRead,
    status_code=status.HTTP_201_CREATED,
    tags=["queries"],
)
async def create_query(
    payload: SavedQueryCreate,
    user: User = Depends(require_role(Role.ANALYST)),
    session: AsyncSession = Depends(get_session),
) -> SavedQueryRead:
    return SavedQueryRead.model_validate(
        await DashboardService(session).create_query(user.organization_id, payload)
    )


@router.get("/queries/run", response_model=QueryResult, tags=["queries"])
async def run_query(
    query_id: str | None = None,
    hours: int = Query(default=24, ge=1, le=720),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> QueryResult:
    return QueryResult.model_validate(
        await DashboardService(session).run_query(user.organization_id, query_id, hours=hours)
    )
