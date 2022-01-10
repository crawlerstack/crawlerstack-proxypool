import pytest
from aiohttp import ClientResponse
from yarl import URL

from crawlerstack_proxypool.crawler.req_resp import ResponseProxy


@pytest.mark.asyncio
async def test_response_proxy(mocker, event_loop):
    mocker.patch.object(ClientResponse, 'text', return_value='foo')
    resp = ClientResponse(
        'GET',
        URL('https://example.com'),
        writer=mocker.MagicMock(),
        continue100=mocker.MagicMock(),
        timer=mocker.MagicMock(),
        request_info=mocker.MagicMock(),
        traces=[],
        loop=event_loop,
        session=mocker.MagicMock()
    )
    result = await ResponseProxy.from_client_response(resp, mocker.MagicMock())
    assert result.text == 'foo'
