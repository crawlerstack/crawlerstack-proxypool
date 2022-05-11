"""Spider"""
import typing
from typing import Generic, Type

from httpx import Response

from crawlerstack_proxypool.aio_scrapy.spider import Spider as ScrapySpider
from crawlerstack_proxypool.common.extractor import ExtractorType


class Spider(ScrapySpider, Generic[ExtractorType]):
    """spider"""

    def __init__(
            self,
            *, name: str,
            start_urls: list[str],
            parser_kls: Type[ExtractorType],
            pipeline: typing.Callable,
            **kwargs
    ):
        super().__init__(name=name, start_urls=start_urls, **kwargs)
        self.parser = parser_kls(self)
        self.pipeline = pipeline

    async def parse(self, response: Response) -> typing.Any:
        result = await self.parser.parse(response)
        await self.pipeline(result)
