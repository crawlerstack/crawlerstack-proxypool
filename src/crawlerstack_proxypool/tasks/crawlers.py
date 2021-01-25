from typing import Dict, Iterator, Tuple, Type

from scrapy import Spider
from scrapy.signalmanager import SignalManager
from stevedore import ExtensionManager
from stevedore.extension import Extension

from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.core.schemas import PageTaskSchema, SceneTaskSchema
from crawlerstack_proxypool.spiders.scene import SceneSpider
from crawlerstack_proxypool.tasks.base import BaseCrawlerTask


class PageCrawlerTask(BaseCrawlerTask):

    def __init__(self, signal: SignalManager):
        super().__init__(signal)
        self.spider_classes: Dict[str, Spider] = {}
        extension_manager = ExtensionManager(namespace='crawlerstack_proxypool.spider', invoke_on_load=False)
        for extension in extension_manager.extensions:  # type: Extension
            self.spider_classes.setdefault(extension.name, extension.plugin)

        self.spider_tasks = settings.get('SPIDER_TASKS')

    def load_crawl_config(self) -> Iterator[Tuple[Type[Spider], PageTaskSchema]]:
        for name, kls in self.spider_classes.items():
            for spider_task in self.spider_tasks:
                if spider_task.get('enable'):
                    if spider_task.get('task_type') == name:
                        yield kls, PageTaskSchema(**spider_task)


class SceneCrawlerTask(BaseCrawlerTask):

    def __init__(self, signal: SignalManager):
        super().__init__(signal)
        self.spider_cls = SceneSpider
        self.scene_tasks = settings.get('SCENE_TASKS')

    def load_crawl_config(self) -> Iterator[Tuple[Type[Spider], SceneTaskSchema]]:
        for scene_task in self.scene_tasks:
            if scene_task.get('enable'):
                yield self.spider_cls, SceneTaskSchema(**scene_task)
