from typing import List

from scrapy.signalmanager import SignalManager

from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.core import signals
from crawlerstack_proxypool.core.queue_name import (PageQueueName,
                                                    SceneQueueName)
from crawlerstack_proxypool.core.schemas import PageTaskSchema, SceneTaskSchema
from crawlerstack_proxypool.tasks.base import BaseSeedTask


class PageSeedTask(BaseSeedTask):
    task_key = 'SPIDER_TASKS'
    _interval_ratio = 60  # 1 minute.
    time_window = settings.get('PROXYIP_TIME_WINDOW') or 60 * 5
    task_schema = PageTaskSchema

    def __init__(self, signal: SignalManager):
        super().__init__(signal)
        self._signal.connect(self.load_tasks, signals.reload_spider_seed)

    def load_seed(self, task_config: PageTaskSchema) -> None:
        name = task_config.name
        resource = task_config.resource
        if isinstance(resource, str):
            urls = eval(resource)
        else:
            urls = resource
        queue_name = str(PageQueueName(name).seed)
        self.client.sadd(PageQueueName(name).seed, *urls)
        self.logger.info(f'Loaded url from <{name}>  to queue <{queue_name}> .')


class SceneSeedTask(BaseSeedTask):
    task_key = 'SCENE_TASKS'
    time_window = settings.get('SCENE_TIME_WINDOW') or 60 * 2

    task_schema = SceneTaskSchema

    def __init__(self, signal: SignalManager):
        super().__init__(signal)
        self._signal.connect(self.load_tasks, signals.reload_scene_seed)

    def load_seed(self, task_config: SceneTaskSchema) -> None:
        """
        加载爬虫所需要的代理IP
        从场景的分数队列中查出所有代理 IP，
            如果数量 < 100 就加载上游任务。
            然后将查到的 IP 写入场景的 seed 队列中
        :param task_config:
        :return:
        """
        task_name = task_config.name
        scene_queue_name = SceneQueueName(task_name)
        # 从场景的 score 队列中查出所有 IP
        pipe = self.client.pipeline(True)
        pipe.zrangebyscore(scene_queue_name.score, '-inf', '+inf', withscores=True)
        pipe.zrangebyscore(scene_queue_name.speed, '-inf', '+inf')
        pipe.zrangebyscore(scene_queue_name.time, '-inf', '+inf')
        score, speed, time = pipe.execute()  # type: List
        filter_score = []
        # 由于存在 score 的分值 <= 0 ，因此在这一步清理掉。防止无用 IP 重复循环
        for i, s in score:
            if s < 0:
                speed.remove(i)
                time.remove(i)
            else:
                filter_score.append(i)
        proxies = list(set(filter_score) | set(speed) | set(time))
        self.logger.info(
            f'Got {self.task_key} <{task_name}> seed from {scene_queue_name.score}, '
            f'proxies length: {len(proxies)}'
        )
        # 如果数量 < 100 加载上游任务
        if len(proxies) < 100:
            seeds = self.load_upstream_seed(task_config)
            proxies.extend(seeds)
        # 将查到的数据写入 seed 队列
        self.logger.debug(f'Save {self.task_key} <{task_name}> seed to {scene_queue_name.seed}')
        if proxies:
            self.client.sadd(scene_queue_name.seed, *proxies)

    def load_upstream_seed(self, task_config: SceneTaskSchema) -> List:
        """
        加载上游 IP
        :param task_config:
        :return:
        """
        seeds = []
        task_name = task_config.name
        self.logger.info(f'{self.task_key} <{task_name}> scene seed is lake, start upstream seed.')
        upstream = task_config.upstream
        if upstream:
            need_reload_upstream_task_name = []
            for u in upstream:
                scene_name = SceneQueueName(u)
                proxies = self.client.zrevrangebyscore(scene_name.score, '+inf', '-inf')
                seeds.extend(proxies)
                self.logger.info(
                    f'{self.task_key} <{task_name}> scene upstream seed {u} '
                    f'from {scene_name.score}, proxies length: {len(proxies)}'
                )
                if len(proxies) < 100:
                    # 如果上游 IP 较少，则需要重新加载上游任务
                    need_reload_upstream_task_name.append(u)
            if need_reload_upstream_task_name:
                self.logger.info(
                    f'{self.task_key} <{task_name}> scene upstream <{need_reload_upstream_task_name}> '
                    f'seed are lake, send signal to reload upstream task seed.'
                )
                self._signal.send_catch_log(signals.reload_scene_seed, task_names=need_reload_upstream_task_name)
        else:
            self.logger.info(
                f'{self.task_key} <{task_name}> scene no upstream, '
                f'send signal to reload spider task seed.'
            )
            self._signal.send_catch_log(signals.reload_spider_seed)
        return seeds
