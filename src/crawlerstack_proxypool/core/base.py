"""Base Spiders"""
from typing import Any, Iterable, Optional, Type

from scrapy import Request
from scrapy.crawler import Crawler
from scrapy.http import Response
from scrapy_splash import SplashRequest
from stevedore import DriverManager

from crawlerstack_proxypool.core.items import ProxyUrlItem
from crawlerstack_proxypool.core.parsers import BaseParser
from crawlerstack_proxypool.core.schemas import (BaseTaskSchema,
                                                 SpiderTaskSchema)
from crawlerstack_proxypool.core.spiders import RedisSpider
from crawlerstack_proxypool.utils.constants import QUEUE_PREFIX


class BaseSpider(RedisSpider):
    """Base spider"""
    TASK_KEY = 'DEMO'
    plugin_namespace: str = None
    TASK_SCHEMA: Type[BaseTaskSchema]

    def __init__(self, name=None, **kwargs):
        self.task: Optional[BaseTaskSchema] = None
        super().__init__(name, **kwargs)

        self.logger.info(f'Init spider: {name}.')

    def _set_crawler(self, crawler: Crawler) -> None:
        super()._set_crawler(crawler)
        self.setup_task()
        self.setup_plugin()

    def setup_task(self):
        """set task use self.TASK_SCHEMA"""
        if not self.task:
            tasks = self.settings.getlist(self.TASK_KEY)
            for task in tasks:
                if task.get('name') == self.name and task.get('enable'):
                    self.task = self.TASK_SCHEMA(**task)
        if not self.task:
            raise ValueError('No task config.')
        self.logger.debug(f'Load task to spider. Detail: {self.task.dict()}')

    def setup_plugin(self):  # pragma: no cover
        """You should imp it, to set up plugin"""
        raise NotImplementedError

    def load_plugin(self, name: str, namespace: Optional[str] = None) -> Any:
        """Load plugin from namespace"""
        if namespace or self.plugin_namespace:
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
    plugin_namespace = 'crawlerstack_proxypool.spider.parsers_driver'
    TASK_KEY = 'SPIDER_TASKS'
    parser: BaseParser = None

    TASK_SCHEMA: Type[SpiderTaskSchema] = SpiderTaskSchema

    def setup_plugin(self) -> None:
        self.parser = self.load_plugin(self.task.parser_name)

    def parse(self, response: Response, **kwargs) -> Iterable[ProxyUrlItem]:
        """Parse response"""
        try:
            items = self.parser.parse(response=response, **self.task.parser_rule)
            for item in items:
                yield ProxyUrlItem(url=f'http://{item}')
                yield ProxyUrlItem(url=f'https://{item}')
        except TypeError as ex:
            self.logger.error(ex)


class BaseProxyIPSpider(BaseParserSpider):
    """
    聚合功能，从 Redis 中获取数据
    """

    def __init__(self, name=None, **kwargs):
        super().__init__(name=name, **kwargs)
        self.redis_key = f'{QUEUE_PREFIX}:spider:{name}:seed'


class BaseAjaxSpider(BaseProxyIPSpider):
    """Use splash access page"""

    def make_request_from_url(self, url: str) -> Request:
        """Note: this method will override scrapy `make_request_from_url()`"""
        return SplashRequest(url, dont_filter=True, args={'wait': 0.5, 'timeout': 10})


class BaseGfwSpider(BaseProxyIPSpider):
    """
    Gfw spider
    Use ProxyMiddleware set gfw proxy to access gfw page
    """
    gfw = True


class BaseGfwAjaxSpider(BaseGfwSpider, BaseAjaxSpider):
    """Gfw and ajax"""
