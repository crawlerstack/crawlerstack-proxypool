"""
Test engine
"""
import asyncio
import typing

import pytest
from httpx import Response

from crawlerstack_proxypool.aio_scrapy.crawler import Crawler
from crawlerstack_proxypool.aio_scrapy.downloader import Downloader
from crawlerstack_proxypool.aio_scrapy.engine import ExecuteEngine
from crawlerstack_proxypool.aio_scrapy.scraper import Scraper
from crawlerstack_proxypool.aio_scrapy.settings import Settings
from crawlerstack_proxypool.aio_scrapy.spider import Spider


class Foo(Spider):
    """Foo spider"""

    async def parse(self, response: Response) -> typing.Any:
        pass


@pytest.fixture()
def spider_settings():
    """spider settings"""
    return Settings()


@pytest.fixture()
def foo_spider(http_url, spider_settings):
    """foo spider fixture"""
    yield Foo(name='test', start_urls=[http_url], settings=spider_settings)


@pytest.fixture()
async def execute_engine(foo_spider):
    """engine fixture"""
    crawler = Crawler(foo_spider)
    yield ExecuteEngine(crawler)


@pytest.fixture()
async def engine_with_spider(mocker, execute_engine):
    """engine with spider fixture"""
    await execute_engine.open_spider(spider=mocker.MagicMock())
    yield execute_engine
    await execute_engine.close()


@pytest.mark.parametrize(
    'closed, called',
    [
        (True, False),
        (False, True)
    ]
)
@pytest.mark.asyncio
async def test_loop_call(event_loop, mocker, execute_engine, called, closed):
    """
    test loop call
    :param event_loop:
    :param mocker:
    :param execute_engine:
    :param called:
    :param closed:
    :return:
    """

    def callback():
        """callback"""
        if not execute_engine._closed.done():  # pylint: disable=protected-access
            execute_engine._closed.set_result('Closed.')  # pylint: disable=protected-access

    event_loop.call_later(0.001, callback)
    if closed:
        execute_engine._closed.set_result('Closed')  # pylint: disable=protected-access
    next_request = mocker.patch.object(ExecuteEngine, 'next_request')
    await execute_engine.loop_call(0)
    assert next_request.called == called


@pytest.mark.parametrize(
    'start_urls, should_pass, crawl_called',
    [
        (None, True, False),
        (None, False, False),
        ((i for i in range(1)), True, False),
        ((i for i in range(1)), False, True),
    ]
)
@pytest.mark.asyncio
async def test_next_request(mocker, execute_engine, start_urls, should_pass, crawl_called):
    """test next request"""

    async def mock_start_requests():
        """mock start requests"""
        for i in start_urls:
            yield i

    mocker.patch.object(ExecuteEngine, 'spider_idle')
    mocker.patch.object(ExecuteEngine, 'should_pass', return_value=should_pass)
    crawl = mocker.patch.object(ExecuteEngine, 'crawl')
    execute_engine._start_requests = start_urls if start_urls is None else mock_start_requests()  # pylint: disable=protected-access
    await execute_engine.next_request()
    assert crawl.called == crawl_called


@pytest.mark.asyncio
async def test_schedule(mocker, engine_with_spider):
    """test schedule"""
    result = asyncio.Future()
    result.set_result(True)
    mocker.patch.object(Downloader, 'enqueue', return_value=result)
    mocker.patch.object(ExecuteEngine, 'next_request')
    mocker.patch.object(Scraper, 'enqueue', return_value=result)

    request = mocker.MagicMock()
    await engine_with_spider._processing_requests_queue.put(request)  # pylint: disable=protected-access

    await engine_with_spider.schedule(request)
    assert engine_with_spider._processing_requests_queue.empty()  # pylint: disable=protected-access


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'downloader_idle, scraper_idle, processing_requests_queue_empty, start_requests, expect_value',
    [
        (True, True, True, None, True),
        (False, True, True, None, False),

        (True, False, True, None, False),
        (False, False, True, None, False),

        (True, True, False, None, False),
        (False, True, False, None, False),

        (True, False, False, None, False),
        (False, False, False, None, False),

        (True, True, True, object(), False),
        (False, True, True, object(), False),

        (True, False, True, object(), False),
        (False, False, True, object(), False),

        (True, True, False, object(), False),
        (False, True, False, object(), False),

    ]
)
async def test_spider_is_idle(
        mocker,
        execute_engine,
        downloader_idle,
        scraper_idle,
        processing_requests_queue_empty,
        start_requests,
        expect_value,
):
    """test spider is idle"""
    queue = asyncio.Queue(1)
    if not processing_requests_queue_empty:
        await queue.put(1)

    mocker.patch.object(Downloader, 'idle', return_value=downloader_idle)
    mocker.patch.object(Scraper, 'idle', return_value=scraper_idle)
    execute_engine._processing_requests_queue = queue  # pylint: disable=protected-access
    execute_engine._start_requests = start_requests  # pylint: disable=protected-access
    result = execute_engine.spider_is_idle()
    assert result == expect_value


@pytest.mark.asyncio
async def test_open_spider(mocker, foo_spider, execute_engine):
    """test spider run"""
    loop_call = mocker.patch.object(execute_engine, 'loop_call')
    await execute_engine.open_spider(foo_spider)

    loop_call.assert_called_once()


@pytest.mark.asyncio
async def test_close(event_loop, execute_engine):
    """test close"""

    async def close():
        await asyncio.sleep(0.001)
        await execute_engine.close()

    close_task = event_loop.create_task(close())
    await execute_engine.start()
    await close_task


@pytest.mark.asyncio
async def test_spider_run(mocker, execute_engine, foo_spider):
    """test spider run"""
    parse = mocker.patch.object(Foo, 'parse')
    await execute_engine.open_spider(foo_spider)
    await execute_engine.start()
    parse.assert_called_once()
