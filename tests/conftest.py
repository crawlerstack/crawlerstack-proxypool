"""Test config"""
import asyncio
import contextlib
from datetime import datetime
from typing import Type

import pytest
from click.testing import CliRunner
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    create_async_engine)
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from crawlerstack_proxypool import config
from crawlerstack_proxypool.db import Database
from crawlerstack_proxypool.log import configure_logging
from crawlerstack_proxypool.manage import ProxyPool
from crawlerstack_proxypool.models import (BaseModel,
                                           SceneProxyModel, RegionModel, IpModel, ProxyModel)
from crawlerstack_proxypool.repositories.base import BaseRepository

configure_logging()

API_VERSION = 'v1'


@pytest.fixture()
def cli_runner():
    """cli runner fixture"""
    runner = CliRunner()
    yield runner


@pytest.fixture()
def settings():
    """settings fixture"""
    yield config.settings


@pytest.fixture()
async def database(migrate) -> Database:
    """database fixture"""
    _database = Database()
    yield _database
    await _database.close()


# @pytest.fixture()
# async def session(settings, db):
#     yield db.session
#     await db.scoped_session.remove()


@pytest.fixture()
async def engine(settings):
    """engine fixture"""
    _engine: AsyncEngine = create_async_engine(
        # 'mysql+pymysql://root:000000@localhost/proxypool',
        settings.DATABASE,
        echo=settings.SHOW_TEST_SQL,
    )
    try:
        yield _engine
    finally:
        await _engine.dispose()


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
    """migrate fixture"""

    async def setup():
        """setup"""
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
async def init_region(session):
    async with session.begin():
        regions = [
            RegionModel(
                name='China',
                numeric='156',
                code='CHN',
            ),
            RegionModel(
                name='United States of America',
                numeric='840',
                code='USA',
            )
        ]
        session.add_all(regions)


@pytest.fixture()
async def init_ip(session, init_region):
    async with session.begin():
        ips = [
            IpModel(
                value='127.0.0.1',
                region_id=1,
            ),
            IpModel(
                value='127.0.0.3',
                region_id=2,
            ),
        ]
        session.add_all(ips)


@pytest.fixture()
async def init_proxy(session, init_ip):
    """init proxy"""
    async with session.begin():
        proxies = [
            ProxyModel(
                protocol='http',
                port=1081,
                ip_id=1,
            ),
            ProxyModel(
                protocol='socks5',
                port=6379,
                ip_id=2,
            ),
            ProxyModel(
                protocol='socks5',
                port=8080,
                ip_id=1,
            ),
            ProxyModel(
                protocol='socks5',
                port=9090,
                ip_id=1,
            ),
        ]
        session.add_all(proxies)


@pytest.fixture()
async def init_scene(session, init_proxy):
    """初始化 scene_proxy 表的数据"""
    async with session.begin():
        result = await session.scalars(select(ProxyModel))
        objs = result.all()
        proxy_statuses = [
            SceneProxyModel(
                proxy_id=objs[0].id,
                name='http',
                alive_count=5,
                update_time=datetime.now()
            ),
            SceneProxyModel(
                proxy_id=objs[0].id,
                name='https',
                alive_count=10,
                update_time=datetime.now()
            ),
            SceneProxyModel(
                proxy_id=objs[0].id,
                name='alibaba',
                alive_count=10,
                update_time=datetime.now()
            ),
            SceneProxyModel(
                proxy_id=objs[1].id,
                name='alibaba',
                alive_count=5,
                update_time=datetime.now()
            ),
            SceneProxyModel(
                proxy_id=objs[2].id,
                name='alibaba',
                alive_count=0,
                update_time=datetime.now()
            ),
            SceneProxyModel(
                proxy_id=objs[3].id,
                name='alibaba',
                alive_count=-1,
                update_time=datetime.now()
            ),
        ]
        session.add_all(proxy_statuses)


@pytest.fixture(autouse=True)
async def proxypool(settings):
    """proxypool fixture"""
    _proxypool = ProxyPool(settings)
    await _proxypool.schedule()
    yield _proxypool
    await _proxypool.stop()


@pytest.fixture()
async def rest_api_client(proxypool):
    """rest api client fixture"""
    _client = TestClient(
        proxypool.rest_api.app
    )
    yield _client


@pytest.fixture()
def api_url_factory():
    """api url factory"""

    def factory(api: str):
        return f'/api/{API_VERSION}{api}'

    return factory


@pytest.fixture()
def repo_factory(database):
    """repo factory"""
    @contextlib.asynccontextmanager
    async def factory(repo_kls: Type[BaseRepository]):
        async with database.session as session:
            async with session.begin():
                yield repo_kls(session) # noqa

    return factory
