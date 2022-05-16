"""Test config"""
import asyncio
from datetime import datetime

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
from crawlerstack_proxypool.models import (BaseModel, IpProxyModel,
                                           SceneProxyModel)

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
        echo=True,
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
async def init_ip_proxy(session):
    """初始化 ip_proxy 表的数据"""
    async with session.begin():
        proxies = [
            IpProxyModel(
                ip='127.0.0.1',
                protocol='http',
                port=1081
            ),
            IpProxyModel(
                ip='127.0.0.3',
                protocol='http',
                port=6379
            ),
        ]
        session.add_all(proxies)


@pytest.fixture()
async def init_scene_proxy(session, init_ip_proxy):
    """初始化 scene_proxy 表的数据"""
    async with session.begin():
        result = await session.scalars(select(IpProxyModel))
        objs = result.all()
        proxy_statuses = [
            SceneProxyModel(
                proxy_id=objs[0].id,
                name='http',
                alive_count=10,
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
