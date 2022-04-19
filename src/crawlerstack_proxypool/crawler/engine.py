import asyncio
import dataclasses
import logging
import typing

from crawlerstack_proxypool.crawler.downloader import Downloader
from crawlerstack_proxypool.crawler.req_resp import RequestProxy
from crawlerstack_proxypool.crawler.scraper import Scraper
from crawlerstack_proxypool.crawler.spider import Spider

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class ExecuteEngine:
    _spider: Spider = dataclasses.field(init=False)
    _running: bool = dataclasses.field(default=False, init=False)
    _closed: asyncio.Future = dataclasses.field(default=None, init=False)
    _next_request_task: asyncio.Task | None = dataclasses.field(default=None, init=False)
    _downloader: Downloader = dataclasses.field(default_factory=Downloader, init=False)
    _scraper: Scraper = dataclasses.field(default_factory=Scraper, init=False)
    _start_requests: typing.Iterator[RequestProxy] | None = dataclasses.field(default=None, init=False)
    _processing_requests: set = dataclasses.field(default_factory=set, init=False)

    def __post_init__(self):
        self._closed = asyncio.Future()

    @property
    def loop(self):
        return asyncio.get_running_loop()

    async def start(self) -> asyncio.Future:
        """"""
        self._running = True
        return await self._closed

    async def close(self):
        if self._running:
            await self.stop()

    async def stop(self):
        self._running = False
        # Spider closed
        await self.close_spider()
        # set closed result.
        self._closed.set_result('Closed.')
        logger.debug('Stopped execution engine.')

    def open_spider(self, spider):
        self._spider = spider
        self._start_requests = self._spider.start_requests()
        self._next_request_task = self.loop.create_task(self.loop_call(5))

    async def loop_call(self, delay: float):
        """
        循环调用 next_request
        :param delay:
        :return:
        """
        await asyncio.sleep(delay)
        if self._closed.done():
            return
        await self.next_request()
        await self.loop_call(delay)

    async def close_spider(self):
        """"""
        await self._downloader.close()
        if self._next_request_task:
            self._next_request_task.cancel('close.')
        logger.debug('Closed spider.')

    async def next_request(self):
        if self._start_requests is not None and not self.should_pass():
            try:
                request = next(self._start_requests)
            except StopIteration:
                self._start_requests = None
            else:
                await self.crawl(request)

        await self.spider_idle()

    async def crawl(self, request: RequestProxy):
        self._processing_requests.add(request)
        self.loop.create_task(self.schedule(request))
        self.loop.create_task(self.next_request())

    async def schedule(self, request):
        try:
            download_task = await self._downloader.enqueue(request)
            response = await download_task

            self.loop.create_task(self.next_request())

            scrap_task = await self._scraper.enqueue(response, self._spider)
            await scrap_task
        finally:
            self._processing_requests.remove(request)

    def should_pass(self):
        """
        下此次操作是否跳过
        :return:
        """
        return any([not self._running])

    def spider_is_idle(self) -> bool:
        """"""
        if not self._downloader.idle():
            return False
        if not self._scraper.idle():
            return False
        if self._processing_requests:
            return False
        if self._start_requests is not None:
            return False
        return True

    async def spider_idle(self):
        """"""
        if self.spider_is_idle():
            logger.debug('Engine is idle.')
            await self.stop()
