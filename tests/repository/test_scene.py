"""test repository"""
import pytest

from crawlerstack_proxypool.repositories import SceneProxyRepository


@pytest.fixture
async def scene_proxy_repo(database):
    """scene proxy repo fixture"""
    async with database.session as session:
        yield SceneProxyRepository(session)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'names, protocol, region, limit, offset, expect_value',
    [
        # ([], None, None, None, None, 4),
        # (['http'], None, None, None, None, 1),
        # (['http', 'https'], None, None, None, None, 2),
        ([], 'http', None, None, None, 1),
        # ([], None, 'CHN', None, None, 1),
        # ([], None, None, 2, None, 2),
        # ([], None, None, 2, 3, 1),
    ]
)
async def test_get(scene_proxy_repo, init_scene, names, protocol, region, limit, offset, expect_value):
    """test get"""
    kwargs = {
        'limit': limit,
        'offset': offset,
    }
    if names:
        kwargs.setdefault('names', names)
    if protocol:
        kwargs.setdefault('protocol', protocol),
    if region:
        kwargs.setdefault('region', region)

    res = await scene_proxy_repo.get_proxy_with_region(**kwargs)
    assert len(res) == expect_value
