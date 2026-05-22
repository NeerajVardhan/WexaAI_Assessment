from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, require_role
from app.core.database import get_session
from app.core.permissions import Role
from app.models import User
from app.schemas import AlertEventRead, AlertRuleCreate, AlertRuleRead
from app.services import AlertService

router = APIRouter()


@router.get("", response_model=list[AlertRuleRead])
async def list_alerts(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AlertRuleRead]:
    return [AlertRuleRead.model_validate(rule) for rule in await AlertService(session).list(user.organization_id)]


@router.post("", response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED)
async def create_alert(
    payload: AlertRuleCreate,
    user: User = Depends(require_role(Role.ANALYST)),
    session: AsyncSession = Depends(get_session),
) -> AlertRuleRead:
    return AlertRuleRead.model_validate(await AlertService(session).create(user.organization_id, payload))


@router.post("/{rule_id}/evaluate", response_model=AlertEventRead)
async def evaluate_alert(
    rule_id: str,
    user: User = Depends(require_role(Role.ANALYST)),
    session: AsyncSession = Depends(get_session),
) -> AlertEventRead:
    return AlertEventRead.model_validate(await AlertService(session).evaluate(user.organization_id, rule_id))


@router.post("/{rule_id}/mute", response_model=AlertRuleRead)
async def mute_alert(
    rule_id: str,
    minutes: int = 60,
    user: User = Depends(require_role(Role.ANALYST)),
    session: AsyncSession = Depends(get_session),
) -> AlertRuleRead:
    return AlertRuleRead.model_validate(await AlertService(session).mute(user.organization_id, rule_id, minutes))


@router.get("/{rule_id}/history", response_model=list[AlertEventRead])
async def alert_history(
    rule_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AlertEventRead]:
    events = await AlertService(session).history(user.organization_id, rule_id)
    return [AlertEventRead.model_validate(event) for event in events]

