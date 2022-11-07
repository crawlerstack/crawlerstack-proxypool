"""test scene"""
import pytest
from sqlalchemy import select

from crawlerstack_proxypool.models import IpModel, ProxyModel, SceneProxyModel


def test_get_proxy(rest_api_client, api_url_factory, init_scene):
    """test scene get"""
    api = api_url_factory('/scenes')
    response = rest_api_client.get(api, params={'name': 'http'})
    assert response.status_code == 200
    assert response.json()
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_decrease_proxy(rest_api_client, api_url_factory, init_scene, session):
    """test put"""
    api = api_url_factory('/scenes/decrease')
    host = '127.0.0.1'
    protocol = 'http'
    port = 1081
    name = 'http'
    response = rest_api_client.put(api, json={
        'url': f'{protocol}://{host}:{port}',
        'name': name,
    })

    assert response.status_code == 200

    stmt = select(SceneProxyModel).where(
        SceneProxyModel.name == name,
    ).join(
        SceneProxyModel.proxy.and_(
            ProxyModel.protocol == protocol,
            ProxyModel.port == port,
        )
    ).join(
        ProxyModel.ip.and_(IpModel.value == host)
    )

    obj = await session.scalar(stmt)

    assert obj.alive_count == 4
