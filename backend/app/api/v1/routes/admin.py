from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_session
from app.core.permissions import Role
from app.models import User
from app.schemas import (
    FeatureFlagsUpdate,
    RetentionPolicyUpdate,
    SqlSandboxRequest,
    SqlSandboxResponse,
    WebhookDeliveryCreate,
    WebhookDeliveryRead,
)
from app.services import AdminService

router = APIRouter()


@router.put("/feature-flags")
async def update_feature_flags(
    payload: FeatureFlagsUpdate,
    user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    return await AdminService(session).update_feature_flags(user.organization_id, payload.feature_flags)


@router.put("/retention")
async def update_retention(
    payload: RetentionPolicyUpdate,
    user: User = Depends(require_role(Role.OWNER)),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    days = await AdminService(session).update_retention(user.organization_id, payload.retention_days)
    return {"retention_days": days}


@router.post("/sql-sandbox", response_model=SqlSandboxResponse)
async def run_sql_sandbox(
    payload: SqlSandboxRequest,
    user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> SqlSandboxResponse:
    return SqlSandboxResponse.model_validate(await AdminService(session).run_sql_sandbox(user.organization_id, payload))


@router.get("/webhook-deliveries", response_model=list[WebhookDeliveryRead])
async def list_webhook_deliveries(
    user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> list[WebhookDeliveryRead]:
    deliveries = await AdminService(session).list_webhook_deliveries(user.organization_id)
    return [WebhookDeliveryRead.model_validate(delivery) for delivery in deliveries]


@router.post("/webhook-deliveries", response_model=WebhookDeliveryRead, status_code=status.HTTP_201_CREATED)
async def create_webhook_delivery(
    payload: WebhookDeliveryCreate,
    user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> WebhookDeliveryRead:
    return WebhookDeliveryRead.model_validate(
        await AdminService(session).create_webhook_delivery(user.organization_id, payload)
    )


@router.post("/webhook-deliveries/{delivery_id}/retry", response_model=WebhookDeliveryRead)
async def retry_webhook_delivery(
    delivery_id: str,
    user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> WebhookDeliveryRead:
    return WebhookDeliveryRead.model_validate(
        await AdminService(session).retry_webhook_delivery(user.organization_id, delivery_id)
    )
