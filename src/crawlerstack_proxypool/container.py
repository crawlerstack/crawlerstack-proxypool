"""
Global Container, provide singleton instance or some instance factory.
"""
import asyncio
import functools
from collections.abc import Callable, Coroutine

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.repositories import IpProxyRepository

from crawlerstack_proxypool.db import Database
from crawlerstack_proxypool.service import IpProxyService


class Dependency:

    @classmethod
    def factory(cls):
        return cls()


class Container(containers.DeclarativeContainer):
    """
    Container
    """

    __self__ = providers.Self()

    event_loop = providers.Resource(asyncio.get_running_loop)
    job_scheduler = providers.Singleton(AsyncIOScheduler, event_loop=event_loop)
    # db = providers.Singleton(Database, db_url=settings.DB_URL)
    db = providers.Factory(Database, url=settings.DB_URL)
    ip_proxy_repository = providers.Factory(IpProxyRepository, session=db.provided.session)
    ip_proxy_service = providers.Factory(IpProxyService, repostory=ip_proxy_repository)


@inject
def scoping_session(db=Provide[Container.db]):
    def decorator(func: Callable[..., Coroutine]):
        @functools.wraps(func)
        async def _wrapper(*args, **kwargs):
            try:
                await func(*args, **kwargs)
            finally:
                await db.provided.scoped_session.remove()

        return _wrapper

    return decorator
