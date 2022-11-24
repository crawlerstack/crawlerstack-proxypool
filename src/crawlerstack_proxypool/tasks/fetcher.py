"""fetcher"""
import dataclasses
from typing import Type

from httpx import URL
from sqlalchemy.ext.asyncio import AsyncSession

from crawlerstack_proxypool.aio_scrapy.crawler import Crawler
from crawlerstack_proxypool.common import BaseParser
from crawlerstack_proxypool.db import session_provider
from crawlerstack_proxypool.service import FetchSpiderService
from crawlerstack_proxypool.spiders import Spider


@dataclasses.dataclass
class FetchSpiderTask:
    """
    Spider fetcher task
    """
    name: str
    urls: list[str]
    dest: list[str]
    parser_kls: Type[BaseParser] | None = None

    async def start_urls(self):
        """start urls"""
        for url in self.urls:
            yield URL(url)

    @session_provider(auto_commit=True)
    async def save(self, proxy: list[URL], session: AsyncSession):
        """save"""
        service = FetchSpiderService(session)
        await service.save(proxy, self.dest)

    async def start(self):
        """start task"""
        crawler = Crawler(Spider)
        await crawler.crawl(
            name=self.name,
            start_urls=self.start_urls(),
            parser_kls=self.parser_kls,
            pipeline=self.save,
            dest=self.dest,
        )
