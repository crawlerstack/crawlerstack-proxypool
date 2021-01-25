from crawlerstack_proxypool.tasks.crawlers import (PageCrawlerTask,
                                                   SceneCrawlerTask)
from crawlerstack_proxypool.tasks.seeds import PageSeedTask, SceneSeedTask


class BaseTask:

    def __init__(self, server):
        self.server = server


class SeedTask(BaseTask):

    def create_proxy_ip_task(self):
        return PageSeedTask(self.server)

    def create_scene_task(self):
        return SceneSeedTask(self.server)


class CrawlerTask(BaseTask):

    def create_proxy_ip_task(self):
        return PageCrawlerTask(self.server)

    def create_scene_task(self):
        return SceneCrawlerTask(self.server)


class PageTask(BaseTask):

    def create_seed_task(self):
        return PageSeedTask(self.server)

    def create_crawler_task(self):
        return PageCrawlerTask(self.server)


class SceneTask(BaseTask):

    def create_seed_task(self):
        return SceneSeedTask(self.server)

    def create_crawler_task(self):
        return SceneCrawlerTask(self.server)
