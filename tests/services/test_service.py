import pytest

from crawlerstack_proxypool.service import IpProxyService


@pytest.fixture
async def service(db):
    async with db.session as session:
        yield IpProxyService(session)


@pytest.mark.asyncio
async def test_get_all(service, init_ip_proxy):
    result = await service.get_all()
    assert result


@pytest.mark.asyncio
async def test_get_by_id(service, init_ip_proxy):
    result = await service.get_by_id(1)
    assert result.id == 1


@pytest.mark.asyncio
async def test_create(service):
    result = await service.create(ip=1)
    assert result.id


@pytest.mark.asyncio
async def test_update(service, init_ip_proxy):
    obj = await service.get_by_id(1)
    data = '10.0.0.1'
    result = await service.update(pk=obj.id, ip=data)
    assert result.ip == data


@pytest.mark.asyncio
async def test_delete(service, init_ip_proxy):
    before = await service.count()
    await service.delete(1)
    after = await service.count()
    assert after == before - 1
