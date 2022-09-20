"""test scene service"""
import inspect

import pytest
from httpx import URL
from sqlalchemy import func, select

from crawlerstack_proxypool.common.checker import CheckedProxy
from crawlerstack_proxypool.exceptions import ObjectDoesNotExist
from crawlerstack_proxypool.models import SceneProxyModel
from crawlerstack_proxypool.schema import SceneIpProxy
from crawlerstack_proxypool.service import SceneProxyService


@pytest.fixture
async def scene_service(database):
    """service fixture"""
    async with database.session as session:
        yield SceneProxyService(session)


@pytest.mark.parametrize(
    'pk, name, alive_count, total',
    [
        (3, 'alibaba', 9, 4),
        (4, 'alibaba', None, 3),
        (5, 'alibaba', None, 3),
        (6, 'alibaba', None, 3),
    ]
)
@pytest.mark.asyncio
async def test_update_with_pk(init_scene, service_factory, session, pk, name, alive_count, total):
    async with service_factory(SceneProxyService) as service:
        res = await service.update_with_pk(pk, -1)
        if alive_count:
            assert res.alive_count == alive_count
        else:
            assert res == alive_count
    stmt = select(func.count()).select_from(SceneProxyModel).where(SceneProxyModel.name == name)
    res = await session.scalar(stmt)
    assert res == total


@pytest.mark.parametrize(
    'ip, protocol, port, name, alive, exist, expect_value',
    [
        ('192.168.1.2', 'http', 2222, 'foo', True, True, 7),
        ('192.168.1.2', 'http', 2222, 'foo', False, True, 7),

        ('127.0.0.1', 'http', 2222, 'foo', False, True, 7),

        ('127.0.0.1', 'http', 1081, 'alibaba', False, True, 6),
        ('127.0.0.3', 'socks5', 6379, 'alibaba', False, False, 5),
        ('127.0.0.1', 'socks5', 8080, 'alibaba', False, False, 5),
        ('127.0.0.1', 'socks5', 8080, 'alibaba', True, True, 6),
    ]
)
@pytest.mark.asyncio
async def test_init_proxy(session, init_scene, service_factory, ip, protocol, port, name, alive, exist, expect_value):
    async with service_factory(SceneProxyService) as service:
        obj_in = CheckedProxy(
            url=URL(f'{protocol}://{ip}:{port}'),
            name=name,
            alive=alive,
        )
        res = await service.init_proxy(obj_in)
        assert (res is not None) == exist

    stmt = select(func.count()).select_from(SceneProxyModel)
    count = await session.scalar(stmt)
    assert count == expect_value


@pytest.mark.parametrize(
    'url, dest, expect_value',
    [
        ('http://127.0.0.1:1081', 'https', 4),
        ('http://127.0.0.1:6379', 'https', ObjectDoesNotExist)
    ]
)
@pytest.mark.asyncio
async def test_decrease(session, scene_service,  init_scene, url, dest, expect_value):
    """test decrease"""
    obj_in = SceneIpProxy(url=URL(url), name=dest)
    if inspect.isclass(expect_value) and issubclass(expect_value, Exception):
        with pytest.raises(expect_value):
            obj = await scene_service.decrease(obj_in)
    else:
        obj = await scene_service.decrease(obj_in)

        if expect_value is None:
            assert obj == expect_value
        else:
            obj = await scene_service.get_by_id(obj.id)
            assert obj.alive_count == expect_value
