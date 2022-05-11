import pytest

from crawlerstack_proxypool.service import FetchSpiderService


@pytest.fixture
async def service(db):
    async with db.session as session:
        yield FetchSpiderService(session)
