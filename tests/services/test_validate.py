import json

import pytest

from crawlerstack_proxypool.service import ValidateService


@pytest.fixture
async def service(db):
    async with db.session as session:
        yield ValidateService(session)
