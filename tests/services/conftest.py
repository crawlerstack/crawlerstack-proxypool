"""conf test"""
import contextlib
import dataclasses
from typing import Type

import pytest

from crawlerstack_proxypool.service import BaseService


@dataclasses.dataclass
class MockMessage:
    """mock message"""
    data: list[list[str] | None] = dataclasses.field(default_factory=list)

    async def pop(self, *_):
        """mock pop"""
        if self.data:
            return self.data.pop()
        return None

    async def add(self, _, data):
        """mock add"""
        self.data.append(data)


@pytest.fixture
def message_factory():
    """message factory"""

    def factory(data: list[list[str] | None] = None) -> MockMessage:
        return MockMessage(data or [])

    return factory


@pytest.fixture()
def service_factory(database):
    """factory"""

    @contextlib.asynccontextmanager
    async def factory(kls: Type[BaseService]):
        async with database.session as session:
            async with session.begin():
                yield kls(session)  # noqa

    return factory
