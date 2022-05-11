import typing

from httpx import Response

from crawlerstack_proxypool.common import BaseParser
from crawlerstack_proxypool.aio_scrapy.spider import Spider


class BaseSpider(Spider):

    def __init__(
            self,
            *, name: str,
            start_urls: list[str],
            parser_kls: typing.Type[BaseParser],
            **kwargs
    ):
        super().__init__(name=name, start_urls=start_urls, **kwargs)
        self.parser_kls = parser_kls

    async def parse(self, response: Response) -> typing.Any:
        pass


class ValidateSpider(Spider):
    """
    校验的 spider
    """

    def __init__(
            self,
            *,
            name: str,
            start_urls: list[str],
            check_urls: list[str]
    ):
        super().__init__(name=name, start_urls=start_urls)
        self.check_urls = check_urls

    async def parse(self, response: Response) -> typing.Any:
        pass


class FetchSpider(Spider):
    """
    抓取网页的 Spider

    通过配置中的 start url 抓取 IP，并写入目标位置。
    """

    def __init__(self,
                 *,
                 name: str,
                 start_urls: list[str],
                 **kwargs
                 ):
        super().__init__(name=name, start_urls=start_urls, **kwargs)

    async def parse(self, response: Response) -> typing.Any:
        pass
