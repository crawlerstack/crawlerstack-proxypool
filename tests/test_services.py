import inspect
from typing import Iterable, AsyncIterable

import pytest
from yarl import URL

from crawlerstack_proxypool.models import ProxyStatusModel
from crawlerstack_proxypool.repositories import ProxyStatusRepository
from crawlerstack_proxypool.service import ValidateService


class TestProxyStatusRepository:

    @pytest.fixture
    async def proxy_status_repo(self, db):
        async with db.session as session:
            yield ProxyStatusRepository(session)

    @pytest.mark.asyncio
    async def test_get_by_name(self, proxy_status_repo, init_proxy_status):
        res = await proxy_status_repo.get_by_names('http', 'https')


class TestValidateService:
    """"""

    @pytest.fixture
    async def service(self, db):
        async with db.session as session:
            yield ValidateService(session)

    @pytest.mark.parametrize(
        'sources',
        (None, ['https'])
    )
    @pytest.mark.asyncio
    async def test_start_urls(self, mocker, service, sources):
        async def foo():
            for i in range(1):
                yield URL(f'https://example.com/{i}')

        mocker.patch.object(ValidateService, 'get_from_message', return_value=foo())
        mocker.patch.object(ValidateService, 'get_from_repository', return_value=['https://example.com'])
        result = await service.start_urls('https', sources)
        if sources:
            assert isinstance(result, Iterable)
        else:
            assert isinstance(result, AsyncIterable)

    @pytest.mark.asyncio
    async def test_get_from_repository(self, service, init_proxy_status):
        """"""
        result = await service.get_from_repository(['https'])
        assert result
        assert len(result) == 1

    @pytest.mark.parametrize(
        'update_count, exist',
        [
            (8, True),
            (-8, True),
            (-10, False),
            (-12, False),
        ]
    )
    @pytest.mark.asyncio
    async def test_update_proxy_status(self, service, init_proxy_status, update_count, exist):
        obj = await service.update_proxy_status(1, update_count)
        assert isinstance(obj, ProxyStatusModel) == exist

    async def save(self, service):
        """"""
