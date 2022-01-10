import asyncio
import logging
import random
from collections.abc import AsyncIterable, Awaitable, Callable, Iterable
from typing import Any, Type

from aiohttp import hdrs
from yarl import URL

from crawlerstack_proxypool.crawler.download_handler import DownloadHandler
from crawlerstack_proxypool.crawler.parser import DefaultParser, BaseParser
from crawlerstack_proxypool.crawler.req_resp import RequestProxy, ResponseProxy
from crawlerstack_proxypool.signals import spider_started, spider_closed


class Spider:

    def __init__(
            self,
            name: str,
            *,
            seeds: AsyncIterable[URL] | Iterable[URL],

            parser_kls: Type[BaseParser] | None = None,

            pipeline_handler: Callable[..., Awaitable] | None = None,
            error_handler: Callable[[RequestProxy, Exception], Awaitable] | None = None,

            stop: asyncio.Future | None = None,

            max_pipeliner=3,
            max_downloader=2,
            max_scraper=5,
            download_delay=1,

            **kwargs
    ):
        """
        Spider.
        :param name:
        :param seeds:
        :param parser_kls:
        :param pipeline_handler:
        :param error_handler:
        :param stop:
        :param max_pipeliner:
        :param max_downloader:
        :param max_scraper:
        :param download_delay:
        :param kwargs:
        """
        self.name = name

        self.seeds = seeds

        self.parser: BaseParser = parser_kls(self) if parser_kls else DefaultParser(self)

        self.pipeline_handler = pipeline_handler
        self.error_handler = error_handler

        self._stop = stop or asyncio.Future()

        self._max_pipeliner = max_pipeliner
        self._max_downloader = max_downloader
        self._max_scraper = max_scraper
        self._download_delay = download_delay

        self._active_downloader = []
        self._active_scraper = []
        self._active_error_capturer = []
        self._active_pipeliner = []

        self._request_queue: asyncio.Queue[RequestProxy] = asyncio.Queue()
        self._response_queue: asyncio.Queue[ResponseProxy] = asyncio.Queue()
        self._error_queue: asyncio.Queue[tuple[RequestProxy, Exception]] = asyncio.Queue()
        self._item_queue = asyncio.Queue()

        self._logger = logging.getLogger(f'{__name__}.{self.name}')

        self._download_handler = DownloadHandler(spider=self)

        # Update config to spider self.
        self.__dict__.update(kwargs)

    @property
    def stop(self) -> asyncio.Future:
        return self._stop

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def download_handler(self) -> DownloadHandler:
        return self._download_handler

    async def _start_request(self):
        self.logger.info('Start request to queue.')
        if isinstance(self.seeds, AsyncIterable):
            async for i in self.seeds:
                result = await self.enqueue_request(i)
                if not result:
                    break
            self.logger.info('No more seed make request to queue.')
        else:
            for i in self.seeds:
                result = await self.enqueue_request(i)
                if not result:
                    break
            self.logger.info('No more seed make request to queue.')

    async def enqueue_request(self, url: URL):
        if self._stop.done():
            return False
        await self._request_queue.put(self._make_request(seed=url))
        self.logger.debug(f'Make request with <{url}> and put it to queue.')
        await self.prepare_download()
        return True

    def _make_request(self, seed: URL) -> RequestProxy:
        req = RequestProxy(method=hdrs.METH_GET, url=seed)
        return req

    async def start(self) -> None:
        """
        启动爬虫，并执等待任务完成。

        :return:
        """
        self.logger.info('Start spider.')

        try:
            await spider_started.send(sender=self)

            await self._start_request()
            await asyncio.gather(*self._active_downloader)
            await self.close()
        except Exception as ex:
            self.logger.exception(ex)
            self.stop.set_result('Failure.')

    async def close(self):
        await self.download_handler.close()

        await spider_closed.send(sender=self)

        if not self._stop.done():
            self._stop.set_result('Finished')
        self.logger.info('Spider finish.')

    async def random_delay(self):
        """
        生成随机延迟时间。
        :return:
        """
        delay = random.uniform(self._download_delay * 0.5, self._download_delay * 1.5)
        self.logger.debug(f'Random sleep {delay} seconds.')
        await asyncio.sleep(delay)

    async def prepare_download(self):
        """
        非阻塞生成下载任务。
        :return:
        """
        if len(self._active_downloader) <= self._max_downloader:
            task = asyncio.create_task(self.downloading())
            self._active_downloader.append(task)
            task.add_done_callback(lambda _: self._active_downloader.remove(task))

    async def downloading(self):
        """
        下载。
        通过不断读取 request_queue 队列中的数据，下载成功后将 request 和 response 加入到 response_queue 中
        如果下载失败，则将 request 和 exception 加入到 error_queue 中。
        :return:
        """
        self.logger.info('Start downloader.')
        while not self._request_queue.empty():
            if self._stop.done():
                self.logger.info('stopping downloader.')
                break

            request: RequestProxy = self._request_queue.get_nowait()
            await self.random_delay()
            response = await self.download_handler.downloading(request)
            if isinstance(response, Exception):
                await self._error_queue.put((request, response))
            else:
                await self._response_queue.put(response)
            await self.prepare_parse_task()
        self.logger.info('No more request in request queue.')

    async def prepare_process_error_task(self):
        """
        非阻塞生成异常处理任务。
        :return:
        """
        if len(self._active_error_capturer) < self._max_scraper:
            task = asyncio.create_task(self.process_error())
            self._active_error_capturer.append(task)
            task.add_done_callback(lambda _: self._active_error_capturer.remove(task))

    async def process_error(self):
        """
        从队列获取下载是的异常信息，并处理异常。
        :return:
        """
        self.logger.info('Start error capturer')
        while not self._error_queue.empty():
            request, exception = self._error_queue.get_nowait()
            if self.error_handler:
                await self.error_handler(request, exception)
        self.logger.info('No more error in error queue.')

    async def prepare_parse_task(self):
        """
        非阻塞生成 parse 任务。
        :return:
        """
        if len(self._active_scraper) <= self._max_scraper:
            task = asyncio.create_task(self.process_parse())
            self._active_scraper.append(task)
            task.add_done_callback(lambda _: self._active_scraper.remove(task))

    async def process_parse(self):
        """
        从队列获取 response ，并解析。
        :return:
        """
        self.logger.info('Start scraper.')
        while not self._response_queue.empty():
            response = self._response_queue.get_nowait()
            result = await self.parse(response)
            await self._item_queue.put(result)
            await self.prepare_pipeline_task()
        self.logger.info('No more response in response queue.')

    async def parse(self, response: ResponseProxy) -> Any:
        """
        解析相应内容。
        :param response:
        :return:
        """
        return await self.parser.parse(response)

    async def prepare_pipeline_task(self):
        """
        非阻塞生成 pipeline 的处理任务。
        :return:
        """
        if len(self._active_pipeliner) <= self._max_pipeliner:
            task = asyncio.create_task(self.process_pipeline())
            self._active_pipeliner.append(task)
            task.add_done_callback(lambda _: self._active_pipeliner.remove(task))

    async def process_pipeline(self):
        """
        从队列获取 parse 的结果，并处理 pipeline
        :return:
        """
        self.logger.info('Start pipeline.')
        while not self._item_queue.empty():
            data = self._item_queue.get_nowait()
            if self.pipeline_handler:
                await self.pipeline_handler(data)
            else:
                self.logger.info(data)

        self.logger.info('No more item in item queue.')


