"""conf test"""
import contextlib
import dataclasses
from datetime import datetime
from typing import Type

import pytest
from sqlalchemy import select

from crawlerstack_proxypool.models import ProxyModel, SceneProxyModel
from crawlerstack_proxypool.service import BaseService


@dataclasses.dataclass
class MockMessage:
    """mock message"""
    data: list[list[str] | None] = dataclasses.field(default_factory=list)

    async def pop(self, *_):
        """mock pop"""
        if self.data:
            return self.data.pop()
        return None

    async def add(self, _, data):
        """mock add"""
        self.data.append(data)


@pytest.fixture
def message_factory():
    """message factory"""

    def factory(data: list[list[str] | None] = None) -> MockMessage:
        return MockMessage(data or [])

    return factory


@pytest.fixture()
def service_factory(database):
    """factory"""

    @contextlib.asynccontextmanager
    async def factory(kls: Type[BaseService]):
        async with database.session as session:
            async with session.begin():
                yield kls(session)  # noqa

    return factory


@pytest.fixture()
async def init_scene(session, init_proxy):
    """初始化 scene_proxy 表的数据"""
    async with session.begin():
        result = await session.scalars(select(ProxyModel))
        objs = result.all()
        proxy_statuses = [
            SceneProxyModel(
                id=1,  # noqa
                proxy_id=objs[0].id,
                name='http',
                alive_count=5,
                update_time=datetime.now()
            ),
            SceneProxyModel(
                id=2,  # noqa
                proxy_id=objs[0].id,
                name='https',
                alive_count=5,
                update_time=datetime.now()
            ),
            SceneProxyModel(
                id=3,  # noqa
                proxy_id=objs[0].id,
                name='alibaba',
                alive_count=10,
                update_time=datetime.now()
            ),
            SceneProxyModel(
                id=4,  # noqa
                proxy_id=objs[1].id,
                name='alibaba',
                alive_count=1,
                update_time=datetime.now()
            ),
            SceneProxyModel(
                id=5,  # noqa
                proxy_id=objs[2].id,
                name='alibaba',
                alive_count=0,
                update_time=datetime.now()
            ),
            SceneProxyModel(
                id=6,  # noqa
                proxy_id=objs[3].id,
                name='alibaba',
                alive_count=-1,
                update_time=datetime.now()
            ),
        ]
        session.add_all(proxy_statuses)
