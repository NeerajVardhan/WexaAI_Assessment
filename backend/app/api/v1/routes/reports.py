from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, require_role
from app.core.database import get_session
from app.core.permissions import Role
from app.models import User
from app.schemas import ReportRunRead, ReportScheduleCreate, ReportScheduleRead
from app.services import ReportService

router = APIRouter()


@router.get("", response_model=list[ReportScheduleRead])
async def list_reports(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ReportScheduleRead]:
    return [ReportScheduleRead.model_validate(item) for item in await ReportService(session).list(user.organization_id)]


@router.post("", response_model=ReportScheduleRead, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ReportScheduleCreate,
    user: User = Depends(require_role(Role.ANALYST)),
    session: AsyncSession = Depends(get_session),
) -> ReportScheduleRead:
    return ReportScheduleRead.model_validate(await ReportService(session).create(user.organization_id, payload))


@router.post("/{schedule_id}/run", response_model=ReportRunRead)
async def run_report(
    schedule_id: str,
    user: User = Depends(require_role(Role.ANALYST)),
    session: AsyncSession = Depends(get_session),
) -> ReportRunRead:
    return ReportRunRead.model_validate(await ReportService(session).run_now(user.organization_id, schedule_id))


@router.get("/{schedule_id}/runs", response_model=list[ReportRunRead])
async def report_history(
    schedule_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ReportRunRead]:
    return [
        ReportRunRead.model_validate(run)
        for run in await ReportService(session).history(user.organization_id, schedule_id)
    ]

