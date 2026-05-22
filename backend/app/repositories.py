from collections.abc import Sequence
from typing import TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFound

ModelT = TypeVar("ModelT")


class Repository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_one(self, statement: Select[tuple[ModelT]], message: str = "Record not found") -> ModelT:
        result = await self.session.execute(statement)
        value = result.scalar_one_or_none()
        if value is None:
            raise NotFound(message)
        return value

    async def list(self, statement: Select[tuple[ModelT]]) -> Sequence[ModelT]:
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def by_id_for_org(self, model: type[ModelT], record_id: str, organization_id: str) -> ModelT:
        return await self.get_one(
            select(model).where(model.id == record_id, model.organization_id == organization_id),
            f"{model.__name__} not found",
        )

