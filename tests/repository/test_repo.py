"""test repository"""
import pytest
from sqlalchemy import func, select

from crawlerstack_proxypool.db import Database
from crawlerstack_proxypool.exceptions import ObjectDoesNotExist
from crawlerstack_proxypool.repositories import RegionRepository


@pytest.fixture()
async def repo(database: Database):
    """repo fixture"""
    async with database.session as session:
        yield RegionRepository(session)


@pytest.mark.asyncio
async def test_get_all(repo, init_region, session):
    """test get all"""
    objs = await repo.get_all()
    assert objs

    result = await session.scalar(select(func.count()).select_from(repo.model))
    assert len(objs) == result


@pytest.mark.parametrize(
    'limit, offset, expect_value',
    [
        (None, None, 2),
        (10, 0, 2),
        (1, 0, 1),
        (1, 1, 1),
        (10, 1, 1),
        (10, 2, 0),
        (0, 0, 2),
    ]
)
@pytest.mark.asyncio
async def test_get(repo, init_region, session, limit, offset, expect_value):
    """test get"""
    objs = await repo.get(limit=limit, offset=offset)
    assert len(objs) == expect_value


@pytest.mark.asyncio
async def test_get_by_id(repo, init_region):
    """test get by ip"""
    assert await repo.get_by_id(1)


@pytest.mark.asyncio
async def test_get_not_exist(repo):
    """test get not exist"""
    with pytest.raises(ObjectDoesNotExist):
        await repo.get_by_id(1)


@pytest.mark.asyncio
async def test_create(repo):
    """test create"""
    obj = await repo.create(name='China', numeric='156', code='CHN')
    assert obj.id
    count = await repo.session.scalar(select(func.count()).select_from(repo.model))
    assert count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'name, numeric, code, expect_value',
    [
        ('China', '156', 'CHN', 1),
        ('Russian Federation', '643', 'RUS', 3),
    ]
)
async def test_get_or_create(repo, init_region, session, name, numeric, code, expect_value):
    """test get or create"""
    obj = await repo.get_or_create(
        params={
            'code': code
        },
        name=name,
        numeric=numeric,
    )
    assert obj
    assert obj.id == expect_value


@pytest.mark.asyncio
async def test_update(repo, init_region):
    """test update"""
    alpha_3 = 'foo'
    obj = await repo.session.scalar(select(repo.model))
    await repo.update(pk=obj.id, alpha_3=alpha_3)
    result = await repo.session.get(repo.model, 1)
    assert obj.id == result.id
    assert result.alpha_3 == alpha_3


@pytest.mark.asyncio
async def test_delete(repo, init_region):
    """test delete"""
    obj = await repo.session.scalar(select(repo.model))
    before_count = await repo.count()
    await repo.delete(pk=obj.id)
    after_count = await repo.count()
    assert before_count - 1 == after_count
