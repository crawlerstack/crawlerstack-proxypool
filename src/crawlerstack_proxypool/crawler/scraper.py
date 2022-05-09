"""
Scraper
"""
import asyncio
import dataclasses
import logging

from crawlerstack_proxypool.crawler.spider import Spider

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Scraper:
    """
    Scraper
    """
    loop: asyncio.AbstractEventLoop = dataclasses.field(default_factory=asyncio.get_running_loop)
    _queue: asyncio.Queue = dataclasses.field(init=False)

    def __post_init__(self):
        self._queue = asyncio.Queue(5)

    @property
    def queue(self):
        """
        Get scraper queue
        :return:
        """
        return self._queue

    async def enqueue(self, response, spider: Spider):
        """
        Set response parse task to queue
        :param response:
        :param spider:
        :return:
        """
        await self._queue.put(response)
        logger.debug('Current scraper queue size: %d, enqueued response: %s', self.queue.qsize(), response)
        task = self.loop.create_task(self.parse(response, spider))
        return task

    def should_pass(self) -> bool:
        """
        判断是否需要跳过
        :return:
        """
        return self.queue.full()

    def idle(self) -> bool:
        """
        Scraper is idle ?
        :return:
        """
        logger.debug('Scrap queue size: %d', self.queue.qsize())
        return self._queue.empty()

    async def parse(self, response, spider):  # noqa
        """
        Parse response use spider.parse method.
        :param response:
        :param spider:
        :return:
        """
        try:
            logger.debug('Parse %s', response)
            result = await spider.parse(response)
            logger.debug(result)
        except Exception as ex:
            logger.exception(ex)
            # 增加异常处理逻辑
        finally:
            await self._queue.get()

    async def close(self):
        """
        Close.
        :return:
        """
