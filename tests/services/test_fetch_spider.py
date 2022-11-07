"""test fetch spider service"""
import pytest
from httpx import URL

from crawlerstack_proxypool.service import FetchSpiderService


@pytest.mark.asyncio
async def test_fetch_spider_service_save(database, message_factory, mocker):
    """test_fetch_spider_service_save"""
    data = [URL('https://example.com')]
    mock_message = message_factory()
    mocker.patch(
        'crawlerstack_proxypool.service.FetchSpiderService.message',
        return_value=mock_message,
        new_callable=mocker.PropertyMock
    )
    async with database.session as session:
        service = FetchSpiderService(session)
        await service.save(data, ['https'])
    assert mock_message.data == data
