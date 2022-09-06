"""test repository"""
import inspect

import pytest
from httpx import URL
from sqlalchemy import select

from crawlerstack_proxypool.exceptions import ObjectDoesNotExist
from crawlerstack_proxypool.models import ProxyModel, IpModel, SceneProxyModel
from crawlerstack_proxypool.repositories import SceneProxyRepository
from crawlerstack_proxypool.schema import SceneProxyUpdate


@pytest.fixture
async def scene_proxy_repo(database):
    """scene proxy repo fixture"""
    async with database.session as session:
        yield SceneProxyRepository(session)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'names, protocol, region, limit, offset, expect_value',
    [
        ([], None, None, None, None, 4),
        (['http'], None, None, None, None, 1),
        (['http', 'https'], None, None, None, None, 2),
        ([], 'socks5', None, None, None, 1),
        ([], None, 'CHN', None, None, 3),
        ([], None, None, 2, None, 2),
        ([], None, None, 2, 3, 1),
        (['alibaba'], 'http', None, None, None, 1),
        (['alibaba'], 'abc', None, None, None, 0),
        (['alibaba'], None, 'CHN', None, None, 1),
        (['alibaba'], None, 'xxx', None, None, 0),
        (['alibaba'], 'http', 'USA', None, None, 0),
        (['alibaba'], 'socks5', 'USA', None, None, 1),
        ([], 'socks5', 'USA', None, None, 1),
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


@pytest.mark.parametrize(
    'name, protocol, ip, port, expect_value',
    [
        ('alibaba', 'socks5', '127.0.0.3', '6379', 4),
        ('alibaba', 'socks5', '127.0.0.1', '8080', None),
        ('foo', 'socks5', '127.0.0.3', '6379', ObjectDoesNotExist),

    ]
)
@pytest.mark.asyncio
async def test_update_proxy(session, repo_factory, init_scene, name, protocol, ip, port, expect_value):
    """test update proxy"""
    obj_in = SceneProxyUpdate(
        proxy=URL(f'{protocol}://{ip}:{port}', scheme=protocol),
        name=name
    )

    if inspect.isclass(expect_value):
        with pytest.raises(expect_value):
            async with repo_factory(SceneProxyRepository) as repo:
                await repo.update_proxy(obj_in)
    else:
        async with repo_factory(SceneProxyRepository) as repo:
            await repo.update_proxy(obj_in)

        stmt = select(
            SceneProxyModel
        ).where(
            SceneProxyModel.name == name,
        ).join(
            SceneProxyModel.proxy.and_(
                ProxyModel.protocol == protocol,
                ProxyModel.port == port
            )
        ).join(
            ProxyModel.ip.and_(IpModel.value == ip)
        )

        obj = await session.scalar(stmt)
        if expect_value:
            assert obj.alive_count == expect_value
        else:
            assert obj == expect_value
