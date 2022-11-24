"""Test downloader"""
import pytest

from crawlerstack_proxypool.aio_scrapy.downloader import (Downloader,
                                                          DownloadHandler)
from crawlerstack_proxypool.aio_scrapy.req_resp import RequestProxy
from crawlerstack_proxypool.aio_scrapy.settings import Settings


@pytest.fixture()
async def downloader():
    """downloader fixture"""
    yield Downloader(Settings())


@pytest.fixture()
async def download_handler():
    """download_handler fixture"""
    yield DownloadHandler(Settings())


@pytest.mark.asyncio
async def test_downloader(mocker, downloader, http_url):
    """test download"""
    request = RequestProxy('GET', http_url, verify=False)
    download = mocker.patch.object(DownloadHandler, 'download')
    download_task = await downloader.enqueue(request, mocker.MagicMock())
    await download_task
    assert downloader.queue.empty()
    download.assert_called_once()


@pytest.mark.asyncio
async def test_download_handler(mocker, download_handler, http_url):
    """test download_handler"""
    request = RequestProxy('GET', http_url, verify=False)
    resp = await download_handler.download(request)
    assert resp.status_code == 200
