"""Spider"""
import random
import typing
from collections.abc import AsyncIterator, Iterator
from typing import Type

from httpx import URL, Response

from crawlerstack_proxypool.aio_scrapy.req_resp import RequestProxy
from crawlerstack_proxypool.aio_scrapy.spider import Spider as ScrapySpider
from crawlerstack_proxypool.common import ParserType


class Spider(ScrapySpider, typing.Generic[ParserType]):
    """spider"""

    def __init__(
            self,
            *, name: str,
            start_urls: list[str] | Iterator[str] | AsyncIterator[str],
            parser_kls: Type[ParserType],
            pipeline: typing.Callable,
            **kwargs
    ):
        super().__init__(name=name, start_urls=start_urls, **kwargs)
        self.parser = parser_kls(self)
        self.pipeline = pipeline

    async def parse(self, response: Response) -> typing.Any:
        result = await self.parser.parse(response)
        await self.pipeline(result)


class ValidateSpider(Spider):
    """
    校验 spider

    使用配置中的 check_urls 来校验已有的代理IP。
    """

    def __init__(
            self,
            *,
            name: str,
            start_urls: list[str] | Iterator[str] | AsyncIterator[str],
            check_urls: list[str],
            parser_kls: Type[ParserType],
            pipeline: typing.Callable,
            **kwargs
    ):
        """
        :param name:
        :param start_urls:  代理IP
        :param check_urls:  校验URL
        :param parser_kls:
        :param pipeline:
        :param kwargs:
        """
        super().__init__(name=name, start_urls=start_urls, parser_kls=parser_kls, pipeline=pipeline, **kwargs)
        self.check_urls = check_urls

    def random_check_url(self) -> str:
        """随机选择一个URL"""
        return random.choice(self.check_urls)

    def _make_request(self, url: URL | str) -> RequestProxy:
        """
        构建 request

        随机选择一个校验 url，然后使用代理IP访问该地址。
        :param url:
        :return:
        """
        req = RequestProxy(
            method='GET',
            url=self.random_check_url(),
            proxy=url
        )
        return req
