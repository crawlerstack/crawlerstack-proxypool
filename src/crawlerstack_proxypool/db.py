import logging
from asyncio import current_task

from sqlalchemy import Column, Integer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class CustomsBase:
    id = Column(Integer, primary_key=True)


Base = declarative_base(cls=CustomsBase)


class Database:

    def __init__(self, url: str, echo: bool = False):
        logger.debug('Init database...')
        self._engine = create_async_engine(url=url, future=True, echo=echo)
        self._session_maker = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        self._scoped_session = async_scoped_session(self._session_maker, scopefunc=current_task)

    @property
    def scoped_session(self):
        return self._scoped_session

    @property
    def session(self):
        """
        init current task context-level session
        """
        return self._scoped_session()

    async def create_database(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
