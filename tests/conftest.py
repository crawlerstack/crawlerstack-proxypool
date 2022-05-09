"""Test config"""
import asyncio
from datetime import datetime

import pytest
from click.testing import CliRunner
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    create_async_engine)
from sqlalchemy.orm import sessionmaker

from crawlerstack_proxypool import alembic, config
from crawlerstack_proxypool.application import Application
from crawlerstack_proxypool.db import Database
from crawlerstack_proxypool.models import (BaseModel, IpProxyModel,
                                           ProxyStatusModel)


@pytest.fixture()
def cli_runner():
    runner = CliRunner()
    yield runner


@pytest.fixture(scope='session')
def settings():
    yield config.settings


@pytest.fixture()
def application():
    yield Application()


@pytest.fixture()
async def db(migrate) -> Database:
    _db = Database()
    yield _db
    await _db.close()


# @pytest.fixture()
# async def session(settings, db):
#     yield db.session
#     await db.scoped_session.remove()


@pytest.fixture()
async def engine(settings):
    engine: AsyncEngine = create_async_engine(
        # 'mysql+pymysql://root:000000@localhost/proxypool',
        settings.DB_URL,
        echo=True,
    )
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture()
async def session_factory(engine):
    """Session factory fixture"""
    yield sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=True,
        autocommit=False,
        # expire_on_commit=False,
    )


@pytest.fixture()
async def session(migrate, session_factory) -> AsyncSession:
    """Session fixture."""
    async with session_factory() as _session:
        yield _session


@pytest.fixture(autouse=True)
def migrate(settings):
    async def setup():
        _engine: AsyncEngine = create_async_engine(settings.DATABASE)
        async with _engine.begin() as conn:
            await conn.run_sync(BaseModel.metadata.drop_all)
            await conn.run_sync(BaseModel.metadata.create_all)
        await _engine.dispose()

    asyncio.run(setup())
    yield
    # async def tear_down():
    #     _engine: AsyncEngine = create_async_engine(settings.DB_URL)
    #     async with _engine.begin() as conn:
    #         await conn.run_sync(BaseModel.metadata.drop_all)
    #     await _engine.dispose()
    #
    # asyncio.run(tear_down())


@pytest.fixture()
async def init_ip_proxy(session):
    async with session.begin():
        proxies = [
            IpProxyModel(
                id=1,
                ip='127.0.0.1',
                schema='http',
                port='1081'
            ),
            IpProxyModel(
                id=2,
                ip='127.0.0.3',
                schema='http',
                port='6379'
            ),
        ]
        session.add_all(proxies)


@pytest.fixture()
async def init_proxy_status(session, init_ip_proxy):
    async with session.begin():
        proxy = await session.scalar(select(IpProxyModel))
        proxy_statuses = [
            ProxyStatusModel(
                id=1,
                proxy_id=proxy.id,
                name='http',
                alive_count=10,
                update_time=datetime.now()
            ),
            ProxyStatusModel(
                id=2,
                proxy_id=proxy.id,
                name='https',
                alive_count=10,
                update_time=datetime.now()
            ),
            ProxyStatusModel(
                id=3,
                proxy_id=proxy.id,
                name='alibaba',
                alive_count=10,
                update_time=datetime.now()
            ),
        ]
        session.add_all(proxy_statuses)
