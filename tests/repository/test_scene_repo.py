"""test repository"""
import pytest

from crawlerstack_proxypool.repositories import SceneProxyRepository


@pytest.fixture
async def scene_proxy_repo(database):
    """scene proxy repo fixture"""
    async with database.session as session:
        yield SceneProxyRepository(session)


@pytest.mark.asyncio
async def test_get_by_names(scene_proxy_repo, init_scene_proxy):
    """test get by name"""
    res = await scene_proxy_repo.get_by_names('http', 'https')
    assert len(res) == 2
    # used joinedload
    obj = res[0]
    assert obj.ip_proxy


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'name, limit, offset, expect_value',
    [
        (None, None, None, 4),
        ('http', None, None, 1),
        ('alibaba', None, None, 2),
        ('alibaba', 2, None, 2),
        ('alibaba', 1, None, 1),
        ('alibaba', 2, 1, 1),
    ]
)
async def test_get(scene_proxy_repo, init_scene_proxy, name, limit, offset, expect_value):
    """test get"""
    kwargs = {
        'limit': limit,
        'offset': offset,
    }
    if name:
        kwargs.setdefault('name', name)

    res = await scene_proxy_repo.get_with_ip(**kwargs)
    assert len(res) == expect_value
