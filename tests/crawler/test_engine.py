"""
Test engine
"""
import asyncio

import pytest

from crawlerstack_proxypool.crawler import ExecuteEngine, Spider
from crawlerstack_proxypool.crawler.downloader import Downloader
from crawlerstack_proxypool.crawler.scraper import Scraper


@pytest.fixture()
async def execute_engine():
    yield ExecuteEngine()


@pytest.fixture()
async def engine_with_spider(mocker, execute_engine):
    execute_engine.open_spider(spider=mocker.MagicMock())
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
    def cb():
        if not execute_engine._closed.done():
            execute_engine._closed.set_result('Closed.')

    event_loop.call_later(0.001, cb)
    if closed:
        execute_engine._closed.set_result('Closed')
    next_request = mocker.patch.object(ExecuteEngine, 'next_request')
    await execute_engine.loop_call(0)
    assert next_request.called == called


@pytest.mark.parametrize(
    'start_requests, should_pass, crawl_called',
    [
        (None, True, False),
        (None, False, False),
        ((i for i in range(1)), True, False),
        ((i for i in range(1)), False, True),
    ]
)
@pytest.mark.asyncio
async def test_next_request(mocker, execute_engine, start_requests, should_pass, crawl_called):
    mocker.patch.object(ExecuteEngine, 'spider_idle')
    mocker.patch.object(ExecuteEngine, 'should_pass', return_value=should_pass)
    crawl = mocker.patch.object(ExecuteEngine, 'crawl')
    execute_engine._start_requests = start_requests
    await execute_engine.next_request()
    assert crawl.called == crawl_called


@pytest.mark.asyncio
async def test_schedule(mocker, engine_with_spider):
    result = asyncio.Future()
    result.set_result(True)
    mocker.patch.object(Downloader, 'enqueue', return_value=result)
    mocker.patch.object(ExecuteEngine, 'next_request')
    mocker.patch.object(Scraper, 'enqueue', return_value=result)

    request = mocker.MagicMock()
    await engine_with_spider._processing_requests_queue.put(request)

    await engine_with_spider.schedule(request)
    assert engine_with_spider._processing_requests_queue.empty()


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
    """
    test spider is idle
    :param mocker:
    :param execute_engine:
    :param downloader_idle:
    :param scraper_idle:
    :param processing_requests_queue_empty:
    :param start_requests:
    :param expect_value:
    :return:
    """
    queue = asyncio.Queue(1)
    if not processing_requests_queue_empty:
        await queue.put(1)

    mocker.patch.object(Downloader, 'idle', return_value=downloader_idle)
    mocker.patch.object(Scraper, 'idle', return_value=scraper_idle)
    execute_engine._processing_requests_queue = queue
    execute_engine._start_requests = start_requests
    result = execute_engine.spider_is_idle()
    assert result == expect_value


@pytest.mark.asyncio
async def test_spider_run(mocker, execute_engine):
    """"""
    mocker.patch.object(asyncio, 'sleep')
    crawl = mocker.patch.object(ExecuteEngine, 'crawl')
    spider = Spider(name='test', start_urls=['https://example.com'])
    execute_engine.open_spider(spider)
    await execute_engine.start()
    crawl.assert_called_once()


@pytest.mark.asyncio
async def test_close(event_loop, execute_engine):
    async def close():
        await asyncio.sleep(0.001)
        await execute_engine.close()

    close_task = event_loop.create_task(close())
    await execute_engine.start()
    await close_task
