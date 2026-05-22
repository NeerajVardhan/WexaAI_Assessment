from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import clear_refresh_cookie, current_user, refresh_cookie, require_role, set_refresh_cookie
from app.core.database import get_session
from app.core.permissions import Role
from app.models import User
from app.schemas import InviteAccept, InviteCreate, InviteRead, LoginRequest, SignupRequest, TokenPair, UserRead
from app.services import AuthService

router = APIRouter()


@router.post("/signup", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    user, refresh_token = await AuthService(session).signup(payload)
    set_refresh_cookie(response, refresh_token)
    return TokenPair(access_token=AuthService.access_token_for(user), user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    user, refresh_token = await AuthService(session).login(payload)
    set_refresh_cookie(response, refresh_token)
    return TokenPair(access_token=AuthService.access_token_for(user), user=UserRead.model_validate(user))


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    response: Response,
    token: str = Depends(refresh_cookie),
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    user = await AuthService(session).refresh(token)
    return TokenPair(access_token=AuthService.access_token_for(user), user=UserRead.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    clear_refresh_cookie(response)


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(current_user)) -> User:
    return user


@router.post("/invites", response_model=InviteRead, status_code=status.HTTP_201_CREATED)
async def create_invite(
    payload: InviteCreate,
    user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_session),
) -> InviteRead:
    invite, raw = await AuthService(session).create_invite(user, payload)
    data = InviteRead.model_validate(invite)
    data.token = raw
    return data


@router.post("/invites/accept", response_model=TokenPair)
async def accept_invite(
    payload: InviteAccept,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    user, refresh_token = await AuthService(session).accept_invite(payload)
    set_refresh_cookie(response, refresh_token)
    return TokenPair(access_token=AuthService.access_token_for(user), user=UserRead.model_validate(user))
