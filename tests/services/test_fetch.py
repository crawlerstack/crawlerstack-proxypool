import pytest

from crawlerstack_proxypool.service import FetchService


@pytest.fixture
async def service(db):
    async with db.session as session:
        yield FetchService(session)
