"""test validate spider service"""
from collections.abc import AsyncIterable, Iterable

import pytest
from httpx import URL

from crawlerstack_proxypool.service import ValidateSpiderService


@pytest.fixture
async def validate_spider_service(database):
    """service fixture"""
    async with database.session as session:
        yield ValidateSpiderService(session)


@pytest.mark.parametrize(
    'sources',
    (None, ['https'])
)
@pytest.mark.asyncio
async def test_start_urls(mocker, validate_spider_service, sources):
    """test start urls"""
    async def mock_get_from_message():
        """foo method"""
        for i in range(1):
            yield URL(f'https://example.com/{i}')

    mocker.patch.object(ValidateSpiderService, 'get_from_message', return_value=mock_get_from_message())
    mocker.patch.object(ValidateSpiderService, 'get_from_repository', return_value=['https://example.com'])
    result = await validate_spider_service.start_urls('https', sources)
    if sources:
        assert isinstance(result, Iterable)
    else:
        assert isinstance(result, AsyncIterable)


@pytest.mark.parametrize(
    'sources, expect_value',
    [
        (['foo'], 'No proxy in db'),
        (['https'], 1)
    ]
)
@pytest.mark.asyncio
async def test_get_from_repository(validate_spider_service, init_scene_proxy, sources, expect_value, caplog):
    """test get from repo"""
    result = await validate_spider_service.get_from_repository(sources)
    if isinstance(expect_value, int):
        assert len(result) == 1
    else:
        assert expect_value in caplog.text


@pytest.mark.parametrize(
    'data, expect_value',
    [
        ([['https://example.com']], 1),
        ([], 'No seed in message with'),
    ]
)
@pytest.mark.asyncio
async def test_get_from_message(validate_spider_service, message_factory, mocker, data, expect_value, caplog):
    """test get from message"""

    mocker.patch(
        'crawlerstack_proxypool.service.ValidateSpiderService.message',
        return_value=message_factory(data),
        new_callable=mocker.PropertyMock
    )
    res_gen = validate_spider_service.get_from_message('foo')
    data = []
    async for i in res_gen:
        data.append(i)
    if isinstance(expect_value, int):
        assert len(data) == expect_value
    else:
        assert expect_value in caplog.text
