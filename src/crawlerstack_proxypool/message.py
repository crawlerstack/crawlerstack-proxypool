"""message"""
import dataclasses

import aioredis

from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.utils import SingletonMeta


@dataclasses.dataclass
class Message(metaclass=SingletonMeta):
    """Message"""
    pool = aioredis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

    _client: aioredis.Redis = dataclasses.field(default=None, init=False)

    async def client(self) -> aioredis.Redis:
        """client"""
        if not self._client:
            self._client = await aioredis.Redis(connection_pool=self.pool)
        return self._client

    async def add(self, name, item):
        """add data"""
        client: aioredis.Redis = await self.client()
        await client.sadd(name, item)

    async def pop(self, name: str, count: int = 10) -> list[str]:
        """remove data"""
        client = await self.client()
        result = await client.spop(name, count)
        return result
