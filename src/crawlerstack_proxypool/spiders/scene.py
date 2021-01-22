"""Scene spider"""
import random
from typing import Iterator, Type

from scrapy import Request

from crawlerstack_proxypool.core.base import BaseSpider
from crawlerstack_proxypool.core.checkers import BaseChecker
from crawlerstack_proxypool.core.items import SceneItem
from crawlerstack_proxypool.core.queue_name import SceneQueueName
from crawlerstack_proxypool.core.schemas import SceneTaskSchema


class SceneSpider(BaseSpider):
    """Scene spider"""
    TASK_KEY = 'SCENE_TASKS'
    plugin_namespace = 'crawlerstack_proxypool.spider.checker_driver'
    use_set = True
    task: SceneTaskSchema = None
    TASK_SCHEMA: Type[SceneTaskSchema] = SceneTaskSchema

    checker: BaseChecker = None

    def __init__(self, name=None, **kwargs):
        super().__init__(name=name, **kwargs)
        self.scene_queue_name = SceneQueueName(self.name)

    def setup_plugin(self):
        """Set checker"""
        self.checker = self.load_plugin(self.task.checker_name)

    def random_verification_url(self) -> str:
        """
        if use redis , zhe redis key is `proxy:verify:xxx`
        :return:
        """
        url = ''
        if self.task.verify_urls_from_redis:
            url: str = self.server.srandmember(self.scene_queue_name.verify)
        if not url:
            url = random.choice(self.task.verify_urls)
        return url

    def make_request_from_url(self, url: str) -> Request:
        """Make request from verification url, and set proxy."""
        verification_url = self.random_verification_url()
        self.logger.debug(f'To check proxy: {url} , target: {url}')
        return Request(
            verification_url,
            dont_filter=True,
            meta={'proxy': url, 'scene': True},
            callback=self.parse,
            errback=self.parse_error
        )

    def parse(self, response, **kwargs):
        """parse"""
        request: Request = response.request
        try:
            available = False
            if self.checker.check(response=response, **self.task.checker_rule):
                available = True
            yield self.set_item(request, available)
        # We want to catch all exceptions
        except Exception as ex:  # pylint: disable=broad-except
            self.logger.error(
                f"Check proxy <{request.meta.get('proxy')}> by url <{request.url}> failure. {ex}"
            )
            yield {}

    def parse_error(self, failure) -> Iterator[SceneItem]:
        """parse error"""
        request = failure.request
        proxy = request.meta.get('proxy')
        self.logger.debug(f'Check proxy <{proxy}> was failed, {failure} is raised')
        yield self.set_item(request=request, available=False)

    def set_item(self, request: Request, available: bool) -> SceneItem:
        """
        :param request:
        :param available:
        :return:
        """
        score = -1
        if available:
            score = 1

        return SceneItem(
            url=request.meta.get('proxy'),
            scene=self.name,
            speed=request.meta.get('speed'),
            time=request.meta.get('start'),
            score=score,
        )
