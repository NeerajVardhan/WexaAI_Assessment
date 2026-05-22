import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Cookie, Depends, Header, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import AppError, AuthenticationFailed
from app.core.permissions import Role, assert_role
from app.core.security import decode_token
from app.models import ApiKey, User
from app.services import ApiKeyService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
rate_buckets: dict[str, deque[float]] = defaultdict(deque)


async def current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise AuthenticationFailed("Invalid bearer token") from exc
    user = await session.scalar(select(User).where(User.id == payload["sub"], User.is_active.is_(True)))
    if user is None:
        raise AuthenticationFailed("User not found")
    return user


def require_role(minimum: Role) -> Callable:
    async def dependency(user: User = Depends(current_user)) -> User:
        assert_role(user.role, minimum)
        return user

    return dependency


async def current_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> ApiKey:
    return await ApiKeyService(session).authenticate(x_api_key)


async def rate_limited_api_key(api_key: ApiKey = Depends(current_api_key)) -> ApiKey:
    now = time.time()
    bucket = rate_buckets[api_key.id]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= 600:
        raise AppError("Ingestion rate limit exceeded", status_code=429, code="rate_limited")
    bucket.append(now)
    return api_key


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        "refresh_token",
        token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie("refresh_token", path="/api/v1/auth")


async def refresh_cookie(refresh_token: str | None = Cookie(default=None)) -> str:
    if not refresh_token:
        raise AuthenticationFailed("Refresh cookie is missing")
    return refresh_token
