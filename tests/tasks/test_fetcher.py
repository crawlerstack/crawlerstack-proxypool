"""test fetcher"""
import pytest
from httpx import Response

from crawlerstack_proxypool.aio_scrapy.downloader import DownloadHandler
from crawlerstack_proxypool.common import BaseParser
from crawlerstack_proxypool.service import FetchSpiderService
from crawlerstack_proxypool.tasks.fetcher import FetchSpiderTask


class MockExtractor(BaseParser):
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
