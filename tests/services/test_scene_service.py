"""test scene service"""

import pytest
from httpx import URL

from crawlerstack_proxypool.common.checker import CheckedProxy
from crawlerstack_proxypool.models import SceneProxyModel
from crawlerstack_proxypool.service import IpProxyService, SceneProxyService


@pytest.fixture
async def scene_service(database):
    """service fixture"""
    async with database.session as session:
        yield SceneProxyService(session)


@pytest.fixture
async def ip_proxy_service(database):
    """service fixture"""
    async with database.session as session:
        yield IpProxyService(session)


@pytest.mark.asyncio
async def test_get_by_name(scene_service, init_scene_proxy):
    """test get by name"""
    res = await scene_service.get_by_names('http', 'https')
    assert res


@pytest.mark.parametrize(
    'update_count, exist',
    [
        (8, True),
        (-8, True),
        (-10, False),
        (-12, False),
    ]
)
@pytest.mark.asyncio
async def test_update_proxy_status(scene_service, init_scene_proxy, update_count, exist):
    """test update proxy status"""
    obj = await scene_service.update_proxy_status(1, update_count)
    assert isinstance(obj, SceneProxyModel) == exist


@pytest.mark.parametrize(
    'url, alive, dest, expect_count',
    [
        ('http://1.0.0.0', True, 'https', 2),
        ('http://1.0.0.0', False, 'https', 1),
        ('http://127.0.0.3:6370', True, 'https', 2),
        ('http://127.0.0.3:6370', False, 'https', 1),

        ('http://127.0.0.1:1081', True, 'https', 1),
        ('http://127.0.0.1:1081', False, 'https', 1),
    ]
)
@pytest.mark.asyncio
async def test_save_scene_proxy(session, scene_service, init_scene_proxy, url, alive, dest, expect_count):
    """test save scene proxy"""
    proxy = CheckedProxy(url=URL(url), alive=alive)
    await scene_service.save_scene_proxy(proxy, dest)

    count = await scene_service.count(name=dest)
    assert count == expect_count


@pytest.mark.parametrize(
    'url, dest, expect_value',
    [
        ('http://127.0.0.1:1081', 'https', 9),
        ('http://127.0.0.1:6379', 'https', 0)
    ]
)
@pytest.mark.asyncio
async def test_decrease(session, scene_service, ip_proxy_service, init_scene_proxy, url, dest, expect_value):
    """test decrease"""
    _url = URL(url)
    await scene_service.decrease(_url, dest)
    objs = await ip_proxy_service.get(
        protocol=_url.scheme,
        port=_url.port,
        ip=_url.host,
    )
    if expect_value:
        scene_objs = await scene_service.get(
            proxy_id=objs[0].id,
            name=dest,
        )
        assert expect_value == scene_objs[0].alive_count
    else:
        assert len(objs) == expect_value
