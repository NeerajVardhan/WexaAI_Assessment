from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, rate_limited_api_key
from app.core.database import get_session
from app.models import ApiKey, User
from app.schemas import BatchEventsIn, EventIn, EventRead
from app.services import IngestionService

router = APIRouter()


@router.post("/event", response_model=EventRead, status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(
    payload: EventIn,
    api_key: ApiKey = Depends(rate_limited_api_key),
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    event = await IngestionService(session).ingest_one(api_key.organization_id, payload, api_key)
    return EventRead.model_validate(event)


@router.post("/batch", response_model=list[EventRead], status_code=status.HTTP_202_ACCEPTED)
async def ingest_batch(
    payload: BatchEventsIn,
    api_key: ApiKey = Depends(rate_limited_api_key),
    session: AsyncSession = Depends(get_session),
) -> list[EventRead]:
    events = await IngestionService(session).ingest_batch(api_key.organization_id, payload, api_key)
    return [EventRead.model_validate(event) for event in events]


@router.post("/csv", response_model=list[EventRead], status_code=status.HTTP_202_ACCEPTED)
async def ingest_csv(
    file: UploadFile = File(...),
    api_key: ApiKey = Depends(rate_limited_api_key),
    session: AsyncSession = Depends(get_session),
) -> list[EventRead]:
    text = (await file.read()).decode("utf-8")
    events = await IngestionService(session).ingest_csv(api_key.organization_id, text, api_key)
    return [EventRead.model_validate(event) for event in events]


@router.post("/webhook/{source}", response_model=EventRead, status_code=status.HTTP_202_ACCEPTED)
async def webhook(
    source: str,
    payload: dict,
    api_key: ApiKey = Depends(rate_limited_api_key),
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    event = await IngestionService(session).ingest_one(
        api_key.organization_id,
        EventIn(event_type=payload.get("event_type", source), source=source, properties=payload),
        api_key,
    )
    return EventRead.model_validate(event)


@router.get("/events", response_model=list[EventRead])
async def recent_events(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EventRead]:
    events = await IngestionService(session).list_recent(user.organization_id)
    return [EventRead.model_validate(event) for event in events]
