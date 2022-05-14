import functools
import logging
from asyncio import current_task
from collections.abc import Awaitable, Callable
from inspect import signature
from typing import TypeVar

from dynaconf import Dynaconf
from dynaconf.base import Settings
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    AsyncSessionTransaction,
                                    async_scoped_session, create_async_engine)
from sqlalchemy.future import Connection, Engine
from sqlalchemy.orm import sessionmaker

from crawlerstack_proxypool.config import settings as default_settings
from crawlerstack_proxypool.utils import SingletonMeta

logger = logging.getLogger(__name__)


class Database(metaclass=SingletonMeta):
    """
    example:
        db = Database()
    """

    _engine: AsyncEngine | None = None
    _session_maker = None
    _scoped_session = None
    _settings = None

    def __init__(self, settings: Settings = None):
        if self._settings is None:
            self._settings = settings or default_settings

    @property
    def settings(self) -> Dynaconf:
        """db settings"""
        return self._settings

    @property
    def engine(self) -> AsyncEngine:
        """db engine"""
        if not self._engine:
            self._engine = create_async_engine(
                self.settings.DATABASE,
                # echo=True,
                future=True,
            )
        return self._engine

    @property
    def session_maker(self) -> sessionmaker:
        """session factory"""
        if not self._session_maker:
            self._session_maker = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,  # 取消提交后过期操作，此现象会产生缓存，请注意清理。
            )
        return self._session_maker

    @property
    def scoped_session(self) -> async_scoped_session:
        """scoped session factory"""
        if not self._scoped_session:
            self._scoped_session = async_scoped_session(self.session_maker, scopefunc=current_task)
        return self._scoped_session

    @property
    def session(self):
        """db scoped session"""
        return self.scoped_session()

    async def close(self) -> None:
        """close db"""
        await self.engine.dispose()

    async def __aenter__(self) -> 'Database':
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


RT = TypeVar("RT")


def find_session_idx(func: Callable[..., Awaitable[RT]]) -> int:
    """通过查找方法的 session 参数是否已经传递 session 变量，如果没有，就自动注入"""
    func_params = signature(func).parameters
    try:
        session_args_idx = tuple(func_params).index("session")
    except ValueError:
        raise ValueError(f"Function {func.__qualname__} has no `session` argument") from None

    return session_args_idx


class SessionProvider:
    """
    参考 sqlalchemy.ext.async.session._AsyncSessionContextManager 实现
    可以控制事务的 SessionProvider.
    """

    def __init__(self, auto_commit: bool | None = False):
        """
        SessionProvider
        :param auto_commit: 是否启用事务，自动提交
        """
        self._auto_commit = auto_commit
        self._session: AsyncSession | None = None
        self._tarns: AsyncSessionTransaction | None = None
        self._db = Database()

    def _create_cm(self):
        """Return context manager"""
        return self

    async def __aenter__(self) -> AsyncSession:
        """
        参考 _AsyncSessionContextManager.__enter__.

        :return:
        """
        self._session: AsyncSession = self._db.session
        logging.warning(f'Session: {self._session}')
        if self._auto_commit:
            self._trans = AsyncSessionTransaction(self._session)
            await self._trans.__aenter__()

        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        参考 参考 _AsyncSessionContextManager.__aexit__
        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return:
        """
        if self._auto_commit:
            await self._trans.__aexit__(exc_type, exc_val, exc_tb)
        await self._session.__aexit__(exc_type, exc_val, exc_tb)
        await self._db.scoped_session.remove()  # clean scoped session.

    def __call__(self, func: Callable[..., Awaitable[RT]]) -> Callable[..., Awaitable[RT]]:
        @functools.wraps(func)
        async def inner(*args, **kwargs):
            session_args_idx = find_session_idx(func)
            if "session" in kwargs or session_args_idx < len(args):
                # TODO 如果 session 已经开启事务，并且 nested 为 True ，则自动开启子事务
                # 调用 func 时已经传入 session 参数
                result = await func(*args, **kwargs)
            else:
                # 自动为方法注入 session
                async with self._create_cm() as session:
                    result = await func(*args, session=session, **kwargs)
            return result

        return inner


def session_provider(
        func: Callable[..., Awaitable[RT]] | None = None,
        auto_commit: bool | None = False,
) -> RT:
    """
    使用方法:
    >>>
        @session_provider()
        async def func(session: AsyncSession):
            # 只使用 session 对象
            result = await session.scalar(text('SELECT * from user'))

        async def foo(session: AsyncSession):
            await func()    # 由 session_provider 注入 session ，但不会自动提交
            await func(session) # 不会自动提交，需要手动提交
            async with session.begin(): # 手动开启事务，完成后提交
                await func(session)
    >>>
        @session_provider()
        async def func(session: AsyncSession):
            # 使用 session 对象，并自行管理事务
            async with session.begin():
                await session.scalar(text('SELECT * from user'))

        async def foo(session: AsyncSession):
            await func()    # 由 session_provider 注入 session ， func 方法已经开始事务，会自动提交
            await func(session) # func 方法已经开始事务，会自动提交
            # async with session.begin(): # 会报错，因为外部已经显示开启事务，内部在应该开启子事务
            #     await func(session)
    >>>
        @session_provider(auto_commit=True)
        async def func(session: AsyncSession):
            # 使用 session 对象，并开启自动提交
            result = await session.scalar(text('INSERT INTO user (name, age) VALUES ("foo", 123)'))

        async def foo(session: AsyncSession):
            await func()    # 由 session_provider 自动注入 session ，并自动提交
            await func(session) # 由于显示了 session 对象，所以不会执行自动提交，如果需要请启用子事务。
            async with session.begin(): # 显示传递 session ，并手动开启事务
                await func(session)
    >>>
        async def func(session: AsyncSession):
            result = await session.scalar(text('SELECT * from user'))
        # 方法形式调用
        result = await session_provider(func, auto_commit=True)

    :param func:
    :param auto_commit:
    :return:
    """
    if callable(func):
        return SessionProvider(auto_commit)(func)
    else:
        return SessionProvider(auto_commit)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, _connection_record):
    """
    sqlite 连接适配操作，使其支持外键。

    :param dbapi_connection:
    :param _connection_record:
    :return:
    """

    if isinstance(dbapi_connection, Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
