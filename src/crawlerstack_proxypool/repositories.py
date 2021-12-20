from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from crawlerstack_proxypool.db import Base
from crawlerstack_proxypool.entities import BaseEntity
from crawlerstack_proxypool.models import IpProxyModel


class BaseRepository:
    MODEL: Base
    ENTITY: BaseEntity

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_all(self) -> list[BaseEntity]:
        result: Result = await self._session.execute(select(self.MODEL))
        entities = []
        for obj in result.scalars().all():
            entities.append(self.ENTITY.from_orm(obj))
        return entities

    async def get_by_id(self, pk: int) -> Base:
        return await self._session.get(self.MODEL, int)

    async def create(self, **kwargs) -> BaseEntity:
        obj = self.MODEL(**kwargs)
        self._session.add(obj)
        await self._session.commit()
        await self._session.refresh(obj)
        return self.ENTITY.from_orm(obj)


class IpProxyRepository(BaseRepository):
    MODEL = IpProxyModel
