"""
Crawler engine
"""
import asyncio
import dataclasses
import logging
import typing
from collections.abc import AsyncGenerator

from crawlerstack_proxypool.aio_scrapy.downloader import Downloader
from crawlerstack_proxypool.aio_scrapy.req_resp import RequestProxy
from crawlerstack_proxypool.aio_scrapy.scraper import Scraper
from crawlerstack_proxypool.aio_scrapy.spider import Spider
from crawlerstack_proxypool.signals import spider_closed, spider_opened

if typing.TYPE_CHECKING:
    from crawlerstack_proxypool.aio_scrapy.crawler import Crawler

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class ExecuteEngine:
    """
    Crawler engine
    """
    crawler: 'Crawler'
    _spider: Spider = dataclasses.field(init=False)
    _running: bool = dataclasses.field(default=False, init=False)
    _closed: asyncio.Future = dataclasses.field(default=None, init=False)
    _next_request_task: asyncio.Task | None = dataclasses.field(default=None, init=False)
    _downloader: Downloader = dataclasses.field(init=False)
    _scraper: Scraper = dataclasses.field(default_factory=Scraper, init=False)
    _start_requests: AsyncGenerator[RequestProxy, None] | None = dataclasses.field(default=None, init=False)
    _processing_requests_queue: asyncio.Queue = dataclasses.field(init=False)

    def __post_init__(self):
        self._closed = asyncio.Future()
        self._processing_requests_queue = asyncio.Queue(10)
        self._downloader = Downloader(self.crawler.settings)

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """
        Get event_loop
        :return:
        """
        return asyncio.get_running_loop()

    async def start(self) -> asyncio.Future:
        """
        Start engine.
        :return:
        """
        self._running = True
        return await self._closed

    async def close(self):
        """
        Close engine.
        :return:
        """
        if self._running:
            await self.stop()

    async def stop(self):
        """
        Stop engine.
        :return:
        """

        self._running = False
        # Spider closed
        await self.close_spider()
        # set closed result.
        if not self._closed.done():
            self._closed.set_result('Closed.')
        logger.debug('Stopped execution engine.')

    async def open_spider(self, spider):
        """
        Open spider.
        :param spider:
        :return:
        """
        logger.info('Open spider: %s', spider.name)
        self._spider = spider
        self._start_requests = self._spider.start_requests()
        await spider_opened.send(sender=self._spider)
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
        self.loop.create_task(self.next_request())
        await self.loop_call(delay)

    async def close_spider(self):
        """
        Close spider.
        :return:
        """
        await self._downloader.close()
        if self._next_request_task:
            self._next_request_task.cancel('close.')
        logger.debug('Closed spider.')

    async def next_request(self):
        """
        Next request.
        :return:
        """
        if self._start_requests is not None and not self.should_pass() and not self._start_requests.ag_running:
            try:
                request = await self._start_requests.__anext__()  # pylint: disable=unnecessary-dunder-call
            except StopAsyncIteration:
                self._start_requests = None
            else:
                await self.crawl(request)

        await self.spider_idle()

    async def crawl(self, request: RequestProxy):
        """
        Crawl task
        :param request:
        :return:
        """
        await self._processing_requests_queue.put(request)
        self.loop.create_task(self.schedule(request))
        self.loop.create_task(self.next_request())

    async def schedule(self, request):
        """
        Schedule.
        :param request:
        :return:
        """
        try:
            download_task = await self._downloader.enqueue(request, self._spider)
            response = await download_task

            if response:
                scrap_task = await self._scraper.enqueue(response, self._spider)
                await scrap_task

            self.loop.create_task(self.next_request())
        finally:
            await self._processing_requests_queue.get()

    def should_pass(self):
        """
        下此次操作是否跳过
        :return:
        """
        return any([
            not self._running,
            self._downloader.should_pass(),
            self._scraper.should_pass(),
            self._processing_requests_queue.full(),
        ])

    def spider_is_idle(self) -> bool:
        """
        CHeck spider is idle.
        :return:
        """
        if not self._downloader.idle():
            return False
        if not self._scraper.idle():
            return False
        if not self._processing_requests_queue.empty():
            return False
        if self._start_requests is not None:
            return False
        return True

    async def spider_idle(self):
        """
        Spider idle.
        :return:
        """
        if self.spider_is_idle():
            logger.debug('Engine is idle, to close...')
            await spider_closed.send(sender=self._spider)
            await self.stop()
