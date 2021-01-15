"""Base"""
from typing import Any, Optional, Type, Iterable

from crawlerstack_proxypool.core.parsers import BaseParser
from scrapy import Spider
from scrapy.crawler import Crawler
from scrapy.http import Response
from stevedore import DriverManager

from crawlerstack_proxypool.core.items import ProxyUrlItem
from crawlerstack_proxypool.core.schemas import (BaseTaskSchema,
                                                 SpiderTaskSchema)
from crawlerstack_proxypool.core.spiders import RedisSpider


class BaseSpider(RedisSpider):
    """Base spider"""

    plugin_namespace = 'crawlerstack_proxypool.parser'
    TASK_KEY = 'DEMO'

    task: BaseTaskSchema = None
    TASK_SCHEMA: Type[BaseTaskSchema]

    def __init__(self, *, name=None, **kwargs):
        super().__init__(name, **kwargs)
        if self.task is None:
            raise Exception(f'Spider {self.name} no task config!')

        self.logger.info(f'Init spider: {name}, task config: {self.task.json()}')

    def _set_crawler(self, crawler: Crawler) -> None:
        super()._set_crawler(crawler)
        self.setup_task()
        self.setup_plugin()

    def setup_task(self):
        """set task"""
        if self.task is None:
            tasks = self.settings.getdict(self.TASK_KEY)
            for task in tasks:
                if task.get('name') == self.name:
                    self.task = self.TASK_SCHEMA(**task)

    def setup_plugin(self):
        """You should imp it, to set up plugin"""
        raise NotImplementedError

    def load_plugin(self, name: str, namespace: Optional[str] = None) -> Any:
        """Load plugin from namespace"""
        return DriverManager(
            namespace=namespace or self.plugin_namespace,
            name=name,
            invoke_on_load=True,
            invoke_kwds={'spider': self}
        ).driver


class BaseParserSpider(BaseSpider):
    """
    Loaded parser's spider
    """
    TASK_KEY = 'SPIDER_TASKS'
    parser: BaseParser
    task: SpiderTaskSchema = None
    TASK_SCHEMA: Type[SpiderTaskSchema] = SpiderTaskSchema

    def setup_plugin(self) -> None:
        self.parser = self.load_plugin(self.task.name)

    def parse(self, response: Response, **kwargs) -> Iterable[ProxyUrlItem]:
        """Parse response"""
        try:
            items = self.parser.parse(response=response, **self.task.parser_rule)
            for item in items:
                yield ProxyUrlItem(url=f'http://{item}')
                yield ProxyUrlItem(url=f'https://{item}')
        except TypeError as ex:
            self.logger.error(ex)
