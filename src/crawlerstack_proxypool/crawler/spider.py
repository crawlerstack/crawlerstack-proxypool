"""
Spider
"""
import logging
import typing

from httpx import URL, Response

from crawlerstack_proxypool.crawler.req_resp import RequestProxy
from crawlerstack_proxypool.signals import spider_opened, spider_closed


class Spider:
    """
    Base spider class
    """

    def __init__(
            self,
            *,
            name: str,
            start_urls: list[str],
            **kwargs,
    ):
        self.name = name
        self.start_urls = start_urls
        for k, v in kwargs.items():
            setattr(self, k, v)

        self.logger = logging.getLogger(self.name)

        spider_opened.connect(self.open_spider, sender=self)  # 将 open_spider 方法绑定到 spider 的 spider_opened 信号上
        spider_closed.connect(self.close_spider, sender=self)  # 将 close_spider 方法绑定到 spider 的 spider_closed 信号上

    def start_requests(self) -> typing.Iterator[RequestProxy]:
        """
        起始 requests
        :return:
        """
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
