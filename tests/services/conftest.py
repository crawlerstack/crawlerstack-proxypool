"""conf test"""
import dataclasses

import pytest


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
