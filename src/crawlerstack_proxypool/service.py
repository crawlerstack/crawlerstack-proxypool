"""service"""
import dataclasses
import logging
from typing import AsyncIterable, Iterable

from httpx import URL
from sqlalchemy.ext.asyncio import AsyncSession

from crawlerstack_proxypool.common.checker import CheckedProxy
from crawlerstack_proxypool.message import Message
from crawlerstack_proxypool.models import SceneProxyModel
from crawlerstack_proxypool.repositories.base import BaseRepository
from crawlerstack_proxypool.repositories.proxy import ProxyRepository
from crawlerstack_proxypool.repositories.scene import SceneProxyRepository

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

    _proxy_status_repo: SceneProxyRepository = dataclasses.field(default=None, init=False)
    _proxy_repo: ProxyRepository = dataclasses.field(default=None, init=False)

    def __post_init__(self):
        self._proxy_status_repo = SceneProxyRepository(self._session)

    @property
    def repository(self) -> SceneProxyRepository:
        return SceneProxyRepository(self._session)

    @property
    def scene_proxy_repo(self) -> SceneProxyRepository:
        """proxy status repo"""
        return self._proxy_status_repo

    async def get_with_ip(self, limit: int = 10, offset: int = 0, **kwargs):
        """get with ip"""
        return await self.repository.get_with_ip(limit=limit, offset=offset, **kwargs)

    @property
    def proxy_repo(self) -> ProxyRepository:
        """ip proxy repo"""
        if not self._proxy_repo:
            self._proxy_repo = ProxyRepository(self._session)
        return self._proxy_repo

    async def get_by_names(self, *names):
        """get by names"""
        return await self.repository.get_by_names(*names)

    async def update_proxy_status(self, pk: int, update_count: int) -> SceneProxyModel | None:
        """
        更新 ProxyStatusModel 对象的状态。
        如果计算后的 alive_count 值 > 0 将会更新；如果 alive_count <= 0 ，将其删除
        :param pk:
        :param update_count:
        :return:
        """
        # TODO 优化，当 http/https 不可用，直接删除 IpProxy ，级联删除所有关联对象
        proxy_status = await self.scene_proxy_repo.get_by_id(pk)
        alive_count = proxy_status.alive_count + update_count
        if alive_count > 0:
            return await self.scene_proxy_repo.update(
                proxy_status.id,
                alive_count=alive_count,
            )
        # 当计算后的 alive_count 小于0，则删除
        logger.debug('"%s" is dead, so delete it.', proxy_status)
        await self.scene_proxy_repo.delete(proxy_status.id)

    async def save_scene_proxy(self, proxy: CheckedProxy, name: str):
        """
        将校验后的代理保存到数据库中。

        保存时，首先检查 IpProxyModel 中是否存在，如果没有，并且 proxy.alive 为 True，
        则创建 IpProxyModel 和 SceneProxyModel 对象。
        如果有，则判断 SceneProxyModel 是否有，如果没有，并且 proxy.alvie 为 True ，则创建。
            如果 SceneProxyModel 存在，并且计算后的 alive_count > 0 则更新，反之删除 SceneProxyModel。

        :param proxy:
        :param name:
        :return:
        """
        ip_proxy = await self.ip_proxy_repo.get_or_create(
            ip=proxy.url.host,
            port=proxy.url.port,
            protocol=proxy.url.scheme,
        )
        scene_proxy = await self.scene_proxy_repo.get_or_create(
            params={'alive_count': 0},
            name=name,
            proxy_id=ip_proxy.id,
        )
        await self.update_proxy_status(scene_proxy.id, proxy.alive_status)

    async def decrease(self, proxy: URL, name: str):
        """
        请求时的异常处理，此时应该对 proxy 减分。

        对于 http/https 初次校验的，数据库中没有记录，就需要忽略。

        :param name:
        :param proxy:
        :return:
        """
        checked_proxy = CheckedProxy(proxy, alive=False)
        await self.save_scene_proxy(checked_proxy, name=name)


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

    async def start_urls(
            self,
            dest: str,
            sources: list[str] | None = None
    ) -> AsyncIterable[URL] | Iterable[URL]:
        """
        get start_urls.

        if has sources, get urls from db, else get urls from queue.
        :param dest:
        :param sources:
        :return:
        """
        if sources:
            # 返回结果，不能返回生成器对象，要不然会超出 session 范围
            return await self.get_from_repository(sources)
        # 返回生成器对象
        return self.get_from_message(dest)

    async def get_from_repository(self, sources: list[str]) -> list[URL]:
        """
        get urls from repository
        :param sources:
        :return:
        """
        proxies = await self.scene_proxy_repo.get_by_names(*sources)
        logger.debug('Get %d proxy from db.', len(proxies))
        result = []
        for status in proxies:
            proxy = status.ip_proxy
            result.append(
                URL(scheme=proxy.protocol, host=proxy.ip, port=proxy.port)
            )
        if not result:
            logger.debug('No proxy in db, to trigger validate proxy task with "%s"', sources)
            await start_validate_proxy.send(sources=sources)
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

    async def save(self, proxy: CheckedProxy, dest: str):
        """save"""
        return await self.save_scene_proxy(proxy, dest)


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
