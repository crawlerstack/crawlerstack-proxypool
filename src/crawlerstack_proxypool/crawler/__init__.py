"""
实现一个底层抓取工具。
未来这个模块可能会独立成一个项目，所以该模块下的内容应该尽量减少对本项目其他模块的依赖，
使其更加独立。
"""
import dataclasses
from typing import Type

from crawlerstack_proxypool.crawler.engine import ExecuteEngine
from crawlerstack_proxypool.crawler.spider import Spider


@dataclasses.dataclass
class Crawler:
    spider_kls: Type[Spider]
    _engine: ExecuteEngine = dataclasses.field(default_factory=ExecuteEngine, init=False)

    async def crawl(self, **kwargs):
        obj = self.spider_kls(**kwargs)  # noqa
        await self._engine.open_spider(obj)
        await self._engine.start()
