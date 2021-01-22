import logging
from datetime import datetime
from typing import List, Optional

from redis import BlockingConnectionPool, Redis

from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.core.queue_name import SceneQueueName

redis_connect_pool = BlockingConnectionPool.from_url(settings.get('REDIS_URL'), decode_responses=True)


class SceneRedisDao:
    default_score = 5

    def __init__(self, *, conn: Redis = None, scene):
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')
        self.redis = conn or Redis(connection_pool=redis_connect_pool)
        self.scene_queue_name = SceneQueueName(scene)

    def get_score_with_url(self, url):
        return self.redis.zscore(self.scene_queue_name.score, url)

    def update(self, url, score=0, speed=0, time=datetime.now().timestamp()):
        """
        :param url:
        :param score:   pipeline 传过来的检测后的需要加减的分值
        :param speed:
        :param time:
        :return:
        """
        exist_score = self.get_score_with_url(url)
        if exist_score is None:
            # 如果代理不存在，且代理可用，就写入，初始化默认分值
            # 如果代理不存在，且不可用，就 pass
            if score > 0:
                self._save(url, score=self.default_score)
        elif exist_score > 1 and score > 0:
            # 如果已存在代理的分数大于 1 且 score 大于 0
            self._save(url, score, speed, time)
        else:
            self.delete(url)

    def delete(self, url):
        pipe = self.redis.pipeline(True)
        pipe.zrem(self.scene_queue_name.score, url)
        pipe.zrem(self.scene_queue_name.speed, url)
        pipe.zrem(self.scene_queue_name.time, url)
        pipe.execute()

    def _save(self, url, score=5, speed=0, time=datetime.now().timestamp()):
        pipe = self.redis.pipeline(True)
        pipe.zincrby(self.scene_queue_name.score, score, url)
        # 由于速度越小越好，为了能让速度小的结果有高分，需要将其转换成负数
        # 虚度越小，其负数越大，在使用 zrangebyscore 获取的时候，排在前面
        pipe.zadd(self.scene_queue_name.speed, {url: speed})
        pipe.zadd(self.scene_queue_name.time, {url: time})
        pipe.execute()

    def decrease_score(self, url):
        exist_score = self.redis.zscore(self.scene_queue_name.score, url)
        if exist_score is None:
            pass
        elif exist_score > 1:
            pipe = self.redis.pipeline(True)
            pipe.zincrby(self.scene_queue_name.score, -1, url)
            pipe.zadd(self.scene_queue_name.time, {url: datetime.now().timestamp()})
            pipe.execute()
        else:
            self.delete(url)

    def get_multi(self, length: Optional[int] = 100) -> List[str]:
        pipe = self.redis.pipeline(True)
        # zrevrangebyscore 分数从高到低返回
        pipe.zrevrangebyscore(
            name=self.scene_queue_name.score,
            max='+inf',
            min=settings.get('MIN_SCORE'),
            start=0,
            num=length
        )
        # zrangebyscore 分数从低到高返回
        pipe.zrangebyscore(
            name=self.scene_queue_name.speed,
            min='-inf',
            max='+inf',
            start=0,
            num=length
        )
        pipe.zrevrangebyscore(
            name=self.scene_queue_name.time,
            max='+inf',
            min='-inf',
            start=0,
            num=length
        )
        score, speed, time = pipe.execute()
        # ^ 求两个集合的差集， & 求两个集合的交集， | 求两个集合的并集
        # 先求 speed 和 time 的交集，再和 score 求交集
        self.logger.debug(
            f'Get {self.scene_queue_name} data from db. '
            f'Score length : {len(score)}, speed length: {len(speed)}, time length: {len(time)}'
        )
        proxies = set(speed) & set(time) & set(score)
        self.logger.debug(f'Merged proxies length: {len(proxies)}')
        if not proxies:
            proxies = set(speed) & set(time)
        return list(proxies)
