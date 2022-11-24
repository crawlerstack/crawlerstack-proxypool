"""conf test"""
import contextlib
from typing import Type

import pytest

from crawlerstack_proxypool.repositories.base import BaseRepository


@pytest.fixture()
def repo_factory(database):
    """repo factory"""

    @contextlib.asynccontextmanager
    async def factory(repo_kls: Type[BaseRepository]):
        """factory"""
        async with database.session as session:
            async with session.begin():
                yield repo_kls(session)  # noqa

    return factory
