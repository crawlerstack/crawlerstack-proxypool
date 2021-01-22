"""Pipeline"""
from redis import Redis
from scrapy import Item, Spider
from twisted.internet.defer import Deferred
from twisted.internet.threads import deferToThread

from crawlerstack_proxypool.core.base import BaseSpider
from crawlerstack_proxypool.core.items import ProxyUrlItem, SceneItem
from crawlerstack_proxypool.core.queue_name import SceneQueueName
from crawlerstack_proxypool.dao.scene import SceneRedisDao


class BaseRedisPipeline:
    """Base redis pipeline"""
    redis: Redis = None

    def open_spider(self, spider: BaseSpider):
        """Init redis client when open spider"""
        self.redis = Redis.from_url(spider.settings.get('REDIS_URL'), decode_responses=True)

    def process_item(self, item: Item, spider: Spider) -> Deferred:
        """Process item and return defer"""
        return deferToThread(self._process_item, item, spider)

    def _process_item(self, item: Item, spider: Spider) -> Item:    # pragma: no cover
        """Process item"""
        raise NotImplementedError('`_process_item()` must be implemented.')


class RawIpPipeline(BaseRedisPipeline):
    """
    原生代理IP，即刚从网页上抓取过来的。
    原生代理为没有校验的代理 IP ，应存入初级场景中，初级场景包含 HTTP 和 HTTPS ，初级场景任务会校验对应的代理 IP
    """

    def _process_item(self, item: ProxyUrlItem, spider: BaseSpider) -> Item:
        """Set data to redis queue"""
        scene_tasks = spider.settings.get('SCENE_TASKS')
        if isinstance(item, ProxyUrlItem):
            pipe = self.redis.pipeline()
            # 遍历所有场景任务，将 IP 写入场景中
            for scene_task in scene_tasks:
                # 如果场景不包含初级场景，就写入
                if not scene_task.get('upstream'):
                    pipe.sadd(SceneQueueName(scene_task.get("name")).seed, item['url'])
            pipe.execute()
        return item


class ScenePipeline(BaseRedisPipeline):
    """Scene pipeline"""
    def _process_item(self, item: SceneItem, spider: Spider):
        """Set data to dao"""
        if isinstance(item, SceneItem):
            url = item['url']
            scene = item['scene']
            speed = item['speed']
            time = item['time']
            score = item['score']

            dao = SceneRedisDao(conn=self.redis, scene=scene)
            dao.update(url, score, speed, time)
        return item
