import dataclasses
import logging
from typing import ClassVar, AsyncIterable, Iterable

from sqlalchemy.ext.asyncio import AsyncSession
from yarl import URL

from crawlerstack_proxypool.common.checker import CheckedProxy
from crawlerstack_proxypool.crawler.req_resp import RequestProxy
from crawlerstack_proxypool.message import Message
from crawlerstack_proxypool.models import ProxyStatusModel
from crawlerstack_proxypool.repositories import (BaseRepository,
                                                 IpProxyRepository,
                                                 ProxyStatusRepository)
from crawlerstack_proxypool.signals import (start_fetch_proxy,
                                            start_validate_proxy)

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class CRUDMixin:  # noqa

    @property
    def repository(self) -> BaseRepository:
        """Init default repository."""
        raise NotImplementedError()

    async def get_all(self):
        return await self.repository.get_all()

    async def get_by_id(self, pk: int):
        return await self.repository.get_by_id(pk)

    async def create(self, /, **kwargs):
        return await self.repository.create(**kwargs)

    async def update(self, pk: int, **kwargs):
        return await self.repository.update(pk, **kwargs)

    async def delete(self, pk: int) -> None:
        await self.repository.delete(pk)

    async def count(self) -> int:
        return await self.repository.count()


@dataclasses.dataclass
class BaseService:
    _session: AsyncSession


class IpProxyService(BaseService, CRUDMixin):

    @property
    def repository(self):
        return IpProxyRepository(self._session)


class ProxyStatusService(BaseService, CRUDMixin):
    @property
    def repository(self):
        return ProxyStatusRepository(self._session)


@dataclasses.dataclass
class ValidateService(BaseService):
    """"""

    _message: Message = dataclasses.field(default=Message(), init=False)
    _proxy_status_repo: ProxyStatusRepository = dataclasses.field(default=None, init=False)
    _ip_proxy_repo: IpProxyRepository = dataclasses.field(default=None, init=False)

    @property
    def message(self):
        return self._message

    @property
    def proxy_status_repo(self) -> ProxyStatusRepository:
        if not self._proxy_status_repo:
            self._proxy_status_repo = ProxyStatusRepository(self._session)
        return self._proxy_status_repo

    @property
    def ip_proxy_repo(self) -> IpProxyRepository:
        if not self._ip_proxy_repo:
            self._ip_proxy_repo = IpProxyRepository(self._session)
        return self._ip_proxy_repo

    async def start_urls(
            self, dest: str,
            sources: list[str] | None = None
    ) -> AsyncIterable[URL] | Iterable[URL]:
        """"""
        if sources:
            # 返回结果，不能返回生成器对象，要不然会超出 session 范围
            return await self.get_from_repository(sources)
        else:
            # 返回生成器对象
            return self.get_from_message(dest)

    async def get_from_repository(self, sources: list[str]) -> list[URL]:
        """"""
        proxies = await self.proxy_status_repo.get_by_names(*sources)
        logger.debug(f'Get {len(proxies)} proxy from db.')
        result = []
        for status in proxies:
            proxy = status.ip_proxy
            result.append(
                URL.build(scheme=proxy.schema, host=proxy.ip, port=proxy.port)
            )
        else:
            logger.debug(f'No proxy in db, to trigger validate proxy task with "{sources}"')
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
        logger.debug(f'Getting seed from message with "{name}"')
        while True:
            result = await self.message.pop(name)
            if not result:
                break

            for i in result:
                yield URL(i)
            has_data = True
        if not has_data:
            logger.debug(f'No seed in message with "{name}", to trigger fetch proxy task.')
            await start_fetch_proxy.send()

    async def update_proxy_status(self, pk: int, update_count: int) -> ProxyStatusModel | None:
        """
        更新 ProxyStatusModel 对象的状态。
        如果计算后的 alive_count 值 > 0 将会更新；如果 alive_count <= 0 ，将其删除
        :param pk:
        :param update_count:
        :return:
        """
        # TODO 优化，当 http/https 不可用，直接删除 IpProxy ，级联删除所有关联对象
        proxy_status = await self.proxy_status_repo.get_by_id(pk)
        alive_count = proxy_status.alive_count + update_count
        if alive_count > 0:
            return await self.proxy_status_repo.update(
                proxy_status.id,
                alive_count=alive_count,
            )
        else:
            # 当计算后的 alive_count 小于0，则删除
            logger.debug(f'{proxy_status}" is dead, so delete it.')
            await self.proxy_status_repo.delete(proxy_status.id)

    async def save(self, proxy: CheckedProxy, dest: str):
        """
        将校验后的代理保存到数据库中。

        保存时，首先检查 IpProxyModel 中是否存在，如果没有，并且 proxy.alive 为 True，
        则创建 IpProxyModel 和 ProxyStatusModel 对象。
        如果有，则判断 ProxyStatusModel 是否有，如果没有，并且 proxy.alvie 为 True ，则创建。
            如果 ProxyStatusModel 存在，并且计算后的 alive_count > 0 则更新，反之删除 ProxyStatusModel。

        :param proxy:
        :param dest:
        :return:
        """
        ip_proxy = await self.ip_proxy_repo.get_or_create(
            ip=proxy.url.host,
            port=proxy.url.port,
            schema=proxy.url.scheme,
        )
        proxy_status = await self.proxy_status_repo.get_or_create(
            params={'alive_count': 0},
            name=dest,
            proxy_id=ip_proxy.id,
        )
        await self.update_proxy_status(proxy_status.id, proxy.alive_status)

    async def error_handler(self, reqeust: RequestProxy, exception: Exception, dest: str):
        """
        请求时的异常处理，此时应该对 proxy 减分。

        对于 http/https 初次校验的，数据库中没有记录，就需要忽略。

        :param dest:
        :param reqeust:
        :param exception:
        :return:
        """

        proxy = reqeust.proxy
        checked_proxy = CheckedProxy(proxy, alive=False)
        await self.save(checked_proxy, dest=dest)


@dataclasses.dataclass
class FetchService(BaseService):
    """"""
    message: ClassVar[Message] = Message()
    dest: list[str]

    async def save(self, data: list[URL]):
        """
        将数据写入到消息队列中。

        :param data:
        :return:
        """
        for i in data:
            for dest_name in self.dest:
                await self.message.add(f'proxypool:{dest_name}', str(i))
