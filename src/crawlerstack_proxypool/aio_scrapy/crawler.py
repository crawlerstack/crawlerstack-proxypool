"""
实现一个底层抓取工具。
未来这个模块可能会独立成一个项目，所以该模块下的内容应该尽量减少对本项目其他模块的依赖，
使其更加独立。
"""
import dataclasses
from typing import Type

from crawlerstack_proxypool.aio_scrapy.engine import ExecuteEngine
from crawlerstack_proxypool.aio_scrapy.settings import Settings
from crawlerstack_proxypool.aio_scrapy.spider import Spider


@dataclasses.dataclass
class Crawler:
    """
    Crawler
    """
    spider_kls: Type[Spider]
    settings: Settings = Settings()
    _engine: ExecuteEngine = None

    def __post_init__(self):
        self._engine = ExecuteEngine(self)

    @property
    def engine(self):
        """engine"""
        return self._engine

    async def crawl(self, **kwargs):
        """
        crawl
        :param kwargs:
        :return:
        """
        kwargs.setdefault('settings', self.settings)
        obj = self.spider_kls(**kwargs)  # noqa
        await self.engine.open_spider(obj)
        await self.engine.start()