class FetchSpider(Spider):
    """"""


class ValidateSpider(Spider):
    """"""

    def __init__(
            self,
            name: str,
            *,
            seeds: AsyncIterable[URL] | Iterable[URL],
            check_urls: list,
            parser_kls: Type[BaseParser] = DefaultParser,
            pipeline_handler: Callable[..., Awaitable] | None = None,
            error_handler: Callable[[RequestProxy, Exception], Awaitable] | None = None,
            stop: asyncio.Future | None = None,
            max_pipeliner=3,
            max_downloader=2,
            max_scraper=5,
            download_delay=1,
            **kwargs
    ):
        """
        验证 Spider.
        :param name:
        :param seeds:
        :param check_urls:
        :param parser_kls:
        :param pipeline_handler:
        :param error_handler:
        :param stop:
        :param max_pipeliner:
        :param max_downloader:
        :param max_scraper:
        :param download_delay:
        :param kwargs:
        """
        self.check_urls = check_urls
        super().__init__(name, seeds=seeds, parser_kls=parser_kls, pipeline_handler=pipeline_handler,
                         error_handler=error_handler, stop=stop, max_pipeliner=max_pipeliner,
                         max_downloader=max_downloader, max_scraper=max_scraper, download_delay=download_delay,
                         **kwargs)

    def _make_request(self, seed: URL) -> RequestProxy:
        if self.check_urls:
            url = random.choice(self.check_urls)
            request = RequestProxy(
                method=hdrs.METH_GET,
                url=url,
                proxy=seed
            )
            self.logger.debug(f'Make request: <{request}>')
            return request
        else:
            raise ValueError('check_urls is empty.')
