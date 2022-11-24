"""
base repository
"""
import dataclasses
import logging
from typing import Generic

from sqlalchemy import delete, func
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.exceptions import ObjectDoesNotExist
from crawlerstack_proxypool.models import ModelT


@dataclasses.dataclass
class BaseRepository(Generic[ModelT]):
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

    async def get_all(self) -> list[ModelT]:
        """
        get all
        :return:
        """
        result: Result = await self.session.execute(select(self.model))
        return result.scalars().all()

    async def get(
            self,
            /,
            limit: int = settings.DEFAULT_PAGE_LIMIT,
            offset: int = 0,
            **kwargs,
    ) -> list[ModelT]:
        """
        条件查找
        :param limit:
        :param offset:
        :param kwargs:
        :return:
        """
        if not limit:
            limit = 10
        if not offset:
            offset = 0

        and_condition = [getattr(self.model, k) == v for k, v in kwargs.items()]
        stmt = select(self.model).filter(*and_condition).limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return result.all()

    async def get_one_or_none(self, /, **kwargs) -> ModelT | None:
        """
        通过条件获取一个对象，如果没有则返回 None
        :param kwargs:
        :return:
        """
        and_condition = [getattr(self.model, k) == v for k, v in kwargs.items()]
        stmt = select(self.model).filter(*and_condition)
        result = await self.session.scalars(stmt)
        return result.one_or_none()

    async def get_or_create(self, /, params: dict = None, **kwargs) -> ModelT:
        """
        根据 kwargs 参数查询对象，如果对象不存在，使用 params 参数更新 kwargs 后创建对象并返回。
        通过 kwargs 参数查询的结果必须只有一个对象。
        :param params:
        :param kwargs:
        :return:
        """
        obj = await self.get_one_or_none(**kwargs)
        logging.debug('get object %s', obj)
        if not obj:
            # 用 params 更新参数，然后创建对象
            kwargs.update(params or {})
            obj = await self.create(**kwargs)

        logging.debug('get or create object %s', obj)
        return obj

    async def get_by_id(self, pk: int) -> ModelT:
        """
        通过 id 查找对象
        :param pk:
        :return:
        """
        result = await self.session.get(self.model, pk)
        if result:
            return result
        raise ObjectDoesNotExist()

    async def create(self, /, **kwargs) -> ModelT:
        """
        创建对象
        :param kwargs:
        :return:
        """
        obj = self.model(**kwargs)
        self.session.add(obj)  # pylint: disable=no-member
        await self.session.flush()
        return obj

    async def update(self, pk: int, **kwargs) -> ModelT:
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

    async def count(
            self,
            **kwargs
    ) -> int:
        """
        获取总和
        :return:
        """
        and_condition = [getattr(self.model, k) == v for k, v in kwargs.items()]
        stmt = select(func.count()).filter(*and_condition).select_from(self.model)
        total = await self.session.scalar(stmt)
        return total
