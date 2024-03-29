"""test database"""
import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Connection

from crawlerstack_proxypool.db import Database


@pytest.mark.asyncio
async def test_database():
    """test database"""
    async with Database() as database1:
        async with Database() as database2:
            assert database1 == database2
            assert database1.engine == database2.engine


@pytest.mark.asyncio
async def test_engine():
    """test engine"""
    async with Database() as database:
        async with database.engine.connect() as connector:
            def get_table_names(conn: Connection):
                inspector = inspect(conn)
                return inspector.get_table_names()

            table_names = await connector.run_sync(get_table_names)

            assert table_names

# async def add_data(session: AsyncSession):
#     obj = IpAddressModel(ip='127.0.0.1')
#     session.add(obj)
#     await session.flush()
#     return obj
#
#
# @session_provider(auto_commit=False)
# async def add_data_with_provider(session: AsyncSession):
#     obj = IpAddressModel(ip='127.0.0.1')
#     session.add(obj)
#     await session.flush()
#
#
# @session_provider(auto_commit=True)
# async def add_data_with_provider_auto_commit(session: AsyncSession):
#     obj = IpAddressModel(ip='127.0.0.1')
#     session.add(obj)
#     await session.flush()
#
#
# @pytest.mark.asyncio
# async def test_add_data(session):
#     obj = await add_data(session)
#     assert obj.id
#
#
# @pytest.mark.parametrize(
#     'foo, pass_session, count',
#     [
#         (add_data_with_provider, True, 0),
#         (add_data_with_provider, False, 0),
#         (add_data_with_provider_auto_commit, True, 0),
#         (add_data_with_provider_auto_commit, False, 1),
#     ]
# )
# @pytest.mark.asyncio
# async def test_add_data_provider(db, session, foo, pass_session, count):
#     if pass_session:
#         async with db.session_maker() as _session:
#             await foo(_session)
#     else:
#         await foo()
#     result = await session.scalar(select(func.count()).select_from(IpAddressModel))
#     assert count == result
#
#
# @pytest.mark.asyncio
# async def test_add_data_provider_error():
#     @session_provider()
#     async def foo():
#         """"""
#
#     with pytest.raises(ValueError):
#         await foo()
#
#
# @pytest.mark.asyncio
# async def test_add_data_call_provider(session):
#     foo = session_provider(add_data)
#     await foo(session)
#     result = await session.scalar(select(func.count()).select_from(IpAddressModel))
#     assert result == 1
