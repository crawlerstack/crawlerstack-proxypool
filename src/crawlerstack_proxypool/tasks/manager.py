from typing import TYPE_CHECKING

from twisted.internet import defer
from twisted.internet.defer import Deferred

from crawlerstack_proxypool.tasks.crawlers import (PageCrawlerTask,
                                                   SceneCrawlerTask)
from crawlerstack_proxypool.tasks.seeds import PageSeedTask, SceneSeedTask

if TYPE_CHECKING:
    from crawlerstack_proxypool.server import Server


class TaskManager:

    def __init__(self, server: 'Server'):
        self.proxy_ip_seed_task = PageSeedTask(server.signal)
        self.scene_seed_task = SceneSeedTask(server.signal)

        self.proxy_ip_crawler_task = PageCrawlerTask(server.signal)
        self.scene_task = SceneCrawlerTask(server.signal)

    def start(self) -> Deferred:
        proxy_ip_seed_task_deferred = self.proxy_ip_seed_task.start()
        scene_seed_task_deferred = self.scene_seed_task.start()
        proxy_ip_crawler_task_deferred = self.proxy_ip_crawler_task.start()
        scene_task_deferred = self.scene_task.start()

        return defer.DeferredList([
            proxy_ip_seed_task_deferred,
            scene_seed_task_deferred,
            proxy_ip_crawler_task_deferred,
            scene_task_deferred
        ])

    def stop(self) -> Deferred:
        proxy_ip_seed_task_deferred = self.proxy_ip_seed_task.stop()
        scene_seed_task_deferred = self.scene_seed_task.stop()
        proxy_ip_crawler_task_deferred = self.proxy_ip_crawler_task.stop()
        scene_task_deferred = self.scene_task.stop()
        return defer.DeferredList([
            proxy_ip_seed_task_deferred,
            scene_seed_task_deferred,
            proxy_ip_crawler_task_deferred,
            scene_task_deferred
        ])
