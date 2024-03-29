"""
Spider
"""
import abc
import inspect
import logging
import typing
from collections.abc import AsyncGenerator, AsyncIterator, Iterator

from httpx import URL, Response

from crawlerstack_proxypool.aio_scrapy.req_resp import RequestProxy
from crawlerstack_proxypool.signals import spider_closed, spider_opened


class Spider(metaclass=abc.ABCMeta):
    """
    Base spider class
    """

    def __init__(
            self,
            *,
            name: str,
            start_urls: list[str] | Iterator[str] | AsyncIterator[str],
            **kwargs,
    ):
        self.name = name
        self.start_urls = start_urls
        for k, v in kwargs.items():
            setattr(self, k, v)

        self.logger = logging.getLogger(self.name)
        # 将 open_spider 方法绑定到 spider 的 spider_opened 信号上
        spider_opened.connect(self.open_spider, sender=self)
        # 将 close_spider 方法绑定到 spider 的 spider_closed 信号上
        spider_closed.connect(self.close_spider, sender=self)

    async def start_requests(self) -> AsyncGenerator[RequestProxy]:
        """
        起始 requests
        :return:
        """
        if inspect.isasyncgen(self.start_urls):
            async for i in self.start_urls:
                yield self._make_request(i)
        else:
            for i in self.start_urls:
                yield self._make_request(i)

    def _make_request(self, url: URL | str) -> RequestProxy:  # noqa
        """
        构建请求
        :param url:
        :return:
        """
        req = RequestProxy(method='GET', url=url)
        return req

    @abc.abstractmethod
    async def parse(self, response: Response) -> typing.Any:
        """
        解析逻辑
        :param response:
        :return:
        """
        raise NotImplementedError()

    async def open_spider(self, **kwargs):
        """open spider"""

    async def close_spider(self, **kwargs):
        """close spider"""
