import json

import pytest

from crawlerstack_proxypool.service import ValidateSpiderService


@pytest.fixture
async def service(db):
    async with db.session as session:
        yield ValidateSpiderService(session)
