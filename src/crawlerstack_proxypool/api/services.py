import logging
import random
from typing import Dict, List, Optional

from twisted.application.service import Service
from twisted.python import components
from twisted.web import resource
from zope.interface import Interface, implementer

from crawlerstack_proxypool.api.resources import DemoResource, RootResource
from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.core import signals
from crawlerstack_proxypool.dao.scene import SceneRedisDao

logger = logging.getLogger(__name__)


class ProxyIP:
    cache: Dict[str, List] = {}  # 单例性质

    def __init__(self, scene: str):
        self.scene = scene
        self.proxies = self.cache.get(self.scene)

    def random(self) -> Optional[str]:
        if not self.proxies:
            self.proxies = self.cache.get(self.scene)
        try:
            proxy_ip = random.choice(self.proxies)
        except IndexError as e:
            logger.warning(f'Scene {self.scene} no proxy to use. Detail: {e}')
            proxy_ip = None
        return proxy_ip

    def delete(self, url) -> None:
        if self.proxies:
            try:
                self.proxies.remove(url)
            except ValueError as e:
                logger.exception(e)

    def reset(self, proxies: List[str]) -> None:
        self.cache.update({self.scene: proxies})
        self.proxies = proxies

    def need_reset(self) -> bool:
        if not self.proxies:
            return True
        else:
            return False


class IProxyIPService(Interface):

    def select():
        """"""

    def update():
        """"""


@implementer(IProxyIPService)
class ProxyIPService(Service):

    def __init__(self, server):
        self.server = server

    def select_from_db(self, scene):
        dao = SceneRedisDao(scene=scene)
        proxies = dao.get_multi(settings.get('CACHE_IP_SIZE'))
        _proxies = []
        _proxies.extend(proxies)
        proxy_ip = ProxyIP(scene)
        proxy_ip.reset(_proxies)

    def select(self, scene):
        proxies = ProxyIP(scene)
        if proxies.need_reset():
            self.select_from_db(scene)
        proxy = proxies.random()
        if proxy:
            return proxy
        else:
            logger.warning(f'Scene {scene} no proxy to use, to reload scene.')
            self.server.signal.send_catch_log(signals.reload_scene_seed, task_names=[scene])

    def update(self, scene, url):
        # 删除缓存库
        proxies = ProxyIP(scene)
        proxies.delete(url)
        # 数据库降分
        dao = SceneRedisDao(scene=scene)
        dao.decrease_score(url)


components.registerAdapter(RootResource, IProxyIPService,
                           resource.IResource)


class IService(Interface):
    def select():
        """"""


@implementer(IService)
class DemoService(Service):

    def select(self):
        return b'select'


components.registerAdapter(DemoResource, IService,
                           resource.IResource)
