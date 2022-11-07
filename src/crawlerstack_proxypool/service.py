"""service"""
import dataclasses
import logging
from typing import AsyncIterable, Iterable

from httpx import URL
from sqlalchemy.ext.asyncio import AsyncSession

from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.message import Message
from crawlerstack_proxypool.models import SceneProxyModel
from crawlerstack_proxypool.repositories import (IpRepository, ProxyRepository,
                                                 SceneProxyRepository)
from crawlerstack_proxypool.repositories.base import BaseRepository
from crawlerstack_proxypool.schema import ValidatedProxy, SceneIpProxy, SceneIpProxyStatus
from crawlerstack_proxypool.signals import (start_fetch_proxy,
                                            start_validate_proxy)

logger = logging.getLogger(__name__)


class CRUDMixin:  # noqa
    """
    CRUD mixin
    """

    @property
    def repository(self) -> BaseRepository:
        """Init default repository."""
        raise NotImplementedError()

    async def get(self, /, **kwargs):
        """Get objects."""
        return await self.repository.get(**kwargs)

    async def get_all(self):
        """Get all objects"""
        return await self.repository.get_all()

    async def get_by_id(self, pk: int):
        """
        Get by id.
        :param pk:
        :return:
        """
        return await self.repository.get_by_id(pk)

    async def create(self, /, **kwargs):
        """
        Create object
        :param kwargs:
        :return:
        """
        return await self.repository.create(**kwargs)

    async def update(self, pk: int, **kwargs):
        """
        Update object
        :param pk:
        :param kwargs:
        :return:
        """
        return await self.repository.update(pk, **kwargs)

    async def delete(self, pk: int) -> None:
        """
        Delete object
        :param pk:
        :return:
        """
        await self.repository.delete(pk)

    async def count(
            self,
            **kwargs,
    ) -> int:
        """Count"""
        return await self.repository.count(**kwargs)


@dataclasses.dataclass
class BaseService:
    """Base service"""
    _session: AsyncSession


@dataclasses.dataclass
class SceneProxyService(BaseService, CRUDMixin):
    """Scene proxy service"""

    _scene_repo: SceneProxyRepository = dataclasses.field(default=None, init=False)
    _ip_repo: IpRepository = dataclasses.field(default=None, init=False)
    _proxy_repo: ProxyRepository = dataclasses.field(default=None, init=False)

    def __post_init__(self):
        self._scene_repo = SceneProxyRepository(self._session)

    @property
    def repository(self) -> SceneProxyRepository:
        return SceneProxyRepository(self._session)

    @property
    def ip_repo(self):
        if not self._ip_repo:
            self._ip_repo = IpRepository(self._session)
        return self._ip_repo

    @property
    def proxy_repo(self) -> ProxyRepository:
        """ip proxy repo"""
        if not self._proxy_repo:
            self._proxy_repo = ProxyRepository(self._session)
        return self._proxy_repo

    async def update_with_pk(self, pk: int, update_count: int) -> SceneProxyModel | None:
        """
        更新 ProxyStatusModel 对象的状态。
        如果计算后的 alive_count 值 > 0 将会更新；如果 alive_count <= 0 ，将其删除
        :param pk:
        :param update_count:
        :return:
        """
        # TODO 优化，当 http/https 不可用，直接删除 IpProxy ，级联删除所有关联对象
        proxy_status = await self.repository.get_by_id(pk)
        alive_count = proxy_status.alive_count + update_count
        if alive_count > 0:
            return await self.repository.update(
                proxy_status.id,
                alive_count=alive_count,
            )
        # 当计算后的 alive_count 小于0，则删除
        logger.debug('"%s" is dead, so delete it.', proxy_status)
        await self.repository.delete(proxy_status.id)

    async def get_with_region(
            self,
            /,
            limit: int = settings.DEFAULT_PAGE_LIMIT,
            offset: int = 0,
            names: list[str] = None,
            region: str | None = None,
            protocol: str | None = None,
            port: int | None = None,
            ip: str | None = None,
    ) -> list[SceneIpProxy]:
        objs = await self.repository.get_proxy_with_region(
            limit=limit,
            offset=offset,
            names=names,
            region=region,
            protocol=protocol,
            port=port,
            ip=ip,
        )
        value_objects = []
        for obj in objs:
            protocol = obj.proxy.protocol
            host = obj.proxy.ip.value
            port = obj.proxy.port
            value_objects.append(SceneIpProxy(
                name=obj.name,
                url=URL(f'{protocol}://{host}:{port}'),
            ))
        return value_objects

    async def update_proxy(self, obj_in: SceneIpProxyStatus) -> SceneProxyModel | None:
        return await self.repository.update_proxy(obj_in)

    async def init_proxy(self, proxy: ValidatedProxy) -> list[SceneProxyModel]:
        """
        初始化 proxy 。

        对于不确定 ip, port, protocol 是否存在数据库中时，可以调用该方法。

        :param proxy:
        :return:
        """

        # 获取 ip 地址信息，如果不存在就创建
        ip_obj = await self.ip_repo.get_or_create(
            value=proxy.url.host
        )
        proxy_obj = await self.proxy_repo.get_or_create(
            ip_id=ip_obj.id,
            port=proxy.url.port,
            protocol=proxy.url.scheme,
        )
        models = []
        for name in proxy.dest:
            scene_proxy = await self.repository.get_or_create(
                params={'alive_count': 5},
                name=name,
                proxy_id=proxy_obj.id,
            )

            alive_count = scene_proxy.alive_count + proxy.get_alive_status()

            if alive_count > 0:
                await self.update(scene_proxy.id, alive_count=alive_count)
                models.append(scene_proxy)
            else:
                await self.delete(scene_proxy.id)
        return models

    async def decrease(self, scene_proxy: SceneIpProxy) -> SceneProxyModel | None:
        """
        请求时的异常处理，此时应该对 proxy 减分。

        对于 http/https 初次校验的，数据库中没有记录，就需要忽略。

        :param scene_proxy:
        :return:
        """
        checked_proxy = SceneIpProxyStatus(
            url=scene_proxy.url,
            alive=False,
            name=scene_proxy.name
        )
        return await self.update_proxy(checked_proxy)


