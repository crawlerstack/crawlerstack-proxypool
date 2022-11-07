import pytest
from sqlalchemy import func, select

from crawlerstack_proxypool.repositories import ProxyRepository


@pytest.fixture()
async def repo(database):
    """repo fixture"""
    async with database.session as session:
        yield ProxyRepository(session)


@pytest.mark.asyncio
async def test_get_all(repo, init_proxy, session):
    """test get all"""
    objs = await repo.get_all()
    assert objs

    result = await session.scalar(select(func.count()).select_from(repo.model))
    assert len(objs) == result
