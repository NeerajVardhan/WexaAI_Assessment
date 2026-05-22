from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_session
from app.core.permissions import Role
from app.models import User
from app.schemas import ApiKeyCreate, ApiKeyRead
from app.services import ApiKeyService

router = APIRouter()


@router.get("", response_model=list[ApiKeyRead])
async def list_api_keys(
    user: User = Depends(require_role(Role.ANALYST)),
    session: AsyncSession = Depends(get_session),
) -> list[ApiKeyRead]:
    return [ApiKeyRead.model_validate(key) for key in await ApiKeyService(session).list(user.organization_id)]


@router.post("", response_model=ApiKeyRead, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreate,
    user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyRead:
    key, raw = await ApiKeyService(session).create(user, payload)
    data = ApiKeyRead.model_validate(key)
    data.key = raw
    return data


@router.post("/{key_id}/revoke", response_model=ApiKeyRead)
async def revoke_api_key(
    key_id: str,
    user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyRead:
    return ApiKeyRead.model_validate(await ApiKeyService(session).revoke(user.organization_id, key_id))


@router.post("/{key_id}/rotate", response_model=ApiKeyRead)
async def rotate_api_key(
    key_id: str,
    user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyRead:
    key, raw = await ApiKeyService(session).rotate(user.organization_id, key_id)
    data = ApiKeyRead.model_validate(key)
    data.key = raw
    return data

