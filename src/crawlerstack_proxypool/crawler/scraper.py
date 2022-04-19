import asyncio
import dataclasses
import logging

from crawlerstack_proxypool.crawler.spider import Spider

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Scraper:
    """"""
    loop: asyncio.AbstractEventLoop = dataclasses.field(default_factory=asyncio.get_running_loop)
    _queue: asyncio.Queue = dataclasses.field(init=False)

    def __post_init__(self):
        self._queue = asyncio.Queue(50)

    @property
    def queue(self):
        return self._queue

    async def enqueue(self, response, spider: Spider):
        """"""
        task = self.loop.create_task(self.parse(response, spider))
        await self._queue.put(task)
        return task

    def idle(self) -> bool:
        logger.debug(f'Scrap queue size: {self.queue.qsize()}')
        return self._queue.empty()

    async def parse(self, response, spider):  # noqa
        """"""
        try:
            logger.debug(f'Parse {response}')
            result = await spider.parse(response)
            logger.debug(result)
        finally:
            await self._queue.get()

    async def close(self):
        pass
