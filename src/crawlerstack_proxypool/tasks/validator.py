"""
Task
"""
import dataclasses
import logging
from typing import Type

from sqlalchemy.ext.asyncio import AsyncSession

from crawlerstack_proxypool.aio_scrapy.crawler import Crawler
from crawlerstack_proxypool.common import BaseParser
from crawlerstack_proxypool.common.validator import ValidatedProxy
from crawlerstack_proxypool.db import session_provider
from crawlerstack_proxypool.service import ValidateSpiderService
from crawlerstack_proxypool.spiders import ValidateSpider

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class ValidateSpiderTask:
    """Validate spider task"""
    name: str
    check_urls: list[str]
    original: bool
    source: str
    dest: list[str]
    parser_kls: Type[BaseParser]

    @session_provider(auto_commit=True)
    async def start_urls(self, session: AsyncSession):
        """
        :param session:
        :return:
        """
        service = ValidateSpiderService(session)
        return await service.get_proxies(self.original, self.source)

    @session_provider(auto_commit=True)
    async def save(self, proxy: ValidatedProxy, session: AsyncSession):
        """
        不需要将 service = ValidateService(session) 提取出来。因为 save 任务传递到
        ValidateSpider 会放到一个 task 中运行，使用 session_provider 自动管理该 task 中的 session 生命周期。
        :param proxy:
        :param session:
        :return:
        """
        service = ValidateSpiderService(session)
        proxy.name = self.dest
        await service.init_proxy(proxy)

    async def start(self):
        """start task"""
        seeds = await self.start_urls()
        crawler = Crawler(ValidateSpider)
        await crawler.crawl(
            name=self.name,
            source=self.source,
            dest=self.dest,
            start_urls=seeds,
            check_urls=self.check_urls,
            parser_kls=self.parser_kls,
            pipeline=self.save
        )
