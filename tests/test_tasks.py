import pytest
from httpx import URL, Response

from crawlerstack_proxypool.aio_scrapy.downloader import DownloadHandler
from crawlerstack_proxypool.common import BaseExtractor
from crawlerstack_proxypool.common.checker import CheckedProxy
from crawlerstack_proxypool.service import (FetchSpiderService,
                                            ValidateSpiderService)
from crawlerstack_proxypool.task import FetchSpiderTask, ValidateSpiderTask


class MockExtractor(BaseExtractor):
    """Mock extractor"""

    async def parse(self, response: Response, **kwargs):
        pass


@pytest.mark.asyncio
async def test_fetch_spider_task(mocker):
    """test fetch spider task"""
    data = ['http://127.0.0.1:1080']
    dest = ['http']
    mocker.patch.object(MockExtractor, 'parse', return_value=data)
    download_mocker = mocker.patch.object(DownloadHandler, 'download')
    save_mocker = mocker.patch.object(FetchSpiderService, 'save')
    task = FetchSpiderTask(
        'foo',
        urls=['https://example.com'],
        dest=dest,
        parser_kls=MockExtractor
    )

    await task.start()
    download_mocker.assert_called_once()
    save_mocker.assert_called_once_with(data, dest)


@pytest.mark.asyncio
async def test_validate_spider_task(mocker):
    """test validate spider task"""
    name = 'foo'
    dest = 'bar'
    check_urls = ['https://example.com']
    exist_proxies = ['http://127.0.0.1:1080']
    checked_data = CheckedProxy(url=URL(exist_proxies[0]), alive=True)
    sources = ['http']

    mocker.patch.object(MockExtractor, 'parse', return_value=checked_data)
    download_mocker = mocker.patch.object(DownloadHandler, 'download')
    save_mocker = mocker.patch.object(ValidateSpiderService, 'save')
    mocker.patch.object(ValidateSpiderService, 'start_urls', return_value=exist_proxies)

    task = ValidateSpiderTask(
        name=name,
        dest=dest,
        check_urls=check_urls,
        parser_kls=MockExtractor,
        sources=sources,
    )
    await task.start()

    save_mocker.assert_called_once_with(checked_data, dest)
    download_mocker.assert_called_once()
