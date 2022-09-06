"""test scene"""
import pytest
from sqlalchemy import select

from crawlerstack_proxypool.models import SceneProxyModel, ProxyModel


def test_get(rest_api_client, api_url_factory, init_scene_proxy):
    """test scene get"""
    api = api_url_factory('/scenes')
    response = rest_api_client.get(api, params={'name': 'http'})
    assert response.status_code == 200
    assert response.json()


@pytest.mark.asyncio
async def test_put(rest_api_client, api_url_factory, init_scene_proxy, session):
    """test put"""
    api = api_url_factory('/scenes/decrease')
    host = '127.0.0.1'
    protocol = 'http'
    port = 1081
    name = 'https'
    response = rest_api_client.put(api, json={
        'proxy': f'{protocol}://{host}:{port}',
        'name': name,
    })

    assert response.status_code == 200

    stmt = select(ProxyModel).filter(
        ProxyModel.protocol == protocol,
        ProxyModel.port == port,
        ProxyModel.ip.value == host,
    )
    ip_proxy_obj = await session.scalar(stmt)

    stmt = select(SceneProxyModel).filter(
        SceneProxyModel.name == 'https',
        SceneProxyModel.proxy_id == ip_proxy_obj.id,
    )
    scene_obj = await session.scalar(stmt)
    assert scene_obj.alive_count == 9
