"""
test repository
"""
import pytest
from sqlalchemy import func, select

from crawlerstack_proxypool.db import Database
from crawlerstack_proxypool.exceptions import ObjectDoesNotExist
from crawlerstack_proxypool.models import IpProxyModel
from crawlerstack_proxypool.repositories import (IpProxyRepository,
                                                 ProxyStatusRepository)


@pytest.fixture()
async def repo(db: Database):
    """repo fixture"""
    async with db.session as session:
        yield IpProxyRepository(session)


@pytest.mark.asyncio
async def test_get_all(repo, init_ip_proxy, session):
    """test get all"""
    objs = await repo.get_all()
    assert objs

    result = await session.scalar(select(func.count()).select_from(IpProxyModel))
    assert len(objs) == result


@pytest.mark.asyncio
async def test_get_by_id(repo, init_ip_proxy):
    """test get by ip"""
    assert await repo.get_by_id(1)


@pytest.mark.asyncio
async def test_get_not_exist(repo):
    """test get not exist"""
    with pytest.raises(ObjectDoesNotExist):
        await repo.get_by_id(1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'ip, schema, port, expect_value',
    [
        ('127.0.0.1', 'http', '1081', 1),
        ('127.0.0.1', 'https', '1081', 3),
    ]
)
async def test_get_or_create(repo, init_ip_proxy, session, ip, schema, port, expect_value):
    """test get or create"""
    obj = await repo.get_or_create(
        params={
            'port': port
        },
        ip=ip,
        schema=schema,
    )
    assert obj
    assert obj.id == expect_value


@pytest.mark.asyncio
async def test_create(repo, db):
    """test create"""
    obj = await repo.create(ip='192.168.10.10')
    assert obj.id
    count = await repo.session.scalar(select(func.count()).select_from(IpProxyModel))
    assert count == 1


@pytest.mark.asyncio
async def test_update(repo, init_ip_proxy):
    """test update"""
    data = '100.100.100.100'
    obj = await repo.session.scalar(select(IpProxyModel))
    await repo.update(pk=obj.id, ip=data)
    result = await repo.session.get(IpProxyModel, 1)
    assert obj.id == result.id
    assert result.ip == data


@pytest.mark.asyncio
async def test_delete(repo, init_ip_proxy):
    """test delete"""
    obj = await repo.session.scalar(select(IpProxyModel))
    before_count = await repo.count()
    await repo.delete(pk=obj.id)
    after_count = await repo.count()
    assert before_count - 1 == after_count


class TestProxyStatusRepository:
    """test proxy status repository"""

    @pytest.fixture
    async def proxy_status_repo(self, db):
        """proxy status repo fixture"""
        async with db.session as session:
            yield ProxyStatusRepository(session)

    @pytest.mark.asyncio
    async def test_get_by_name(self, proxy_status_repo, init_proxy_status):
        """test get by name"""
        res = await proxy_status_repo.get_by_names('http', 'https')
        assert len(res) == 2
        # used joinedload
        obj = res[0]
        assert obj.ip_proxy

    # @pytest.mark.asyncio
    # async def test_get_by_ip(self, proxy_status_service, init_proxy_status):
    #     await proxy_status_service.get_by_name_ip('127.0.0.1')
