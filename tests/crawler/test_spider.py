import asyncio

import pytest
from aiohttp import ClientSession
from yarl import URL

from crawlerstack_proxypool.crawler.download_handler import DownloadHandler
from crawlerstack_proxypool.crawler.req_resp import RequestProxy
from crawlerstack_proxypool.crawler.spider import Spider


@pytest.mark.parametrize(
    'async_iterable',
    [True, False]
)
@pytest.mark.asyncio
async def test__start_request(mocker, async_iterable):
    seeds = [URL('https://example.com')]
    if async_iterable:
        async def foo():
            yield URL('https://example.com')

        seeds = foo()
    prepare_download_mocker = mocker.patch.object(Spider, 'prepare_download')
    spider = Spider('foo', seeds=seeds)
    try:
        await spider._start_request()

        prepare_download_mocker.assert_called_once()
        assert spider._request_queue.qsize() == 1
    finally:
        """"""
        await spider.close()


@pytest.mark.parametrize(
    'stop',
    [True, False]
)
@pytest.mark.asyncio
async def test__enqueue_request(mocker, stop):
    future = asyncio.Future()
    if future:
        future.set_result(True)
    prepare_download_mocker = mocker.patch.object(Spider, 'prepare_download')
    spider = Spider('foo', seeds=[], stop=future)
    try:
        result = await spider.enqueue_request(URL('https://example.com'))

        if future:
            assert not result
        else:
            prepare_download_mocker.assert_called_once()
            assert spider._request_queue.qsize() == 1
            assert result
    finally:
        await spider.close()


@pytest.mark.asyncio
async def test_prepare_download(mocker):
    downloading_mocker = mocker.patch.object(Spider, 'downloading')
    spider = Spider('foo', seeds=[])
    try:
        await spider.prepare_download()
        downloading_mocker.assert_called_once()
    finally:
        await spider.close()


@pytest.mark.parametrize(
    'download_result, spider_stop, resp_queue_size, err_queue_size',
    [
        (object, False, 1, 0),
        (object, True, 0, 0),
        (Exception(), False, 0, 1),
        (Exception(), True, 0, 0),
    ]
)
@pytest.mark.asyncio
async def test_downloading(mocker, download_result, spider_stop, resp_queue_size, err_queue_size):
    """"""
    handler_downloading = mocker.patch.object(DownloadHandler, 'downloading', return_value=download_result)
    mocker.patch.object(Spider, 'prepare_parse_task')
    mocker.patch.object(Spider, 'random_delay')
    stop = asyncio.Future()
    if spider_stop:
        stop.set_result('Finish.')
    spider = Spider('foo', seeds=[], stop=stop)
    try:
        await spider._request_queue.put(RequestProxy(method='GET', url=URL('https://example.com')))
        await spider.downloading()
        if not spider_stop:
            handler_downloading.assert_called_once()
        assert spider._response_queue.qsize() == resp_queue_size
        assert spider._error_queue.qsize() == err_queue_size
    finally:
        await spider.close()
