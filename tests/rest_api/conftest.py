"""conf test"""
# pylint: disable=duplicate-code
from datetime import datetime

import pytest
from sqlalchemy import select

from crawlerstack_proxypool.models import ProxyModel, SceneProxyModel


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
                proxy_id=objs[1].id,
                name='http',
                alive_count=10,
                update_time=datetime.now()
            ),
        ]
        session.add_all(proxy_statuses)
