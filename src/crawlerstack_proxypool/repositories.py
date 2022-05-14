"""
repository
"""
import dataclasses
from typing import Generic

from sqlalchemy import delete, func
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from crawlerstack_proxypool import models
from crawlerstack_proxypool.exceptions import ObjectDoesNotExist
from crawlerstack_proxypool.models import ModelType, ProxyStatusModel


@dataclasses.dataclass
class BaseRepository(Generic[ModelType]):
    """
    仓储对象基类
    """
    session: AsyncSession

    @property
    def model(self):
        """
        对象模型
        :return:
        """
        raise NotImplementedError()

    async def get_all(self) -> list[ModelType]:
        """
        get all
        :return:
        """
        result: Result = await self.session.execute(select(self.model))
        return result.scalars().all()

    async def get(self, /, **kwargs) -> list[ModelType]:
        """
        条件查找
        :param kwargs:
        :return:
        """
        and_condition = [getattr(self.model, k) == v for k, v in kwargs.items()]
        stmt = select(self.model).filter(*and_condition)
        result = await self.session.scalars(stmt)
        return result.all()

    async def get_one_or_none(self, /, **kwargs) -> ModelType | None:
        """
        通过条件获取一个对象，如果没有则返回 None
        :param kwargs:
        :return:
        """
        and_condition = [getattr(self.model, k) == v for k, v in kwargs.items()]
        stmt = select(self.model).filter(*and_condition)
        result = await self.session.scalars(stmt)
        return result.one_or_none()

    async def get_or_create(self, /, params: dict = None, **kwargs) -> ModelType:
        """
        根据 kwargs 参数查询对象，如果对象不存在，使用 params 参数更新 kwargs 后创建对象并返回。
        通过 kwargs 参数查询的结果必须只有一个对象。
        :param params:
        :param kwargs:
        :return:
        """
        obj = await self.get_one_or_none(**kwargs)
        if not obj:
            # 用 params 更新参数，然后创建对象
            kwargs.update(params or {})
            obj = await self.create(**kwargs)
        return obj

    async def get_by_id(self, pk: int) -> ModelType:
        """
        通过 id 查找对象
        :param pk:
        :return:
        """
        result = await self.session.get(self.model, pk)
        if result:
            return result
        raise ObjectDoesNotExist()

    async def create(self, /, **kwargs) -> ModelType:
        """
        创建对象
        :param kwargs:
        :return:
        """
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update(self, pk: int, **kwargs) -> ModelType:
        """
        更新对象
        :param pk:
        :param kwargs:
        :return:
        """
        obj = await self.get_by_id(pk)
        for k, v in kwargs.items():
            setattr(obj, k, v)
        await self.session.flush()
        return obj

    async def delete(self, pk: int) -> None:
        """
        删除对象
        :param pk:
        :return:
        """
        stmt = delete(self.model).where(self.model.id == pk)
        await self.session.execute(stmt)

    async def count(self) -> int:
        """
        获取总和
        :return:
        """
        stmt = select(func.count()).select_from(self.model)
        total = await self.session.scalar(stmt)
        return total


class IpProxyRepository(BaseRepository[models.IpProxyModel]):
    """
    Ip 代理对象
    """

    @property
    def model(self):
        return models.IpProxyModel

    async def get(
            self,
            /,
            usage: str = None,
            limit: int = None,
            **kwargs,
    ) -> list[ModelType]:
        """
        根据条件获取
        :param usage:
        :param limit:
        :param kwargs:  Obj 的基本属性
        :return:
        """
        and_condition = [getattr(self.model, k) == v for k, v in kwargs.items()]
        stmt = select(self.model).filter(*and_condition)
        if usage:
            # 通过 name 过滤，
            # 同时根据 ProxyStatusModel 的 alive_count 和 update_time 倒序返回
            stmt = stmt.join(
                self.model.proxy_status.and_(ProxyStatusModel.name == usage)
            ).order_by(
                ProxyStatusModel.alive_count.desc(),
                ProxyStatusModel.update_time.desc(),
            )
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.scalars(stmt)
        return result.all()

    async def get_by_uri(self, ip: str, port: int, schema: str):
        """
        通过 uri 获取对象
        :param ip:
        :param port:
        :param schema:
        :return:
        """
        return self.get_one_or_none(ip=ip, port=port, schema=schema)


class ProxyStatusRepository(BaseRepository[ProxyStatusModel]):
    """
    代理状态
    """

    @property
    def model(self):
        return ProxyStatusModel

    async def get_by_ip_proxy_and_name(self, name: str, proxy_id: int) -> ProxyStatusModel:
        """
        通过 ip 或 名称获取
        :param name:
        :param proxy_id:
        :return:
        """
        result = await self.get_one_or_none(name=name, proxy_id=proxy_id)
        return result

    async def get_by_names(self, *names) -> list[ProxyStatusModel]:
        """"""
        # 如果 ProxyStatusModel 没有数据，会提示 ProxyStatusModel.ip_proxy
        # 不存在
        stmt = select(self.model).filter(
            self.model.name.in_(names)
        ).options(
            joinedload(self.model.ip_proxy)
        )
        result = await self.session.scalars(stmt)
        objs = result.all()
        return objs
