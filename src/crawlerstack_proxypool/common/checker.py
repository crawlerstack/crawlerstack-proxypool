import asyncio
import dataclasses
import random
from typing import TypeVar

from httpx import URL

from crawlerstack_proxypool.common.parser import BaseParser, ParserKwargs
from crawlerstack_proxypool.crawler.downloader import DownloadHandler
from crawlerstack_proxypool.crawler.req_resp import RequestProxy, ResponseProxy
from crawlerstack_proxypool.crawler.spider import Spider
from crawlerstack_proxypool.signals import spider_closed, spider_started


@dataclasses.dataclass
class CheckedProxy:
    url: URL
    alive: bool
    alive_status: int = dataclasses.field(default=None)

    def __post_init__(self):
        if self.alive:
            self.alive_status = 1
        else:
            self.alive_status = -1


class BaseChecker(BaseParser):

    async def parse(self, response: ResponseProxy, **kwargs):
        return await self.check(response)

    async def check(self, response: ResponseProxy) -> CheckedProxy:
        raise NotImplementedError()


_CheckerType = TypeVar('_CheckerType', bound=BaseChecker)


@dataclasses.dataclass
class KeywordCheckKwargs(ParserKwargs):
    keywords: list = dataclasses.field(default_factory=list)
    any: bool = False


class KeywordChecker(BaseChecker):
    """
    关键词校验。
    """
    KWARGS_KLS = KeywordCheckKwargs

    async def check(self, response: ResponseProxy) -> CheckedProxy:
        alive = False
        if response.ok:
            if self.check_keywords(response.text):
                alive = True

        return CheckedProxy(url=response.request.proxy, alive=alive)

    def check_keywords(self, text: str) -> bool:
        checked = []
        for keyword in self.kwargs.keywords:
            if keyword in text:
                checked.append(True)
            else:
                checked.append(False)
        if self.kwargs.any:
            return any(checked)
        else:
            return all(checked)


@dataclasses.dataclass
class AnonymousKwargs(ParserKwargs):
    """
    严格模式。
    """
    strict: bool = False


class AnonymousChecker(BaseChecker):
    """
    根据 request 中的 proxy 和 response 信息，检查
    proxy 是否可用
    """
    KWARGS_KLS = AnonymousKwargs

    def __init__(self, spider: Spider):
        """"""
        super().__init__(spider)

        self._download_handler = DownloadHandler(self.spider)
        self._public_ip = ''
        self._refresh_ip_task: asyncio.Task | None = None
        spider_started.connect(self.spider_start, sender=self.spider)
        spider_closed.connect(self.spider_closed, sender=self.spider)

    async def spider_start(self, **_kwargs):
        loop = asyncio.get_running_loop()
        self._refresh_ip_task = loop.create_task(self.refresh_public_ip())

    async def spider_closed(self, **_kwargs):
        """"""
        self._refresh_ip_task.cancel()
        await self._download_handler.close()

    async def refresh_public_ip(self):
        while not self.spider.stop.done():
            await self.get_public_ip()
            delay = random.randint(10, 20)
            await asyncio.sleep(delay)

    async def get_public_ip(self):
        request = RequestProxy(method='GET', url=URL('https://httpbin.iclouds.work/ip'))
        # response: "{"origin": "100.247.100.254"}"
        # response: "{"origin": "139.227.236.141, 123.13.247.40"}"
        response = await self._download_handler.downloading(request)
        self._public_ip = response.json.get('origin')
        self.spider.logger.debug(f'Refresh public ip: "{self._public_ip}"')

    async def check(self, response: ResponseProxy):
        """
        检查本地公网 IP 是否在响应中。
        如果使用严格模式，还会检查配置的代理是否在响应中。
        :param response:
        :return:
        """
        if not self._public_ip:
            await self.get_public_ip()
        alive = False
        proxy = response.request.proxy
        if response.ok:
            if self._public_ip not in response.text:
                if self.kwargs.strict and proxy.host in response.text:
                    alive = True
                else:
                    alive = True
        return CheckedProxy(url=proxy, alive=alive)