@dataclasses.dataclass
class ValidateSpiderService(SceneProxyService):
    """
    验证 spider service
    """

    _message: Message = dataclasses.field(default=Message(), init=False)

    @property
    def message(self):
        """
        message queue
        :return:
        """
        return self._message

    async def get_proxies(
            self,
            original: bool,
            source: str
    ) -> AsyncIterable[URL] | list[URL]:
        """
        get_proxies
        :param original:
        :param source:
        :return:
        """
        if original:
            return self.get_from_message(source)
        return await self.get_from_repository(source)

    async def get_from_repository(self, source: str) -> list[URL]:
        """
        get urls from repository
        :param source:
        :return:
        """
        scene_proxies = await self.repository.get_by_names(source)
        logger.debug('Get %d proxy from db.', len(scene_proxies))
        result = []
        for scene in scene_proxies:
            result.append(
                URL(
                    scheme=scene.proxy.protocol,
                    host=scene.proxy.ip.value,
                    port=scene.proxy.port,
                )
            )
        if not result:
            logger.debug('No proxy in db, to trigger validate proxy task with "%s"', source)
            await start_validate_proxy.send(sources=source)
        return result

    async def get_from_message(self, dest: str):
        """
        从消息队列中获取数据。
        当爬虫从页面抓到数据后，现写入消息队列，然后从消息队列中获取原始的代理 IP ，校验后写入 http/https。
        :param dest:
        :return:
        """
        has_data = False
        name = f'proxypool:{dest}'
        logger.debug('Getting seed from message with "%s"', name)
        while True:
            result = await self.message.pop(name)
            if not result:
                break

            for i in result:
                yield URL(i)
            has_data = True
        if not has_data:
            logger.debug('No seed in message with "%s", to trigger fetch proxy task.', name)
            await start_fetch_proxy.send()


@dataclasses.dataclass
class FetchSpiderService(SceneProxyService):
    """
    Fetch spider service
    """
    _message: Message = dataclasses.field(default=Message(), init=False)

    @property
    def message(self):
        """
        message queue
        :return:
        """
        return self._message

    async def save(self, data: list[URL], dest: list[str]):
        """
        将数据写入到消息队列中。

        :param data:
        :param dest:
        :return:
        """
        for i in data:
            for dest_name in dest:
                await self.message.add(f'proxypool:{dest_name}', str(i))
