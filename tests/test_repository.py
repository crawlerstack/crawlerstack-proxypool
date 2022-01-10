import pytest
from sqlalchemy import func, select

from crawlerstack_proxypool.db import Database
from crawlerstack_proxypool.exceptions import ObjectDoesNotExist
from crawlerstack_proxypool.models import IpProxyModel
from crawlerstack_proxypool.repositories import (IpProxyRepository,
                                                 ProxyStatusRepository)


@pytest.fixture()
async def repo(db: Database):
    async with db.session as session:
        yield IpProxyRepository(session)


@pytest.mark.asyncio
async def test_get_all(repo, init_ip_proxy):
    """"""
    res = await repo.get_all()
    assert res


@pytest.mark.asyncio
async def test_get(repo, init_ip_proxy):
    assert await repo.get_by_id(1)


@pytest.mark.asyncio
async def test_get_not_exist(repo):
    with pytest.raises(ObjectDoesNotExist):
        await repo.get_by_id(1)


@pytest.mark.asyncio
async def test_create(repo, db):
    obj = await repo.create(ip='192.168.10.10')
    assert obj.id
    count = await repo.session.scalar(select(func.count()).select_from(IpProxyModel))
    assert count == 1


@pytest.mark.asyncio
async def test_update(repo, init_ip_proxy):
    data = '100.100.100.100'
    obj = await repo.session.scalar(select(IpProxyModel))
    await repo.update(pk=obj.id, ip=data)
    result = await repo.session.get(IpProxyModel, 1)
    assert obj.id == result.id
    assert result.ip == data


@pytest.mark.asyncio
async def test_delete(repo, init_ip_proxy):
    obj = await repo.session.scalar(select(IpProxyModel))
    before_count = await repo.count()
    await repo.delete(pk=obj.id)
    after_count = await repo.count()
    assert before_count - 1 == after_count


class TestProxyStatusRepository:

    @pytest.fixture
    async def proxy_status_repo(self, db):
        async with db.session as session:
            yield ProxyStatusRepository(session)

    @pytest.mark.asyncio
    async def test_get_by_name(self, proxy_status_repo, init_proxy_status):
        res = await proxy_status_repo.get_by_names('http', 'https')
        assert len(res) == 2
        # used joinedload
        obj = res[0]
        assert obj.ip_proxy

    # @pytest.mark.asyncio
    # async def test_get_by_ip(self, proxy_status_service, init_proxy_status):
    #     await proxy_status_service.get_by_name_ip('127.0.0.1')
