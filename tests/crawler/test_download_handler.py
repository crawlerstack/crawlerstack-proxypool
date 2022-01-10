import pytest
from aiohttp import ClientSession
from yarl import URL

from crawlerstack_proxypool.crawler.download_handler import DownloadHandler
from crawlerstack_proxypool.crawler.req_resp import RequestProxy, ResponseProxy


@pytest.mark.asyncio
async def test_downloading(mocker):
    resp_mocker = mocker.AsyncMock()
    resp_mocker.headers = None
    mocker.patch.object(ClientSession, '_request', return_value=resp_mocker)
    handler = DownloadHandler(mocker.AsyncMock())
    try:
        req = RequestProxy('GET', URL('https://example.com'))
        result = await handler.downloading(req)
        assert isinstance(result, ResponseProxy)
    finally:
        await handler.close()
